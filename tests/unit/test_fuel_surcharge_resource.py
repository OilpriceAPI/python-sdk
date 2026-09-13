"""Typed LTL + parcel fuel-surcharge clients (#101).

Every test drives the REAL sync or async client against a mocked transport
(`httpx.Client.request` / `httpx.AsyncClient.request`, the repo convention used
by tests/unit/test_empty_204_response.py). Nothing here stubs the resource or
asserts that a method "was called": each test checks what went out on the wire
and what came back to the caller.

Success fixtures are trimmed copies of production bodies captured on
2026-09-13 from https://api.oilpriceapi.com (GET /v1/fuel-surcharge,
/v1/fuel-surcharge/parcel, /odfl/latest, /odfl/history?per_page=3&page=2,
/parcel/ups/latest[?service_level=ground], /parcel/ups/history?service_level=
ground&per_page=2). The 404 bodies are production captures too (unknown
carrier `nope`, reserved carrier `fedex-freight`, parcel no-data for an unknown
service level). The 400 body is the production response to
/parcel/ups/history without a service level. The 401 body is the production
response to an unauthenticated call. 402/403/429 use the canonical nested error
envelope; only their status mapping is under test.
"""

import asyncio
import copy
import json
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from oilpriceapi import (
    AsyncOilPriceAPI,
    FuelSurchargeDieselBand,
    FuelSurchargeHistoryPage,
    FuelSurchargeRate,
    OilPriceAPI,
    ParcelFuelSurchargeCarrier,
)
from oilpriceapi.exceptions import (
    AuthenticationError,
    BadRequestError,
    DataNotFoundError,
    OilPriceAPIError,
    PaymentRequiredError,
    PermissionDeniedError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)

# Not a credential: a fixture string, every request here is mocked.
FIXTURE_KEY = "-".join(["fixture", "not", "a", "real", "key"])

# --- production captures (2026-09-13) ---------------------------------------

ODFL_LATEST = {
    "carrier": "odfl",
    "carrier_name": "Old Dominion Freight Line",
    "mode": "ltl",
    "surcharge_percent": 46.32,
    "effective_date": "2026-09-09",
    "doe_diesel_price": 5.599,
    "diesel_band": None,
    "source": "https://www.odfl.com/us/en/resources/fuel-surcharge.html",
    "retrieved_at": "2026-09-08T16:10:10Z",
}

ABF_LATEST = {
    "carrier": "abf",
    "carrier_name": "ABF Freight (ArcBest)",
    "mode": "ltl",
    "surcharge_percent": 50.0,
    "effective_date": "2026-09-02",
    "doe_diesel_price": None,
    "diesel_band": None,
    "source": "https://arcb.com/abf-freight/resources/fuel-surcharge.html",
    "retrieved_at": "2026-09-08T16:10:29Z",
}

SEFL_LATEST = {
    "carrier": "southeastern-freight",
    "carrier_name": "Southeastern Freight Lines",
    "mode": "ltl",
    "surcharge_percent": 44.63,
    "effective_date": "2026-09-02",
    "doe_diesel_price": 5.599,
    "diesel_band": {"min": 5.57, "max": 5.6},
    "source": "https://www.sefl.com/seflWebsite/servlet/FUELSURCHARGE_FUELPAGEUPDATE",
    "retrieved_at": "2026-09-08T16:10:34Z",
}

LTL_LIST = {"status": "success", "data": {"carriers": [ODFL_LATEST, ABF_LATEST, SEFL_LATEST]}}

ODFL_HISTORY_PAGE_2 = {
    "status": "success",
    "data": {
        "history": [
            {
                "carrier": "odfl",
                "carrier_name": "Old Dominion Freight Line",
                "mode": "ltl",
                "surcharge_percent": 43.82,
                "effective_date": "2026-08-05",
                "doe_diesel_price": 5.313,
                "diesel_band": None,
                "source": "https://www.odfl.com/us/en/resources/fuel-surcharge.html",
                "retrieved_at": "2026-08-04T16:10:04Z",
            },
            {
                "carrier": "odfl",
                "carrier_name": "Old Dominion Freight Line",
                "mode": "ltl",
                "surcharge_percent": 41.82,
                "effective_date": "2026-07-29",
                "doe_diesel_price": 5.134,
                "diesel_band": None,
                "source": "https://www.odfl.com/us/en/resources/fuel-surcharge.html",
                "retrieved_at": "2026-07-28T16:10:40Z",
            },
            {
                "carrier": "odfl",
                "carrier_name": "Old Dominion Freight Line",
                "mode": "ltl",
                "surcharge_percent": 38.32,
                "effective_date": "2026-07-22",
                "doe_diesel_price": 4.796,
                "diesel_band": None,
                "source": "https://www.odfl.com/us/en/resources/fuel-surcharge.html",
                "retrieved_at": "2026-07-21T16:10:07Z",
            },
        ],
        "meta": {"page": 2, "per_page": 3, "total_count": 6, "total_pages": 2},
    },
}

UPS_SOURCE = "https://www.ups.com/us/en/support/shipping-support/shipping-costs-rates/fuel-surcharges"

UPS_AIR = {
    "carrier": "ups",
    "carrier_name": "UPS",
    "mode": "parcel",
    "surcharge_percent": 29.25,
    "effective_date": "2026-09-07",
    "doe_diesel_price": None,
    "diesel_band": None,
    "source": UPS_SOURCE,
    "retrieved_at": "2026-09-08T16:10:36Z",
    "service_level": "air",
}

UPS_GROUND = {
    "carrier": "ups",
    "carrier_name": "UPS",
    "mode": "parcel",
    "surcharge_percent": 27.5,
    "effective_date": "2026-09-07",
    "doe_diesel_price": None,
    "diesel_band": None,
    "source": UPS_SOURCE,
    "retrieved_at": "2026-09-08T16:10:36Z",
    "service_level": "ground",
}

UPS_GROUND_PREVIOUS = {
    "carrier": "ups",
    "carrier_name": "UPS",
    "mode": "parcel",
    "surcharge_percent": 27.75,
    "effective_date": "2026-08-31",
    "doe_diesel_price": None,
    "diesel_band": None,
    "source": UPS_SOURCE,
    "retrieved_at": "2026-09-08T16:10:36Z",
    "service_level": "ground",
}

DHL_EXPORT = {
    "carrier": "dhl",
    "carrier_name": "DHL Express (U.S.)",
    "mode": "parcel",
    "surcharge_percent": 33.25,
    "effective_date": "2026-09-14",
    "doe_diesel_price": None,
    "diesel_band": None,
    "source": "https://www.dhl.com/us-en/home/express/products-and-solutions/products-and-services-overview/surcharges.html",
    "retrieved_at": "2026-09-08T16:10:38Z",
    "service_level": "export",
}

UPS_CARRIER = {"carrier": "ups", "carrier_name": "UPS", "mode": "parcel", "service_levels": [UPS_AIR, UPS_GROUND]}
DHL_CARRIER = {
    "carrier": "dhl",
    "carrier_name": "DHL Express (U.S.)",
    "mode": "parcel",
    "service_levels": [DHL_EXPORT],
}

PARCEL_LIST = {"status": "success", "data": {"carriers": [UPS_CARRIER, DHL_CARRIER]}}
UPS_PARCEL_LATEST = {"status": "success", "data": UPS_CARRIER}
UPS_GROUND_LATEST = {"status": "success", "data": UPS_GROUND}
UPS_GROUND_HISTORY = {
    "status": "success",
    "data": {
        "history": [UPS_GROUND, UPS_GROUND_PREVIOUS],
        "meta": {"page": 1, "per_page": 2, "total_count": 20, "total_pages": 10},
    },
}

LTL_COVERED = ["odfl", "saia", "estes", "xpo", "abf", "tforce", "averitt", "southeastern-freight"]

UNKNOWN_CARRIER_404 = {
    "status": "fail",
    "data": {
        "error": "Unknown carrier 'nope'. Covered carriers: odfl, saia, estes, xpo, abf, tforce, "
        "averitt, southeastern-freight.",
        "covered_carriers": LTL_COVERED,
        "hint": "Call GET /v1/fuel-surcharge to list every covered carrier with its latest surcharge.",
    },
}

RESERVED_CARRIER_404 = {
    "status": "fail",
    "data": {
        "error": "Carrier 'fedex-freight' is not yet covered — we have not ingested its "
        "fuel-surcharge schedule. Covered carriers: odfl, saia, estes, xpo, abf, tforce, averitt, "
        "southeastern-freight.",
        "covered_carriers": LTL_COVERED,
    },
}

PARCEL_NO_DATA_404 = {
    "status": "fail",
    "data": {
        "error": "No fuel-surcharge data retrieved yet for carrier 'ups'. Call GET /v1/fuel-surcharge "
        "to see which carriers currently have data.",
        "covered_carriers": ["ups", "fedex", "dhl"],
    },
}

MISSING_SERVICE_LEVEL_400 = {
    "status": "fail",
    "data": {
        "error": "Parcel fuel-surcharge history requires a service_level parameter.",
        "carrier": "ups",
        "available_service_levels": [
            "air",
            "ground",
            "international_air_export",
            "international_air_import",
            "international_ground",
        ],
    },
}

UNAUTHORIZED_401 = {
    "error": {
        "code": "UNAUTHORIZED",
        "message": "Missing or invalid API key. Include header: Authorization: Token YOUR_API_KEY",
        "status": 401,
        "request_id": "bc98b482-7a78-4802-b0fe-53da93baab92",
        "docs": "https://docs.oilpriceapi.com#UNAUTHORIZED",
    }
}


def _envelope(code, status, message):
    return {"error": {"code": code, "message": message, "status": status}}


# --- transport harness --------------------------------------------------------


def _response(status, payload=None, *, raw=None):
    response = Mock()
    response.status_code = status
    response.headers = {}
    if raw is not None:
        response.content = raw
        response.text = raw.decode()
        response.json.side_effect = json.JSONDecodeError("Expecting value", raw.decode(), 0)
    else:
        text = json.dumps(payload)
        response.content = text.encode()
        response.text = text
        response.json.return_value = copy.deepcopy(payload)
    return response


class Transport:
    """Both transports patched at once; tests run the same body on either client."""

    def __init__(self, sync_mock, async_mock):
        self.sync_mock = sync_mock
        self.async_mock = async_mock

    def respond(self, status, payload=None, **kwargs):
        response = _response(status, payload, **kwargs)
        self.sync_mock.return_value = response
        self.async_mock.return_value = response

    def raise_(self, exc):
        self.sync_mock.side_effect = exc
        self.async_mock.side_effect = exc

    @property
    def calls(self):
        return self.sync_mock.call_args_list + self.async_mock.call_args_list

    def last(self):
        calls = self.calls
        assert len(calls) == 1, f"expected exactly one request, got {len(calls)}"
        return calls[0].kwargs


@pytest.fixture
def transport():
    sync_mock = Mock()
    async_mock = AsyncMock()
    with patch("httpx.Client.request", sync_mock), patch("httpx.AsyncClient.request", async_mock):
        yield Transport(sync_mock, async_mock)


@pytest.fixture(params=["sync", "async"])
def call(request):
    """Run `fn(client)` against a real sync or async client."""

    def run(fn):
        if request.param == "sync":
            client = OilPriceAPI(api_key=FIXTURE_KEY, max_retries=1)
            try:
                return fn(client)
            finally:
                client.close()

        async def go():
            client = AsyncOilPriceAPI(api_key=FIXTURE_KEY, max_retries=1)
            try:
                return await fn(client)
            finally:
                await client.close()

        return asyncio.run(go())

    return run


def _path(kwargs):
    return httpx.URL(str(kwargs["url"])).path


# --- LTL -----------------------------------------------------------------------


def test_list_returns_typed_rates_with_provenance_and_nulls(transport, call):
    transport.respond(200, LTL_LIST)

    rates = call(lambda c: c.fuel_surcharge.list())

    sent = transport.last()
    assert sent["method"] == "GET"
    assert _path(sent) == "/v1/fuel-surcharge"
    assert [r.carrier for r in rates] == ["odfl", "abf", "southeastern-freight"]
    assert all(isinstance(r, FuelSurchargeRate) for r in rates)

    odfl, abf, sefl = rates
    assert odfl.carrier_name == "Old Dominion Freight Line"
    assert odfl.mode == "ltl"
    assert odfl.surcharge_percent == 46.32
    assert odfl.effective_date == date(2026, 9, 9)
    assert type(odfl.effective_date) is date
    assert odfl.retrieved_at == datetime(2026, 9, 8, 16, 10, 10, tzinfo=timezone.utc)
    assert odfl.retrieved_at.tzinfo is not None
    assert odfl.source == "https://www.odfl.com/us/en/resources/fuel-surcharge.html"
    assert odfl.doe_diesel_price == 5.599
    assert odfl.service_level is None

    # A null the API sends stays a null: no invented diesel price or band.
    assert abf.doe_diesel_price is None
    assert abf.diesel_band is None

    assert isinstance(sefl.diesel_band, FuelSurchargeDieselBand)
    assert sefl.diesel_band.min == 5.57
    assert sefl.diesel_band.max == 5.6


def test_list_with_no_carriers_is_an_empty_list(transport, call):
    transport.respond(200, {"status": "success", "data": {"carriers": []}})
    assert call(lambda c: c.fuel_surcharge.list()) == []


def test_latest_hits_the_carrier_route(transport, call):
    transport.respond(200, {"status": "success", "data": ODFL_LATEST})

    rate = call(lambda c: c.fuel_surcharge.latest("odfl"))

    sent = transport.last()
    assert _path(sent) == "/v1/fuel-surcharge/odfl/latest"
    assert not sent.get("params")
    assert isinstance(rate, FuelSurchargeRate)
    assert rate.surcharge_percent == 46.32
    assert rate.effective_date == date(2026, 9, 9)


def test_latest_keeps_the_public_hyphenated_slug(transport, call):
    transport.respond(200, {"status": "success", "data": SEFL_LATEST})

    rate = call(lambda c: c.fuel_surcharge.latest("southeastern-freight"))

    assert _path(transport.last()) == "/v1/fuel-surcharge/southeastern-freight/latest"
    assert rate.carrier == "southeastern-freight"


def test_history_sends_pagination_and_preserves_meta(transport, call):
    transport.respond(200, ODFL_HISTORY_PAGE_2)

    page = call(lambda c: c.fuel_surcharge.history("odfl", page=2, per_page=3))

    sent = transport.last()
    assert _path(sent) == "/v1/fuel-surcharge/odfl/history"
    assert sent["params"] == {"page": 2, "per_page": 3}
    assert isinstance(page, FuelSurchargeHistoryPage)
    assert [r.effective_date for r in page.history] == [
        date(2026, 8, 5),
        date(2026, 7, 29),
        date(2026, 7, 22),
    ]
    assert page.meta.page == 2
    assert page.meta.per_page == 3
    assert page.meta.total_count == 6
    assert page.meta.total_pages == 2


def test_history_without_pagination_sends_no_page_params(transport, call):
    transport.respond(200, ODFL_HISTORY_PAGE_2)

    call(lambda c: c.fuel_surcharge.history("odfl"))

    assert not transport.last().get("params")


# --- parcel ---------------------------------------------------------------------


def test_parcel_list_returns_carriers_with_service_levels(transport, call):
    transport.respond(200, PARCEL_LIST)

    carriers = call(lambda c: c.fuel_surcharge.parcel_list())

    assert _path(transport.last()) == "/v1/fuel-surcharge/parcel"
    assert [c.carrier for c in carriers] == ["ups", "dhl"]
    ups = carriers[0]
    assert isinstance(ups, ParcelFuelSurchargeCarrier)
    assert ups.mode == "parcel"
    assert [s.service_level for s in ups.service_levels] == ["air", "ground"]
    assert ups.service_levels[1].surcharge_percent == 27.5
    assert ups.service_levels[1].doe_diesel_price is None
    assert carriers[1].service_levels[0].effective_date == date(2026, 9, 14)


def test_parcel_latest_without_service_level_returns_the_carrier(transport, call):
    transport.respond(200, UPS_PARCEL_LATEST)

    carrier = call(lambda c: c.fuel_surcharge.parcel_latest("ups"))

    sent = transport.last()
    assert _path(sent) == "/v1/fuel-surcharge/parcel/ups/latest"
    assert not sent.get("params")
    assert isinstance(carrier, ParcelFuelSurchargeCarrier)
    assert carrier.carrier_name == "UPS"
    assert len(carrier.service_levels) == 2


def test_parcel_latest_rate_returns_one_service_level(transport, call):
    transport.respond(200, UPS_GROUND_LATEST)

    rate = call(lambda c: c.fuel_surcharge.parcel_latest_rate("ups", "ground"))

    sent = transport.last()
    assert _path(sent) == "/v1/fuel-surcharge/parcel/ups/latest"
    assert sent["params"] == {"service_level": "ground"}
    assert isinstance(rate, FuelSurchargeRate)
    assert rate.service_level == "ground"
    assert rate.mode == "parcel"
    assert rate.source == UPS_SOURCE


def test_parcel_history_requires_and_sends_service_level(transport, call):
    transport.respond(200, UPS_GROUND_HISTORY)

    page = call(lambda c: c.fuel_surcharge.parcel_history("ups", "ground", per_page=2))

    sent = transport.last()
    assert _path(sent) == "/v1/fuel-surcharge/parcel/ups/history"
    assert sent["params"] == {"service_level": "ground", "per_page": 2}
    assert page.meta.total_count == 20
    assert page.meta.total_pages == 10
    assert [r.effective_date for r in page.history] == [date(2026, 9, 7), date(2026, 8, 31)]


# --- API refusals ---------------------------------------------------------------


def test_unknown_carrier_is_a_404_that_names_the_covered_carriers(transport, call):
    transport.respond(404, UNKNOWN_CARRIER_404)

    with pytest.raises(DataNotFoundError) as info:
        call(lambda c: c.fuel_surcharge.latest("nope"))

    error = info.value
    assert error.status_code == 404
    assert "Unknown carrier 'nope'" in error.message
    assert error.suggestions == LTL_COVERED
    assert error.raw_body["data"]["covered_carriers"] == LTL_COVERED


def test_reserved_carrier_is_a_404_not_fabricated_data(transport, call):
    transport.respond(404, RESERVED_CARRIER_404)

    with pytest.raises(DataNotFoundError) as info:
        call(lambda c: c.fuel_surcharge.history("fedex-freight"))

    assert "not yet covered" in info.value.message
    assert info.value.suggestions == LTL_COVERED


def test_no_data_yet_is_a_404(transport, call):
    transport.respond(404, PARCEL_NO_DATA_404)

    with pytest.raises(DataNotFoundError) as info:
        call(lambda c: c.fuel_surcharge.parcel_latest_rate("ups", "bogus"))

    assert "No fuel-surcharge data retrieved yet" in info.value.message
    assert info.value.suggestions == ["ups", "fedex", "dhl"]


def test_server_missing_service_level_400_surfaces_available_levels(transport, call):
    transport.respond(400, MISSING_SERVICE_LEVEL_400)

    with pytest.raises(BadRequestError) as info:
        call(lambda c: c.fuel_surcharge.parcel_history("ups", "ground"))

    assert "requires a service_level" in info.value.message
    assert info.value.suggestions == MISSING_SERVICE_LEVEL_400["data"]["available_service_levels"]


def test_401_raises_authentication_error(transport, call):
    transport.respond(401, UNAUTHORIZED_401)

    with pytest.raises(AuthenticationError) as info:
        call(lambda c: c.fuel_surcharge.list())

    assert info.value.code == "UNAUTHORIZED"
    assert info.value.request_id == "bc98b482-7a78-4802-b0fe-53da93baab92"


@pytest.mark.parametrize(
    "status,exc",
    [(402, PaymentRequiredError), (403, PermissionDeniedError)],
)
def test_entitlement_statuses_raise_typed_errors(transport, call, status, exc):
    transport.respond(status, _envelope("PLAN_REQUIRED", status, "Upgrade required"))

    with pytest.raises(exc) as info:
        call(lambda c: c.fuel_surcharge.parcel_list())

    assert info.value.status_code == status


def test_429_raises_rate_limit_error_without_replaying(transport, call):
    transport.respond(429, _envelope("RATE_LIMITED", 429, "Too many requests"))

    with pytest.raises(RateLimitError):
        call(lambda c: c.fuel_surcharge.latest("odfl"))

    assert len(transport.calls) == 1


def test_timeout_raises_timeout_error(transport, call):
    transport.raise_(httpx.ReadTimeout("timed out"))

    with pytest.raises(TimeoutError):
        call(lambda c: c.fuel_surcharge.history("odfl"))


# --- malformed successes ------------------------------------------------------------


@pytest.mark.parametrize(
    "field",
    [
        "carrier",
        "carrier_name",
        "mode",
        "surcharge_percent",
        "effective_date",
        "doe_diesel_price",
        "diesel_band",
        "source",
        "retrieved_at",
    ],
)
def test_latest_missing_a_field_raises_instead_of_defaulting(transport, call, field):
    body = copy.deepcopy(ODFL_LATEST)
    del body[field]
    transport.respond(200, {"status": "success", "data": body})

    with pytest.raises(OilPriceAPIError) as info:
        call(lambda c: c.fuel_surcharge.latest("odfl"))

    assert info.value.code == "MALFORMED_RESPONSE"
    assert field in str(info.value)


@pytest.mark.parametrize(
    "field,value",
    [
        ("surcharge_percent", None),
        ("surcharge_percent", "46.32"),
        ("surcharge_percent", True),
        ("effective_date", None),
        ("effective_date", "09/09/2026"),
        ("effective_date", 0),
        ("retrieved_at", "2026-09-08T16:10:10"),  # naive: no zone, not provenance
        ("retrieved_at", None),
        ("source", None),
        ("source", ""),
        ("diesel_band", {"min": 5.57}),
    ],
)
def test_latest_with_a_bad_value_raises(transport, call, field, value):
    body = copy.deepcopy(ODFL_LATEST)
    body[field] = value
    transport.respond(200, {"status": "success", "data": body})

    with pytest.raises(OilPriceAPIError) as info:
        call(lambda c: c.fuel_surcharge.latest("odfl"))

    assert info.value.code == "MALFORMED_RESPONSE"


def test_ltl_route_returning_a_parcel_row_is_malformed(transport, call):
    transport.respond(200, {"status": "success", "data": UPS_GROUND})

    with pytest.raises(OilPriceAPIError) as info:
        call(lambda c: c.fuel_surcharge.latest("odfl"))

    assert info.value.code == "MALFORMED_RESPONSE"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"status": "success"},
        {"status": "success", "data": None},
        {"status": "success", "data": []},
        {"status": "success", "data": {"history": []}},
        {"status": "success", "data": {"meta": ODFL_HISTORY_PAGE_2["data"]["meta"]}},
        {"status": "success", "data": {"history": [ODFL_LATEST], "meta": {"page": 1}}},
        {"status": "success", "data": {"history": "odfl", "meta": ODFL_HISTORY_PAGE_2["data"]["meta"]}},
    ],
)
def test_history_malformed_envelopes_raise(transport, call, payload):
    transport.respond(200, payload)

    with pytest.raises(OilPriceAPIError) as info:
        call(lambda c: c.fuel_surcharge.history("odfl"))

    assert info.value.code == "MALFORMED_RESPONSE"


@pytest.mark.parametrize(
    "payload",
    [
        {"status": "success", "data": {}},
        {"status": "success", "data": {"carriers": None}},
        {"status": "success", "data": {"carriers": [ODFL_LATEST, "abf"]}},
    ],
)
def test_list_malformed_envelopes_raise(transport, call, payload):
    transport.respond(200, payload)

    with pytest.raises(OilPriceAPIError) as info:
        call(lambda c: c.fuel_surcharge.list())

    assert info.value.code == "MALFORMED_RESPONSE"


def test_parcel_carrier_row_without_service_level_is_malformed(transport, call):
    level = copy.deepcopy(UPS_GROUND)
    del level["service_level"]
    carrier = dict(UPS_CARRIER, service_levels=[level])
    transport.respond(200, {"status": "success", "data": carrier})

    with pytest.raises(OilPriceAPIError) as info:
        call(lambda c: c.fuel_surcharge.parcel_latest("ups"))

    assert info.value.code == "MALFORMED_RESPONSE"


def test_parcel_latest_rate_given_a_carrier_object_is_malformed(transport, call):
    """The server ignored the service level: do not hand back a guessed row."""
    transport.respond(200, UPS_PARCEL_LATEST)

    with pytest.raises(OilPriceAPIError) as info:
        call(lambda c: c.fuel_surcharge.parcel_latest_rate("ups", "ground"))

    assert info.value.code == "MALFORMED_RESPONSE"


def test_non_json_200_is_an_error_not_an_empty_result(transport, call):
    transport.respond(200, raw=b"<html>gateway</html>")

    with pytest.raises(ValueError):
        call(lambda c: c.fuel_surcharge.list())


def test_malformed_error_keeps_the_raw_body(transport, call):
    payload = {"status": "success", "data": {"carriers": None}}
    transport.respond(200, payload)

    with pytest.raises(OilPriceAPIError) as info:
        call(lambda c: c.fuel_surcharge.list())

    assert info.value.raw_body == payload


# --- local validation happens before the network ----------------------------------


def _assert_local_refusal(info, field, value, transport):
    """A local refusal is a ValidationError with no HTTP status: nothing was sent."""
    error = info.value
    assert type(error) is ValidationError
    assert error.status_code is None
    assert error.is_client_error is False
    assert error.field == field
    assert error.value == value
    assert transport.calls == []


@pytest.mark.parametrize("carrier", ["", "   ", "odfl/latest", "odfl?x=1", "../prices", None, 7])
@pytest.mark.parametrize(
    "method",
    [
        lambda c, v: c.fuel_surcharge.latest(v),
        lambda c, v: c.fuel_surcharge.history(v),
        lambda c, v: c.fuel_surcharge.parcel_latest(v),
        lambda c, v: c.fuel_surcharge.parcel_latest_rate(v, "ground"),
        lambda c, v: c.fuel_surcharge.parcel_history(v, "ground"),
    ],
    ids=["latest", "history", "parcel_latest", "parcel_latest_rate", "parcel_history"],
)
def test_invalid_carrier_is_refused_locally(transport, call, carrier, method):
    with pytest.raises(ValidationError) as info:
        call(lambda c: method(c, carrier))

    _assert_local_refusal(info, "carrier", carrier, transport)


@pytest.mark.parametrize("service_level", ["", " ", "ground/x", None])
@pytest.mark.parametrize(
    "method",
    [
        lambda c, v: c.fuel_surcharge.parcel_latest_rate("ups", v),
        lambda c, v: c.fuel_surcharge.parcel_history("ups", v),
    ],
    ids=["parcel_latest_rate", "parcel_history"],
)
def test_invalid_service_level_is_refused_locally(transport, call, service_level, method):
    with pytest.raises(ValidationError) as info:
        call(lambda c: method(c, service_level))

    _assert_local_refusal(info, "service_level", service_level, transport)


@pytest.mark.parametrize(
    "field,value",
    [("page", 0), ("page", -1), ("page", "2"), ("per_page", 0), ("per_page", 101), ("per_page", True)],
)
@pytest.mark.parametrize("parcel", [False, True], ids=["ltl", "parcel"])
def test_out_of_range_pagination_is_refused_not_silently_clamped(transport, call, field, value, parcel):
    kwargs = {field: value}
    if parcel:
        fn = lambda c: c.fuel_surcharge.parcel_history("ups", "ground", **kwargs)  # noqa: E731
    else:
        fn = lambda c: c.fuel_surcharge.history("odfl", **kwargs)  # noqa: E731
    with pytest.raises(ValidationError) as info:
        call(fn)

    _assert_local_refusal(info, field, value, transport)


def test_per_page_100_is_the_accepted_maximum(transport, call):
    transport.respond(200, ODFL_HISTORY_PAGE_2)

    call(lambda c: c.fuel_surcharge.history("odfl", per_page=100))

    assert transport.last()["params"] == {"per_page": 100}


def test_both_clients_expose_the_resource():
    sync_client = OilPriceAPI(api_key=FIXTURE_KEY)
    async_client = AsyncOilPriceAPI(api_key=FIXTURE_KEY)
    try:
        for client in (sync_client, async_client):
            for name in (
                "list",
                "latest",
                "history",
                "parcel_list",
                "parcel_latest",
                "parcel_latest_rate",
                "parcel_history",
            ):
                assert callable(getattr(client.fuel_surcharge, name))
    finally:
        sync_client.close()
