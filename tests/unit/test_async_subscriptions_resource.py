"""
Unit tests for AsyncSubscriptionsResource + async market_brief, #3245.
"""

from unittest.mock import AsyncMock, patch

import pytest

from oilpriceapi import (
    AsyncOilPriceAPI,
    MarketBrief,
    Subscription,
    SubscriptionEvent,
    SubscriptionEventsPage,
)
from oilpriceapi._subscriptions_common import DEFAULT_SOURCE


@pytest.fixture
def client():
    return AsyncOilPriceAPI(api_key="test_key")


class TestAsyncSubscriptionsResource:
    @pytest.mark.asyncio
    async def test_list(self, client):
        payload = {
            "data": {
                "subscriptions": [
                    {"id": "abc-123", "codes": ["BRENT_CRUDE_USD"], "interval_seconds": 300, "status": "active"}
                ]
            }
        }
        with patch.object(client, "request", new=AsyncMock(return_value=payload)):
            subs = await client.subscriptions.list()
        assert len(subs) == 1
        assert isinstance(subs[0], Subscription)
        assert subs[0].id == "abc-123"

    @pytest.mark.asyncio
    async def test_create_maps_interval_and_headers(self, client):
        payload = {"data": {"subscription": {"id": "n1", "codes": ["WTI_USD"], "interval_seconds": 3600}}}
        mock = AsyncMock(return_value=payload)
        with patch.object(client, "request", new=mock):
            sub = await client.subscriptions.create(["WTI_USD"], interval="1h", name="hr")
        assert isinstance(sub, Subscription)
        _, kwargs = mock.call_args
        assert kwargs["json_data"]["interval_seconds"] == 3600
        assert kwargs["json_data"]["name"] == "hr"
        assert kwargs["headers"]["X-OPA-Source"] == DEFAULT_SOURCE

    @pytest.mark.asyncio
    async def test_create_custom_source(self, client):
        payload = {"data": {"subscription": {"id": "x", "codes": ["WTI_USD"], "interval_seconds": 60}}}
        mock = AsyncMock(return_value=payload)
        with patch.object(client, "request", new=mock):
            await client.subscriptions.create(["WTI_USD"], interval=60, source="mcp", tool="claude")
        _, kwargs = mock.call_args
        assert kwargs["headers"] == {"X-OPA-Source": "mcp", "X-OPA-Tool": "claude"}

    @pytest.mark.asyncio
    async def test_delete(self, client):
        mock = AsyncMock(return_value=None)
        with patch.object(client, "request", new=mock):
            assert await client.subscriptions.delete("abc-123") is True
        _, kwargs = mock.call_args
        assert kwargs["method"] == "DELETE"
        assert kwargs["path"] == "/v1/subscriptions/abc-123"

    @pytest.mark.asyncio
    async def test_events(self, client):
        payload = {
            "data": {
                "cursor": 7,
                "has_more": False,
                "events": [{"seq": 7, "watch_id": "abc-123", "type": "threshold", "code": "WTI_USD"}],
            }
        }
        mock = AsyncMock(return_value=payload)
        with patch.object(client, "request", new=mock):
            page = await client.subscriptions.events(since=6, limit=10)
        assert isinstance(page, SubscriptionEventsPage)
        assert page.cursor == 7
        assert page.has_more is False
        assert len(page) == 1
        assert isinstance(page.events[0], SubscriptionEvent)
        _, kwargs = mock.call_args
        assert kwargs["params"] == {"since": 6, "limit": 10}


class TestAsyncMarketBrief:
    @pytest.mark.asyncio
    async def test_market_brief(self, client):
        payload = {
            "data": {
                "codes": ["BRENT_CRUDE_USD"],
                "commodities": [
                    {"code": "BRENT_CRUDE_USD", "price": 78.5, "currency": "USD"}
                ],
            }
        }
        mock = AsyncMock(return_value=payload)
        with patch.object(client, "request", new=mock):
            brief = await client.market_brief(["BRENT_CRUDE_USD"], narrative=True)
        assert isinstance(brief, MarketBrief)
        assert brief.commodities[0].price == 78.5
        _, kwargs = mock.call_args
        assert kwargs["params"]["codes"] == "BRENT_CRUDE_USD"
        assert kwargs["params"]["narrative"] == "true"
