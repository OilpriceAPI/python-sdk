"""#149 -- ``SubscriptionEvent`` is typed from the event the API actually sends.

Wire shape, ``WatchEvent#as_poll_json`` (oilpriceapi-api origin/main,
2026-09-13): ``id, seq, watch_id, observed_at, snapshot, deltas, source,
tool_name``. ``db/schema.rb`` has ``seq``, ``watch_id``, ``observed_at``,
``snapshot`` and ``deltas`` as ``null: false`` (``snapshot``/``deltas`` default
``{}``); ``source`` and ``tool_name`` are nullable.

* ``snapshot`` is ``MarketBriefBuilder#snapshot_hash``:
  ``{code: {price, change_24h_pct, currency, as_of}}``. ``change_24h_pct`` is nil
  when there is no 24h comparison.
* ``deltas`` is ``Watch#compute_deltas``: ``{}`` on the first event, a code is
  left out when either snapshot lacks a price, and ``pct_change`` is dropped
  (``.compact``) when the prior price is 0.

The model declared ``type``, ``code``, ``payload`` and ``created_at``, none of
which are sent, so every real event read ``None`` for them, while the fields
that are sent were untyped pydantic extras.

The two events below are verbatim from ``GET /v1/subscriptions/events`` on
2026-09-13 (223 events on the test account; every one had all eight keys, and
only seq 1 had empty ``deltas``). Client tests drive the REAL sync and async
clients over a mocked transport.
"""

import asyncio
import json
import warnings
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from oilpriceapi import AsyncOilPriceAPI, OilPriceAPI, SubscriptionEvent
from oilpriceapi.exceptions import OilPriceAPIError

# Not a credential: a fixture string. Every request here is mocked.
FIXTURE_KEY = "-".join(["fixture", "not", "a", "real", "key"])

MODES = ["sync", "async"]

# live, seq 1: the first observation, so `deltas` is {}.
FIRST_EVENT = {
    "id": "c167cbb1-e10f-48e3-a8c5-523ea5c9d2f9",
    "seq": 1,
    "watch_id": "b84b24a0-2b28-4eac-835e-db92bab5c0cb",
    "observed_at": "2026-09-04T12:22:35Z",
    "snapshot": {"BRENT_CRUDE_USD": {"as_of": "2026-09-04T12:21:56Z", "price": 94.76, "currency": "USD", "change_24h_pct": -2.16}},
    "deltas": {},
    "source": "api",
    "tool_name": "opa_create_price_subscription",
}

# live, seq 223.
LAST_EVENT = {
    "id": "f5419cd4-86ea-47f8-b670-4770c9d68650",
    "seq": 223,
    "watch_id": "b84b24a0-2b28-4eac-835e-db92bab5c0cb",
    "observed_at": "2026-09-13T20:32:18Z",
    "snapshot": {"BRENT_CRUDE_USD": {"as_of": "2026-09-13T20:16:20Z", "price": 104.32, "currency": "USD", "change_24h_pct": 0.0}},
    "deltas": {"BRENT_CRUDE_USD": {"pct_change": -0.14, "price_change": -0.15}},
    "source": "api",
    "tool_name": "opa_create_price_subscription",
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


def _poll(mode, events, cursor):
    payload = {"status": "success", "data": {"cursor": cursor, "has_more": False, "events": events}}
    if mode == "sync":
        client = OilPriceAPI(api_key=FIXTURE_KEY, max_retries=1)
        with patch("httpx.Client.request", return_value=_response(payload)):
            return client.subscriptions.events(since=0)

    async def go():
        client = AsyncOilPriceAPI(api_key=FIXTURE_KEY, max_retries=1)
        with patch("httpx.AsyncClient.request", new=AsyncMock(return_value=_response(payload))):
            return await client.subscriptions.events(since=0)

    return asyncio.run(go())


def _without(event, key):
    return {k: v for k, v in event.items() if k != key}


# --- the wire fields are typed ---------------------------------------------------


@pytest.mark.parametrize("mode", MODES)
def test_live_events_parse_into_typed_fields(mode):
    page = _poll(mode, [FIRST_EVENT, LAST_EVENT], cursor=223)
    first, last = page.events

    assert isinstance(last, SubscriptionEvent)
    assert last.id == "f5419cd4-86ea-47f8-b670-4770c9d68650"
    assert last.seq == 223
    assert last.watch_id == "b84b24a0-2b28-4eac-835e-db92bab5c0cb"
    assert last.observed_at == datetime(2026, 9, 13, 20, 32, 18, tzinfo=timezone.utc)
    assert last.source == "api"
    assert last.tool_name == "opa_create_price_subscription"

    brent = last.snapshot["BRENT_CRUDE_USD"]
    assert brent.price == 104.32
    assert brent.currency == "USD"
    assert brent.change_24h_pct == 0.0
    assert brent.as_of == datetime(2026, 9, 13, 20, 16, 20, tzinfo=timezone.utc)

    delta = last.deltas["BRENT_CRUDE_USD"]
    assert delta.price_change == -0.15
    assert delta.pct_change == -0.14

    assert first.deltas == {}
    assert first.snapshot["BRENT_CRUDE_USD"].change_24h_pct == -2.16


def test_nothing_the_api_did_not_send_is_left_as_an_untyped_extra():
    event = SubscriptionEvent(**LAST_EVENT)

    assert event.model_extra == {}


# --- names the API never sends: deprecated accessors, not fields --------------------

DEPRECATED = ["type", "code", "payload", "created_at"]


@pytest.mark.parametrize(
    ("name", "guidance"),
    [("type", "no equivalent"), ("code", "event.snapshot"), ("payload", "event.snapshot")],
)
def test_never_sent_names_read_none_and_warn_once_per_access(name, guidance):
    event = SubscriptionEvent(**LAST_EVENT)

    for _ in range(2):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            value = getattr(event, name)
        assert value is None
        assert [w.category for w in caught] == [DeprecationWarning]
        message = str(caught[0].message)
        assert f"SubscriptionEvent.{name} is deprecated" in message
        assert "2.0.0" in message
        assert guidance in message


def test_created_at_is_a_deprecated_alias_for_observed_at():
    event = SubscriptionEvent(**LAST_EVENT)

    for _ in range(2):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            value = event.created_at
        assert value == event.observed_at
        assert [w.category for w in caught] == [DeprecationWarning]
        assert "use observed_at" in str(caught[0].message)
        assert "2.0.0" in str(caught[0].message)


@pytest.mark.parametrize("name", DEPRECATED)
def test_deprecated_names_are_not_fields_and_not_serialized(name):
    event = SubscriptionEvent(**LAST_EVENT)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        dumped = event.model_dump()
        dumped_json = json.loads(event.model_dump_json())

    assert name not in SubscriptionEvent.model_fields
    assert name not in dumped
    assert name not in dumped_json
    assert set(dumped) == set(LAST_EVENT)


# --- what the API can legitimately omit or null ------------------------------------


def test_nullable_attribution_stays_none():
    event = SubscriptionEvent(**{**LAST_EVENT, "source": None, "tool_name": None})

    assert event.source is None
    assert event.tool_name is None


def test_null_24h_change_is_none_not_zero():
    snapshot = {"BRENT_CRUDE_USD": {"as_of": "2026-09-13T20:16:20Z", "price": 104.32, "currency": "USD", "change_24h_pct": None}}

    event = SubscriptionEvent(**{**LAST_EVENT, "snapshot": snapshot})

    assert event.snapshot["BRENT_CRUDE_USD"].change_24h_pct is None


def test_pct_change_dropped_for_a_zero_prior_price_is_none_not_invented():
    event = SubscriptionEvent(**{**LAST_EVENT, "deltas": {"BRENT_CRUDE_USD": {"price_change": 104.32}}})

    assert event.deltas["BRENT_CRUDE_USD"].price_change == 104.32
    assert event.deltas["BRENT_CRUDE_USD"].pct_change is None


def test_a_code_left_out_of_deltas_is_not_filled_in():
    event = SubscriptionEvent(**{**LAST_EVENT, "deltas": {}})

    assert "BRENT_CRUDE_USD" not in event.deltas


# --- what the API always sends is required ----------------------------------------


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("missing", ["id", "seq", "watch_id", "observed_at", "snapshot", "deltas"])
def test_an_event_missing_a_field_the_api_always_sends_is_malformed(mode, missing):
    with pytest.raises(OilPriceAPIError) as info:
        _poll(mode, [_without(LAST_EVENT, missing)], cursor=223)

    assert info.value.code == "MALFORMED_RESPONSE"
    assert missing in info.value.message


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("missing", ["price", "currency"])
def test_a_snapshot_entry_missing_price_or_currency_is_malformed(mode, missing):
    entry = _without(LAST_EVENT["snapshot"]["BRENT_CRUDE_USD"], missing)

    with pytest.raises(OilPriceAPIError) as info:
        _poll(mode, [{**LAST_EVENT, "snapshot": {"BRENT_CRUDE_USD": entry}}], cursor=223)

    assert info.value.code == "MALFORMED_RESPONSE"


LIVE_EVENTS = json.loads(
    (Path(__file__).parent / "fixtures" / "subscription_events_live_2026-09-13.json").read_text()
)


def test_parsing_all_223_live_events_emits_no_warning_and_leaves_nothing_untyped():
    assert len(LIVE_EVENTS) == 223

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        events = [SubscriptionEvent(**raw) for raw in LIVE_EVENTS]
        for event in events:
            event.model_dump()

    assert [event.seq for event in events] == list(range(1, 224))
    assert all(event.model_extra == {} for event in events)
    assert [event.seq for event in events if not event.deltas] == [1]


@pytest.mark.parametrize("mode", MODES)
def test_polling_the_live_events_emits_no_deprecation_warning(mode):
    # Only deprecation / SubscriptionEvent warnings are this PR's concern: building
    # a client can emit unrelated ImportWarnings for optional extras.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        page = _poll(mode, LIVE_EVENTS, cursor=223)

    assert len(page) == 223
    ours = [
        str(w.message)
        for w in caught
        if issubclass(w.category, DeprecationWarning) or "SubscriptionEvent" in str(w.message)
    ]
    assert ours == []
