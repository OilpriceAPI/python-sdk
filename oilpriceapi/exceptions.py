"""Typed OilPriceAPI errors and compatibility parsing for API responses."""

from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

_SENSITIVE_HEADERS = {
    "authorization",
    "proxy-authorization",
    "x-api-key",
    "api-key",
}
_REDACTED = "[REDACTED]"


def _redact_text(value: str, secrets: Iterable[str]) -> str:
    redacted = value
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, _REDACTED)
    return redacted


def _redact_value(value: Any, secrets: Iterable[str]) -> Any:
    if isinstance(value, str):
        return _redact_text(value, secrets)
    if isinstance(value, Mapping):
        return {
            str(key): _redact_value(item, secrets)
            for key, item in value.items()
            if str(key).lower() not in _SENSITIVE_HEADERS
        }
    if isinstance(value, list):
        return [_redact_value(item, secrets) for item in value]
    return value


def _response_secrets(response: Any) -> List[str]:
    """Read request credentials only to redact them; never retain request headers."""
    try:
        request = response.request
        request_headers = request.headers
    except (AttributeError, RuntimeError):
        return []

    if not isinstance(request_headers, Mapping):
        return []

    secrets: List[str] = []
    for name, value in request_headers.items():
        if str(name).lower() not in _SENSITIVE_HEADERS:
            continue
        text = str(value)
        secrets.append(text)
        if " " in text:
            secrets.append(text.split(" ", 1)[1])
    return secrets


def _response_headers(response: Any, secrets: Iterable[str]) -> Dict[str, str]:
    try:
        response_headers = response.headers
    except AttributeError:
        return {}
    if not isinstance(response_headers, Mapping):
        return {}

    result: Dict[str, str] = {}
    for name, value in response_headers.items():
        normalized_name = str(name).lower()
        if normalized_name in _SENSITIVE_HEADERS:
            continue
        result[normalized_name] = _redact_text(str(value), secrets)
    return result


def _response_body(response: Any, secrets: Iterable[str]) -> Tuple[Any, str]:
    try:
        parsed = response.json()
    except (ValueError, TypeError, AttributeError):
        parsed = None

    try:
        response_text = response.text
    except (AttributeError, RuntimeError):
        response_text = ""

    if not isinstance(response_text, str):
        response_text = ""

    if parsed is None:
        raw_text = response_text or "Unknown error"
        return _redact_text(raw_text, secrets), _redact_text(raw_text, secrets)

    redacted_body = _redact_value(parsed, secrets)
    if response_text:
        raw_text = _redact_text(response_text, secrets)
    else:
        # Mock responses used by SDK consumers/tests may not retain encoded text.
        raw_text = str(redacted_body)
    return redacted_body, raw_text


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _first_value(sources: Iterable[Mapping[str, Any]], *keys: str) -> Any:
    for source in sources:
        for key in keys:
            value = source.get(key)
            if value is not None and value != "":
                return value
    return None


def _number(value: Any) -> Any:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return value
    return int(number) if number.is_integer() else number


def _parse_reset_time(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(float(value))
    except (TypeError, ValueError, OSError):
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None


class OilPriceAPIError(Exception):
    """Stable base contract for API, transport, and configuration errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        *,
        code: Optional[str] = None,
        docs_url: Optional[str] = None,
        current_plan: Optional[str] = None,
        required_plan: Optional[str] = None,
        required_feature: Optional[str] = None,
        remediation_url: Optional[str] = None,
        retry_after: Any = None,
        retry_metadata: Optional[Dict[str, Any]] = None,
        raw_body: Any = None,
        raw_text: str = "",
        headers: Optional[Mapping[str, str]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.machine_code = code
        self.request_id = request_id
        self.docs_url = docs_url
        self.current_plan = current_plan
        self.required_plan = required_plan
        self.required_feature = required_feature
        self.remediation_url = remediation_url
        self.retry_after = retry_after
        self.retry_metadata = retry_metadata or {}
        self.raw_body = raw_body if raw_body is not None else response
        self.raw_text = raw_text
        self.headers = dict(headers or {})
        # Retain the historical attribute while exposing raw_body for all shapes.
        self.response = (
            response
            if response is not None
            else (self.raw_body if isinstance(self.raw_body, dict) else None)
        )

    @property
    def retryable(self) -> bool:
        explicit = self.retry_metadata.get("retryable")
        if isinstance(explicit, bool):
            return explicit
        return self.status_code == 429 or (self.status_code is not None and self.status_code >= 500)

    @property
    def is_client_error(self) -> bool:
        return self.status_code is not None and 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        return self.status_code is not None and self.status_code >= 500

    def __str__(self) -> str:
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class BadRequestError(OilPriceAPIError):
    """Raised for malformed requests (HTTP 400)."""

    def __init__(self, message: str = "Bad request", **kwargs: Any):
        super().__init__(message, status_code=400, **kwargs)


class AuthenticationError(OilPriceAPIError):
    """Raised when API authentication fails (HTTP 401)."""

    def __init__(
        self,
        message: str = "Invalid API key or authentication failed",
        **kwargs: Any,
    ):
        super().__init__(message, status_code=401, **kwargs)


class PaymentRequiredError(OilPriceAPIError):
    """Raised when account billing or plan access is required (HTTP 402)."""

    def __init__(self, message: str = "Payment or plan upgrade required", **kwargs: Any):
        super().__init__(message, status_code=402, **kwargs)


class PermissionDeniedError(OilPriceAPIError):
    """Raised when the account lacks permission for a feature (HTTP 403)."""

    def __init__(self, message: str = "Permission denied", **kwargs: Any):
        super().__init__(message, status_code=403, **kwargs)


class RateLimitError(OilPriceAPIError):
    """Raised when API rate limit is exceeded (HTTP 429)."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        reset_time: Optional[datetime] = None,
        limit: Any = None,
        remaining: Any = None,
        retry_after: Any = None,
        **kwargs: Any,
    ):
        super().__init__(
            message,
            status_code=429,
            retry_after=retry_after,
            **kwargs,
        )
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
        message = super().__str__()
        if self.seconds_until_reset:
            message += f" (resets in {self.seconds_until_reset:.0f}s)"
        return message


class DataNotFoundError(OilPriceAPIError):
    """Raised when requested data is not found (HTTP 404)."""

    def __init__(
        self,
        message: str = "Data not found",
        commodity: Optional[str] = None,
        valid_commodities: Optional[List[str]] = None,
        **kwargs: Any,
    ):
        super().__init__(message, status_code=404, **kwargs)
        self.commodity = commodity
        self.valid_commodities = valid_commodities

    def __str__(self) -> str:
        message = super().__str__()
        if self.commodity:
            message = f"Commodity '{self.commodity}' not found"
        if self.valid_commodities:
            message += f". Valid options: {', '.join(self.valid_commodities[:5])}"
            if len(self.valid_commodities) > 5:
                message += f" (and {len(self.valid_commodities) - 5} more)"
        return message


class ValidationError(OilPriceAPIError):
    """Raised when request validation fails (HTTP 422)."""

    def __init__(
        self,
        message: str = "Validation error",
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs: Any,
    ):
        super().__init__(message, status_code=422, **kwargs)
        self.field = field
        self.value = value

    def __str__(self) -> str:
        message = super().__str__()
        if self.field:
            message = f"Validation error for '{self.field}'"
            if self.value is not None:
                message += f": invalid value '{self.value}'"
        return message


class ServerError(OilPriceAPIError):
    """Raised when the server returns HTTP 5xx."""

    def __init__(
        self,
        message: str = "Server error",
        status_code: int = 500,
        retry_after: Any = None,
        **kwargs: Any,
    ):
        super().__init__(
            message,
            status_code=status_code,
            retry_after=retry_after,
            **kwargs,
        )


class NetworkError(OilPriceAPIError):
    """Raised when a request cannot reach or complete with the API."""

    def __init__(
        self,
        message: str = "Network request failed",
        cause_type: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(message, **kwargs)
        self.cause_type = cause_type

    @property
    def retryable(self) -> bool:
        return True


class TimeoutError(NetworkError):
    """Raised when a request times out."""

    def __init__(
        self,
        message: str = "Request timed out",
        timeout: Optional[float] = None,
        **kwargs: Any,
    ):
        super().__init__(message, cause_type="TimeoutException", **kwargs)
        self.timeout = timeout

    def __str__(self) -> str:
        message = super().__str__()
        if self.timeout:
            message += f" (timeout: {self.timeout}s)"
        return message


class ConfigurationError(OilPriceAPIError):
    """Raised when client configuration is invalid."""

    def __init__(self, message: str):
        super().__init__(message)


def error_from_response(
    response: Any,
    *,
    commodity: Optional[str] = None,
) -> OilPriceAPIError:
    """Normalize canonical, legacy, and malformed HTTP error responses."""
    secrets = _response_secrets(response)
    raw_body, raw_text = _response_body(response, secrets)
    headers = _response_headers(response, secrets)
    payload = _mapping(raw_body)
    nested_error = _mapping(payload.get("error"))
    primary = nested_error or payload
    details = _mapping(primary.get("details")) or _mapping(payload.get("details"))
    sources = (primary, details, payload)

    legacy_error = payload.get("error")
    message_value = _first_value(sources, "message", "detail", "title")
    if message_value is None and isinstance(legacy_error, str):
        message_value = legacy_error
    status_code = int(response.status_code)
    message = str(message_value or raw_text.strip() or f"HTTP {status_code} error")

    code_value = _first_value(sources, "code", "error_code", "type")
    request_id_value = _first_value(
        sources,
        "request_id",
        "requestId",
        "correlation_id",
    )
    if request_id_value is None:
        request_id_value = headers.get("x-request-id") or headers.get("x-correlation-id")

    retry_value = _first_value(sources, "retry")
    retry_metadata = dict(_mapping(retry_value))
    retry_after = _first_value(sources, "retry_after", "retryAfter")
    if retry_after is None:
        retry_after = headers.get("retry-after")
    retry_after = _number(retry_after)

    # Preserve the historical string attributes exposed by RateLimitError.
    limit = headers.get("x-ratelimit-limit")
    remaining = headers.get("x-ratelimit-remaining")
    reset_value = _first_value(sources, "retry_at", "reset_at", "reset_time")
    if reset_value is None:
        reset_value = headers.get("x-ratelimit-reset")
    reset_time = _parse_reset_time(reset_value)

    if retry_after is not None:
        retry_metadata.setdefault("retry_after", retry_after)
    if reset_value is not None:
        retry_metadata.setdefault("reset", reset_value)
    if limit is not None:
        retry_metadata.setdefault("limit", limit)
    if remaining is not None:
        retry_metadata.setdefault("remaining", remaining)

    raw_response = raw_body if isinstance(raw_body, dict) else None
    common: Dict[str, Any] = {
        "response": raw_response,
        "request_id": str(request_id_value) if request_id_value is not None else None,
        "code": str(code_value) if code_value is not None else None,
        "docs_url": _first_value(
            sources,
            "docs_url",
            "documentation_url",
            "help_url",
        ),
        "current_plan": _first_value(sources, "current_plan", "plan"),
        "required_plan": _first_value(sources, "required_plan"),
        "required_feature": _first_value(
            sources,
            "required_feature",
            "feature",
        ),
        "remediation_url": _first_value(
            sources,
            "remediation_url",
            "upgrade_url",
            "action_url",
        ),
        "retry_metadata": retry_metadata,
        "raw_body": raw_body,
        "raw_text": raw_text,
        "headers": headers,
    }

    if status_code == 400:
        return BadRequestError(message, **common)
    if status_code == 401:
        return AuthenticationError(message, **common)
    if status_code == 402:
        return PaymentRequiredError(message, **common)
    if status_code == 403:
        return PermissionDeniedError(message, **common)
    if status_code == 404:
        return DataNotFoundError(message, commodity=commodity, **common)
    if status_code == 422:
        return ValidationError(
            message,
            field=_first_value(sources, "field"),
            value=_first_value(sources, "value"),
            **common,
        )
    if status_code == 429:
        return RateLimitError(
            message,
            reset_time=reset_time,
            limit=limit,
            remaining=remaining,
            retry_after=retry_after,
            **common,
        )
    if status_code >= 500:
        return ServerError(
            message,
            status_code=status_code,
            retry_after=retry_after,
            **common,
        )
    return OilPriceAPIError(message, status_code=status_code, retry_after=retry_after, **common)


def error_from_exception(
    error: BaseException,
    *,
    api_key: Optional[str] = None,
    timeout: Optional[float] = None,
) -> OilPriceAPIError:
    """Normalize transport failures while redacting the configured API key."""
    secrets = [api_key] if api_key else []
    if "Timeout" in error.__class__.__name__:
        return TimeoutError(timeout=timeout)
    message = _redact_text(str(error), secrets)
    return NetworkError(
        message=f"Request failed: {message}",
        cause_type=error.__class__.__name__,
    )
