"""
OilPriceAPI Client

Main client class for interacting with OilPriceAPI.
"""

import os
import logging
from typing import Optional, Dict, Any, Union
import httpx
from datetime import datetime, timedelta
import json
import time
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

from .retry import RetryStrategy
from .exceptions import (
    OilPriceAPIError,
    AuthenticationError,
    RateLimitError,
    DataNotFoundError,
    ServerError,
    TimeoutError,
    ValidationError,
    ConfigurationError,
)
from .models import Price, PriceResponse, HistoricalResponse
from .resources.prices import PricesResource
from .resources.historical import HistoricalResource
from .resources.diesel import DieselResource
from .resources.alerts import AlertsResource


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
        max_retries: Maximum retry attempts for failed requests. Defaults to 3.
        retry_on: Status codes to retry on. Defaults to [429, 500, 502, 503, 504].

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
        retry_on: Optional[list] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        # Get API key from parameter or environment
        self.api_key = api_key or os.environ.get("OILPRICEAPI_KEY")
        if not self.api_key:
            logger.error("API key not provided - client initialization failed")
            raise ConfigurationError(
                "API key required. Set OILPRICEAPI_KEY environment variable or pass api_key parameter."
            )

        # Configuration
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.max_retries = max_retries or self.DEFAULT_MAX_RETRIES
        self.retry_on = retry_on or self.DEFAULT_RETRY_CODES

        # Initialize retry strategy
        self._retry_strategy = RetryStrategy(
            max_retries=self.max_retries,
            retry_on=self.retry_on
        )

        logger.debug(
            f"Initialized OilPriceAPI client: base_url={self.base_url}, "
            f"timeout={self.timeout}s, max_retries={self.max_retries}"
        )
        
        # Build headers
        import sys
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"oilpriceapi-python/1.4.2 python/{python_version}",
            "X-Api-Client": "oilpriceapi-python",
            "X-Client-Version": "1.4.2",
        }
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

        # Initialize visualization (optional)
        try:
            from .visualization import PriceVisualizer
            self.viz = PriceVisualizer(self)
        except ImportError:
            self.viz = None
    
    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs
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
        # Ensure path starts with / for proper urljoin behavior
        if not path.startswith('/'):
            path = '/' + path
        url = urljoin(self.base_url + '/', path)

        # Use provided timeout or default
        effective_timeout = timeout if timeout is not None else self.timeout

        # Retry logic using retry strategy
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"API request: {method} {url} (attempt {attempt + 1}/{self.max_retries})")

                response = self._client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    timeout=effective_timeout,
                    **kwargs
                )

                logger.debug(f"API response: {response.status_code} for {method} {url}")

                # Handle different status codes
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    logger.error(f"Authentication failed for {url}")
                    raise AuthenticationError("Invalid API key or authentication failed")
                elif response.status_code == 404:
                    error_data = self._safe_parse_json(response)
                    raise DataNotFoundError(
                        message=error_data.get("error", "Resource not found"),
                        commodity=params.get("commodity") if params else None,
                    )
                elif response.status_code == 422:
                    error_data = self._safe_parse_json(response)
                    raise ValidationError(
                        message=error_data.get("error", "Validation failed"),
                        field=error_data.get("field"),
                        value=error_data.get("value"),
                    )
                elif response.status_code == 429:
                    # Parse rate limit headers
                    reset_time = self._parse_rate_limit_reset(response.headers)
                    logger.warning(
                        f"Rate limit exceeded. Limit: {response.headers.get('X-RateLimit-Limit')}, "
                        f"Remaining: {response.headers.get('X-RateLimit-Remaining')}"
                    )
                    raise RateLimitError(
                        message="Rate limit exceeded",
                        reset_time=reset_time,
                        limit=response.headers.get("X-RateLimit-Limit"),
                        remaining=response.headers.get("X-RateLimit-Remaining"),
                    )
                elif response.status_code >= 500:
                    if self._retry_strategy.should_retry(attempt, response.status_code):
                        wait_time = self._retry_strategy.calculate_wait_time(attempt)
                        self._retry_strategy.log_retry(
                            attempt,
                            f"Server error {response.status_code}",
                            wait_time,
                            is_async=False
                        )
                        time.sleep(wait_time)
                        continue
                    raise ServerError(
                        message=f"Server error: {response.status_code}",
                        status_code=response.status_code,
                    )
                else:
                    error_data = self._safe_parse_json(response)
                    raise OilPriceAPIError(
                        message=error_data.get("error", f"Unexpected error: {response.status_code}"),
                        status_code=response.status_code,
                        response=error_data,
                    )

            except httpx.TimeoutException as e:
                last_exception = TimeoutError(
                    message="Request timed out",
                    timeout=self.timeout,
                )
                if self._retry_strategy.should_retry_on_exception(attempt):
                    wait_time = self._retry_strategy.calculate_wait_time(attempt)
                    self._retry_strategy.log_retry(
                        attempt,
                        "Request timeout",
                        wait_time,
                        is_async=False
                    )
                    time.sleep(wait_time)
                    continue
                logger.error(f"Request timed out after {self.max_retries} attempts")
                raise last_exception
            except httpx.RequestError as e:
                last_exception = OilPriceAPIError(
                    message=f"Request failed: {str(e)}",
                )
                if self._retry_strategy.should_retry_on_exception(attempt):
                    wait_time = self._retry_strategy.calculate_wait_time(attempt)
                    self._retry_strategy.log_retry(
                        attempt,
                        f"Request error: {e}",
                        wait_time,
                        is_async=False
                    )
                    time.sleep(wait_time)
                    continue
                logger.error(f"Request failed after {self.max_retries} attempts: {e}")
                raise last_exception

        if last_exception:
            raise last_exception

        raise OilPriceAPIError("Max retries exceeded")
    
    def _safe_parse_json(self, response: httpx.Response) -> Dict[str, Any]:
        """Safely parse JSON response."""
        try:
            return response.json()
        except json.JSONDecodeError:
            return {"error": response.text or "Unknown error"}
    
    def _parse_rate_limit_reset(self, headers: Dict[str, str]) -> Optional[datetime]:
        """Parse rate limit reset time from headers."""
        reset_header = headers.get("X-RateLimit-Reset")
        if reset_header:
            try:
                # Try parsing as Unix timestamp
                timestamp = float(reset_header)
                return datetime.fromtimestamp(timestamp)
            except (ValueError, TypeError):
                # Try parsing as ISO format
                try:
                    return datetime.fromisoformat(reset_header)
                except (ValueError, TypeError):
                    pass
        return None
    
    def close(self):
        """Close the HTTP client."""
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
