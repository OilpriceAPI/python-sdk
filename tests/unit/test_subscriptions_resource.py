"""
Unit tests for SubscriptionsResource + market_brief (sync), #3245.
"""

from unittest.mock import patch

import pytest

from oilpriceapi import (
    MarketBrief,
    OilPriceAPI,
    Subscription,
    SubscriptionEvent,
    SubscriptionEventsPage,
)
from oilpriceapi._subscriptions_common import (
    DEFAULT_SOURCE,
    build_attribution_headers,
    build_create_body,
    normalize_interval,
)


class TestIntervalMapping:
    """Friendly interval → interval_seconds conversion."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("1m", 60),
            ("5m", 300),
            ("15m", 900),
            ("1h", 3600),
            ("hourly", 3600),
            ("daily", 86400),
            ("1d", 86400),
            ("30s", 30),
            ("2h", 7200),
            ("300", 300),
            (300, 300),
            ("5M", 300),  # case-insensitive alias
            (" 5m ", 300),  # whitespace tolerant
        ],
    )
    def test_normalize_interval(self, value, expected):
        assert normalize_interval(value) == expected

    @pytest.mark.parametrize("bad", ["", "abc", "0", 0, -5, "-1h", "5x", True])
    def test_normalize_interval_invalid(self, bad):
        with pytest.raises(ValueError):
            normalize_interval(bad)

    def test_build_create_body(self):
        body = build_create_body(["BRENT_CRUDE_USD"], "5m", name="Brent")
        assert body == {
            "codes": ["BRENT_CRUDE_USD"],
            "interval_seconds": 300,
            "name": "Brent",
        }

    def test_build_create_body_no_name(self):
        body = build_create_body(["WTI_USD"], 600)
        assert "name" not in body
        assert body["interval_seconds"] == 600

    def test_attribution_headers_default_source(self):
        assert build_attribution_headers() == {"X-OPA-Source": DEFAULT_SOURCE}

    def test_attribution_headers_custom(self):
        headers = build_attribution_headers(source="mcp", tool="claude")
        assert headers == {"X-OPA-Source": "mcp", "X-OPA-Tool": "claude"}


class TestSubscriptionsResource:
    @pytest.fixture
    def client(self):
        return OilPriceAPI(api_key="test_key")

    def test_list(self, client):
        payload = {
            "status": "success",
            "data": {
                "subscriptions": [
                    {
                        "id": "abc-123",
                        "name": "Brent watch",
                        "codes": ["BRENT_CRUDE_USD"],
                        "interval_seconds": 300,
                        "status": "active",
                    }
                ]
            },
        }
        with patch.object(client, "request", return_value=payload):
            subs = client.subscriptions.list()
        assert len(subs) == 1
        assert isinstance(subs[0], Subscription)
        assert subs[0].id == "abc-123"
        assert subs[0].codes == ["BRENT_CRUDE_USD"]

    def test_create_maps_interval_and_headers(self, client):
        payload = {
            "status": "success",
            "data": {
                "subscription": {
                    "id": "new-1",
                    "name": "My watch",
                    "codes": ["WTI_USD"],
                    "interval_seconds": 300,
                    "status": "active",
                }
            },
        }
        with patch.object(client, "request", return_value=payload) as mock_req:
            sub = client.subscriptions.create(["WTI_USD"], interval="5m", name="My watch")

        assert isinstance(sub, Subscription)
        assert sub.id == "new-1"
        _, kwargs = mock_req.call_args
        assert kwargs["json_data"]["interval_seconds"] == 300
        assert kwargs["json_data"]["codes"] == ["WTI_USD"]
        assert kwargs["json_data"]["name"] == "My watch"
        # Default attribution source applied.
        assert kwargs["headers"]["X-OPA-Source"] == DEFAULT_SOURCE

    def test_create_custom_source_and_tool(self, client):
        payload = {"data": {"subscription": {"id": "x", "codes": ["WTI_USD"], "interval_seconds": 60}}}
        with patch.object(client, "request", return_value=payload) as mock_req:
            client.subscriptions.create(["WTI_USD"], interval=60, source="mcp", tool="claude")
        _, kwargs = mock_req.call_args
        assert kwargs["headers"] == {"X-OPA-Source": "mcp", "X-OPA-Tool": "claude"}

    def test_delete(self, client):
        with patch.object(client, "request", return_value=None) as mock_req:
            assert client.subscriptions.delete("abc-123") is True
        args, kwargs = mock_req.call_args
        assert kwargs["method"] == "DELETE"
        assert kwargs["path"] == "/v1/subscriptions/abc-123"

    def test_events(self, client):
        payload = {
            "status": "success",
            "data": {
                "cursor": 42,
                "has_more": True,
                "events": [
                    {"seq": 41, "watch_id": "abc-123", "type": "threshold", "code": "BRENT_CRUDE_USD"},
                    {"seq": 42, "watch_id": "abc-123", "type": "threshold", "code": "BRENT_CRUDE_USD"},
                ],
            },
        }
        with patch.object(client, "request", return_value=payload) as mock_req:
            page = client.subscriptions.events(since=40)

        assert isinstance(page, SubscriptionEventsPage)
        assert page.cursor == 42
        assert page.has_more is True
        assert len(page) == 2
        assert all(isinstance(e, SubscriptionEvent) for e in page)
        _, kwargs = mock_req.call_args
        assert kwargs["params"]["since"] == 40

    def test_events_no_since(self, client):
        payload = {"data": {"cursor": 0, "has_more": False, "events": []}}
        with patch.object(client, "request", return_value=payload) as mock_req:
            page = client.subscriptions.events()
        assert page.has_more is False
        assert len(page) == 0
        _, kwargs = mock_req.call_args
        assert kwargs["params"] == {}


class TestMarketBrief:
    @pytest.fixture
    def client(self):
        return OilPriceAPI(api_key="test_key")

    def test_market_brief(self, client):
        payload = {
            "status": "success",
            "data": {
                "as_of": "2026-06-21T12:00:00Z",
                "codes": ["BRENT_CRUDE_USD"],
                "commodities": [
                    {
                        "code": "BRENT_CRUDE_USD",
                        "name": "Brent Crude",
                        "price": 78.5,
                        "currency": "USD",
                        "change_24h_pct": 1.2,
                        "forecast_1m": {"point": 80.0, "low": 76.0, "high": 84.0, "confidence": "medium"},
                        "stale": False,
                    }
                ],
            },
        }
        with patch.object(client, "request", return_value=payload) as mock_req:
            brief = client.market_brief(["BRENT_CRUDE_USD"])

        assert isinstance(brief, MarketBrief)
        assert brief.codes == ["BRENT_CRUDE_USD"]
        assert brief.commodities[0].price == 78.5
        assert brief.commodities[0].forecast_1m.point == 80.0
        _, kwargs = mock_req.call_args
        assert kwargs["params"]["codes"] == "BRENT_CRUDE_USD"
        assert "narrative" not in kwargs["params"]

    def test_market_brief_narrative(self, client):
        payload = {
            "data": {
                "codes": ["WTI_USD", "BRENT_CRUDE_USD"],
                "commodities": [],
                "narrative": "Crude markets edged higher.",
            }
        }
        with patch.object(client, "request", return_value=payload) as mock_req:
            brief = client.market_brief(["WTI_USD", "BRENT_CRUDE_USD"], narrative=True)
        assert brief.narrative == "Crude markets edged higher."
        _, kwargs = mock_req.call_args
        assert kwargs["params"]["codes"] == "WTI_USD,BRENT_CRUDE_USD"
        assert kwargs["params"]["narrative"] == "true"


class TestMarketBriefForecastConfidence:
    """#2026-07-03 live-contract catch: API sends numeric confidence (0.65),
    SDK previously required a string label — accept both."""

    def test_confidence_accepts_float(self):
        from oilpriceapi.models import MarketBriefForecast

        f = MarketBriefForecast(point=71.5, low=65.0, high=78.0, confidence=0.65)
        assert f.confidence == 0.65

    def test_confidence_accepts_label(self):
        from oilpriceapi.models import MarketBriefForecast

        f = MarketBriefForecast(confidence="high")
        assert f.confidence == "high"
