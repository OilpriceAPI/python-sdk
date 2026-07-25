"""Pinned compatibility tests for canonical and legacy API error contracts."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from oilpriceapi import AsyncOilPriceAPI, OilPriceAPI
from oilpriceapi.exceptions import (
    AuthenticationError,
    BadRequestError,
    DataNotFoundError,
    NetworkError,
    OilPriceAPIError,
    PaymentRequiredError,
    PermissionDeniedError,
    RateLimitError,
    ServerError,
    TimeoutError,
    ValidationError,
    error_from_response,
)

FIXTURES = Path(__file__).parents[1] / "fixtures" / "error_contract"


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text())


def make_response(
    status_code: int,
    *,
    json_body=None,
    text: str = "",
    headers=None,
    api_key: str = "secret-test-key",
) -> httpx.Response:
    request = httpx.Request(
        "GET",
        "https://api.oilpriceapi.com/v1/prices/latest",
        headers={"Authorization": f"Token {api_key}"},
    )
    kwargs = {"headers": headers or {}, "request": request}
    if json_body is not None:
        kwargs["json"] = json_body
    else:
        kwargs["text"] = text
    return httpx.Response(status_code, **kwargs)


def test_canonical_nested_error_preserves_recovery_contract():
    response = make_response(
        403,
        json_body=load_fixture("canonical.json.fixture"),
        headers={
            "X-Request-ID": "req_header_fallback",
            "Authorization": "Token secret-test-key",
        },
    )

    error = error_from_response(response)

    assert isinstance(error, PermissionDeniedError)
    assert error.status_code == 403
    assert error.code == "plan_upgrade_required"
    assert error.machine_code == "plan_upgrade_required"
    assert error.message == "Futures data requires a higher plan."
    assert error.request_id == "req_canonical_123"
    assert error.docs_url.endswith("/plan-upgrade-required")
    assert error.current_plan == "developer"
    assert error.required_plan == "professional"
    assert error.required_feature == "futures"
    assert error.remediation_url.endswith("/dashboard/billing")
    assert error.retry_metadata == {"retryable": False}
    assert error.raw_body == load_fixture("canonical.json.fixture")
    assert error.headers["x-request-id"] == "req_header_fallback"
    assert "authorization" not in error.headers
    assert "secret-test-key" not in error.raw_text
    assert "secret-test-key" not in repr(error.raw_body)


def test_legacy_flat_error_and_rate_limit_headers_are_normalized():
    response = make_response(
        429,
        json_body=load_fixture("legacy-flat.json.fixture"),
        headers={
            "Retry-After": "12",
            "X-RateLimit-Limit": "1000",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "1705320000",
        },
    )

    error = error_from_response(response)

    assert isinstance(error, RateLimitError)
    assert error.code == "rate_limit_exceeded"
    assert error.request_id == "req_legacy_429"
    assert error.retry_after == 12
    assert error.limit == "1000"
    assert error.remaining == "0"
    assert error.reset_time is not None
    assert error.retry_metadata["retry_after"] == 12
    assert error.retry_metadata["limit"] == "1000"


@pytest.mark.parametrize(
    ("status_code", "expected_type"),
    [
        (400, BadRequestError),
        (401, AuthenticationError),
        (402, PaymentRequiredError),
        (403, PermissionDeniedError),
        (404, DataNotFoundError),
        (422, ValidationError),
        (429, RateLimitError),
        (503, ServerError),
    ],
)
def test_status_codes_have_stable_subclasses(status_code, expected_type):
    error = error_from_response(
        make_response(
            status_code,
            json_body={"message": "Stable message", "code": "stable_code"},
        )
    )

    assert isinstance(error, expected_type)
    assert isinstance(error, OilPriceAPIError)
    assert error.status_code == status_code
    assert error.code == "stable_code"


def test_malformed_non_json_body_is_preserved_without_losing_type():
    error = error_from_response(
        make_response(
            502,
            text="<html>upstream unavailable</html>",
            headers={"Content-Type": "text/html"},
        )
    )

    assert isinstance(error, ServerError)
    assert error.message == "<html>upstream unavailable</html>"
    assert error.raw_body == "<html>upstream unavailable</html>"
    assert error.raw_text == "<html>upstream unavailable</html>"
    assert error.headers["content-type"] == "text/html"


def test_sync_client_normalizes_timeout_and_network_failures():
    timeout_request = httpx.Request("GET", "https://api.oilpriceapi.com/v1/prices/latest")
    client = OilPriceAPI(api_key="secret-test-key", max_retries=1)

    with patch.object(
        client._client,
        "request",
        side_effect=httpx.ReadTimeout("timed out", request=timeout_request),
    ):
        with pytest.raises(TimeoutError) as timeout:
            client.request("GET", "/v1/prices/latest")

    assert timeout.value.timeout == client.timeout

    with patch.object(
        client._client,
        "request",
        side_effect=httpx.ConnectError(
            "connection failed for secret-test-key",
            request=timeout_request,
        ),
    ):
        with pytest.raises(NetworkError) as network:
            client.request("GET", "/v1/prices/latest")

    assert "secret-test-key" not in str(network.value)
    assert network.value.cause_type == "ConnectError"


@pytest.mark.asyncio
async def test_async_client_uses_same_canonical_error_contract():
    response = make_response(402, json_body=load_fixture("canonical.json.fixture"))

    async with AsyncOilPriceAPI(api_key="secret-test-key", max_retries=1) as client:
        with patch.object(client._client, "request", new=AsyncMock(return_value=response)):
            with pytest.raises(PaymentRequiredError) as captured:
                await client.request("GET", "/v1/prices/latest")

    assert captured.value.code == "plan_upgrade_required"
    assert captured.value.request_id == "req_canonical_123"
