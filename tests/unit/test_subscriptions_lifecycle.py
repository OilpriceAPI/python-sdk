"""Subscription lifecycle: get, update, pause, resume (#100).

Every test drives the REAL client -- request building, the retry loop, error
normalization, response decoding -- against a mocked transport, patching
`httpx.Client.request` / `httpx.AsyncClient.request` as the rest of this suite
does. Sync and async run the same cases so the two clients cannot drift.

Wire shapes are the ones production and `V1::SubscriptionsController` return
(verified 2026-09-13):

* success: ``{"status": "success", "data": {"subscription": {...}}}``
* unknown id: 404 ``{"error": {"code": "NOT_FOUND", "message": ..., "request_id": ...}}``
* update validation: 422 ``{"status": "fail", "data": {"error": "VALIDATION_ERROR", "message", "details"}}``
* watch limit on create: 402 ``{"status": "fail", "data": {"error": "WATCH_LIMIT", ..., "upgrade_url", "upgrade"}}``
"""

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from oilpriceapi import AsyncOilPriceAPI, OilPriceAPI, Subscription
from oilpriceapi.exceptions import (
    AuthenticationError,
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

WATCH_ID = "f72ceac2-8b9a-406a-a57e-90c625785444"

WIRE_SUBSCRIPTION = {
    "id": WATCH_ID,
    "name": "Brent daily",
    "codes": ["BRENT_CRUDE_USD"],
    "interval_seconds": 86400,
    "status": "active",
    "deliver_webhook": False,
    "source": "api",
    "tool_name": None,
    "last_evaluated_at": None,
    "next_run_at": "2026-09-13T19:57:22Z",
    "created_at": "2026-09-13T19:57:20Z",
}

MODES = ["sync", "async"]


def _response(status, payload=None, *, body=None, headers=None):
    response = Mock()
    response.status_code = status
    response.headers = headers or {}
    if body is not None:
        response.content = body
        response.text = body.decode()
        response.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
    else:
        text = json.dumps(payload)
        response.content = text.encode()
        response.text = text
        response.json.return_value = payload
    return response


def _success(subscription):
    return _response(200, {"status": "success", "data": {"subscription": subscription}})


def _run(mode, call, *, responses=None, side_effect=None, max_retries=1):
    """Run ``call(client)`` on a sync or async client over a mocked transport.

    Returns ``(result, transport_mock)``. Exceptions propagate.
    """
    effect = side_effect if side_effect is not None else responses
    if mode == "sync":
        client = OilPriceAPI(api_key=FIXTURE_KEY, max_retries=max_retries)
        with patch("httpx.Client.request") as transport, patch("time.sleep"):
            if isinstance(effect, list):
                transport.side_effect = effect
            elif isinstance(effect, BaseException):
                transport.side_effect = effect
            else:
                transport.return_value = effect
            return call(client), transport

    client = AsyncOilPriceAPI(api_key=FIXTURE_KEY, max_retries=max_retries)

    async def go():
        with patch("httpx.AsyncClient.request") as transport, patch(
            "asyncio.sleep", new=AsyncMock()
        ):
            if isinstance(effect, list):
                transport.side_effect = effect
            elif isinstance(effect, BaseException):
                transport.side_effect = effect
            else:
                transport.return_value = effect
            return await call(client), transport

    return asyncio.run(go())


def _run_expect(mode, call, exc_type, **kwargs):
    """Like _run, but assert ``exc_type`` is raised; return (exc, transport)."""
    captured = {}
    if mode == "sync":
        client = OilPriceAPI(api_key=FIXTURE_KEY, max_retries=kwargs.get("max_retries", 1))
        effect = kwargs.get("side_effect", kwargs.get("responses"))
        with patch("httpx.Client.request") as transport, patch("time.sleep"):
            if isinstance(effect, (list, BaseException)):
                transport.side_effect = effect
            else:
                transport.return_value = effect
            with pytest.raises(exc_type) as info:
                call(client)
            captured["transport"] = transport
        return info.value, captured["transport"]

    client = AsyncOilPriceAPI(api_key=FIXTURE_KEY, max_retries=kwargs.get("max_retries", 1))
    effect = kwargs.get("side_effect", kwargs.get("responses"))

    async def go():
        with patch("httpx.AsyncClient.request") as transport, patch(
            "asyncio.sleep", new=AsyncMock()
        ):
            if isinstance(effect, (list, BaseException)):
                transport.side_effect = effect
            else:
                transport.return_value = effect
            with pytest.raises(exc_type) as info:
                await call(client)
            return info.value, transport

    return asyncio.run(go())


def _sent(transport):
    """The (method, url, json) of the single request the transport received."""
    assert transport.call_count == 1
    kwargs = transport.call_args.kwargs
    return kwargs["method"], str(kwargs["url"]), kwargs.get("json")


# ---------------------------------------------------------------------------
# Success paths


@pytest.mark.parametrize("mode", MODES)
def test_get_returns_typed_subscription_with_wire_values(mode):
    sub, transport = _run(
        mode, lambda c: c.subscriptions.get(WATCH_ID), responses=_success(WIRE_SUBSCRIPTION)
    )
    assert isinstance(sub, Subscription)
    assert sub.id == WATCH_ID
    assert sub.codes == ["BRENT_CRUDE_USD"]
    assert sub.interval_seconds == 86400
    assert sub.status == "active"
    # Nulls stay null; timestamps are the server's, not "now".
    assert sub.last_evaluated_at is None
    assert sub.tool_name is None
    assert sub.next_run_at.isoformat() == "2026-09-13T19:57:22+00:00"
    assert sub.created_at.isoformat() == "2026-09-13T19:57:20+00:00"
    method, url, body = _sent(transport)
    assert method == "GET"
    assert url.endswith(f"/v1/subscriptions/{WATCH_ID}")
    assert body is None


@pytest.mark.parametrize("mode", MODES)
def test_update_sends_only_the_given_fields_and_returns_the_server_record(mode):
    updated = dict(WIRE_SUBSCRIPTION, name="renamed", interval_seconds=3600)
    sub, transport = _run(
        mode,
        lambda c: c.subscriptions.update(WATCH_ID, name="renamed", interval="1h"),
        responses=_success(updated),
    )
    assert sub.name == "renamed"
    assert sub.interval_seconds == 3600
    method, url, body = _sent(transport)
    assert method == "PATCH"
    assert url.endswith(f"/v1/subscriptions/{WATCH_ID}")
    assert body == {"name": "renamed", "interval_seconds": 3600}


@pytest.mark.parametrize("mode", MODES)
def test_update_maps_every_supported_field(mode):
    _, transport = _run(
        mode,
        lambda c: c.subscriptions.update(
            WATCH_ID,
            codes=["WTI_USD", "BRENT_CRUDE_USD"],
            deliver_webhook=False,
            status="paused",
        ),
        responses=_success(dict(WIRE_SUBSCRIPTION, status="paused")),
    )
    _, _, body = _sent(transport)
    assert body == {
        "codes": ["WTI_USD", "BRENT_CRUDE_USD"],
        "deliver_webhook": False,
        "status": "paused",
    }


@pytest.mark.parametrize("mode", MODES)
def test_pause_posts_member_action_and_returns_paused(mode):
    sub, transport = _run(
        mode,
        lambda c: c.subscriptions.pause(WATCH_ID),
        responses=_success(dict(WIRE_SUBSCRIPTION, status="paused")),
    )
    assert sub.status == "paused"
    method, url, body = _sent(transport)
    assert method == "POST"
    assert url.endswith(f"/v1/subscriptions/{WATCH_ID}/pause")
    assert body is None


@pytest.mark.parametrize("mode", MODES)
def test_resume_posts_member_action_and_returns_active(mode):
    sub, transport = _run(
        mode,
        lambda c: c.subscriptions.resume(WATCH_ID),
        responses=_success(WIRE_SUBSCRIPTION),
    )
    assert sub.status == "active"
    method, url, _ = _sent(transport)
    assert method == "POST"
    assert url.endswith(f"/v1/subscriptions/{WATCH_ID}/resume")


# ---------------------------------------------------------------------------
# Pre-network validation: nothing is sent


BAD_IDS = ["", "   ", None, 42, "abc/pause", "../webhooks", "a?b=1", "a#b", " abc"]


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("bad_id", BAD_IDS)
@pytest.mark.parametrize("action", ["get", "pause", "resume", "delete"])
def test_invalid_id_is_rejected_before_the_network(mode, bad_id, action):
    exc, transport = _run_expect(
        mode,
        lambda c: getattr(c.subscriptions, action)(bad_id),
        ValueError,
        responses=_success(WIRE_SUBSCRIPTION),
    )
    assert transport.call_count == 0


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("bad_id", BAD_IDS)
def test_update_invalid_id_is_rejected_before_the_network(mode, bad_id):
    _, transport = _run_expect(
        mode,
        lambda c: c.subscriptions.update(bad_id, name="x"),
        ValueError,
        responses=_success(WIRE_SUBSCRIPTION),
    )
    assert transport.call_count == 0


BAD_UPDATES = [
    pytest.param({}, id="empty-payload"),
    pytest.param({"interval": "5x"}, id="bad-interval"),
    pytest.param({"interval": 0}, id="zero-interval"),
    pytest.param({"deliver_webhook": "yes"}, id="non-bool-deliver_webhook"),
    pytest.param({"deliver_webhook": 1}, id="int-deliver_webhook"),
    pytest.param({"status": "cancelled"}, id="unknown-status"),
    pytest.param({"status": "ACTIVE "}, id="unnormalized-status"),
    pytest.param({"codes": []}, id="empty-codes"),
    pytest.param({"codes": "BRENT_CRUDE_USD"}, id="codes-as-string"),
    pytest.param({"codes": ["BRENT_CRUDE_USD", ""]}, id="blank-code"),
    pytest.param({"codes": ["BRENT_CRUDE_USD", 5]}, id="non-string-code"),
    pytest.param({"name": 5}, id="non-string-name"),
]


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("fields", BAD_UPDATES)
def test_invalid_update_payload_is_rejected_before_the_network(mode, fields):
    _, transport = _run_expect(
        mode,
        lambda c: c.subscriptions.update(WATCH_ID, **fields),
        ValueError,
        responses=_success(WIRE_SUBSCRIPTION),
    )
    assert transport.call_count == 0


# ---------------------------------------------------------------------------
# Server errors keep their type and recovery metadata


NOT_FOUND = {
    "error": {
        "code": "NOT_FOUND",
        "message": "Subscription not found",
        "status": 404,
        "request_id": "f34f0d7d-3a1c-464f-b951-27163cf0aae1",
        "docs": "https://docs.oilpriceapi.com#NOT_FOUND",
    }
}


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    "call",
    [
        pytest.param(lambda c: c.subscriptions.get(WATCH_ID), id="get"),
        pytest.param(lambda c: c.subscriptions.update(WATCH_ID, name="x"), id="update"),
        pytest.param(lambda c: c.subscriptions.pause(WATCH_ID), id="pause"),
        pytest.param(lambda c: c.subscriptions.resume(WATCH_ID), id="resume"),
    ],
)
def test_unknown_id_raises_data_not_found_with_request_id(mode, call):
    exc, transport = _run_expect(mode, call, DataNotFoundError, responses=_response(404, NOT_FOUND))
    assert exc.status_code == 404
    assert exc.code == "NOT_FOUND"
    assert exc.request_id == "f34f0d7d-3a1c-464f-b951-27163cf0aae1"
    assert transport.call_count == 1


@pytest.mark.parametrize("mode", MODES)
def test_update_422_raises_validation_error_with_details(mode):
    payload = {
        "status": "fail",
        "data": {
            "error": "VALIDATION_ERROR",
            "message": "Interval seconds is below your plan minimum of 3600 seconds",
            "details": {"interval_seconds": ["is below your plan minimum of 3600 seconds"]},
        },
    }
    exc, _ = _run_expect(
        mode,
        lambda c: c.subscriptions.update(WATCH_ID, interval=60),
        ValidationError,
        responses=_response(422, payload),
    )
    assert exc.status_code == 422
    assert exc.code == "VALIDATION_ERROR"
    assert "plan minimum" in str(exc)
    assert exc.raw_body["data"]["details"]["interval_seconds"]


@pytest.mark.parametrize("mode", MODES)
def test_update_webhook_entitlement_refusal_is_a_422_not_a_success(mode):
    """The Watch model refuses deliver_webhook without the entitlement."""
    payload = {
        "status": "fail",
        "data": {
            "error": "VALIDATION_ERROR",
            "message": "Deliver webhook requires a plan with webhook delivery",
            "details": {"deliver_webhook": ["requires a plan with webhook delivery"]},
        },
    }
    exc, _ = _run_expect(
        mode,
        lambda c: c.subscriptions.update(WATCH_ID, deliver_webhook=True),
        ValidationError,
        responses=_response(422, payload),
    )
    assert "webhook delivery" in str(exc)


UPGRADE_URL = (
    "https://www.oilpriceapi.com/pricing?plan=starter"
    "&utm_source=api&utm_medium=agent&utm_campaign=agent_watches"
)
WATCH_LIMIT = {
    "status": "fail",
    "data": {
        "error": "WATCH_LIMIT",
        "message": "Your plan allows up to 1 active watches. Upgrade for more.",
        "limit": 1,
        "current": 1,
        "upgrade_trigger": "watch_limit",
        "upgrade_url": UPGRADE_URL,
        "upgrade": {"url": UPGRADE_URL, "next_tier": "starter", "plans": []},
    },
}


@pytest.mark.parametrize("mode", MODES)
def test_create_watch_limit_402_keeps_upgrade_recovery_metadata(mode):
    exc, transport = _run_expect(
        mode,
        lambda c: c.subscriptions.create(["BRENT_CRUDE_USD"], interval="daily"),
        PaymentRequiredError,
        responses=_response(402, WATCH_LIMIT),
    )
    assert exc.status_code == 402
    assert exc.code == "WATCH_LIMIT"
    assert exc.remediation_url == UPGRADE_URL
    assert exc.raw_body["data"]["upgrade"]["next_tier"] == "starter"
    assert transport.call_count == 1


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    "status,exc_type",
    [(401, AuthenticationError), (403, PermissionDeniedError), (429, RateLimitError)],
)
def test_auth_permission_and_rate_limit_are_typed(mode, status, exc_type):
    payload = {"error": {"code": "X", "message": "refused", "status": status}}
    headers = {"Retry-After": "0"} if status == 429 else {}
    exc, _ = _run_expect(
        mode,
        lambda c: c.subscriptions.pause(WATCH_ID),
        exc_type,
        responses=_response(status, payload, headers=headers),
    )
    assert exc.status_code == status


@pytest.mark.parametrize("mode", MODES)
def test_get_429_then_success_recovers(mode):
    limited = _response(429, {"error": {"code": "RATE_LIMITED", "message": "slow"}}, headers={"Retry-After": "0"})
    sub, transport = _run(
        mode,
        lambda c: c.subscriptions.get(WATCH_ID),
        responses=[limited, _success(WIRE_SUBSCRIPTION)],
        max_retries=2,
    )
    assert sub.id == WATCH_ID
    assert transport.call_count == 2


# ---------------------------------------------------------------------------
# Malformed successes are reported, never laundered


MALFORMED_BODIES = [
    pytest.param({"status": "success", "data": {}}, id="data-without-subscription"),
    pytest.param({"status": "success", "data": {"subscriptions": [WIRE_SUBSCRIPTION]}}, id="list-shape"),
    pytest.param({"status": "success", "data": {"subscription": None}}, id="null-subscription"),
    pytest.param({"status": "success", "data": {"subscription": [WIRE_SUBSCRIPTION]}}, id="subscription-is-list"),
    pytest.param(
        {"status": "success", "data": {"subscription": {k: v for k, v in WIRE_SUBSCRIPTION.items() if k != "id"}}},
        id="missing-id",
    ),
    pytest.param(
        {"status": "success", "data": {"subscription": {k: v for k, v in WIRE_SUBSCRIPTION.items() if k != "codes"}}},
        id="missing-codes",
    ),
    pytest.param({"status": "success", "data": WIRE_SUBSCRIPTION}, id="unwrapped-record"),
    pytest.param({}, id="empty-object"),
    pytest.param([WIRE_SUBSCRIPTION], id="bare-list"),
]


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("payload", MALFORMED_BODIES)
@pytest.mark.parametrize(
    "call",
    [
        pytest.param(lambda c: c.subscriptions.get(WATCH_ID), id="get"),
        pytest.param(lambda c: c.subscriptions.update(WATCH_ID, name="x"), id="update"),
        pytest.param(lambda c: c.subscriptions.pause(WATCH_ID), id="pause"),
        pytest.param(lambda c: c.subscriptions.resume(WATCH_ID), id="resume"),
        pytest.param(
            lambda c: c.subscriptions.create(["BRENT_CRUDE_USD"], interval="daily"), id="create"
        ),
    ],
)
def test_malformed_success_raises_malformed_response(mode, payload, call):
    exc, _ = _run_expect(mode, call, OilPriceAPIError, responses=_response(200, payload))
    assert exc.code == "MALFORMED_RESPONSE"
    assert exc.raw_body == payload


@pytest.mark.parametrize("mode", MODES)
def test_non_json_200_is_a_parse_failure_not_an_empty_success(mode):
    _run_expect(
        mode,
        lambda c: c.subscriptions.get(WATCH_ID),
        ValueError,
        responses=_response(200, body=b"<html>gateway</html>"),
    )


# ---------------------------------------------------------------------------
# Timeouts: reads recover, writes are sent once and flagged ambiguous


@pytest.mark.parametrize("mode", MODES)
def test_get_timeout_raises_timeout_error(mode):
    exc, transport = _run_expect(
        mode,
        lambda c: c.subscriptions.get(WATCH_ID),
        TimeoutError,
        side_effect=httpx.TimeoutException("timed out"),
        max_retries=2,
    )
    assert transport.call_count == 2


@pytest.mark.parametrize("mode", MODES)
def test_get_timeout_then_success_recovers(mode):
    sub, transport = _run(
        mode,
        lambda c: c.subscriptions.get(WATCH_ID),
        side_effect=[httpx.TimeoutException("timed out"), _success(WIRE_SUBSCRIPTION)],
        max_retries=2,
    )
    assert sub.id == WATCH_ID
    assert transport.call_count == 2


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    "call",
    [
        pytest.param(lambda c: c.subscriptions.update(WATCH_ID, name="x"), id="update"),
        pytest.param(lambda c: c.subscriptions.pause(WATCH_ID), id="pause"),
        pytest.param(lambda c: c.subscriptions.resume(WATCH_ID), id="resume"),
    ],
)
def test_write_timeout_is_sent_once_and_marked_ambiguous(mode, call):
    exc, transport = _run_expect(
        mode,
        call,
        TimeoutError,
        side_effect=httpx.TimeoutException("timed out"),
        max_retries=3,
    )
    assert transport.call_count == 1
    assert getattr(exc, "ambiguous_write", False) is True


# ---------------------------------------------------------------------------
# Model contract


def test_subscription_model_requires_codes_rather_than_fabricating_empty():
    """A record missing ``codes`` is malformed, not a watch on nothing."""
    record = {k: v for k, v in WIRE_SUBSCRIPTION.items() if k != "codes"}
    with pytest.raises(Exception):
        Subscription(**record)


def test_subscription_model_keeps_explicit_empty_codes():
    assert Subscription(**dict(WIRE_SUBSCRIPTION, codes=[])).codes == []
