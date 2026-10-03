"""#153: methods that called unrouted paths now hit canonical routes or fail locally.

The older mocked tests never asserted the request path, so every one of these
methods stayed green while production answered 404. These assert the exact
path and params, for both the sync and async clients.
"""

from unittest.mock import AsyncMock, patch

import pytest

from oilpriceapi import AsyncOilPriceAPI, OilPriceAPI
from oilpriceapi.exceptions import ValidationError

KEY = "test_key_000000000000000000000000"

BUNKER_HISTORY = {
    "data": {
        "port": {"code": "SIN"},
        "historical_data": [
            {"timestamp": "2026-10-03T00:00:00Z", "code": "HFO_380_SGSIN_USD", "average_value": 1},
            {"timestamp": "2026-10-03T00:00:00Z", "code": "MGO_05S_SGSIN_USD", "average_value": 2},
            {"timestamp": "2026-10-03T00:00:00Z", "code": "VLSFO_SGSIN_USD", "average_value": 3},
        ],
    }
}

# (callable on a resource-bearing client, response, expected path, expected params)
REPOINTED = [
    (
        lambda c: c.storage.history("cushing", period="30d"),
        {"data": {"code": "CUSHING_STORAGE", "history": []}},
        "/v1/storage/history/CUSHING_STORAGE",
        {"period": "30d"},
    ),
    (
        lambda c: c.storage.history("US_SPR"),
        {"data": {"code": "US_SPR", "history": []}},
        "/v1/storage/history/US_SPR",
        {"period": "90d"},
    ),
    (
        lambda c: c.bunker_fuels.spreads("sin", "RTM", grade="vlsfo"),
        {"data": {"spreads": {}}},
        "/v1/bunker-fuels/spreads/ports",
        {"from": "SIN", "to": "RTM", "grade": "VLSFO"},
    ),
    (
        lambda c: c.bunker_fuels.historical("sin", start_date="2026-09-01", end_date="2026-10-01"),
        BUNKER_HISTORY,
        "/v1/bunker-fuels/historical/SIN",
        {"from": "2026-09-01", "to": "2026-10-01"},
    ),
    (
        lambda c: c.forecasts.accuracy(),
        {"data": {}},
        "/v1/forecasts/monthly/accuracy",
        None,
    ),
    (
        lambda c: c.forecasts.archive(year=2026),
        {"data": []},
        "/v1/forecasts/monthly/archive",
        {"year": 2026},
    ),
    (
        lambda c: c.futures.calendar_spreads("BZ"),
        {"spreads": []},
        "/v1/futures/brent/spreads",
        None,
    ),
]

REMOVED = [
    (lambda c: c.drilling.trends(), "rig_counts.trends"),
    (lambda c: c.drilling.basin("permian"), "drilling_productivity.by_basin"),
    (lambda c: c.futures.spreads("CL.1", "CL.2"), "calendar_spreads"),
]

LOCAL_REJECTIONS = [
    lambda c: c.storage.history("padd1"),
    lambda c: c.storage.history("cushing", period="2w"),
    lambda c: c.bunker_fuels.spreads("SIN", ""),
    lambda c: c.bunker_fuels.historical(""),
    lambda c: c.bunker_fuels.historical("SIN", fuel_type="lng"),
]


def _assert_call(req, path, params):
    kwargs = req.call_args.kwargs
    assert kwargs["path"] == path
    assert kwargs.get("params") == params


@pytest.mark.parametrize("call,response,path,params", REPOINTED)
def test_sync_repointed_paths(call, response, path, params):
    client = OilPriceAPI(api_key=KEY)
    with patch.object(client, "request", return_value=response) as req:
        call(client)
    _assert_call(req, path, params)


@pytest.mark.asyncio
@pytest.mark.parametrize("call,response,path,params", REPOINTED)
async def test_async_repointed_paths(call, response, path, params):
    client = AsyncOilPriceAPI(api_key=KEY)
    with patch.object(client, "request", new=AsyncMock(return_value=response)) as req:
        await call(client)
    _assert_call(req, path, params)


@pytest.mark.parametrize("call,alternative", REMOVED)
def test_sync_removed_methods_raise_without_request(call, alternative):
    client = OilPriceAPI(api_key=KEY)
    with patch.object(client, "request") as req:
        with pytest.warns(DeprecationWarning):
            with pytest.raises(ValidationError, match=alternative) as exc:
                call(client)
    req.assert_not_called()
    assert exc.value.code == "ENDPOINT_NOT_AVAILABLE"
    assert exc.value.status_code is None


@pytest.mark.asyncio
@pytest.mark.parametrize("call,alternative", REMOVED)
async def test_async_removed_methods_raise_without_request(call, alternative):
    client = AsyncOilPriceAPI(api_key=KEY)
    with patch.object(client, "request", new=AsyncMock()) as req:
        with pytest.warns(DeprecationWarning):
            with pytest.raises(ValidationError, match=alternative):
                await call(client)
    req.assert_not_called()


@pytest.mark.parametrize("call", LOCAL_REJECTIONS)
def test_sync_invalid_arguments_rejected_before_request(call):
    client = OilPriceAPI(api_key=KEY)
    with patch.object(client, "request", return_value=BUNKER_HISTORY) as req:
        with pytest.raises(ValidationError) as exc:
            call(client)
    assert exc.value.status_code is None
    req.assert_not_called()


@pytest.mark.parametrize(
    "fuel_type,expected",
    [("vlsfo", ["VLSFO_SGSIN_USD"]), ("MGO", ["MGO_05S_SGSIN_USD"]), ("hfo380", ["HFO_380_SGSIN_USD"]), (None, None)],
)
def test_bunker_history_fuel_type_filter(fuel_type, expected):
    client = OilPriceAPI(api_key=KEY)
    with patch.object(client, "request", return_value=BUNKER_HISTORY):
        result = client.bunker_fuels.historical("SIN", fuel_type=fuel_type)
    codes = [r["code"] for r in result["historical_data"]]
    assert codes == (expected if expected is not None else [r["code"] for r in BUNKER_HISTORY["data"]["historical_data"]])
