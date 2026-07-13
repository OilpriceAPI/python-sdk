"""
Unit tests for WellProductionResource (#50).

Fixture shapes mirror live /v1/well-production responses captured 2026-07-13.
No API key required — all HTTP traffic is mocked.
"""

from unittest.mock import Mock, patch

import httpx
import pytest

from oilpriceapi import OilPriceAPI
from oilpriceapi.exceptions import DataNotFoundError, OilPriceAPIError


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
        },
        {
            "state": "NM",
            "period": "2026-04",
            "oil_bbl": 70985000,
            "oil_bpd": 2366167,
            "gas_mcf": 359485000,
            "boe": 130899167,
        },
    ],
}

STATES_DATA = {
    "period": "2026-04",
    "count": 2,
    "states": SUMMARY_DATA["top_states"],
}

STATE_DETAIL_DATA = {
    "state": "TX",
    "period": {"start": "2026-01-01", "end": "2026-04-30"},
    "count": 1,
    "data": [
        {
            "period": "2026-01",
            "oil_bbl": 172442000,
            "gas_mcf": 1156809000,
            "water_bbl": None,
            "boe": 365243500,
            "days_producing": None,
            "source": "eia_api",
        }
    ],
}

WELL_DATA = {
    "api_number": "42285343290000",
    "operator": "FW EAGLE FORD I, LLC",
    "well_name": "Test Well #1",
    "state": "TX",
    "count": 1,
    "data": [
        {
            "period": "2025-09",
            "oil_bbl": 12000,
            "gas_mcf": 34000,
            "water_bbl": 5000,
            "boe": 17667,
            "days_producing": 30,
            "source": "state_regulatory",
        }
    ],
}

CYCLE_TIME_DATA = {
    "filters": {"state": "TX"},
    "well_count": 6988,
    "wells_with_cycle_data": 2,
    "cycle_time_stats": {
        "count": 2,
        "median_days": 132,
        "p25_days": 46,
        "p75_days": 132,
        "p90_days": 132,
        "min_days": 46,
        "max_days": 132,
        "avg_days": 89,
    },
}

COHORTS_DATA = {
    "group_by": "quarter",
    "cohorts": {
        "2025-Q2": {
            "well_count": 1,
            "wells_with_data": 1,
            "stats": {"count": 1, "median_days": 132, "avg_days": 132},
        }
    },
}


@pytest.fixture
def client():
    """Create a test client."""
    return OilPriceAPI(api_key="test_key")


def _http_response(status_code, json_data):
    """Build a mock httpx.Response for negative-path tests."""
    response = Mock(spec=httpx.Response)
    response.status_code = status_code
    response.json.return_value = json_data
    response.headers = {}
    response.text = str(json_data)
    return response


class TestWellProductionResource:
    """Happy-path tests (patch client.request, matching repo convention)."""

    def test_summary(self, client):
        """Test national production overview."""
        with patch.object(client, "request", return_value={"status": "success", "data": SUMMARY_DATA}) as mock:
            summary = client.well_production.summary()

        assert summary["national"]["period"] == "2026-07"
        assert summary["top_states"][0]["state"] == "TX"
        _, kwargs = mock.call_args
        assert kwargs["path"] == "/v1/well-production"

    def test_states_default_period(self, client):
        """Test state-level production without a period."""
        with patch.object(client, "request", return_value={"data": STATES_DATA}) as mock:
            result = client.well_production.states()

        assert result["count"] == 2
        _, kwargs = mock.call_args
        assert kwargs["path"] == "/v1/well-production/states"
        assert kwargs["params"] == {}

    def test_states_with_period(self, client):
        """Test period param is passed as YYYY-MM."""
        with patch.object(client, "request", return_value={"data": STATES_DATA}) as mock:
            result = client.well_production.states(period="2026-04")

        assert result["states"][0]["oil_bpd"] == 5824767
        _, kwargs = mock.call_args
        assert kwargs["params"] == {"period": "2026-04"}

    def test_state_detail_with_date_range(self, client):
        """Test per-state history with start/end dates."""
        with patch.object(client, "request", return_value={"data": STATE_DETAIL_DATA}) as mock:
            result = client.well_production.state(
                "TX", start_date="2026-01-01", end_date="2026-04-30"
            )

        assert result["state"] == "TX"
        assert result["data"][0]["source"] == "eia_api"
        _, kwargs = mock.call_args
        assert kwargs["path"] == "/v1/well-production/states/TX"
        assert kwargs["params"] == {"start_date": "2026-01-01", "end_date": "2026-04-30"}

    def test_well_normalizes_api_number(self, client):
        """Test dashed API numbers are normalized to 14 digits."""
        with patch.object(client, "request", return_value={"data": WELL_DATA}) as mock:
            well = client.well_production.well("42-285-34329-00-00")

        assert well["operator"] == "FW EAGLE FORD I, LLC"
        _, kwargs = mock.call_args
        assert kwargs["path"] == "/v1/well-production/wells/42285343290000"

    def test_well_invalid_api_number_raises_before_http(self, client):
        """Test invalid API numbers fail client-side (no request made)."""
        with patch.object(client, "request") as mock:
            with pytest.raises(ValueError, match="14 digits"):
                client.well_production.well("123")

        mock.assert_not_called()

    def test_top_producers_params(self, client):
        """Test state_code/limit/months params."""
        payload = {"data": {"state": "NM", "count": 0, "producers": []}}
        with patch.object(client, "request", return_value=payload) as mock:
            result = client.well_production.top_producers("NM", limit=10, months=6)

        assert result["producers"] == []
        _, kwargs = mock.call_args
        assert kwargs["path"] == "/v1/well-production/top-producers"
        assert kwargs["params"] == {"state_code": "NM", "limit": 10, "months": 6}

    def test_cycle_time_filters(self, client):
        """Test cycle-time filter params are compacted (None dropped)."""
        with patch.object(client, "request", return_value={"data": CYCLE_TIME_DATA}) as mock:
            result = client.well_production.cycle_time(state="TX", operator="FW EAGLE FORD I, LLC")

        assert result["cycle_time_stats"]["median_days"] == 132
        _, kwargs = mock.call_args
        assert kwargs["path"] == "/v1/well-production/cycle-time"
        assert kwargs["params"] == {"state": "TX", "operator": "FW EAGLE FORD I, LLC"}

    def test_cycle_time_geographic_cohort(self, client):
        """Test lat/lng/radius params."""
        with patch.object(client, "request", return_value={"data": CYCLE_TIME_DATA}) as mock:
            client.well_production.cycle_time(lat=31.9, lng=-102.1, radius_miles=25)

        _, kwargs = mock.call_args
        assert kwargs["params"] == {"lat": 31.9, "lng": -102.1, "radius_miles": 25}

    def test_cycle_time_cohorts_group_by(self, client):
        """Test cohort comparison with group_by."""
        with patch.object(client, "request", return_value={"data": COHORTS_DATA}) as mock:
            result = client.well_production.cycle_time_cohorts(state="TX", group_by="quarter")

        assert "2025-Q2" in result["cohorts"]
        _, kwargs = mock.call_args
        assert kwargs["path"] == "/v1/well-production/cycle-time/cohorts"
        assert kwargs["params"] == {"state": "TX", "group_by": "quarter"}

    def test_empty_successful_response(self, client):
        """Test empty-but-successful payloads pass through unchanged."""
        payload = {"status": "success", "data": {"period": None, "count": 0, "states": []}}
        with patch.object(client, "request", return_value=payload):
            result = client.well_production.states()

        assert result["count"] == 0
        assert result["states"] == []


class TestWellProductionErrors:
    """Negative-path tests through the real client.request error mapping."""

    def test_unsupported_state_raises_not_found(self, client):
        """404 DATA_NOT_AVAILABLE (unsupported state) -> DataNotFoundError."""
        response = _http_response(
            404,
            {
                "error": {
                    "code": "DATA_NOT_AVAILABLE",
                    "message": "No production data for state: ZZ",
                    "status": 404,
                }
            },
        )
        with patch.object(client._client, "request", return_value=response):
            with pytest.raises(DataNotFoundError):
                client.well_production.state("ZZ")

    def test_missing_well_data_raises_not_found(self, client):
        """404 for a valid-format API number with no data -> DataNotFoundError."""
        response = _http_response(
            404,
            {
                "error": {
                    "code": "DATA_NOT_AVAILABLE",
                    "message": "No production data for well: 99999999999999",
                    "status": 404,
                }
            },
        )
        with patch.object(client._client, "request", return_value=response):
            with pytest.raises(DataNotFoundError):
                client.well_production.well("99999999999999")

    def test_entitlement_gate_raises_api_error(self, client):
        """403 ENTERPRISE_REQUIRED (plan gate) -> OilPriceAPIError with status 403.

        Note: the live gate is HTTP 403 with code ENTERPRISE_REQUIRED (the
        drilling_intelligence feature), not 402.
        """
        response = _http_response(
            403,
            {
                "error": {
                    "code": "ENTERPRISE_REQUIRED",
                    "message": "Well production data requires the Scale plan.",
                    "status": 403,
                }
            },
        )
        with patch.object(client._client, "request", return_value=response):
            with pytest.raises(OilPriceAPIError) as exc_info:
                client.well_production.summary()

        assert exc_info.value.status_code == 403

    def test_invalid_period_raises_api_error(self, client):
        """400 INVALID_PARAMETER (bad period format) -> OilPriceAPIError 400."""
        response = _http_response(
            400,
            {
                "error": {
                    "code": "INVALID_PARAMETER",
                    "message": "Invalid period format. Use YYYY-MM.",
                    "status": 400,
                }
            },
        )
        with patch.object(client._client, "request", return_value=response):
            with pytest.raises(OilPriceAPIError) as exc_info:
                client.well_production.states(period="bogus")

        assert exc_info.value.status_code == 400
