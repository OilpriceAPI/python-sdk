"""
Asynchronous OilPriceAPI Client

Async/await support for high-performance applications.
"""

import os
import logging
from typing import Optional, Dict, Any, Union, List
import httpx
from datetime import datetime
import json
import asyncio
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
from .models import Price, HistoricalPrice, HistoricalResponse


class AsyncOilPriceAPI:
    """Asynchronous client for OilPriceAPI.
    
    Provides async/await support for all API operations.
    
    Args:
        api_key: API key for authentication
        base_url: Base URL for API
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
        
    Example:
        >>> async with AsyncOilPriceAPI() as client:
        ...     price = await client.prices.get("BRENT_CRUDE_USD")
        ...     print(f"Brent: ${price.value:.2f}")
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
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
    ):
        # Get API key
        self.api_key = api_key or os.environ.get("OILPRICEAPI_KEY")
        if not self.api_key:
            raise ConfigurationError(
                "API key required. Set OILPRICEAPI_KEY environment variable or pass api_key parameter."
            )

        # Configuration
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.max_retries = max_retries or self.DEFAULT_MAX_RETRIES
        self.retry_on = retry_on or self.DEFAULT_RETRY_CODES
        self.max_connections = max_connections
        self.max_keepalive_connections = max_keepalive_connections

        # Initialize retry strategy
        self._retry_strategy = RetryStrategy(
            max_retries=self.max_retries,
            retry_on=self.retry_on
        )

        # Build headers
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "OilPriceAPI-Python-Async/1.3.0",
            "X-SDK-Language": "python",
            "X-SDK-Version": "1.3.0",
            "X-Client-Type": "sdk",
        }
        if headers:
            self.headers.update(headers)
        
        # Client will be created in __aenter__ or when needed
        self._client = None
        
        # Initialize resources
        self.prices = AsyncPricesResource(self)
        self.historical = AsyncHistoricalResource(self)
    
    async def _ensure_client(self):
        """
        Ensure HTTP client is created with connection pooling.

        Configures connection limits to prevent resource exhaustion under
        concurrent load. Max 100 concurrent connections prevents spawning
        unlimited connections, while keeping 20 alive improves performance
        for subsequent requests.
        """
        if self._client is None:
            limits = httpx.Limits(
                max_connections=self.max_connections,
                max_keepalive_connections=self.max_keepalive_connections
            )

            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=self.timeout,
                limits=limits,
                follow_redirects=True,
            )
    
    async def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Union[Dict[str, Any], list]:
        """Make async HTTP request to API."""
        await self._ensure_client()
        
        # Ensure path starts with / for proper urljoin behavior
        if not path.startswith('/'):
            path = '/' + path
        url = urljoin(self.base_url + '/', path)
        
        # Retry logic
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Async API request: {method} {url} (attempt {attempt + 1}/{self.max_retries})")

                response = await self._client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    **kwargs
                )

                logger.debug(f"Async API response: {response.status_code} for {method} {url}")

                # Handle response codes
                if response.status_code == 200:
                    return await response.json()
                elif response.status_code == 401:
                    logger.error(f"Authentication failed for {url}")
                    raise AuthenticationError()
                elif response.status_code == 404:
                    error_data = await self._safe_parse_json(response)
                    raise DataNotFoundError(
                        message=error_data.get("error", "Not found"),
                        commodity=params.get("commodity") if params else None,
                    )
                elif response.status_code == 429:
                    reset_time = self._parse_rate_limit_reset(response.headers)
                    logger.warning(
                        f"Rate limit exceeded. Limit: {response.headers.get('X-RateLimit-Limit')}, "
                        f"Remaining: {response.headers.get('X-RateLimit-Remaining')}"
                    )
                    raise RateLimitError(
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
                            is_async=True
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    raise ServerError(
                        message=f"Server error: {response.status_code}",
                        status_code=response.status_code,
                    )
                else:
                    error_data = await self._safe_parse_json(response)
                    raise OilPriceAPIError(
                        message=error_data.get("error", f"Error: {response.status_code}"),
                        status_code=response.status_code,
                    )

            except httpx.TimeoutException:
                last_exception = TimeoutError(timeout=self.timeout)
                if self._retry_strategy.should_retry_on_exception(attempt):
                    wait_time = self._retry_strategy.calculate_wait_time(attempt)
                    self._retry_strategy.log_retry(
                        attempt,
                        "Request timeout",
                        wait_time,
                        is_async=True
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise last_exception
            except httpx.RequestError as e:
                last_exception = OilPriceAPIError(message=str(e))
                if self._retry_strategy.should_retry_on_exception(attempt):
                    wait_time = self._retry_strategy.calculate_wait_time(attempt)
                    self._retry_strategy.log_retry(
                        attempt,
                        f"Request error: {e}",
                        wait_time,
                        is_async=True
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise last_exception

        if last_exception:
            raise last_exception

        raise OilPriceAPIError("Max retries exceeded")
    
    async def _safe_parse_json(self, response: httpx.Response) -> Dict[str, Any]:
        """Safely parse JSON response."""
        try:
            return await response.json()
        except json.JSONDecodeError:
            return {"error": response.text or "Unknown error"}
    
    def _parse_rate_limit_reset(self, headers: Dict[str, str]) -> Optional[datetime]:
        """Parse rate limit reset time."""
        reset_header = headers.get("X-RateLimit-Reset")
        if reset_header:
            try:
                timestamp = float(reset_header)
                return datetime.fromtimestamp(timestamp)
            except (ValueError, TypeError):
                try:
                    return datetime.fromisoformat(reset_header)
                except (ValueError, TypeError):
                    pass
        return None
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


class AsyncPricesResource:
    """Async resource for current prices."""
    
    def __init__(self, client: AsyncOilPriceAPI):
        self.client = client
    
    async def get(self, commodity: str) -> Price:
        """Get current price for commodity."""
        response = await self.client.request(
            method="GET",
            path="/v1/prices/latest",
            params={"by_code": commodity}
        )
        
        if "data" in response:
            price_data = response["data"]
        else:
            price_data = response

        # Map API response to Price model
        # Note: API should provide 'unit' field. If missing, we default to 'barrel'
        # for backwards compatibility, but this may be incorrect for non-oil commodities
        mapped_data = {
            "commodity": price_data.get("code", commodity),
            "value": price_data.get("price"),
            "currency": price_data.get("currency", "USD"),
            "unit": price_data.get("unit", "barrel"),
            "timestamp": price_data.get("created_at"),
        }

        return Price(**mapped_data)
    
    async def get_multiple(
        self,
        commodities: List[str],
        raise_on_error: bool = False,
        return_failures: bool = False
    ) -> Union[List[Price], tuple[List[Price], List[tuple[str, str]]]]:
        """Get prices for multiple commodities concurrently.

        Args:
            commodities: List of commodity codes
            raise_on_error: If True, raise exception on first failure. If False, skip failed commodities.
            return_failures: If True, return tuple of (prices, failures). Failures is list of (commodity, error_message).

        Returns:
            List of Price objects, or tuple of (prices, failures) if return_failures=True

        Raises:
            OilPriceAPIError: If raise_on_error=True and any commodity fails
        """
        from .exceptions import OilPriceAPIError

        # Use gather for concurrent requests
        tasks = [self.get(commodity) for commodity in commodities]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        prices = []
        failures = []

        for commodity, result in zip(commodities, results):
            if isinstance(result, Price):
                prices.append(result)
            elif isinstance(result, Exception):
                if raise_on_error:
                    raise result
                failures.append((commodity, str(result)))

        if return_failures:
            return prices, failures
        return prices
    
    async def get_all(self) -> List[Price]:
        """Get all available prices."""
        response = await self.client.request(
            method="GET",
            path="/v1/prices/all"
        )
        
        if "data" in response:
            prices_data = response["data"]
        else:
            prices_data = response
        
        return [Price(**price_data) for price_data in prices_data]


class AsyncHistoricalResource:
    """Async resource for historical data."""
    
    def __init__(self, client: AsyncOilPriceAPI):
        self.client = client
    
    async def get(
        self,
        commodity: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "daily",
        page: int = 1,
        per_page: int = 100,
        type_name: str = "spot_price"
    ) -> HistoricalResponse:
        """Get historical price data."""
        params = {
            "commodity": commodity,
            "interval": interval,
            "page": page,
            "per_page": min(per_page, 1000),
            "by_type": type_name,
        }
        
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        response = await self.client.request(
            method="GET",
            path="/v1/prices/past_year",
            params=params
        )
        
        # Parse response - handle nested structure
        # API returns: {"status": "success", "data": {"prices": [...]}}
        if "data" in response and isinstance(response["data"], dict) and "prices" in response["data"]:
            prices_data = response["data"]["prices"]
        elif "data" in response and isinstance(response["data"], list):
            prices_data = response["data"]
        else:
            prices_data = response if isinstance(response, list) else []

        # Create HistoricalPrice objects
        prices = []
        for price_data in prices_data:
            if isinstance(price_data, dict):
                # Map API fields to model fields
                mapped_data = {
                    "created_at": price_data.get("created_at"),
                    "commodity_name": price_data.get("code", price_data.get("commodity_name")),
                    "price": price_data.get("price"),
                    "unit_of_measure": price_data.get("unit", "barrel"),
                    "type_name": price_data.get("type", "spot_price"),
                }
                prices.append(HistoricalPrice(**mapped_data))
        
        return HistoricalResponse(
            success=True,
            data=prices,
            meta=None  # Simplified for now
        )
    
    async def get_all(
        self,
        commodity: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "daily"
    ) -> List[HistoricalPrice]:
        """Get all historical data with automatic pagination."""
        all_prices = []
        page = 1
        
        while True:
            response = await self.get(
                commodity=commodity,
                start_date=start_date,
                end_date=end_date,
                interval=interval,
                page=page,
                per_page=1000
            )
            
            all_prices.extend(response.data)
            
            # Check if we got a full page (might be more)
            if len(response.data) < 1000:
                break
            
            page += 1
        
        return all_prices
