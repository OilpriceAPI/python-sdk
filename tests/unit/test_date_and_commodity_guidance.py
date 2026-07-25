"""Regression tests for date validation and live commodity-code guidance."""

from datetime import date, datetime
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from oilpriceapi import AsyncOilPriceAPI, OilPriceAPI
from oilpriceapi.exceptions import BadRequestError, NetworkError, error_from_response
from oilpriceapi.resource_validators import format_date


@pytest.mark.parametrize(
    "value",
    [
        "2025-03-010",
        "2025-3-01",
        "2025-02-29",
        "2025-03-01T12:00:00",
        "",
    ],
)
def test_format_date_rejects_malformed_or_non_date_strings(value):
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        format_date(value)


def test_format_date_accepts_strict_strings_and_python_date_types():
    assert format_date("2024-02-29") == "2024-02-29"
    assert format_date(date(2024, 2, 29)) == "2024-02-29"
    assert format_date(datetime(2024, 2, 29, 23, 59)) == "2024-02-29"


def test_malformed_historical_date_fails_without_request():
    client = OilPriceAPI(api_key="test-key")
    with patch.object(client, "request_with_headers") as request:
        with pytest.raises(ValueError, match="YYYY-MM-DD"):
            client.historical.get("BRENT_CRUDE_USD", start_date="2025-03-010")
    request.assert_not_called()
    client.close()


def test_well_formed_reversed_range_is_left_to_server():
    client = OilPriceAPI(api_key="test-key")
    response = {"status": "success", "data": {"prices": []}}
    with patch.object(
        client,
        "request_with_headers",
        return_value=(response, {}),
    ) as request:
        client.historical.get(
            "BRENT_CRUDE_USD",
            start_date="2025-03-02",
            end_date="2025-03-01",
        )
    request.assert_called_once()
    assert request.call_args.kwargs["params"]["start_date"] == "2025-03-02"
    assert request.call_args.kwargs["params"]["end_date"] == "2025-03-01"
    client.close()


@pytest.mark.asyncio
async def test_async_malformed_historical_date_fails_without_request():
    client = AsyncOilPriceAPI(api_key="test-key")
    client.request = AsyncMock()
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        await client.historical.get(
            "BRENT_CRUDE_USD",
            start_date="2025-03-010",
        )
    client.request.assert_not_awaited()
    await client.close()


def test_commodities_search_uses_current_catalog_and_ranks_code_matches():
    client = OilPriceAPI(api_key="test-key")
    catalog = [
        {
            "code": "WTI_USD",
            "name": "WTI Crude Oil",
            "category": "Crude Oil",
        },
        {
            "code": "BRENT_CRUDE_USD",
            "name": "Brent Crude Oil",
            "category": "Crude Oil",
        },
        {
            "code": "BRENT_CRUDE_EUR",
            "name": "Brent Crude Oil",
            "category": "Crude Oil",
        },
    ]
    with patch.object(
        client,
        "request",
        return_value={"data": {"commodities": catalog, "metadata": {"count": 3}}},
    ) as request:
        matches = client.commodities.search("brent crude usd", limit=2)
    request.assert_called_once_with(method="GET", path="/v1/commodities")
    assert [item["code"] for item in matches] == [
        "BRENT_CRUDE_USD",
        "BRENT_CRUDE_EUR",
    ]
    client.close()


def test_commodities_search_returns_empty_list_for_empty_catalog():
    client = OilPriceAPI(api_key="test-key")
    with patch.object(client, "request", return_value={"data": []}):
        assert client.commodities.search("brent") == []
    client.close()


def test_commodities_search_preserves_network_error():
    client = OilPriceAPI(api_key="test-key")
    network_error = NetworkError("catalog unavailable")
    with patch.object(client, "request", side_effect=network_error):
        with pytest.raises(NetworkError) as raised:
            client.commodities.search("brent")
    assert raised.value is network_error
    client.close()


@pytest.mark.asyncio
async def test_async_commodities_search_matches_sync_behavior():
    client = AsyncOilPriceAPI(api_key="test-key")
    client.request = AsyncMock(
        return_value={
            "data": [
                {"code": "WTI_USD", "name": "WTI Crude Oil"},
                {"code": "BRENT_CRUDE_USD", "name": "Brent Crude Oil"},
            ]
        }
    )
    matches = await client.commodities.search("brent")
    assert [item["code"] for item in matches] == ["BRENT_CRUDE_USD"]
    await client.close()


def test_nested_invalid_code_response_exposes_sanitized_suggestions():
    secret = "secret-test-key"
    response = httpx.Response(
        400,
        request=httpx.Request(
            "GET",
            "https://api.oilpriceapi.com/v1/prices/latest",
            headers={"Authorization": f"Token {secret}"},
        ),
        json={
            "status": "fail",
            "data": {
                "error": "invalid_code",
                "message": f"Unknown code; credential {secret}",
                "suggestions": [
                    "BRENT_CRUDE_USD",
                    secret,
                    {"unexpected": "shape"},
                ],
                "invalid_codes": ["BRENNT"],
            },
        },
    )

    error = error_from_response(response, commodity="BRENNT")

    assert isinstance(error, BadRequestError)
    assert error.code == "invalid_code"
    assert error.suggestions == ["BRENT_CRUDE_USD", "[REDACTED]"]
    assert error.invalid_codes == ["BRENNT"]
    assert secret not in error.message
    assert secret not in repr(error.suggestions)


def test_legacy_top_level_error_message_is_not_misclassified_as_a_code():
    response = httpx.Response(
        400,
        request=httpx.Request("GET", "https://api.oilpriceapi.com/v1/prices/latest"),
        json={"error": "Invalid request parameters"},
    )

    error = error_from_response(response)

    assert error.message == "Invalid request parameters"
    assert error.code is None
