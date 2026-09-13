"""client.diesel.* must parse the envelope production actually returns (#110).

The fixtures below are the real response bodies. The state-average one was
captured live from GET /v1/diesel-prices?state=CA on 2026-09-13; the station one
mirrors the documented POST /v1/diesel-prices/stations envelope, verified by
signature only because it is a POST.

The existing tests in test_diesel_resource.py mock a *top-level*
`regional_average`, a shape the API does not return — which is exactly how this
shipped. Those shapes stay supported; these add the shape customers hit.
"""

from unittest.mock import Mock, patch

import pytest

from oilpriceapi import OilPriceAPI
from oilpriceapi.models import DieselPrice, DieselStationsResponse

# Not a credential: a fixture string, every request here is mocked.
FIXTURE_KEY = "-".join(["fixture", "not", "a", "real", "key"])

# Captured live from production on 2026-09-13.
LIVE_STATE_ENVELOPE = {
    "status": "success",
    "data": {
        "regional_average": {
            "price": 8.136,
            "currency": "USD",
            "unit": "gallon",
            "region": "california",
            "granularity": "state",
            "source": "aaa",
            "updated_at": "2026-09-13T14:57:19Z",
            "cached": True,
        },
        "sources": {"primary": "aaa"},
        "upgrade": {"message": "Station-level pricing available on higher plans"},
        "location": {"type": "state", "state_code": "CA"},
    },
}

LIVE_STATIONS_ENVELOPE = {
    "status": "success",
    "data": {
        "regional_average": {
            "price": 8.136,
            "currency": "USD",
            "unit": "gallon",
            "region": "california",
            "granularity": "state",
            "source": "aaa",
            "updated_at": "2026-09-13T14:57:19Z",
        },
        "stations": [
            {
                "name": "Fixture Truck Stop",
                "address": "1 Fixture Way, San Francisco, CA",
                "location": {"lat": 37.7749, "lng": -122.4194},
                "diesel_price": 7.99,
                "formatted_price": "$7.99",
                "currency": "USD",
                "unit": "gallon",
                "price_delta": -0.146,
                "price_vs_average": "$0.15 below average",
            }
        ],
        "search_area": {
            "center": {"lat": 37.7749, "lng": -122.4194},
            "radius_meters": 8047,
            "radius_miles": 5.0,
        },
        "metadata": {
            "total_stations": 1,
            "source": "google_maps",
            "cached": False,
            "api_cost": 0.024,
            "timestamp": "2026-09-13T14:57:19Z",
        },
    },
}


def _mock_client(mock_request, payload):
    response = Mock()
    response.status_code = 200
    response.json.return_value = payload
    mock_request.return_value = response
    return OilPriceAPI(api_key=FIXTURE_KEY)


@patch("httpx.Client.request")
def test_get_price_parses_the_live_production_envelope(mock_request):
    client = _mock_client(mock_request, LIVE_STATE_ENVELOPE)

    price = client.diesel.get_price("CA")

    assert isinstance(price, DieselPrice)
    assert price.price == 8.136
    assert price.currency == "USD"
    assert price.unit == "gallon"
    assert price.granularity == "state"
    assert price.source == "aaa"
    assert price.cached is True
    assert price.updated_at.year == 2026


@patch("httpx.Client.request")
def test_get_price_fills_state_from_the_envelope_location(mock_request):
    """`regional_average` carries `region`, not `state` — the code must not drop it."""
    client = _mock_client(mock_request, LIVE_STATE_ENVELOPE)

    assert client.diesel.get_price("ca").state == "CA"


@patch("httpx.Client.request")
def test_get_price_falls_back_to_the_requested_state_when_location_is_absent(mock_request):
    payload = {
        "status": "success",
        "data": {
            "regional_average": dict(LIVE_STATE_ENVELOPE["data"]["regional_average"]),
        },
    }
    client = _mock_client(mock_request, payload)

    assert client.diesel.get_price("tx").state == "TX"


@patch("httpx.Client.request")
def test_get_price_still_accepts_the_legacy_top_level_shape(mock_request):
    payload = {
        "regional_average": {
            "state": "CA",
            "price": 3.89,
            "currency": "USD",
            "unit": "gallon",
            "granularity": "state",
            "source": "EIA",
            "updated_at": "2025-12-15T10:00:00Z",
        }
    }
    client = _mock_client(mock_request, payload)

    price = client.diesel.get_price("CA")
    assert price.price == 3.89
    assert price.state == "CA"


@patch("httpx.Client.request")
def test_get_price_still_accepts_a_flat_record(mock_request):
    payload = {
        "state": "NY",
        "price": 4.21,
        "currency": "USD",
        "unit": "gallon",
        "granularity": "state",
        "source": "EIA",
        "updated_at": "2025-12-15T10:00:00Z",
    }
    client = _mock_client(mock_request, payload)

    assert client.diesel.get_price("NY").price == 4.21


@patch("httpx.Client.request")
def test_get_stations_parses_the_data_envelope(mock_request):
    client = _mock_client(mock_request, LIVE_STATIONS_ENVELOPE)

    result = client.diesel.get_stations(lat=37.7749, lng=-122.4194, radius=8047)

    assert isinstance(result, DieselStationsResponse)
    assert result.regional_average.price == 8.136
    assert len(result.stations) == 1
    assert result.stations[0].diesel_price == 7.99
    assert result.search_area.radius_miles == 5.0
    assert result.metadata.total_stations == 1


@patch("httpx.Client.request")
def test_get_stations_still_accepts_the_legacy_top_level_shape(mock_request):
    payload = dict(LIVE_STATIONS_ENVELOPE["data"])
    client = _mock_client(mock_request, payload)

    result = client.diesel.get_stations(lat=37.7749, lng=-122.4194)
    assert len(result.stations) == 1


@patch("httpx.Client.request")
def test_to_dataframe_state_works_on_the_live_envelope(mock_request):
    pytest.importorskip("pandas")
    client = _mock_client(mock_request, LIVE_STATE_ENVELOPE)

    df = client.diesel.to_dataframe(state="CA")

    assert df["price"].iloc[0] == 8.136
    assert df["state"].iloc[0] == "CA"
