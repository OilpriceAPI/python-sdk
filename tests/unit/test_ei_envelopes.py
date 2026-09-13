"""Energy Intelligence resources must return what they promise (#107).

Every fixture in this file is the real production envelope, captured live from
``https://api.oilpriceapi.com`` on 2026-09-13 with a Scale-tier key. The bodies
are trimmed to one or two rows; no key name, nesting level or type is invented.

These tests drive the **actual client transport** (respx intercepts httpx), not
a mocked resource object, because the defect in #107 lives in the unwrapping
step between the HTTP body and the returned value. A test that stubs
``client.request`` cannot see it.
"""

from typing import Any, Dict, List

import httpx
import pytest
import respx

from oilpriceapi import AsyncOilPriceAPI, OilPriceAPI
from oilpriceapi.exceptions import (
    AuthenticationError,
    OilPriceAPIError,
    PermissionDeniedError,
    RateLimitError,
)

BASE_URL = "https://api.oilpriceapi.com"

# Not a credential: a fixture string. Every request in this module is mocked.
FIXTURE_KEY = "-".join(["fixture", "not", "a", "real", "key"])

META = {"api_version": "v1", "tier_required": "reservoir_mastery", "cache_ttl": 3600}


def _wrapped(data: Any) -> Dict[str, Any]:
    """The ``{data, meta}`` envelope used by the report-backed EI controllers."""
    return {"data": data, "meta": META}


def _status_wrapped(data: Any) -> Dict[str, Any]:
    """The ``{status, data}`` envelope used by well-permits and frac-focus."""
    return {"status": "success", "data": data}


# --------------------------------------------------------------------------
# Live-captured rows
# --------------------------------------------------------------------------

BASIN_ROW = {
    "region": "permian",
    "region_type": "basin",
    "count": 267,
    "week_over_week": 0,
    "change_direction": "flat",
}
STATE_ROW = {
    "region": "texas",
    "region_type": "state",
    "count": 282,
    "week_over_week": 1,
    "change_direction": "up",
}
RIG_HISTORY_ROW = {"date": "2026-08-28", "count": 588, "week_over_week": 0}
DUC_ROW = {
    "basin": "permian",
    "basin_name": "Permian",
    "duc_count": 1000,
    "region": "Permian",
    "type": "duc",
}
DP_MONTH_ROW = {"report_month": "2026-08-01", "basins": [{"basin": "permian"}]}
DP_HISTORY_ROW = {
    "report_month": "2026-08-01",
    "duc_count": 1000,
    "new_well_oil_per_rig": 1234,
    "new_well_gas_per_rig": 5678,
}
DP_TREND_ROW = {
    "basin": "permian",
    "current_duc": 1000,
    "previous_duc": 1010,
    "duc_change": -10,
    "duc_trend": "declining",
    "productivity_oil": 1234,
    "productivity_gas": 5678,
}
FORECAST_ACTUAL_ROW = {"report_month": "2026-08-01", "period": "2026-07", "value": 68.1}
INVENTORY_PRODUCT_ROW = {
    "product_type": "crude_commercial",
    "location": "us",
    "volume_mmbbl": 420.1,
    "week_over_week": -1.2,
    "direction": "draw",
    "vs_five_year_avg": -5.0,
}
INVENTORY_HISTORY_ROW = {
    "week_ending": "2026-09-05",
    "volume_mmbbl": 420.1,
    "week_over_week": -1.2,
}
OPEC_COUNTRY_ROW = {
    "country": "saudi_arabia",
    "name": "Saudi Arabia",
    "report_month": "2026-08-01",
    "publication_month": "2026-08-01",
    "production_month": "2026-07-01",
    "production_mbpd": 9000.0,
}
OPEC_HISTORY_ROW = {
    "report_month": "2026-08-01",
    "publication_month": "2026-08-01",
    "production_month": "2026-07-01",
    "production_mbpd": 9000.0,
}
OPEC_PRODUCER_ROW = {
    "rank": 1,
    "publication_month": "2026-08-01",
    "production_month": "2026-07-01",
    "country": "saudi_arabia",
    "name": "Saudi Arabia",
    "production_mbpd": 9000.0,
    "share_of_opec": 33.0,
}
PERMIT_ROW = {
    "api_number": "05123534110000",
    "state_code": "CO",
    "county": "Weld",
    "permit_number": "P-1",
    "permit_type": "drill",
    "permit_status": "approved",
    "permit_date": "2026-09-01",
    "operator": {"name": "Fixture Operating"},
    "well": {"name": "Fixture 1H"},
    "location": {"lat": 40.1, "lng": -104.7},
    "target": {"formation": "Niobrara"},
    "provenance": {"source": "cogcc"},
}
DISCLOSURE_ROW = {
    "upload_key": "ec7d19aa-2004-4e39-bd88-e660230cf74e",
    "api_number": "33053090090000",
    "api_number_formatted": "33-053-09009-00-00",
    "state_code": "ND",
    "county": "McKenzie",
    "operator": {"name": "Fixture Operating"},
    "well_name": "Fixture 1H",
    "location": {"lat": 47.8, "lng": -103.3},
    "job": {"start_date": "2026-08-01"},
    "water": {"total_water_volume": 400000},
    "chemicals": {"count": 26},
    "provenance": {"source": "fracfocus"},
}
CHEMICAL_ROW = {
    "cas": "7732-18-5",
    "mass": 1000.0,
    "name": "Water",
    "percent_hf_job": 88.0,
    "percent_additive": None,
}

# --------------------------------------------------------------------------
# The contract table: every EI method that returns a NAMED collection.
#
#   (dotted resource path, method name, route, envelope body, named key, rows)
# --------------------------------------------------------------------------

COLLECTION_CASES: List[tuple] = [
    (
        "rig_counts",
        "by_basin",
        "/v1/ei/rig_counts/by_basin",
        lambda rows: _wrapped({"report_date": "2026-08-28", "basins": rows}),
        "basins",
        [BASIN_ROW],
    ),
    (
        "rig_counts",
        "by_state",
        "/v1/ei/rig_counts/by_state",
        lambda rows: _wrapped({"report_date": "2026-08-28", "states": rows}),
        "states",
        [STATE_ROW],
    ),
    (
        "rig_counts",
        "historical",
        "/v1/ei/rig_counts/historical",
        lambda rows: _wrapped(
            {
                "region": "us",
                "start_date": "2025-09-13",
                "end_date": "2026-09-13",
                "records": rows,
            }
        ),
        "records",
        [RIG_HISTORY_ROW],
    ),
    (
        "drilling_productivity",
        "duc_wells",
        "/v1/ei/drilling_productivities/duc_wells",
        lambda rows: _wrapped(
            {
                "report_month": "2026-08-01",
                "total_duc": 5000,
                "by_basin": rows,
                "declining_basins": [],
            }
        ),
        "by_basin",
        [DUC_ROW],
    ),
    (
        "drilling_productivity",
        "by_basin",
        "/v1/ei/drilling_productivities/by_basin",
        # `basins` here is the echoed filter (a string), NOT the collection.
        lambda rows: _wrapped({"basins": "all", "months": rows}),
        "months",
        [DP_MONTH_ROW],
    ),
    (
        "drilling_productivity",
        "historical",
        "/v1/ei/drilling_productivities/historical",
        lambda rows: _wrapped(
            {"basin": "permian", "basin_name": "Permian", "records": rows}
        ),
        "records",
        [DP_HISTORY_ROW],
    ),
    (
        "drilling_productivity",
        "trends",
        "/v1/ei/drilling_productivities/trends",
        lambda rows: _wrapped(
            {
                "report_month": "2026-08-01",
                "analysis_months": 6,
                "trends": rows,
                "declining_duc_basins": [],
            }
        ),
        "trends",
        [DP_TREND_ROW],
    ),
    (
        "forecasts",
        "historical",
        "/v1/ei/forecasts/historical",
        lambda rows: _wrapped({"series_code": "BREPUUS", "actuals": rows}),
        "actuals",
        [FORECAST_ACTUAL_ROW],
    ),
    (
        "oil_inventories",
        "by_product",
        "/v1/ei/oil_inventories/by_product",
        lambda rows: _wrapped({"week_ending": "2026-09-05", "products": rows}),
        "products",
        [INVENTORY_PRODUCT_ROW],
    ),
    (
        "oil_inventories",
        "historical",
        "/v1/ei/oil_inventories/historical",
        lambda rows: _wrapped(
            {"product_type": "crude_commercial", "location": "us", "records": rows}
        ),
        "records",
        [INVENTORY_HISTORY_ROW],
    ),
    (
        "opec_production",
        "by_country",
        "/v1/ei/opec_productions/by_country",
        lambda rows: _wrapped(
            {
                "report_month": "2026-08-01",
                "publication_month": "2026-08-01",
                "production_month": "2026-07-01",
                "countries": rows,
                "opec_total": 27000.0,
            }
        ),
        "countries",
        [OPEC_COUNTRY_ROW],
    ),
    (
        "opec_production",
        "historical",
        "/v1/ei/opec_productions/historical",
        lambda rows: _wrapped(
            {"country": "saudi_arabia", "country_name": "Saudi Arabia", "records": rows}
        ),
        "records",
        [OPEC_HISTORY_ROW],
    ),
    (
        "opec_production",
        "top_producers",
        "/v1/ei/opec_productions/top_producers",
        lambda rows: _wrapped(
            {
                "report_month": "2026-08-01",
                "publication_month": "2026-08-01",
                "production_month": "2026-07-01",
                "producers": rows,
                "opec_total": 27000.0,
            }
        ),
        "producers",
        [OPEC_PRODUCER_ROW],
    ),
    (
        "well_permits",
        "list",
        "/v1/ei/well-permits",
        lambda rows: _status_wrapped({"well_permits": rows, "meta": {"total_count": 1}}),
        "well_permits",
        [PERMIT_ROW],
    ),
    (
        "well_permits",
        "by_state",
        "/v1/ei/well-permits/by-state",
        lambda rows: _status_wrapped(
            {"well_permits": rows, "state": "TX", "meta": {"total_count": 1}}
        ),
        "well_permits",
        [PERMIT_ROW],
    ),
    (
        "well_permits",
        "by_operator",
        "/v1/ei/well-permits/by-operator",
        lambda rows: _status_wrapped(
            {"well_permits": rows, "operator_query": "x", "meta": {"total_count": 1}}
        ),
        "well_permits",
        [PERMIT_ROW],
    ),
    (
        "well_permits",
        "by_formation",
        "/v1/ei/well-permits/by-formation",
        lambda rows: _status_wrapped(
            {"well_permits": rows, "formation_query": "x", "meta": {"total_count": 1}}
        ),
        "well_permits",
        [PERMIT_ROW],
    ),
    (
        "frac_focus",
        "list",
        "/v1/ei/frac-focus",
        lambda rows: _status_wrapped(
            {"frac_focus_disclosures": rows, "meta": {"total_count": 1}}
        ),
        "frac_focus_disclosures",
        [DISCLOSURE_ROW],
    ),
    (
        "frac_focus",
        "by_state",
        "/v1/ei/frac-focus/by-state",
        lambda rows: _status_wrapped(
            {"frac_focus_disclosures": rows, "state": "TX", "meta": {"total_count": 1}}
        ),
        "frac_focus_disclosures",
        [DISCLOSURE_ROW],
    ),
    (
        "frac_focus",
        "by_operator",
        "/v1/ei/frac-focus/by-operator",
        lambda rows: _status_wrapped(
            {
                "frac_focus_disclosures": rows,
                "operator_query": "x",
                "meta": {"total_count": 1},
            }
        ),
        "frac_focus_disclosures",
        [DISCLOSURE_ROW],
    ),
    (
        "frac_focus",
        "by_chemical",
        "/v1/ei/frac-focus/by-chemical",
        lambda rows: _status_wrapped(
            {
                "frac_focus_disclosures": rows,
                "chemical_query": {"cas": "7732-18-5"},
                "meta": {"total_count": 1},
            }
        ),
        "frac_focus_disclosures",
        [DISCLOSURE_ROW],
    ),
]

# Methods that take a positional argument, kept separate so the parametrised
# cases above stay uniform.
POSITIONAL_COLLECTION_CASES: List[tuple] = [
    (
        "frac_focus",
        "chemicals",
        ("ec7d19aa-2004-4e39-bd88-e660230cf74e",),
        "/v1/ei/frac-focus/ec7d19aa-2004-4e39-bd88-e660230cf74e/chemicals",
        lambda rows: _status_wrapped(
            {
                "upload_key": "ec7d19aa-2004-4e39-bd88-e660230cf74e",
                "api_number": "33053090090000",
                "well_name": "Fixture 1H",
                "operator": "Fixture Operating",
                "job_start_date": None,
                "chemical_count": len(rows),
                "chemicals": rows,
                "additives": [],
                "cas_numbers": [],
                "suppliers": [],
            }
        ),
        "chemicals",
        [CHEMICAL_ROW],
    ),
    (
        "frac_focus",
        "for_well",
        ("33053090090000",),
        "/v1/ei/frac-focus/for-well/33053090090000",
        lambda rows: _status_wrapped(
            {
                "api_number": "33053090090000",
                "frac_focus_disclosures": rows,
                "count": len(rows),
            }
        ),
        "frac_focus_disclosures",
        [DISCLOSURE_ROW],
    ),
    (
        "frac_focus",
        "search",
        ("Fixture",),
        "/v1/ei/frac-focus/search",
        lambda rows: _status_wrapped(
            {"frac_focus_disclosures": rows, "meta": {"total_count": 1}}
        ),
        "frac_focus_disclosures",
        [DISCLOSURE_ROW],
    ),
]

ALL_COLLECTION_CASES = [
    (res, meth, (), route, body, key, rows)
    for (res, meth, route, body, key, rows) in COLLECTION_CASES
] + POSITIONAL_COLLECTION_CASES

CASE_IDS = ["%s.%s" % (c[0], c[1]) for c in ALL_COLLECTION_CASES]

# Single-object endpoints whose record is nested under a named key.
OBJECT_CASES = [
    (
        "well_permits",
        "get",
        ("05123534110000",),
        "/v1/ei/well-permits/05123534110000",
        _status_wrapped({"well_permit": PERMIT_ROW}),
        PERMIT_ROW,
    ),
    (
        "frac_focus",
        "get",
        ("ec7d19aa-2004-4e39-bd88-e660230cf74e",),
        "/v1/ei/frac-focus/ec7d19aa-2004-4e39-bd88-e660230cf74e",
        _status_wrapped({"frac_focus_disclosure": DISCLOSURE_ROW}),
        DISCLOSURE_ROW,
    ),
]
OBJECT_IDS = ["%s.%s" % (c[0], c[1]) for c in OBJECT_CASES]


def _sync_method(client: OilPriceAPI, resource: str, method: str):
    return getattr(getattr(client.ei, resource), method)


def _async_method(client: AsyncOilPriceAPI, resource: str, method: str):
    return getattr(getattr(client.ei, resource), method)


# --------------------------------------------------------------------------
# 1. Valid: the named collection is returned, not the envelope object
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "resource,method,args,route,body,key,rows", ALL_COLLECTION_CASES, ids=CASE_IDS
)
@respx.mock
def test_named_collection_is_unwrapped(resource, method, args, route, body, key, rows):
    respx.get(BASE_URL + route).mock(
        return_value=httpx.Response(200, json=body(rows))
    )
    client = OilPriceAPI(api_key=FIXTURE_KEY)

    result = _sync_method(client, resource, method)(*args)

    assert result == rows, (
        "%s.%s must return the %r list, got %r" % (resource, method, key, result)
    )


@pytest.mark.parametrize(
    "resource,method,args,route,body,key,rows", ALL_COLLECTION_CASES, ids=CASE_IDS
)
@pytest.mark.asyncio
@respx.mock
async def test_named_collection_is_unwrapped_async(
    resource, method, args, route, body, key, rows
):
    respx.get(BASE_URL + route).mock(
        return_value=httpx.Response(200, json=body(rows))
    )
    client = AsyncOilPriceAPI(api_key=FIXTURE_KEY)

    result = await _async_method(client, resource, method)(*args)

    assert result == rows, (
        "async %s.%s must return the %r list, got %r" % (resource, method, key, result)
    )


# --------------------------------------------------------------------------
# 2. Empty collection is a valid empty list, never an error
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "resource,method,args,route,body,key,rows", ALL_COLLECTION_CASES, ids=CASE_IDS
)
@respx.mock
def test_empty_named_collection_returns_empty_list(
    resource, method, args, route, body, key, rows
):
    respx.get(BASE_URL + route).mock(return_value=httpx.Response(200, json=body([])))
    client = OilPriceAPI(api_key=FIXTURE_KEY)

    assert _sync_method(client, resource, method)(*args) == []


# --------------------------------------------------------------------------
# 3. Missing collection key is an explicit failure, never a fabricated []
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "resource,method,args,route,body,key,rows", ALL_COLLECTION_CASES, ids=CASE_IDS
)
@respx.mock
def test_missing_collection_key_raises(resource, method, args, route, body, key, rows):
    broken = body(rows)
    # Drop the named collection, keep everything else the server sent.
    if isinstance(broken.get("data"), dict):
        broken["data"].pop(key, None)
    respx.get(BASE_URL + route).mock(return_value=httpx.Response(200, json=broken))
    client = OilPriceAPI(api_key=FIXTURE_KEY)

    with pytest.raises(OilPriceAPIError, match=key) as error:
        _sync_method(client, resource, method)(*args)

    assert error.value.code == "MALFORMED_RESPONSE"


@pytest.mark.parametrize(
    "resource,method,args,route,body,key,rows", ALL_COLLECTION_CASES, ids=CASE_IDS
)
@pytest.mark.asyncio
@respx.mock
async def test_missing_collection_key_raises_async(
    resource, method, args, route, body, key, rows
):
    broken = body(rows)
    if isinstance(broken.get("data"), dict):
        broken["data"].pop(key, None)
    respx.get(BASE_URL + route).mock(return_value=httpx.Response(200, json=broken))
    client = AsyncOilPriceAPI(api_key=FIXTURE_KEY)

    with pytest.raises(OilPriceAPIError, match=key) as error:
        await _async_method(client, resource, method)(*args)

    assert error.value.code == "MALFORMED_RESPONSE"


# --------------------------------------------------------------------------
# 4. A malformed row is an explicit failure
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "resource,method,args,route,body,key,rows", ALL_COLLECTION_CASES, ids=CASE_IDS
)
@respx.mock
def test_malformed_row_raises(resource, method, args, route, body, key, rows):
    respx.get(BASE_URL + route).mock(
        return_value=httpx.Response(200, json=body(["not-a-record"]))
    )
    client = OilPriceAPI(api_key=FIXTURE_KEY)

    with pytest.raises(OilPriceAPIError, match=key) as error:
        _sync_method(client, resource, method)(*args)

    assert error.value.code == "MALFORMED_RESPONSE"


# --------------------------------------------------------------------------
# 5. Single-object endpoints unwrap their named record
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "resource,method,args,route,body,expected", OBJECT_CASES, ids=OBJECT_IDS
)
@respx.mock
def test_named_object_is_unwrapped(resource, method, args, route, body, expected):
    respx.get(BASE_URL + route).mock(return_value=httpx.Response(200, json=body))
    client = OilPriceAPI(api_key=FIXTURE_KEY)

    assert _sync_method(client, resource, method)(*args) == expected


@pytest.mark.parametrize(
    "resource,method,args,route,body,expected", OBJECT_CASES, ids=OBJECT_IDS
)
@pytest.mark.asyncio
@respx.mock
async def test_named_object_is_unwrapped_async(
    resource, method, args, route, body, expected
):
    respx.get(BASE_URL + route).mock(return_value=httpx.Response(200, json=body))
    client = AsyncOilPriceAPI(api_key=FIXTURE_KEY)

    assert await _async_method(client, resource, method)(*args) == expected


# --------------------------------------------------------------------------
# 6. Methods whose envelope is genuinely an object keep returning the object
#    (regression guard: the fix must not broad-unwrap everything)
# --------------------------------------------------------------------------

OBJECT_PASSTHROUGH_CASES = [
    (
        "rig_counts",
        "latest",
        "/v1/ei/rig_counts/latest",
        _wrapped(
            {
                "id": "1",
                "report_date": "2026-08-28",
                "source": "baker_hughes",
                "last_updated": "2026-09-01T00:00:00Z",
                "us_total": {"total_rigs": 588},
                "basins": {"permian": {"count": 267}},
                "top_states": [{"state": "texas", "count": 282}],
                "drilling_type": None,
            }
        ),
    ),
    (
        "forecasts",
        "compare",
        "/v1/ei/forecasts/compare",
        _wrapped(
            {
                "series_code": "BREPUUS",
                "month1": "2026-07-01",
                "month2": "2026-08-01",
                "comparison": [],
            }
        ),
    ),
    (
        "forecasts",
        "prices",
        "/v1/ei/forecasts/prices",
        _wrapped(
            {
                "report_month": "2026-08-01",
                # A mapping keyed by commodity — not a list.
                "commodities": {"brent": [{"period": "2026-09", "value": 68.0}]},
            }
        ),
    ),
    (
        "forecasts",
        "production",
        "/v1/ei/forecasts/production",
        _wrapped({"report_month": "2026-08-01", "series": {}}),
    ),
    (
        "oil_inventories",
        "cushing",
        "/v1/ei/oil_inventories/cushing",
        _wrapped({"location": "cushing", "latest": {}, "history": []}),
    ),
    (
        "opec_production",
        "total",
        "/v1/ei/opec_productions/total",
        _wrapped({"latest": {}, "history": [], "trend": {}}),
    ),
    (
        "well_permits",
        "summary",
        "/v1/ei/well-permits/summary",
        _status_wrapped({"period_days": 90, "total_permits": 10, "by_state": {}}),
    ),
    (
        "frac_focus",
        "summary",
        "/v1/ei/frac-focus/summary",
        _status_wrapped({"period_days": 90, "total_disclosures": 10, "by_state": {}}),
    ),
]
PASSTHROUGH_IDS = ["%s.%s" % (c[0], c[1]) for c in OBJECT_PASSTHROUGH_CASES]


@pytest.mark.parametrize(
    "resource,method,route,body", OBJECT_PASSTHROUGH_CASES, ids=PASSTHROUGH_IDS
)
@respx.mock
def test_object_envelopes_are_returned_whole(resource, method, route, body):
    respx.get(BASE_URL + route).mock(return_value=httpx.Response(200, json=body))
    client = OilPriceAPI(api_key=FIXTURE_KEY)

    assert _sync_method(client, resource, method)() == body["data"]


# --------------------------------------------------------------------------
# 7. Auth / permission / rate-limit paths stay explicit
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "status,body,expected",
    [
        (401, {"error": "Invalid API key"}, AuthenticationError),
        (
            403,
            {
                "error": "This endpoint requires the Scale plan",
                "upgrade_url": "https://oilpriceapi.com/pricing",
            },
            PermissionDeniedError,
        ),
        (429, {"error": "Rate limit exceeded"}, RateLimitError),
    ],
)
@respx.mock
def test_error_statuses_raise_and_never_return_empty(status, body, expected):
    respx.get(BASE_URL + "/v1/ei/rig_counts/by_basin").mock(
        return_value=httpx.Response(status, json=body)
    )
    client = OilPriceAPI(api_key=FIXTURE_KEY, max_retries=1)

    with pytest.raises(expected):
        client.ei.rig_counts.by_basin()


@pytest.mark.parametrize(
    "status,expected",
    [(401, AuthenticationError), (403, PermissionDeniedError), (429, RateLimitError)],
)
@pytest.mark.asyncio
@respx.mock
async def test_error_statuses_raise_and_never_return_empty_async(status, expected):
    respx.get(BASE_URL + "/v1/ei/well-permits/by-state").mock(
        return_value=httpx.Response(status, json={"error": "nope"})
    )
    client = AsyncOilPriceAPI(api_key=FIXTURE_KEY, max_retries=1)

    with pytest.raises(expected):
        await client.ei.well_permits.by_state(state="TX")


# --------------------------------------------------------------------------
# 8. Sync and async must not diverge
# --------------------------------------------------------------------------

EI_RESOURCE_PAIRS = [
    "rig_counts",
    "oil_inventories",
    "opec_production",
    "drilling_productivity",
    "forecasts",
    "well_permits",
    "frac_focus",
]


def _public_methods(obj) -> set:
    return {
        name
        for name in dir(obj)
        if not name.startswith("_") and callable(getattr(obj, name))
    } - {"client"}


@pytest.mark.parametrize("resource", EI_RESOURCE_PAIRS)
def test_sync_and_async_expose_the_same_ei_methods(resource):
    sync_client = OilPriceAPI(api_key=FIXTURE_KEY)
    async_client = AsyncOilPriceAPI(api_key=FIXTURE_KEY)

    sync_methods = _public_methods(getattr(sync_client.ei, resource))
    async_methods = _public_methods(getattr(async_client.ei, resource))

    assert sync_methods == async_methods, (
        "sync/async drift on ei.%s: sync-only=%s async-only=%s"
        % (resource, sorted(sync_methods - async_methods), sorted(async_methods - sync_methods))
    )


@pytest.mark.parametrize(
    "resource,method,args,route,body,key,rows", ALL_COLLECTION_CASES, ids=CASE_IDS
)
@pytest.mark.asyncio
async def test_sync_and_async_return_identical_values(
    resource, method, args, route, body, key, rows
):
    payload = body(rows)

    with respx.mock:
        respx.get(BASE_URL + route).mock(
            return_value=httpx.Response(200, json=payload)
        )
        sync_result = _sync_method(OilPriceAPI(api_key=FIXTURE_KEY), resource, method)(
            *args
        )

    with respx.mock:
        respx.get(BASE_URL + route).mock(
            return_value=httpx.Response(200, json=payload)
        )
        async_result = await _async_method(
            AsyncOilPriceAPI(api_key=FIXTURE_KEY), resource, method
        )(*args)

    assert sync_result == async_result


# --------------------------------------------------------------------------
# 9. Source-level parity: the async copy must unwrap exactly like the sync one
# --------------------------------------------------------------------------

SYNC_MODULES = {
    "AsyncEIRigCountsResource": "rig_counts",
    "AsyncEIOilInventoriesResource": "oil_inventories",
    "AsyncEIOpecProductionResource": "opec_production",
    "AsyncEIDrillingProductivityResource": "drilling_productivity",
    "AsyncEIForecastsResource": "forecasts",
    "AsyncEIWellPermitsResource": "well_permits",
    "AsyncEIFracFocusResource": "frac_focus",
}

SYNC_CLASSES = {
    "rig_counts": "EIRigCountsResource",
    "oil_inventories": "EIOilInventoriesResource",
    "opec_production": "EIOpecProductionResource",
    "drilling_productivity": "EIDrillingProductivityResource",
    "forecasts": "EIForecastsResource",
    "well_permits": "EIWellPermitsResource",
    "frac_focus": "EIFracFocusResource",
}


def _return_expression(func) -> str:
    """The text of the function's trailing return statement, normalised."""
    import inspect
    import textwrap

    source = textwrap.dedent(inspect.getsource(func))
    index = source.rfind("\n    return ")
    if index == -1:
        index = source.rfind("\nreturn ")
    assert index != -1, func
    return " ".join(source[index:].split())


@pytest.mark.parametrize("async_class,module", sorted(SYNC_MODULES.items()))
def test_async_ei_unwrapping_matches_sync_line_for_line(async_class, module):
    import importlib

    async_mod = importlib.import_module("oilpriceapi.async_resources")
    sync_mod = importlib.import_module("oilpriceapi.resources.ei.%s" % module)

    async_cls = getattr(async_mod, async_class)
    sync_cls = getattr(sync_mod, SYNC_CLASSES[module])

    mismatches = []
    for name in sorted(_public_methods(sync_cls)):
        sync_fn = getattr(sync_cls, name)
        async_fn = getattr(async_cls, name, None)
        assert async_fn is not None, "%s is missing %s" % (async_class, name)
        sync_expr = _return_expression(sync_fn)
        async_expr = _return_expression(async_fn)
        if sync_expr != async_expr:
            mismatches.append((name, sync_expr, async_expr))

    assert not mismatches, "sync/async unwrapping drift: %r" % (mismatches,)
