"""Regression tests for currency-safe, complete DataFrame pagination."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import httpx
import pytest

from oilpriceapi import OilPriceAPI

FIXTURES = Path(__file__).parents[1] / "fixtures" / "dataframe"
HISTORICAL_COLUMNS = ["commodity", "value", "currency", "unit", "type_name"]


def load_fixture(name: str):
    """Load a production-shaped pagination fixture."""
    return json.loads((FIXTURES / name).read_text())


def make_response(page):
    """Create an HTTP response mock from a fixture page."""
    response = Mock(spec=httpx.Response)
    response.status_code = 200
    response.json.return_value = page["body"]
    response.headers = page["headers"]
    return response


@patch("httpx.Client.request")
def test_historical_dataframe_preserves_context_and_page_boundaries(mock_request, api_key):
    """Every unique API row survives pagination with its currency and unit intact."""
    pytest.importorskip("pandas")
    pages = load_fixture("historical-pages.json.fixture")["pages"]
    mock_request.side_effect = [make_response(page) for page in pages]

    client = OilPriceAPI(api_key=api_key)
    dataframe = client.historical.to_dataframe(
        commodity="ENERGY_DATA",
        start="2026-07-20",
        end="2026-07-21",
        per_page=3,
    )

    assert len(dataframe) == 5
    assert dataframe.index.is_unique
    assert mock_request.call_count == 2
    assert [call.kwargs["params"]["page"] for call in mock_request.call_args_list] == [1, 2]
    assert all(call.kwargs["params"]["per_page"] == 3 for call in mock_request.call_args_list)

    context = {row.commodity: (row.currency, row.unit) for row in dataframe.itertuples()}
    assert context["BRENT_CRUDE_USD"] == ("USD", "barrel")
    assert context["EU_CARBON_EUR"] == ("EUR", "tonne")
    assert context["UK_NATURAL_GAS_GBP"] == ("GBP", "pence_per_therm")
    assert context["US_REFINERY_UTILIZATION"][1] == "percent"
    assert context["ENERGY_PRICE_INDEX"][1] == "index_points"
    assert (
        dataframe.loc[
            dataframe["commodity"].isin(["US_REFINERY_UTILIZATION", "ENERGY_PRICE_INDEX"]),
            "currency",
        ]
        .isna()
        .all()
    )
    assert set(context) == {
        "BRENT_CRUDE_USD",
        "EU_CARBON_EUR",
        "UK_NATURAL_GAS_GBP",
        "US_REFINERY_UTILIZATION",
        "ENERGY_PRICE_INDEX",
    }


@patch("httpx.Client.request")
def test_historical_empty_page_stops_and_returns_stable_dataframe(mock_request, api_key):
    """An empty page is terminal even when stale pagination metadata says otherwise."""
    pytest.importorskip("pandas")
    page = load_fixture("empty-page.json.fixture")
    mock_request.return_value = make_response(page)

    client = OilPriceAPI(api_key=api_key)
    dataframe = client.historical.to_dataframe(
        commodity="BRENT_CRUDE_USD",
        per_page=100,
    )

    assert dataframe.empty
    assert dataframe.index.name == "date"
    assert list(dataframe.columns) == HISTORICAL_COLUMNS
    mock_request.assert_called_once()


@pytest.mark.parametrize("per_page", [0, -1, 1001, 1.5, True])
def test_historical_rejects_page_sizes_outside_api_limits(api_key, per_page):
    """Invalid page sizes fail before any network request is made."""
    client = OilPriceAPI(api_key=api_key)

    with patch.object(client, "request_with_headers") as request:
        with pytest.raises(ValueError, match="per_page must be an integer between 1 and 1000"):
            client.historical.get("BRENT_CRUDE_USD", per_page=per_page)
        request.assert_not_called()


@patch("oilpriceapi.resources.historical.HistoricalResource")
def test_prices_dataframe_forwards_page_size_to_historical(mock_historical, api_key):
    """The convenience DataFrame path honors page size for date-range queries."""
    pytest.importorskip("pandas")
    resource = mock_historical.return_value
    resource.to_dataframe.return_value = Mock()

    client = OilPriceAPI(api_key=api_key)
    client.prices.to_dataframe(
        commodity="BRENT_CRUDE_USD",
        start="2026-07-01",
        end="2026-07-20",
        per_page=250,
    )

    resource.to_dataframe.assert_called_once_with(
        commodity="BRENT_CRUDE_USD",
        start="2026-07-01",
        end="2026-07-20",
        interval="daily",
        per_page=250,
    )
