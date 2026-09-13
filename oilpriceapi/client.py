"""
OilPriceAPI Client

Main client class for interacting with OilPriceAPI.
"""

import logging
import os
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import httpx

if TYPE_CHECKING:
    from .visualization import PriceVisualizer

logger = logging.getLogger(__name__)

from ._body import decode_json_body
from ._subscriptions_common import unwrap_data
from ._url import resolve_api_url
from .exceptions import (
    ConfigurationError,
    OilPriceAPIError,
    error_from_exception,
    error_from_response,
)
from .models import DataConnectorPrice, MarketBrief
from .resources.alerts import AlertsResource
from .resources.analysis import AnalysisResource
from .resources.analytics import AnalyticsResource
from .resources.bunker_fuels import BunkerFuelsResource
from .resources.commodities import CommoditiesResource
from .resources.data_quality import DataQualityResource
from .resources.data_sources import DataSourcesResource
from .resources.demo import DemoResource
from .resources.diesel import DieselResource
from .resources.drilling import DrillingIntelligenceResource
from .resources.ei import EnergyIntelligenceResource
from .resources.forecasts import ForecastsResource
from .resources.futures import FuturesResource
from .resources.historical import HistoricalResource
from .resources.prices import PricesResource
from .resources.rig_counts import RigCountsResource
from .resources.storage import StorageResource
from .resources.subscriptions import SubscriptionsResource
from .resources.webhooks import WebhooksResource
from .resources.well_production import WellProductionResource
from .retry import (
    RetryStrategy,
    mark_ambiguous_write,
    validated_base_url,
    validated_max_retries,
    validated_timeout,
)


class OilPriceAPI:
    """Main synchronous client for OilPriceAPI.

    Thread Safety: The underlying httpx.Client is thread-safe and can be used
    from multiple threads. However, you should not modify client attributes
    (like headers) after initialization when using from multiple threads.

    Resource Management: Always use context managers (with statement) or
    explicitly call close() to ensure proper cleanup of network resources.
    Do not rely on __del__ for cleanup as it is non-deterministic.

    Args:
        api_key: API key for authentication. If not provided, uses OILPRICEAPI_KEY env var.
        base_url: Base URL for API. Defaults to production.
        timeout: Request timeout in seconds. Defaults to 30.
        max_retries: Total request ATTEMPTS, not retries after the first.
            Defaults to 3. Must be at least 1; pass 1 for a single attempt with
            no retries. Anything less, or a non-int, raises ConfigurationError
            rather than being silently replaced by the default.
        retry_on: Status codes to retry on. Defaults to [429, 500, 502, 503, 504].
            An explicit empty list is honoured and disables status-code retries.

    Retry safety: a non-idempotent method (POST, PATCH) is sent exactly ONCE.
    A timeout, a transport error or a 5xx is an ambiguous outcome — the server
    may have committed the write before the response was lost — so replaying it
    could create a duplicate. Idempotent methods (GET, HEAD, OPTIONS, TRACE,
    PUT, DELETE) still retry as before, and a 429 still retries any method
    because it is an outright refusal. Pass ``idempotent=True`` to ``request()``
    to opt a specific write back into retrying.

    Example:
        >>> # Recommended: Use context manager for automatic cleanup
        >>> with OilPriceAPI() as client:
        ...     price = client.prices.get("BRENT_CRUDE_USD")
        ...     print(f"Brent: ${price.value:.2f}")

        >>> # Or explicitly manage lifecycle
        >>> client = OilPriceAPI()
        >>> try:
        ...     price = client.prices.get("BRENT_CRUDE_USD")
        ... finally:
        ...     client.close()
    """

    DEFAULT_BASE_URL = "https://api.oilpriceapi.com"
    DEFAULT_TIMEOUT = 30
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_CODES = [429, 500, 502, 503, 504]

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        retry_on: Optional[List[int]] = None,
        headers: Optional[Dict[str, str]] = None,
        app_url: Optional[str] = None,
        app_name: Optional[str] = None,
        enable_telemetry: bool = False,
    ):
        # Get API key from parameter or environment
        self.api_key = api_key or os.environ.get("OILPRICEAPI_KEY")
        if not self.api_key:
            logger.error("API key not provided - client initialization failed")
            raise ConfigurationError(
                "API key required. Set OILPRICEAPI_KEY environment variable or pass api_key parameter."
            )

        # Configuration
        # Explicit None checks, not `or`, on every one of these four lines.
        # #115 fixed the two below and left these two, so `timeout=0` silently
        # became 30 and `base_url=""` silently became production (#120).
        self.base_url = (
            self.DEFAULT_BASE_URL if base_url is None else validated_base_url(base_url)
        )
        self.timeout = self.DEFAULT_TIMEOUT if timeout is None else validated_timeout(timeout)
        # max_retries=0 and retry_on=[] used to be discarded the same way (#104).
        self.max_retries = (
            self.DEFAULT_MAX_RETRIES if max_retries is None else validated_max_retries(max_retries)
        )
        self.retry_on = (
            list(self.DEFAULT_RETRY_CODES) if retry_on is None else list(retry_on)
        )

        # Initialize retry strategy
        self._retry_strategy = RetryStrategy(max_retries=self.max_retries, retry_on=self.retry_on)

        logger.debug(
            f"Initialized OilPriceAPI client: base_url={self.base_url}, "
            f"timeout={self.timeout}s, max_retries={self.max_retries}"
        )

        # Store telemetry settings
        self.app_url = app_url
        self.app_name = app_name

        # Build headers
        import sys

        from .version import SDK_NAME, SDK_VERSION

        python_version = (
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"{SDK_NAME}/{SDK_VERSION} python/{python_version}",
            "X-SDK-Name": SDK_NAME,
            "X-SDK-Version": SDK_VERSION,
            "X-SDK-Language": "python",
            "X-Client-Type": "sdk",
        }

        # Add optional usage-attribution headers.
        if self.app_url:
            self.headers["X-App-URL"] = self.app_url
        if self.app_name:
            self.headers["X-App-Name"] = self.app_name

        if headers:
            self.headers.update(headers)

        # Create HTTP client
        self._client = httpx.Client(
            base_url=self.base_url,
            headers=self.headers,
            timeout=self.timeout,
            follow_redirects=True,
        )

        # Initialize resources
        self.prices = PricesResource(self)
        self.historical = HistoricalResource(self)
        self.diesel = DieselResource(self)
        self.alerts = AlertsResource(self)
        self.commodities = CommoditiesResource(self)
        self.futures = FuturesResource(self)
        self.storage = StorageResource(self)
        self.rig_counts = RigCountsResource(self)
        self.bunker_fuels = BunkerFuelsResource(self)
        self.analytics = AnalyticsResource(self)
        self.analysis = AnalysisResource(self)
        self.forecasts = ForecastsResource(self)
        self.data_quality = DataQualityResource(self)
        self.drilling = DrillingIntelligenceResource(self)
        # US well production aggregates + per-well beta data (#50).
        self.well_production = WellProductionResource(self)
        self.ei = EnergyIntelligenceResource(self)
        self.webhooks = WebhooksResource(self)
        self.data_sources = DataSourcesResource(self)
        # Agent watch subscriptions + event polling (#3245 Phase 2).
        self.subscriptions = SubscriptionsResource(self)
        # Public, no-auth demo endpoints (/v1/demo/*).
        self.demo = DemoResource(self)

        # Initialize visualization (optional)
        self.viz: Optional["PriceVisualizer"]
        try:
            from .visualization import PriceVisualizer

            self.viz = PriceVisualizer(self)
        except ImportError:
            self.viz = None

        # Initialize telemetry (opt-in, disabled by default)
        from .telemetry import Telemetry

        self._telemetry = Telemetry(enabled=enable_telemetry)

    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        idempotent: Optional[bool] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Make HTTP request to API.

        Warning: This method uses blocking time.sleep() for retries.
        For async/await applications, use AsyncOilPriceAPI instead.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path
            params: Query parameters
            json_data: JSON body data
            timeout: Request timeout in seconds. If None, uses client's default timeout.
            idempotent: Assert that repeating this request is safe. Without it,
                POST and PATCH are sent exactly once and never replayed after an
                ambiguous outcome (#104).
            **kwargs: Additional httpx request arguments

        Returns:
            Parsed JSON response dict

        Raises:
            OilPriceAPIError: On API errors
            AuthenticationError: On 401 status
            RateLimitError: On 429 status
            DataNotFoundError: On 404 status
            ServerError: On 5xx status
            TimeoutError: On request timeout
        """
        # Pin the request to the configured API origin. A raw path may not
        # move the destination host, because the API key rides on this client
        # and would go with it (#102).
        url = resolve_api_url(self.base_url, path)

        # Use provided timeout or default
        effective_timeout = timeout if timeout is not None else self.timeout

        # Retry logic using retry strategy
        last_exception: Optional[OilPriceAPIError] = None
        start_time = time.time()
        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    f"API request: {method} {url} (attempt {attempt + 1}/{self.max_retries})"
                )

                response = self._client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    timeout=effective_timeout,
                    **kwargs,
                )

                logger.debug(f"API response: {response.status_code} for {method} {url}")

                if 200 <= response.status_code < 300:
                    self._telemetry.track_request(
                        operation=self._sanitize_path_for_telemetry(method, path),
                        duration=time.time() - start_time,
                        success=True,
                    )
                    return decode_json_body(response)
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    logger.warning(
                        f"Rate limit exceeded. Limit: {response.headers.get('X-RateLimit-Limit')}, "
                        f"Remaining: {response.headers.get('X-RateLimit-Remaining')}"
                    )

                    # Auto-retry with Retry-After if we have attempts left
                    if self._retry_strategy.should_retry(
                        attempt, 429, response.headers, method=method, idempotent=idempotent
                    ):
                        # Bounded in BOTH directions: a server Retry-After of
                        # 31612 would park the process for 8.8 hours, and a
                        # negative one makes time.sleep() raise (#104).
                        wait_time = self._retry_strategy.bounded_wait(
                            retry_after, self._retry_strategy.calculate_wait_time(attempt)
                        )
                        logger.info(
                            f"Rate limited. Retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        time.sleep(wait_time)
                        continue
                elif response.status_code >= 500:
                    if self._retry_strategy.should_retry(
                        attempt,
                        response.status_code,
                        response.headers,
                        method=method,
                        idempotent=idempotent,
                    ):
                        wait_time = self._retry_strategy.calculate_wait_time(attempt)
                        self._retry_strategy.log_retry(
                            attempt,
                            f"Server error {response.status_code}",
                            wait_time,
                            is_async=False,
                        )
                        time.sleep(wait_time)
                        continue
                error = error_from_response(
                    response,
                    commodity=params.get("commodity") if params else None,
                )
                # A 5xx is ambiguous, not a refusal: a gateway can return 502
                # after the origin already committed. The write was correctly
                # sent once and not replayed -- tell the caller the outcome is
                # unknown so they reconcile instead of assuming it failed
                # (#116). 4xx and 429 refused the request outright, so nothing
                # landed and there is nothing to reconcile.
                if response.status_code >= 500 and not self._retry_strategy.is_replay_safe(
                    method, idempotent
                ):
                    raise mark_ambiguous_write(error, method)
                raise error

            except httpx.TimeoutException as error:
                last_exception = error_from_exception(
                    error,
                    api_key=self.api_key,
                    timeout=effective_timeout,
                )
                if self._retry_strategy.should_retry_on_exception(
                    attempt, method=method, idempotent=idempotent
                ):
                    wait_time = self._retry_strategy.calculate_wait_time(attempt)
                    self._retry_strategy.log_retry(
                        attempt, "Request timeout", wait_time, is_async=False
                    )
                    time.sleep(wait_time)
                    continue
                if not self._retry_strategy.is_replay_safe(method, idempotent):
                    raise mark_ambiguous_write(last_exception, method)
                logger.error(f"Request timed out after {self.max_retries} attempts")
                raise last_exception
            except httpx.RequestError as error:
                last_exception = error_from_exception(
                    error,
                    api_key=self.api_key,
                )
                if self._retry_strategy.should_retry_on_exception(
                    attempt, method=method, idempotent=idempotent
                ):
                    wait_time = self._retry_strategy.calculate_wait_time(attempt)
                    self._retry_strategy.log_retry(
                        attempt,
                        f"Request error: {error.__class__.__name__}",
                        wait_time,
                        is_async=False,
                    )
                    time.sleep(wait_time)
                    continue
                if not self._retry_strategy.is_replay_safe(method, idempotent):
                    raise mark_ambiguous_write(last_exception, method)
                logger.error(
                    f"Request failed after {self.max_retries} attempts: "
                    f"{error.__class__.__name__}"
                )
                raise last_exception

        if last_exception:
            self._telemetry.track_request(
                operation=f"{method} {path}",
                duration=time.time() - start_time,
                success=False,
                error_type=type(last_exception).__name__,
            )
            raise last_exception

        raise OilPriceAPIError("Max retries exceeded")

    def request_with_headers(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        idempotent: Optional[bool] = None,
        **kwargs,
    ) -> Tuple[Dict[str, Any], httpx.Headers]:
        """Make HTTP request and return (json_body, headers) tuple.

        Identical to request() but also returns response headers so callers
        can inspect pagination headers like X-Has-Next, X-Page, X-Per-Page.

        Returns:
            Tuple of (parsed JSON dict, httpx.Headers)
        """
        # Pin the request to the configured API origin. A raw path may not
        # move the destination host, because the API key rides on this client
        # and would go with it (#102).
        url = resolve_api_url(self.base_url, path)

        effective_timeout = timeout if timeout is not None else self.timeout

        last_exception: Optional[OilPriceAPIError] = None
        for attempt in range(self.max_retries):
            try:
                response = self._client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    timeout=effective_timeout,
                    **kwargs,
                )

                if 200 <= response.status_code < 300:
                    return decode_json_body(response), response.headers
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")

                    if self._retry_strategy.should_retry(
                        attempt, 429, response.headers, method=method, idempotent=idempotent
                    ):
                        # Bounded in BOTH directions: a server Retry-After of
                        # 31612 would park the process for 8.8 hours, and a
                        # negative one makes time.sleep() raise (#104).
                        wait_time = self._retry_strategy.bounded_wait(
                            retry_after, self._retry_strategy.calculate_wait_time(attempt)
                        )
                        logger.info(
                            f"Rate limited. Retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        time.sleep(wait_time)
                        continue
                elif response.status_code >= 500:
                    if self._retry_strategy.should_retry(
                        attempt,
                        response.status_code,
                        response.headers,
                        method=method,
                        idempotent=idempotent,
                    ):
                        wait_time = self._retry_strategy.calculate_wait_time(attempt)
                        self._retry_strategy.log_retry(
                            attempt,
                            f"Server error {response.status_code}",
                            wait_time,
                            is_async=False,
                        )
                        time.sleep(wait_time)
                        continue
                error = error_from_response(
                    response,
                    commodity=params.get("commodity") if params else None,
                )
                # A 5xx is ambiguous, not a refusal: a gateway can return 502
                # after the origin already committed. The write was correctly
                # sent once and not replayed -- tell the caller the outcome is
                # unknown so they reconcile instead of assuming it failed
                # (#116). 4xx and 429 refused the request outright, so nothing
                # landed and there is nothing to reconcile.
                if response.status_code >= 500 and not self._retry_strategy.is_replay_safe(
                    method, idempotent
                ):
                    raise mark_ambiguous_write(error, method)
                raise error

            except httpx.TimeoutException as error:
                last_exception = error_from_exception(
                    error,
                    api_key=self.api_key,
                    timeout=effective_timeout,
                )
                if self._retry_strategy.should_retry_on_exception(
                    attempt, method=method, idempotent=idempotent
                ):
                    wait_time = self._retry_strategy.calculate_wait_time(attempt)
                    self._retry_strategy.log_retry(
                        attempt, "Request timeout", wait_time, is_async=False
                    )
                    time.sleep(wait_time)
                    continue
                if not self._retry_strategy.is_replay_safe(method, idempotent):
                    raise mark_ambiguous_write(last_exception, method)
                raise last_exception
            except httpx.RequestError as error:
                last_exception = error_from_exception(
                    error,
                    api_key=self.api_key,
                )
                if self._retry_strategy.should_retry_on_exception(
                    attempt, method=method, idempotent=idempotent
                ):
                    wait_time = self._retry_strategy.calculate_wait_time(attempt)
                    self._retry_strategy.log_retry(
                        attempt,
                        f"Request error: {error.__class__.__name__}",
                        wait_time,
                        is_async=False,
                    )
                    time.sleep(wait_time)
                    continue
                if not self._retry_strategy.is_replay_safe(method, idempotent):
                    raise mark_ambiguous_write(last_exception, method)
                raise last_exception

        if last_exception:
            raise last_exception

        raise OilPriceAPIError("Max retries exceeded")

    @staticmethod
    def _sanitize_path_for_telemetry(method: str, path: str) -> str:
        """Strip resource IDs from path to avoid leaking user data in telemetry."""
        import re

        # Replace UUIDs and numeric IDs with :id
        sanitized = re.sub(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "/:id", path
        )
        sanitized = re.sub(r"/\d+", "/:id", sanitized)
        return f"{method} {sanitized}"

    def get_data_connector_prices(
        self,
        fuel_type: Optional[str] = None,
        port: Optional[str] = None,
        region: Optional[str] = None,
        since: Optional[str] = None,
    ) -> List[DataConnectorPrice]:
        """
        Get prices from connected data sources (BYOS - Bring Your Own Subscription).

        Requires Data Connector feature enabled on your organization.

        Args:
            fuel_type: Filter by fuel type (VLSFO, MGO, IFO380)
            port: Filter by port name
            region: Filter by region (AMERICAS, EMEA, APAC)
            since: ISO 8601 timestamp to fetch prices after

        Returns:
            List of DataConnectorPrice objects

        Example:
            >>> prices = client.get_data_connector_prices(fuel_type='VLSFO')
            >>> for p in prices:
            ...     print(f"{p.port}: ${p.price}/{p.unit}")
        """
        params = {}
        if fuel_type:
            params["fuel_type"] = fuel_type
        if port:
            params["port"] = port
        if region:
            params["region"] = region
        if since:
            params["since"] = since

        response = self.request("GET", "/v1/prices/data-connector", params=params)
        prices_data = response.get("data", {}).get("prices", [])
        return [DataConnectorPrice(**p) for p in prices_data]

    def market_brief(
        self,
        codes: List[str],
        narrative: bool = False,
    ) -> MarketBrief:
        """Get a multi-commodity structured (+ optional narrative) market brief.

        Composes existing price/forecast data for the given commodity codes into
        a single structured summary (#3245 Phase 1a). Counts as one request.

        Args:
            codes: Commodity codes to include (e.g. ["BRENT_CRUDE_USD", "WTI"]).
            narrative: When True, request a natural-language narrative as well.

        Returns:
            A MarketBrief model.

        Example:
            >>> brief = client.market_brief(["BRENT_CRUDE_USD"], narrative=True)
            >>> print(brief.commodities[0].price)
        """
        params: Dict[str, Any] = {"codes": ",".join(codes)}
        if narrative:
            params["narrative"] = "true"

        response = self.request(
            method="GET",
            path="/v1/market-brief",
            params=params,
        )
        return MarketBrief(**unwrap_data(response))

    def close(self):
        """Close the HTTP client and flush telemetry."""
        self._telemetry.close()
        self._client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def __del__(self):
        """Cleanup on deletion.

        Note: Relying on __del__ for cleanup is non-deterministic.
        Prefer using context managers (with statement) or explicitly calling close().
        """
        try:
            self.close()
        except Exception:
            # Silently fail during cleanup - cannot handle exceptions in __del__
            # GC is already running, logging or raising would cause issues
            pass
