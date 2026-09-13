"""#142 -- ``subscriptions.list()`` / ``events()`` never turn a malformed 200 into success.

``V1::SubscriptionsController`` (oilpriceapi-api origin/main, 2026-09-13):

* ``#index`` always renders ``{"status": "success", "data": {"subscriptions": [...]}}``.
* ``#events`` always renders ``{"cursor", "has_more", "events"}`` under ``data``,
  with ``cursor = events.last&.seq || since``, so the cursor is an integer that
  never moves backwards.
* ``#events`` reads ``since = params[:since].to_i``. Missing, ``""``, ``"abc"``
  and ``-1`` all become ``0`` and replay the account's whole event history;
  ``1.5`` becomes ``1``. Confirmed live on 2026-09-13 against an account with
  101 events: every one of those returned ``first_seq=1, cursor=100``.

Before this fix a body without those keys returned ``[]`` / an empty page with
``cursor=None``, and the documented loop ``events(since=page.cursor)`` then sent
no ``since`` at all -- restarting the poller from event 1.

Every test drives the REAL sync and async clients over a mocked transport.
"""

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from oilpriceapi import AsyncOilPriceAPI, OilPriceAPI, Subscription, SubscriptionEventsPage
from oilpriceapi.exceptions import OilPriceAPIError, ValidationError

# Not a credential: a fixture string. Every request here is mocked.
FIXTURE_KEY = "-".join(["fixture", "not", "a", "real", "key"])

MODES = ["sync", "async"]

# live: GET /v1/subscriptions, 2026-09-13
WIRE_SUBSCRIPTION = {
    "id": "b84b24a0-2b28-4eac-835e-db92bab5c0cb",
    "name": "mcp-live-contract-1788524538194",
    "codes": ["BRENT_CRUDE_USD"],
    "interval_seconds": 3600,
    "status": "active",
    "deliver_webhook": False,
    "source": "api",
    "tool_name": "opa_create_price_subscription",
    "last_evaluated_at": "2026-09-13T20:32:18Z",
    "next_run_at": "2026-09-13T21:32:18Z",
    "created_at": "2026-09-04T12:22:19Z",
}

# live: GET /v1/subscriptions/events?since=99&limit=2, 2026-09-13
WIRE_EVENTS_PAGE = {
    "status": "success",
    "data": {
        "cursor": 101,
        "has_more": True,
        "events": [
            {
                "id": "d73c7b25-875b-403e-a429-0d7049245c30",
                "seq": 100,
                "watch_id": "b84b24a0-2b28-4eac-835e-db92bab5c0cb",
                "observed_at": "2026-09-08T16:20:42Z",
                "snapshot": {"BRENT_CRUDE_USD": {"as_of": "2026-09-08T16:16:14Z", "price": 97.27, "currency": "USD", "change_24h_pct": -0.04}},
                "deltas": {"BRENT_CRUDE_USD": {"pct_change": -0.53, "price_change": -0.52}},
                "source": "api",
                "tool_name": "opa_create_price_subscription",
            },
            {
                "id": "a835a930-f34f-4001-80b1-38fb3cde3797",
                "seq": 101,
                "watch_id": "b84b24a0-2b28-4eac-835e-db92bab5c0cb",
                "observed_at": "2026-09-08T17:21:19Z",
                "snapshot": {"BRENT_CRUDE_USD": {"as_of": "2026-09-08T17:20:37Z", "price": 97.02, "currency": "USD", "change_24h_pct": -0.08}},
                "deltas": {"BRENT_CRUDE_USD": {"pct_change": -0.26, "price_change": -0.25}},
                "source": "api",
                "tool_name": "opa_create_price_subscription",
            },
        ],
    },
}


def _response(payload):
    response = Mock()
    response.status_code = 200
    response.headers = {}
    text = json.dumps(payload)
    response.content = text.encode()
    response.text = text
    response.json.return_value = payload
    return response


def _run(mode, call, payload):
    """Run ``call(client)`` over a mocked transport; return ``(result, transport)``."""
    if mode == "sync":
        client = OilPriceAPI(api_key=FIXTURE_KEY, max_retries=1)
        with patch("httpx.Client.request", return_value=_response(payload)) as transport:
            return call(client), transport

    async def go():
        client = AsyncOilPriceAPI(api_key=FIXTURE_KEY, max_retries=1)
        with patch("httpx.AsyncClient.request", new=AsyncMock(return_value=_response(payload))) as transport:
            return await call(client), transport

    return asyncio.run(go())


def _raises(mode, call, payload, exc_type=OilPriceAPIError):
    with pytest.raises(exc_type) as info:
        _run(mode, call, payload)
    return info.value


def _list(client):
    return client.subscriptions.list()


def _events(**kwargs):
    return lambda client: client.subscriptions.events(**kwargs)


def _page(**data):
    return {"status": "success", "data": data}


# --- list() --------------------------------------------------------------------

MALFORMED_LIST_BODIES = {
    "data without subscriptions": {"status": "success", "data": {}},
    "data is a list": {"status": "success", "data": []},
    "no data at all": {"message": "maintenance"},
    "subscriptions is null": {"status": "success", "data": {"subscriptions": None}},
    "subscriptions is an object": {"status": "success", "data": {"subscriptions": {}}},
    "a record is not an object": {"status": "success", "data": {"subscriptions": ["b84b24a0"]}},
    "a record lacks id": {
        "status": "success",
        "data": {"subscriptions": [{k: v for k, v in WIRE_SUBSCRIPTION.items() if k != "id"}]},
    },
}


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("case", sorted(MALFORMED_LIST_BODIES))
def test_list_malformed_success_raises(mode, case):
    payload = MALFORMED_LIST_BODIES[case]

    error = _raises(mode, _list, payload)

    assert error.code == "MALFORMED_RESPONSE"
    assert error.raw_body == payload
    assert "subscriptions.list" in error.message


@pytest.mark.parametrize("mode", MODES)
def test_list_genuinely_empty_is_an_empty_success(mode):
    result, _ = _run(mode, _list, {"status": "success", "data": {"subscriptions": []}})

    assert result == []


@pytest.mark.parametrize("mode", MODES)
def test_list_live_body_parses(mode):
    result, _ = _run(mode, _list, {"status": "success", "data": {"subscriptions": [WIRE_SUBSCRIPTION]}})

    assert len(result) == 1
    assert isinstance(result[0], Subscription)
    assert result[0].id == WIRE_SUBSCRIPTION["id"]
    assert result[0].codes == ["BRENT_CRUDE_USD"]


# --- events(): the response ----------------------------------------------------

MALFORMED_EVENT_BODIES = {
    "data without events or cursor": {"status": "success", "data": {}},
    "empty object": {},
    "events missing": _page(cursor=41, has_more=False),
    "events is an object": _page(cursor=41, has_more=False, events={}),
    "an event is not an object": _page(cursor=42, has_more=False, events=[42]),
    "cursor missing": _page(has_more=False, events=[]),
    "cursor is null": _page(cursor=None, has_more=False, events=[]),
    "cursor is a string": _page(cursor="41", has_more=False, events=[]),
    "cursor is a float": _page(cursor=41.5, has_more=False, events=[]),
    "cursor is a bool": _page(cursor=True, has_more=False, events=[]),
    "cursor is negative": _page(cursor=-1, has_more=False, events=[]),
    "has_more missing": _page(cursor=41, events=[]),
    "has_more is a string": _page(cursor=41, has_more="false", events=[]),
    "cursor behind since": _page(cursor=0, has_more=False, events=[]),
    "cursor behind the last event": _page(
        cursor=41, has_more=False, events=[{**WIRE_EVENTS_PAGE["data"]["events"][0], "seq": 43}]
    ),
}


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("case", sorted(MALFORMED_EVENT_BODIES))
def test_events_malformed_success_raises(mode, case):
    payload = MALFORMED_EVENT_BODIES[case]

    error = _raises(mode, _events(since=41), payload)

    assert error.code == "MALFORMED_RESPONSE"
    assert error.raw_body == payload
    assert "subscriptions.events" in error.message


@pytest.mark.parametrize("mode", MODES)
def test_events_empty_page_keeps_the_cursor(mode):
    page, _ = _run(mode, _events(since=41), _page(cursor=41, has_more=False, events=[]))

    assert isinstance(page, SubscriptionEventsPage)
    assert len(page) == 0
    assert page.cursor == 41
    assert page.has_more is False


@pytest.mark.parametrize("mode", MODES)
def test_events_live_body_parses_and_advances(mode):
    page, transport = _run(mode, _events(since=99, limit=2), WIRE_EVENTS_PAGE)

    assert page.cursor == 101
    assert page.has_more is True
    assert [event.seq for event in page] == [100, 101]
    assert page.events[0].watch_id == "b84b24a0-2b28-4eac-835e-db92bab5c0cb"
    assert transport.call_args.kwargs["params"] == {"since": 99, "limit": 2}


@pytest.mark.parametrize("mode", MODES)
def test_first_poll_without_since_is_allowed(mode):
    page, transport = _run(mode, _events(), _page(cursor=0, has_more=False, events=[]))

    assert page.cursor == 0
    assert "since" not in (transport.call_args.kwargs.get("params") or {})


# --- events(): the cursor the caller sends --------------------------------------


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("since", ["abc", "", "41", -1, 1.5, True, [41]], ids=repr)
def test_events_refuses_a_cursor_the_api_would_read_as_zero(mode, since):
    error = _raises(mode, _events(since=since), _page(cursor=0, has_more=False, events=[]), ValidationError)

    assert error.status_code is None
    assert error.field == "since"
    assert error.value == since


@pytest.mark.parametrize("mode", MODES)
def test_refused_cursor_sends_nothing(mode):
    if mode == "sync":
        client = OilPriceAPI(api_key=FIXTURE_KEY, max_retries=1)
        with patch("httpx.Client.request") as transport:
            with pytest.raises(ValidationError):
                client.subscriptions.events(since="abc")
        assert transport.call_count == 0
        return

    async def go():
        client = AsyncOilPriceAPI(api_key=FIXTURE_KEY, max_retries=1)
        with patch("httpx.AsyncClient.request", new=AsyncMock()) as transport:
            with pytest.raises(ValidationError):
                await client.subscriptions.events(since="abc")
        assert transport.call_count == 0

    asyncio.run(go())


@pytest.mark.parametrize("mode", MODES)
def test_poll_loop_never_resends_from_the_start(mode):
    """The documented loop, fed a malformed page, stops instead of replaying."""
    first, _ = _run(mode, _events(since=99, limit=2), WIRE_EVENTS_PAGE)
    assert first.cursor == 101

    error = _raises(mode, _events(since=first.cursor), {"status": "success", "data": {}})

    assert error.code == "MALFORMED_RESPONSE"
