"""
Unit tests for AsyncWellProductionResource (#50).

Mirror of tests/unit/test_well_production_resource.py for the async client.
No API key required — all HTTP traffic is mocked.
"""

from unittest.mock import AsyncMock, patch

import pytest

from oilpriceapi import AsyncOilPriceAPI


SUMMARY_DATA = {
    "national": {
        "period": "2026-07",
        "oil_bbl": 0,
        "gas_mcf": 0,
        "water_bbl": 0,
        "boe": 0,
        "days_producing": None,
        "source": "market_reporting",
    },
    "top_states": [
        {
            "state": "TX",
            "period": "2026-04",
            "oil_bbl": 174743000,
            "oil_bpd": 5824767,
            "gas_mcf": 1164406000,
            "boe": 368810667,
        }
    ],
}


@pytest.fixture
def client():
    return AsyncOilPriceAPI(api_key="test_key")


class TestAsyncWellProductionResource:
    @pytest.mark.asyncio
    async def test_summary(self, client):
        mock = AsyncMock(return_value={"status": "success", "data": SUMMARY_DATA})
        with patch.object(client, "request", new=mock):
            summary = await client.well_production.summary()

        assert summary["top_states"][0]["state"] == "TX"
        _, kwargs = mock.call_args
        assert kwargs["path"] == "/v1/well-production"

    @pytest.mark.asyncio
    async def test_states_with_period(self, client):
        payload = {"data": {"period": "2026-04", "count": 0, "states": []}}
        mock = AsyncMock(return_value=payload)
        with patch.object(client, "request", new=mock):
            result = await client.well_production.states(period="2026-04")

        assert result["count"] == 0
        _, kwargs = mock.call_args
        assert kwargs["path"] == "/v1/well-production/states"
        assert kwargs["params"] == {"period": "2026-04"}

    @pytest.mark.asyncio
    async def test_state_detail_with_date_range(self, client):
        payload = {"data": {"state": "TX", "count": 0, "data": []}}
        mock = AsyncMock(return_value=payload)
        with patch.object(client, "request", new=mock):
            result = await client.well_production.state(
                "TX", start_date="2026-01-01", end_date="2026-04-30"
            )

        assert result["state"] == "TX"
        _, kwargs = mock.call_args
        assert kwargs["path"] == "/v1/well-production/states/TX"
        assert kwargs["params"] == {"start_date": "2026-01-01", "end_date": "2026-04-30"}

    @pytest.mark.asyncio
    async def test_well_normalizes_api_number(self, client):
        payload = {"data": {"api_number": "42285343290000", "count": 0, "data": []}}
        mock = AsyncMock(return_value=payload)
        with patch.object(client, "request", new=mock):
            await client.well_production.well("42-285-34329-00-00")

        _, kwargs = mock.call_args
        assert kwargs["path"] == "/v1/well-production/wells/42285343290000"

    @pytest.mark.asyncio
    async def test_well_invalid_api_number_raises_before_http(self, client):
        mock = AsyncMock()
        with patch.object(client, "request", new=mock):
            with pytest.raises(ValueError, match="14 digits"):
                await client.well_production.well("123")

        mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_top_producers_params(self, client):
        payload = {"data": {"state": "NM", "count": 0, "producers": []}}
        mock = AsyncMock(return_value=payload)
        with patch.object(client, "request", new=mock):
            await client.well_production.top_producers("NM", limit=10, months=6)

        _, kwargs = mock.call_args
        assert kwargs["path"] == "/v1/well-production/top-producers"
        assert kwargs["params"] == {"state_code": "NM", "limit": 10, "months": 6}

    @pytest.mark.asyncio
    async def test_cycle_time_filters(self, client):
        payload = {"data": {"well_count": 0, "cycle_time_stats": {}}}
        mock = AsyncMock(return_value=payload)
        with patch.object(client, "request", new=mock):
            await client.well_production.cycle_time(state="TX", formation="EAGLE FORD")

        _, kwargs = mock.call_args
        assert kwargs["path"] == "/v1/well-production/cycle-time"
        assert kwargs["params"] == {"state": "TX", "formation": "EAGLE FORD"}

    @pytest.mark.asyncio
    async def test_cycle_time_cohorts_group_by(self, client):
        payload = {"data": {"group_by": "quarter", "cohorts": {}}}
        mock = AsyncMock(return_value=payload)
        with patch.object(client, "request", new=mock):
            result = await client.well_production.cycle_time_cohorts(
                state="TX", group_by="quarter"
            )

        assert result["cohorts"] == {}
        _, kwargs = mock.call_args
        assert kwargs["path"] == "/v1/well-production/cycle-time/cohorts"
        assert kwargs["params"] == {"state": "TX", "group_by": "quarter"}
