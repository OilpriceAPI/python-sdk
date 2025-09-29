"""
OilPriceAPI SDK Exceptions

Custom exceptions for better error handling and debugging.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime


class OilPriceAPIError(Exception):
    """Base exception for all OilPriceAPI errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response
        self.request_id = request_id

    def __str__(self) -> str:
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class AuthenticationError(OilPriceAPIError):
    """Raised when API authentication fails."""

    def __init__(self, message: str = "Invalid API key or authentication failed"):
        super().__init__(message, status_code=401)


class RateLimitError(OilPriceAPIError):
    """Raised when API rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        reset_time: Optional[datetime] = None,
        limit: Optional[int] = None,
        remaining: Optional[int] = None,
    ):
        super().__init__(message, status_code=429)
        self.reset_time = reset_time
        self.limit = limit
        self.remaining = remaining

    @property
    def seconds_until_reset(self) -> Optional[float]:
        """Calculate seconds until rate limit resets."""
        if self.reset_time:
            delta = self.reset_time - datetime.now(self.reset_time.tzinfo)
            return max(0, delta.total_seconds())
        return None

    def __str__(self) -> str:
        msg = super().__str__()
        if self.seconds_until_reset:
            msg += f" (resets in {self.seconds_until_reset:.0f}s)"
        return msg


class DataNotFoundError(OilPriceAPIError):
    """Raised when requested data is not found."""

    def __init__(
        self,
        message: str = "Data not found",
        commodity: Optional[str] = None,
        valid_commodities: Optional[List[str]] = None,
    ):
        super().__init__(message, status_code=404)
        self.commodity = commodity
        self.valid_commodities = valid_commodities

    def __str__(self) -> str:
        msg = super().__str__()
        if self.commodity:
            msg = f"Commodity '{self.commodity}' not found"
        if self.valid_commodities:
            msg += f". Valid options: {', '.join(self.valid_commodities[:5])}"
            if len(self.valid_commodities) > 5:
                msg += f" (and {len(self.valid_commodities) - 5} more)"
        return msg


class ValidationError(OilPriceAPIError):
    """Raised when request validation fails."""

    def __init__(
        self,
        message: str = "Validation error",
        field: Optional[str] = None,
        value: Optional[Any] = None,
    ):
        super().__init__(message, status_code=422)
        self.field = field
        self.value = value

    def __str__(self) -> str:
        msg = super().__str__()
        if self.field:
            msg = f"Validation error for '{self.field}'"
            if self.value is not None:
                msg += f": invalid value '{self.value}'"
        return msg


class ServerError(OilPriceAPIError):
    """Raised when server returns 5xx error."""

    def __init__(
        self,
        message: str = "Server error",
        status_code: int = 500,
        retry_after: Optional[int] = None,
    ):
        super().__init__(message, status_code=status_code)
        self.retry_after = retry_after


class TimeoutError(OilPriceAPIError):
    """Raised when request times out."""

    def __init__(self, message: str = "Request timed out", timeout: Optional[float] = None):
        super().__init__(message)
        self.timeout = timeout

    def __str__(self) -> str:
        msg = super().__str__()
        if self.timeout:
            msg += f" (timeout: {self.timeout}s)"
        return msg


class ConfigurationError(OilPriceAPIError):
    """Raised when client configuration is invalid."""

    def __init__(self, message: str):
        super().__init__(message)