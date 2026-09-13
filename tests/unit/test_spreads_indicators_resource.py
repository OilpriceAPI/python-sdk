"""Typed Spreads and market Indicators resources (#99).

Every test drives the REAL sync or async client through a mocked transport
(``httpx.Client.request`` / ``httpx.AsyncClient.request``, this repo's
convention), so envelope unwrapping, error mapping, retry and model
validation all run exactly as they do against production.

Success fixtures in ``fixtures/calculated_metrics/`` are verbatim production
bodies captured on 2026-09-13 with a paid test account. Nothing in them is
invented; tests that need a malformed body derive it from a real one by
removing or breaking a single field.
"""

import copy
import json
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import httpx
import pytest

from oilpriceapi import AsyncOilPriceAPI, OilPriceAPI
from oilpriceapi.exceptions import (
    AuthenticationError,
    BadRequestError,
    DataNotFoundError,
    OilPriceAPIError,
    PaymentRequiredError,
    PermissionDeniedError,
    RateLimitError,
)
from oilpriceapi.exceptions import TimeoutError as OPATimeoutError
from oilpriceapi.metrics_models import (
    BasisSpread,
    BasisSpreadHistory,
    CftcPositioning,
    CftcPositioningHistory,
    CrackSpread,
    CrackSpreadAll,
    CrackSpreadHistory,
    CurveStructure,
    FuelSwitching,
    FuelSwitchingHistory,
    GasoilCrackSpread,
    MarketAnnotations,
    MarketAnnotationsBatch,
    PhysicalPremium,
    PhysicalPremiumHistory,
    PriceContext,
    RefineryMargin,
    RefineryMarginHistory,
    StorageAnalytics,
)

FIXTURES = Path(__file__).parent / "fixtures" / "calculated_metrics"

# Not a credential: a fixture string, every request here is mocked.
FIXTURE_KEY = "-".join(["fixture", "not", "a", "real", "key"])

UTC = timezone.utc


def load(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def _response(status, payload=None, *, body=None, headers=None):
    response = Mock()
    response.status_code = status
    response.headers = headers or {}
    if body is None:
        text = json.dumps(payload)
        response.json.return_value = payload
    else:
        text = body
        response.json.side_effect = json.JSONDecodeError("Expecting value", body, 0)
    response.text = text
    response.content = text.encode()
    return response


def _sync(**kwargs):
    kwargs.setdefault("max_retries", 1)
    return OilPriceAPI(api_key=FIXTURE_KEY, **kwargs)


def _async(**kwargs):
    kwargs.setdefault("max_retries", 1)
    return AsyncOilPriceAPI(api_key=FIXTURE_KEY, **kwargs)


def _sent(mock_request):
    """Return (path, params) of the single request the client sent."""
    assert mock_request.call_count == 1
    kwargs = mock_request.call_args.kwargs
    url = httpx.URL(kwargs["url"])
    return url.path, kwargs.get("params")


# ---------------------------------------------------------------------------
# Field-level assertions against the captured production bodies
# ---------------------------------------------------------------------------


def check_crack(result):
    assert isinstance(result, CrackSpread)
    assert result.spread_type == "3-2-1"
    assert result.crude_benchmark == "BRENT_CRUDE_USD"
    assert result.value == 58.5
    assert result.unit == "USD/bbl"
    assert result.components["crude"].code == "BRENT_CRUDE_USD"
    assert result.components["gasoline"].price == 139.44
    assert result.components["diesel"].unit == "USD/bbl"
    assert result.timestamp == datetime(2026, 9, 13, 19, 50, 24, tzinfo=UTC)
    assert result.changes.change_1m_pct == -1.81
    # The composite body carries no stale flag; absence is not turned into False.
    assert result.data_stale is None


def check_crack_historical(result):
    assert isinstance(result, CrackSpreadHistory)
    assert result.period.start == date(2026, 9, 1)
    assert result.period.end == date(2026, 9, 12)
    assert result.coverage.from_ == date(2026, 9, 1)
    assert result.coverage.to == date(2026, 9, 11)
    assert result.coverage.observations == 9
    assert result.coverage.complete is True
    assert result.data_revised_at == datetime(2026, 9, 13, 0, 5, 27, 514000, tzinfo=UTC)
    assert result.count == 9 == len(result.data)
    first = result.data[0]
    assert first.date == date(2026, 9, 11)
    assert first.value == 58.93
    # Full precision exactly as sent, not rounded by the SDK.
    assert first.crude == 105.50626910999999
    assert first.gasoline == 140.9 and first.diesel == 211.51
    assert first.product is None


def check_crack_all(result):
    assert isinstance(result, CrackSpreadAll)
    assert result.crude_benchmark == "BRENT_CRUDE_USD"
    assert [s.spread_type for s in result.spreads] == ["jet", "diesel", "gasoline", "3-2-1"]
    jet = result.spreads[0]
    assert jet.components["product"].code == "JET_FUEL_USD"
    assert jet.data_stale is True
    assert jet.stale_warning.startswith("Some price data is older than 24 hours")


def check_gasoil_crack(result):
    assert isinstance(result, GasoilCrackSpread)
    assert result.value == 92.19
    product = result.components["product"]
    assert product.unit == "USD/tonne"
    assert product.contract_month == "2026-09"
    assert product.updated_at == datetime(2026, 9, 11, 7, 7, 31, tzinfo=UTC)
    assert product.settlement_date is None
    assert result.conversion.barrels_per_tonne == 7.45
    assert result.timestamp == datetime(2026, 9, 11, 7, 7, 31, tzinfo=UTC)
    assert result.updated_at == datetime(2026, 9, 13, 19, 56, 18, tzinfo=UTC)
    assert result.data_stale is True


def check_basis(result):
    assert isinstance(result, BasisSpread)
    assert result.pair == "BRENT_WTI"
    assert result.components == {"BRENT_CRUDE_USD": 104.32, "WTI_USD": 99.99}
    assert result.percentile_1y == 49
    assert result.negative_streak_days is None


def check_basis_historical(result):
    assert isinstance(result, BasisSpreadHistory)
    assert result.pair == "BRENT_WTI"
    assert result.count == 9
    assert result.data[0].code_a == 105.50626910999999
    assert result.data[0].code_b == 100.71776786000001


def check_basis_all(result):
    assert [s.pair for s in result] == ["WAHA_HH", "BRENT_WTI", "BRENT_DUBAI", "TTF_HH", "BRENT_OMAN"]
    assert all(isinstance(s, BasisSpread) for s in result)
    assert result[0].negative_streak_days == 61
    assert result[0].data_stale is True


def check_curve(result):
    assert isinstance(result, CurveStructure)
    assert result.commodity == "ICE_BRENT"
    assert result.structure == "backwardation"
    assert result.spreads.m1_m12 == 25.26
    assert result.front_month.contract == "Nov 2026"
    assert result.back_month_6.price == 87.5
    assert result.curve_points == 16


def check_curve_all(result):
    assert [c.commodity for c in result] == ["ICE_BRENT", "ICE_WTI", "ICE_GASOIL", "NYMEX_NG", "ICE_TTF"]


def check_margin(result):
    assert isinstance(result, RefineryMargin)
    assert result.index == "usgc"
    assert result.margin_usd_bbl == 67.46
    assert result.crude_input.code == "BRENT_CRUDE_USD"
    assert result.product_basket["jet_fuel"].yield_pct == 10
    assert result.percentile_1y == 97


def check_margin_historical(result):
    assert isinstance(result, RefineryMarginHistory)
    assert result.index == "usgc"
    assert result.data[0].margin == 49.54
    assert result.data[0].revenue == 155.05


def check_margin_all(result):
    assert [m.index for m in result] == ["usgc", "singapore", "nwe"]
    assert set(result[1].product_basket) == {"mogas", "gasoil", "jet", "naphtha", "fuel_oil"}


def check_premium(result):
    assert isinstance(result, PhysicalPremium)
    assert result.premium == 4.7
    assert result.components.futures.contract == "Continuous"
    # null is preserved as None, not replaced with 0.
    assert result.percentile_1y is None
    assert result.elevated_streak_days == 0


def check_premium_historical_empty(result):
    assert isinstance(result, PhysicalPremiumHistory)
    assert result.commodity == "BRENT"
    assert result.count == 0
    assert result.data == []


def check_premium_all(result):
    assert [p.commodity for p in result] == ["BRENT", "WTI"]


def check_fuel_switching(result):
    assert isinstance(result, FuelSwitching)
    assert result.oil_parity.ratio_pct == 15.73
    assert result.oil_parity.signal == "gas_cheap_vs_oil"
    assert result.components.gas.unit == "USD/MMBtu"
    assert result.energy_equivalent.gas_premium_discount == -15.16
    assert result.historical_context.data_points == 347


def check_fuel_switching_historical(result):
    assert isinstance(result, FuelSwitchingHistory)
    assert result.count == 34 == len(result.data)
    assert result.data[0].above_parity is False
    assert result.data[0].gas_price == 2.8208421099999996


def check_price_context(result):
    assert isinstance(result, PriceContext)
    assert result.code == "DIESEL_USD"
    assert result.context.percentile_1y == 100
    assert result.context.anomaly is True
    assert result.related_spreads is None


def check_price_context_related(result):
    assert isinstance(result, PriceContext)
    names = [s.name for s in result.related_spreads]
    assert names == ["Brent-WTI", "Brent-Dubai", "3-2-1 Crack", "Curve Structure"]
    crack = result.related_spreads[2]
    assert crack.value == 58.5 and crack.signal is None
    curve = result.related_spreads[3]
    assert curve.value == "backwardation"
    assert curve.unit is None
    assert curve.slope == -38.7


def check_storage(result):
    assert isinstance(result, StorageAnalytics)
    assert result.location == "CUSHING"
    assert result.current.volume_mmbbl == 21.82
    assert result.current.data_date == datetime(2026, 9, 4, tzinfo=UTC)
    assert result.draw_rate.days_to_depletion == 225
    # The server sends {} when there is too little history; it stays empty.
    assert result.seasonal.five_year_avg_mmbbl is None
    assert result.range_52w.high_mmbbl is None


def check_storage_all(result):
    assert [s.location for s in result] == ["CUSHING"]


def check_annotations(result):
    assert isinstance(result, MarketAnnotations)
    assert result.annotation_count == 3
    kinds = [a.type for a in result.annotations]
    assert kinds == ["anomaly", "velocity", "streak"]
    assert result.annotations[0].z_score == 2.24
    assert result.annotations[2].streak_days == 5


def check_annotations_batch(result):
    assert isinstance(result, MarketAnnotationsBatch)
    assert result.total_codes == 2
    assert result.codes_with_annotations == 2
    assert [a.code for a in result.annotated] == ["BRENT_CRUDE_USD", "WTI_USD"]


def check_cftc(result):
    assert isinstance(result, CftcPositioning)
    assert result.report_date == date(2026, 9, 11)
    assert result.positioning.speculative.net == 136579
    assert result.positioning.speculative.net_pct_of_oi == 7.04
    assert result.positioning.open_interest == 1939911


def check_cftc_historical(result):
    assert isinstance(result, CftcPositioningHistory)
    assert result.count == 10
    assert result.data[0].spec_net == 136579
    # Preserved exactly as the API sends it (the 0 itself is an API defect).
    assert result.data[0].spec_net_pct_oi == 0


def check_cftc_all(result):
    brent = result[1]
    assert brent.commodity == "BRENT"
    assert brent.positioning.speculative.long is None
    assert brent.positioning.commercial.net is None
    assert brent.positioning.open_interest is None


# (namespace, method, args, kwargs, path, params, fixture, check)
CASES = [
    ("spreads", "crack", (), {}, "/v1/spreads/crack", {}, "crack", check_crack),
    (
        "spreads", "crack", (), {"spread_type": "diesel", "crude": "WTI_USD"},
        "/v1/spreads/crack", {"type": "diesel", "crude": "WTI_USD"}, "crack", check_crack,
    ),
    (
        "spreads", "crack_historical", (),
        {"start_date": "2026-09-01", "end_date": date(2026, 9, 12)},
        "/v1/spreads/crack/historical", {"start_date": "2026-09-01", "end_date": "2026-09-12"},
        "crack_historical", check_crack_historical,
    ),
    ("spreads", "crack_all", (), {}, "/v1/spreads/crack/all", {}, "crack_all", check_crack_all),
    (
        "spreads", "gasoil_crack", (), {}, "/v1/spreads/gasoil-crack", {},
        "gasoil_crack", check_gasoil_crack,
    ),
    (
        "spreads", "basis", ("BRENT_WTI",), {}, "/v1/spreads/basis", {"pair": "BRENT_WTI"},
        "basis", check_basis,
    ),
    (
        "spreads", "basis_historical", ("BRENT_WTI",), {"start_date": "2026-09-01"},
        "/v1/spreads/basis/historical", {"pair": "BRENT_WTI", "start_date": "2026-09-01"},
        "basis_historical", check_basis_historical,
    ),
    ("spreads", "basis_all", (), {}, "/v1/spreads/basis/all", {}, "basis_all", check_basis_all),
    (
        "spreads", "curve_structure", ("ICE_BRENT",), {}, "/v1/spreads/curve-structure",
        {"commodity": "ICE_BRENT"}, "curve_structure", check_curve,
    ),
    (
        "spreads", "curve_structure_all", (), {}, "/v1/spreads/curve-structure/all", {},
        "curve_structure_all", check_curve_all,
    ),
    ("spreads", "margin", (), {}, "/v1/spreads/margin", {}, "margin", check_margin),
    (
        "spreads", "margin_historical", (), {"index": "usgc", "start_date": "2026-09-01"},
        "/v1/spreads/margin/historical", {"index": "usgc", "start_date": "2026-09-01"},
        "margin_historical", check_margin_historical,
    ),
    ("spreads", "margin_all", (), {}, "/v1/spreads/margin/all", {}, "margin_all", check_margin_all),
    (
        "spreads", "physical_premium", (), {"commodity": "BRENT"},
        "/v1/spreads/physical-premium", {"commodity": "BRENT"},
        "physical_premium", check_premium,
    ),
    (
        "spreads", "physical_premium_historical", (), {"start_date": "2026-09-01"},
        "/v1/spreads/physical-premium/historical", {"start_date": "2026-09-01"},
        "physical_premium_historical_empty", check_premium_historical_empty,
    ),
    (
        "spreads", "physical_premium_all", (), {}, "/v1/spreads/physical-premium/all", {},
        "physical_premium_all", check_premium_all,
    ),
    (
        "indicators", "fuel_switching", (), {}, "/v1/indicators/fuel-switching", {},
        "fuel_switching", check_fuel_switching,
    ),
    (
        "indicators", "fuel_switching_historical", (),
        {"gas": "NATURAL_GAS_USD", "start_date": "2026-08-01"},
        "/v1/indicators/fuel-switching/historical",
        {"gas": "NATURAL_GAS_USD", "start_date": "2026-08-01"},
        "fuel_switching_historical", check_fuel_switching_historical,
    ),
    (
        "indicators", "price_context", ("DIESEL_USD",), {}, "/v1/indicators/price-context",
        {"code": "DIESEL_USD"}, "price_context", check_price_context,
    ),
    (
        "indicators", "price_context", ("BRENT_CRUDE_USD",), {"related_spreads": True},
        "/v1/indicators/price-context", {"code": "BRENT_CRUDE_USD", "spreads": "related"},
        "price_context_related", check_price_context_related,
    ),
    (
        "indicators", "storage_analytics", (), {"location": "CUSHING"},
        "/v1/indicators/storage-analytics", {"location": "CUSHING"},
        "storage_analytics", check_storage,
    ),
    (
        "indicators", "storage_analytics_all", (), {}, "/v1/indicators/storage-analytics/all", {},
        "storage_analytics_all", check_storage_all,
    ),
    (
        "indicators", "annotations", ("BRENT_CRUDE_USD",), {}, "/v1/indicators/annotations",
        {"code": "BRENT_CRUDE_USD"}, "annotations", check_annotations,
    ),
    (
        "indicators", "annotations_batch", (["BRENT_CRUDE_USD", "WTI_USD"],), {},
        "/v1/indicators/annotations/batch", {"codes": "BRENT_CRUDE_USD,WTI_USD"},
        "annotations_batch", check_annotations_batch,
    ),
    (
        "indicators", "cftc_positioning", (), {}, "/v1/indicators/cftc-positioning", {},
        "cftc_positioning", check_cftc,
    ),
    (
        "indicators", "cftc_positioning_historical", (), {"commodity": "WTI", "start_date": "2026-06-01"},
        "/v1/indicators/cftc-positioning/historical", {"commodity": "WTI", "start_date": "2026-06-01"},
        "cftc_positioning_historical", check_cftc_historical,
    ),
    (
        "indicators", "cftc_positioning_all", (), {}, "/v1/indicators/cftc-positioning/all", {},
        "cftc_positioning_all", check_cftc_all,
    ),
]

CASE_IDS = [f"{c[0]}.{c[1]}-{c[6]}" for c in CASES]


@pytest.mark.parametrize("namespace,method,args,kwargs,path,params,fixture,check", CASES, ids=CASE_IDS)
@patch("httpx.Client.request")
def test_sync_success_is_typed_from_the_wire(
    mock_request, namespace, method, args, kwargs, path, params, fixture, check
):
    mock_request.return_value = _response(200, load(fixture))
    result = getattr(getattr(_sync(), namespace), method)(*args, **kwargs)
    sent_path, sent_params = _sent(mock_request)
    assert sent_path == path
    assert (sent_params or {}) == params
    assert mock_request.call_args.kwargs["method"] == "GET"
    check(result)


@pytest.mark.asyncio
@pytest.mark.parametrize("namespace,method,args,kwargs,path,params,fixture,check", CASES, ids=CASE_IDS)
@patch("httpx.AsyncClient.request")
async def test_async_success_matches_sync(
    mock_request, namespace, method, args, kwargs, path, params, fixture, check
):
    mock_request.return_value = _response(200, load(fixture))
    result = await getattr(getattr(_async(), namespace), method)(*args, **kwargs)
    sent_path, sent_params = _sent(mock_request)
    assert sent_path == path
    assert (sent_params or {}) == params
    check(result)


# ---------------------------------------------------------------------------
# HTTP errors map to the SDK's typed exceptions with recovery metadata intact
# ---------------------------------------------------------------------------

PREMIUM_REQUIRED = {
    # Shape of V1::SpreadsController#check_analytics_access -> render_standard_error.
    "error": {
        "code": "PREMIUM_REQUIRED",
        "message": "Calculated metrics require a paid plan (Developer and above). "
        "Upgrade at https://oilpriceapi.com/pricing",
        "status": 403,
        "request_id": "fixture-request-id",
        "docs": "https://docs.oilpriceapi.com#PREMIUM_REQUIRED",
    }
}

ERROR_CASES = [
    (401, "error_401", {}, AuthenticationError, "UNAUTHORIZED"),
    (
        402,
        {"error": {"code": "PAYMENT_REQUIRED", "message": "Upgrade required", "required_plan": "developer",
                   "upgrade_url": "https://www.oilpriceapi.com/pricing"}},
        {},
        PaymentRequiredError,
        "PAYMENT_REQUIRED",
    ),
    (403, PREMIUM_REQUIRED, {}, PermissionDeniedError, "PREMIUM_REQUIRED"),
    (404, "error_404_unknown_index", {}, DataNotFoundError, "DATA_NOT_AVAILABLE"),
    (400, "error_400_missing_pair", {}, BadRequestError, "MISSING_PARAMETER"),
    (
        429,
        {"error": {"code": "RATE_LIMIT_EXCEEDED", "message": "Too many requests"}},
        {"Retry-After": "7", "X-RateLimit-Limit": "1", "X-RateLimit-Remaining": "0"},
        RateLimitError,
        "RATE_LIMIT_EXCEEDED",
    ),
]


def _error_body(spec):
    return load(spec) if isinstance(spec, str) else spec


@pytest.mark.parametrize("status,body,headers,exc_type,code", ERROR_CASES, ids=[str(c[0]) for c in ERROR_CASES])
@patch("httpx.Client.request")
def test_sync_http_errors_are_typed(mock_request, status, body, headers, exc_type, code):
    mock_request.return_value = _response(status, _error_body(body), headers=headers)
    with pytest.raises(exc_type) as info:
        _sync().spreads.margin(index="nope")
    assert info.value.status_code == status
    assert info.value.code == code
    if status == 404:
        assert "Valid: usgc, singapore, nwe" in str(info.value)
    if status == 402:
        assert info.value.required_plan == "developer"
        assert info.value.remediation_url == "https://www.oilpriceapi.com/pricing"
    if status == 403:
        assert info.value.request_id == "fixture-request-id"
    if status == 429:
        assert info.value.retry_after == 7


@pytest.mark.asyncio
@pytest.mark.parametrize("status,body,headers,exc_type,code", ERROR_CASES, ids=[str(c[0]) for c in ERROR_CASES])
@patch("httpx.AsyncClient.request")
async def test_async_http_errors_are_typed(mock_request, status, body, headers, exc_type, code):
    mock_request.return_value = _response(status, _error_body(body), headers=headers)
    with pytest.raises(exc_type) as info:
        await _async().indicators.cftc_positioning(commodity="NOPE")
    assert info.value.status_code == status
    assert info.value.code == code


@patch("httpx.Client.request")
def test_no_data_404_is_data_not_found(mock_request):
    mock_request.return_value = _response(404, load("error_404_no_data"))
    with pytest.raises(DataNotFoundError) as info:
        _sync().spreads.gasoil_crack()
    assert info.value.code == "DATA_NOT_AVAILABLE"


# ---------------------------------------------------------------------------
# A malformed 200 raises; nothing is defaulted
# ---------------------------------------------------------------------------


def _without(fixture, *path):
    body = copy.deepcopy(load(fixture))
    node = body
    for key in path[:-1]:
        node = node[key]
    del node[path[-1]]
    return body


def _replace(fixture, value, *path):
    body = copy.deepcopy(load(fixture))
    node = body
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    return body


MALFORMED = [
    ("missing value", "spreads", "crack", (), _without("crack", "data", "value")),
    ("missing unit", "spreads", "crack", (), _without("crack", "data", "unit")),
    ("missing timestamp", "spreads", "basis", ("BRENT_WTI",), _without("basis", "data", "timestamp")),
    ("non-numeric value", "spreads", "crack", (), _replace("crack", "n/a", "data", "value")),
    ("unparseable timestamp", "spreads", "crack", (), _replace("crack", "yesterday", "data", "timestamp")),
    ("data is a list", "spreads", "crack", (), {"status": "success", "data": []}),
    ("no data envelope", "spreads", "crack", (), {"status": "success"}),
    ("status not success", "spreads", "crack", (), _replace("crack", "fail", "status")),
    ("collection key missing", "spreads", "basis_all", (), {"status": "success", "data": {}}),
    (
        "collection not a list", "spreads", "margin_all", (),
        {"status": "success", "data": {"margins": {"index": "usgc"}}},
    ),
    (
        "collection row missing field", "indicators", "cftc_positioning_all", (),
        _without("cftc_positioning_all", "data", "commodities", 0, "report_date"),
    ),
    (
        "history row missing date", "spreads", "crack_historical", (),
        _without("crack_historical", "data", "data", 0, "date"),
    ),
    (
        "history missing period", "spreads", "crack_historical", (),
        _without("crack_historical", "data", "period"),
    ),
    (
        "nullable key absent", "spreads", "physical_premium", (),
        _without("physical_premium", "data", "percentile_1y"),
    ),
    (
        "annotation missing message", "indicators", "annotations", ("BRENT_CRUDE_USD",),
        _without("annotations", "data", "annotations", 0, "message"),
    ),
]


@pytest.mark.parametrize("label,namespace,method,args,body", MALFORMED, ids=[m[0] for m in MALFORMED])
@patch("httpx.Client.request")
def test_sync_malformed_success_raises(mock_request, label, namespace, method, args, body):
    mock_request.return_value = _response(200, body)
    with pytest.raises(OilPriceAPIError) as info:
        getattr(getattr(_sync(), namespace), method)(*args)
    assert info.value.code == "MALFORMED_RESPONSE"
    assert info.value.raw_body == body


@pytest.mark.asyncio
@pytest.mark.parametrize("label,namespace,method,args,body", MALFORMED, ids=[m[0] for m in MALFORMED])
@patch("httpx.AsyncClient.request")
async def test_async_malformed_success_raises(mock_request, label, namespace, method, args, body):
    mock_request.return_value = _response(200, body)
    with pytest.raises(OilPriceAPIError) as info:
        await getattr(getattr(_async(), namespace), method)(*args)
    assert info.value.code == "MALFORMED_RESPONSE"


@patch("httpx.Client.request")
def test_sync_non_json_200_is_malformed(mock_request):
    mock_request.return_value = _response(200, body="<html>gateway</html>")
    with pytest.raises(OilPriceAPIError) as info:
        _sync().spreads.crack()
    assert info.value.code == "MALFORMED_RESPONSE"


@pytest.mark.asyncio
@patch("httpx.AsyncClient.request")
async def test_async_non_json_200_is_malformed(mock_request):
    mock_request.return_value = _response(200, body="<html>gateway</html>")
    with pytest.raises(OilPriceAPIError) as info:
        await _async().indicators.fuel_switching()
    assert info.value.code == "MALFORMED_RESPONSE"


@patch("httpx.Client.request")
def test_empty_200_body_is_malformed_not_empty_success(mock_request):
    mock_request.return_value = _response(200, body="")
    with pytest.raises(OilPriceAPIError) as info:
        _sync().spreads.basis_all()
    assert info.value.code == "MALFORMED_RESPONSE"


# ---------------------------------------------------------------------------
# No-data: an empty historical window is an empty result, not an error
# ---------------------------------------------------------------------------


@patch("httpx.Client.request")
def test_empty_history_is_empty_not_error(mock_request):
    mock_request.return_value = _response(200, load("physical_premium_historical_empty"))
    result = _sync().spreads.physical_premium_historical(start_date="2026-09-01")
    assert result.count == 0
    assert result.data == []


@patch("httpx.Client.request")
def test_empty_collection_is_empty_list(mock_request):
    mock_request.return_value = _response(200, {"status": "success", "data": {"locations": []}})
    assert _sync().indicators.storage_analytics_all() == []


@patch("httpx.Client.request")
def test_crack_history_with_no_observations_keeps_null_coverage(mock_request):
    body = {
        # Verbatim production body for /v1/spreads/crack/historical?type=nope.
        "status": "success",
        "data": {
            "spread_type": "nope",
            "crude_benchmark": "BRENT_CRUDE_USD",
            "period": {"start": "2026-08-14", "end": "2026-09-13"},
            "coverage": {"from": None, "to": None, "observations": 0, "complete": False},
            "data_revised_at": "2026-09-13T19:56:18.781Z",
            "count": 0,
            "data": [],
        },
    }
    mock_request.return_value = _response(200, body)
    result = _sync().spreads.crack_historical(spread_type="nope")
    assert result.coverage.from_ is None and result.coverage.to is None
    assert result.coverage.complete is False
    assert result.data == []


# ---------------------------------------------------------------------------
# Timeouts: typed, and a replay-safe GET recovers on retry
# ---------------------------------------------------------------------------


@patch("httpx.Client.request")
def test_sync_timeout_is_typed(mock_request):
    mock_request.side_effect = httpx.ReadTimeout("timed out")
    with pytest.raises(OPATimeoutError):
        _sync().spreads.crack()


@pytest.mark.asyncio
@patch("httpx.AsyncClient.request")
async def test_async_timeout_is_typed(mock_request):
    mock_request.side_effect = httpx.ReadTimeout("timed out")
    with pytest.raises(OPATimeoutError):
        await _async().indicators.price_context("BRENT_CRUDE_USD")


@patch("oilpriceapi.client.time.sleep")
@patch("httpx.Client.request")
def test_sync_timeout_recovers_on_retry(mock_request, _sleep):
    mock_request.side_effect = [httpx.ReadTimeout("timed out"), _response(200, load("crack"))]
    result = _sync(max_retries=2).spreads.crack()
    assert mock_request.call_count == 2
    check_crack(result)


@pytest.mark.asyncio
@patch("oilpriceapi.async_client.asyncio.sleep")
@patch("httpx.AsyncClient.request")
async def test_async_timeout_recovers_on_retry(mock_request, _sleep):
    mock_request.side_effect = [httpx.ReadTimeout("timed out"), _response(200, load("margin"))]
    result = await _async(max_retries=2).spreads.margin()
    assert mock_request.call_count == 2
    check_margin(result)


# ---------------------------------------------------------------------------
# Local validation happens before any request is sent
# ---------------------------------------------------------------------------

INVALID_CALLS = [
    ("basis empty pair", "spreads", "basis", ("",), {}),
    ("basis blank pair", "spreads", "basis", ("   ",), {}),
    ("basis non-str pair", "spreads", "basis", (None,), {}),
    ("basis_historical empty pair", "spreads", "basis_historical", ("",), {}),
    ("curve empty commodity", "spreads", "curve_structure", ("",), {}),
    ("crack blank type", "spreads", "crack", (), {"spread_type": " "}),
    ("crack bad start_date", "spreads", "crack_historical", (), {"start_date": "09/01/2026"}),
    ("margin impossible end_date", "spreads", "margin_historical", (), {"end_date": "2026-02-30"}),
    (
        "start after end", "spreads", "basis_historical", ("BRENT_WTI",),
        {"start_date": "2026-09-10", "end_date": "2026-09-01"},
    ),
    ("price_context empty code", "indicators", "price_context", ("",), {}),
    ("annotations empty code", "indicators", "annotations", ("",), {}),
    ("annotations_batch empty list", "indicators", "annotations_batch", ([],), {}),
    ("annotations_batch blank code", "indicators", "annotations_batch", (["BRENT_CRUDE_USD", ""],), {}),
    ("annotations_batch comma in code", "indicators", "annotations_batch", (["A,B"],), {}),
    ("annotations_batch bare string", "indicators", "annotations_batch", ("BRENT_CRUDE_USD",), {}),
    (
        "annotations_batch over server cap", "indicators", "annotations_batch",
        ([f"CODE_{i}" for i in range(21)],), {},
    ),
    ("cftc bad date type", "indicators", "cftc_positioning_historical", (), {"start_date": 20260901}),
]


@pytest.mark.parametrize("label,namespace,method,args,kwargs", INVALID_CALLS, ids=[c[0] for c in INVALID_CALLS])
@patch("httpx.Client.request")
def test_sync_invalid_arguments_never_reach_the_network(mock_request, label, namespace, method, args, kwargs):
    with pytest.raises(ValueError):
        getattr(getattr(_sync(), namespace), method)(*args, **kwargs)
    mock_request.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("label,namespace,method,args,kwargs", INVALID_CALLS, ids=[c[0] for c in INVALID_CALLS])
@patch("httpx.AsyncClient.request")
async def test_async_invalid_arguments_never_reach_the_network(
    mock_request, label, namespace, method, args, kwargs
):
    with pytest.raises(ValueError):
        await getattr(getattr(_async(), namespace), method)(*args, **kwargs)
    mock_request.assert_not_called()


def test_congressional_trades_is_not_exposed():
    """The route has never produced data in production; no typed method ships for it."""
    assert not hasattr(_sync().indicators, "congressional_trades")
