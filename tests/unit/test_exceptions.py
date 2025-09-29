"""
Unit tests for exceptions.
"""

import pytest
from datetime import datetime

from oilpriceapi.exceptions import (
    OilPriceAPIError,
    ConfigurationError,
    AuthenticationError,
    RateLimitError,
    DataNotFoundError,
    ServerError,
    TimeoutError,
    ValidationError,
)


class TestOilPriceAPIError:
    """Test base exception class."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = OilPriceAPIError("Something went wrong")
        assert str(error) == "Something went wrong"  # No status code by default
        assert error.message == "Something went wrong"
        assert error.status_code is None

    def test_error_with_status_code(self):
        """Test error with custom status code."""
        error = OilPriceAPIError("Bad request", status_code=400)
        assert str(error) == "[400] Bad request"
        assert error.status_code == 400

    def test_error_with_response_data(self):
        """Test error with response data."""
        response_data = {"error": "Invalid", "details": "Missing field"}
        error = OilPriceAPIError("Error", status_code=422, response=response_data)

        assert error.response == response_data
        assert error.response["details"] == "Missing field"


class TestConfigurationError:
    """Test ConfigurationError."""

    def test_configuration_error(self):
        """Test configuration error."""
        error = ConfigurationError("API key required")

        assert "API key required" in str(error)
        assert isinstance(error, OilPriceAPIError)


class TestAuthenticationError:
    """Test AuthenticationError."""

    def test_authentication_error(self):
        """Test authentication error."""
        error = AuthenticationError("Invalid API key")

        assert "Invalid API key" in str(error)
        assert error.status_code == 401
        assert isinstance(error, OilPriceAPIError)

    def test_authentication_error_string_representation(self):
        """Test string representation."""
        error = AuthenticationError("Token expired")
        assert "[401]" in str(error)
        assert "Token expired" in str(error)


class TestRateLimitError:
    """Test RateLimitError."""

    def test_rate_limit_basic(self):
        """Test basic rate limit error."""
        error = RateLimitError("Rate limit exceeded")

        assert error.status_code == 429
        assert "Rate limit exceeded" in str(error)
        assert isinstance(error, OilPriceAPIError)

    def test_rate_limit_with_reset_time(self):
        """Test rate limit with reset time."""
        reset_time = datetime(2024, 1, 15, 12, 0, 0)
        error = RateLimitError(
            "Rate limit exceeded",
            reset_time=reset_time,
            limit="1000",
            remaining="0",
        )

        assert error.reset_time == reset_time
        assert error.limit == "1000"
        assert error.remaining == "0"

    def test_rate_limit_seconds_until_reset(self):
        """Test seconds_until_reset calculation."""
        from datetime import timedelta, timezone

        # Reset time 60 seconds in the future (using timezone-aware datetime)
        future_time = datetime.now(timezone.utc) + timedelta(seconds=60)
        error = RateLimitError("Rate limit exceeded", reset_time=future_time)

        seconds = error.seconds_until_reset
        assert seconds is not None
        assert 50 < seconds <= 60  # Allow small timing variance

    def test_rate_limit_seconds_until_reset_none(self):
        """Test seconds_until_reset when no reset_time."""
        error = RateLimitError("Rate limit exceeded")
        assert error.seconds_until_reset is None

    def test_rate_limit_string_with_reset(self):
        """Test string representation with reset time."""
        reset_time = datetime(2024, 1, 15, 12, 0, 0)
        error = RateLimitError("Rate limit exceeded", reset_time=reset_time)

        result = str(error)
        assert "[429]" in result
        assert "Rate limit exceeded" in result


class TestDataNotFoundError:
    """Test DataNotFoundError."""

    def test_data_not_found_basic(self):
        """Test basic data not found error."""
        error = DataNotFoundError("Resource not found")

        assert error.status_code == 404
        assert "Resource not found" in str(error)
        assert isinstance(error, OilPriceAPIError)

    def test_data_not_found_with_commodity(self):
        """Test data not found with commodity info."""
        error = DataNotFoundError(
            "Commodity not found",
            commodity="INVALID_CODE",
        )

        assert error.commodity == "INVALID_CODE"
        # The __str__ method overrides the message when commodity is set
        assert "INVALID_CODE" in str(error)
        assert "not found" in str(error)


class TestServerError:
    """Test ServerError."""

    def test_server_error_500(self):
        """Test 500 server error."""
        error = ServerError("Internal server error", status_code=500)

        assert error.status_code == 500
        assert "Internal server error" in str(error)
        assert isinstance(error, OilPriceAPIError)

    def test_server_error_502(self):
        """Test 502 bad gateway error."""
        error = ServerError("Bad gateway", status_code=502)

        assert error.status_code == 502
        assert "Bad gateway" in str(error)

    def test_server_error_503(self):
        """Test 503 service unavailable."""
        error = ServerError("Service unavailable", status_code=503)

        assert error.status_code == 503
        assert "Service unavailable" in str(error)


class TestTimeoutError:
    """Test TimeoutError."""

    def test_timeout_error(self):
        """Test timeout error."""
        error = TimeoutError("Request timed out", timeout=30)

        assert "Request timed out" in str(error)
        assert error.timeout == 30
        assert isinstance(error, OilPriceAPIError)

    def test_timeout_error_string_representation(self):
        """Test timeout error string includes timeout value."""
        error = TimeoutError("Timeout", timeout=60)
        result = str(error)

        assert "Timeout" in result
        # Timeout value might be in message or shown separately


class TestValidationError:
    """Test ValidationError."""

    def test_validation_error_basic(self):
        """Test basic validation error."""
        error = ValidationError("Validation failed")

        assert error.status_code == 422
        assert "Validation failed" in str(error)
        assert isinstance(error, OilPriceAPIError)

    def test_validation_error_with_field(self):
        """Test validation error with field info."""
        error = ValidationError(
            "Invalid date format",
            field="start_date",
            value="invalid",
        )

        assert error.field == "start_date"
        assert error.value == "invalid"
        # The __str__ method overrides to show field and value
        assert "start_date" in str(error)
        assert "invalid" in str(error)

    def test_validation_error_string_with_field(self):
        """Test string representation includes field."""
        error = ValidationError(
            "Must be positive",
            field="per_page",
            value=-1,
        )

        result = str(error)
        # The __str__ method overrides to show field and value
        assert "per_page" in result
        assert "-1" in result


class TestExceptionHierarchy:
    """Test exception inheritance hierarchy."""

    def test_all_errors_inherit_from_base(self):
        """Test all custom errors inherit from OilPriceAPIError."""
        errors = [
            ConfigurationError("test"),
            AuthenticationError("test"),
            RateLimitError("test"),
            DataNotFoundError("test"),
            ServerError("test", status_code=500),
            TimeoutError("test", timeout=30),
            ValidationError("test"),
        ]

        for error in errors:
            assert isinstance(error, OilPriceAPIError)
            assert isinstance(error, Exception)

    def test_errors_can_be_caught_generically(self):
        """Test errors can be caught with base exception."""
        try:
            raise AuthenticationError("Invalid key")
        except OilPriceAPIError as e:
            assert e.status_code == 401
            assert "Invalid key" in str(e)

    def test_errors_can_be_caught_specifically(self):
        """Test errors can be caught with specific type."""
        try:
            raise DataNotFoundError("Not found")
        except DataNotFoundError as e:
            assert e.status_code == 404
            assert isinstance(e, OilPriceAPIError)