"""
Unit tests for DemoResource (mocked — no network).

The live contract is asserted separately in
tests/integration/test_demo_contract.py (marked `live`).
"""

from unittest.mock import patch

import pytest

from oilpriceapi import OilPriceAPI
from oilpriceapi.resources.demo import DemoResource

DEMO_PRICES_ENVELOPE = {
    "status": "success",
    "data": {
        "prices": [
            {"code": "BRENT_CRUDE_USD", "name": "Brent Crude", "price": 80.4,
             "currency": "USD", "updated_at": "2026-06-20T10:00:00Z"},
            {"code": "WTI_USD", "name": "WTI", "price": 76.1,
             "currency": "USD", "updated_at": "2026-06-20T10:00:00Z"},
        ],
        "meta": {"demo_mode": True, "available_commodities": 9},
        "examples": {},
    },
}

DEMO_COMMODITIES_ENVELOPE = {
    "status": "success",
    "data": {
        "commodities": {"crude_oil": [{"code": "BRENT_CRUDE_USD"}], "fx": [{"code": "EUR_USD"}]},
        "meta": {"total": 2, "categories": ["crude_oil", "fx"],
                 "free_commodities": ["BRENT_CRUDE_USD", "WTI_USD"]},
    },
}


class TestDemoResourceStandalone:
    """DemoResource with no client issues its own unauthenticated requests."""

    def test_prices_parses_envelope(self):
        demo = DemoResource()
        with patch("oilpriceapi.resources.demo.httpx.get") as mock_get:
            mock_get.return_value.json.return_value = DEMO_PRICES_ENVELOPE
            mock_get.return_value.raise_for_status.return_value = None

            data = demo.prices()

            assert [p["code"] for p in data["prices"]] == ["BRENT_CRUDE_USD", "WTI_USD"]
            assert data["meta"]["demo_mode"] is True
            # No auth header / api key required.
            url = mock_get.call_args.args[0]
            assert url.endswith("/v1/demo/prices")

    def test_prices_with_codes_filter(self):
        demo = DemoResource()
        with patch("oilpriceapi.resources.demo.httpx.get") as mock_get:
            mock_get.return_value.json.return_value = DEMO_PRICES_ENVELOPE
            mock_get.return_value.raise_for_status.return_value = None

            demo.prices(codes=["BRENT_CRUDE_USD", "WTI_USD"])

            url = mock_get.call_args.args[0]
            assert "codes=BRENT_CRUDE_USD,WTI_USD" in url

    def test_commodities_parses_envelope(self):
        demo = DemoResource()
        with patch("oilpriceapi.resources.demo.httpx.get") as mock_get:
            mock_get.return_value.json.return_value = DEMO_COMMODITIES_ENVELOPE
            mock_get.return_value.raise_for_status.return_value = None

            data = demo.commodities()

            assert "free_commodities" in data["meta"]
            assert data["meta"]["total"] == 2


class TestDemoResourceViaClient:
    """client.demo reuses the authenticated client's transport."""

    @pytest.fixture
    def client(self):
        return OilPriceAPI(api_key="test_key")

    def test_client_exposes_demo(self, client):
        assert isinstance(client.demo, DemoResource)
        assert client.demo.client is client

    def test_demo_prices_via_client(self, client):
        with patch.object(client, "request", return_value=DEMO_PRICES_ENVELOPE) as req:
            data = client.demo.prices()

            assert data["prices"][0]["code"] == "BRENT_CRUDE_USD"
            _, kwargs = req.call_args
            assert kwargs["path"] == "/v1/demo/prices"
