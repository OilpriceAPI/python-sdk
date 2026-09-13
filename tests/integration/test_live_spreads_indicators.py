"""
Live smoke for the typed Spreads and Indicators resources (#99).

Hits the REAL OilPriceAPI with the key in ``OILPRICEAPI_TEST_KEY`` and is
skipped without it. Read-only: every call is a GET. The calculated-metrics
routes require a paid plan, so the key must belong to an entitled account.

Each call is spaced to respect the shared 1 request/second key, and a 429 is
reported as a skip rather than a failure, matching ``tests/integration``.
"""

import os
import time

import pytest

from oilpriceapi import OilPriceAPI
from oilpriceapi.exceptions import RateLimitError
from oilpriceapi.metrics_models import (
    BasisSpread,
    CftcPositioning,
    CrackSpread,
    CrackSpreadHistory,
    CurveStructure,
    FuelSwitching,
    MarketAnnotations,
    PhysicalPremium,
    PriceContext,
    RefineryMargin,
    StorageAnalytics,
)

TEST_KEY = os.environ.get("OILPRICEAPI_TEST_KEY")

pytestmark = [
    pytest.mark.live,
    pytest.mark.integration,
    pytest.mark.skipif(not TEST_KEY, reason="OILPRICEAPI_TEST_KEY not set; skipping live metrics smoke"),
]

SPACING_SECONDS = 1.1


@pytest.fixture(scope="module")
def client():
    c = OilPriceAPI(api_key=TEST_KEY, max_retries=1, timeout=60)
    yield c
    c.close()


def _call(fn, *args, **kwargs):
    time.sleep(SPACING_SECONDS)
    try:
        return fn(*args, **kwargs)
    except RateLimitError:
        pytest.skip("shared live key rate-limited")


def test_spreads_latest_and_all(client):
    crack = _call(client.spreads.crack)
    assert isinstance(crack, CrackSpread)
    assert crack.unit and crack.timestamp.tzinfo is not None

    history = _call(client.spreads.crack_historical)
    assert isinstance(history, CrackSpreadHistory)
    assert history.count == len(history.data)

    assert _call(client.spreads.crack_all).spreads
    assert _call(client.spreads.gasoil_crack).components["product"].unit

    basis_all = _call(client.spreads.basis_all)
    assert basis_all and all(isinstance(b, BasisSpread) for b in basis_all)
    pair = basis_all[0].pair
    assert _call(client.spreads.basis, pair).pair == pair
    assert _call(client.spreads.basis_historical, pair).pair == pair

    curves = _call(client.spreads.curve_structure_all)
    assert curves
    commodity = curves[0].commodity
    assert isinstance(_call(client.spreads.curve_structure, commodity), CurveStructure)

    assert isinstance(_call(client.spreads.margin), RefineryMargin)
    assert _call(client.spreads.margin_historical).index
    assert _call(client.spreads.margin_all)

    assert isinstance(_call(client.spreads.physical_premium), PhysicalPremium)
    assert _call(client.spreads.physical_premium_historical).commodity
    assert _call(client.spreads.physical_premium_all)


def test_indicators(client):
    assert isinstance(_call(client.indicators.fuel_switching), FuelSwitching)
    assert _call(client.indicators.fuel_switching_historical).gas_benchmark

    context = _call(client.indicators.price_context, "BRENT_CRUDE_USD", related_spreads=True)
    assert isinstance(context, PriceContext)
    assert context.code == "BRENT_CRUDE_USD"

    assert isinstance(_call(client.indicators.storage_analytics), StorageAnalytics)
    assert isinstance(_call(client.indicators.storage_analytics_all), list)

    notes = _call(client.indicators.annotations, "BRENT_CRUDE_USD")
    assert isinstance(notes, MarketAnnotations)
    assert notes.annotation_count == len(notes.annotations)
    batch = _call(client.indicators.annotations_batch, ["BRENT_CRUDE_USD", "WTI_USD"])
    assert batch.total_codes == 2

    assert isinstance(_call(client.indicators.cftc_positioning), CftcPositioning)
    assert _call(client.indicators.cftc_positioning_historical).commodity
    assert _call(client.indicators.cftc_positioning_all)
