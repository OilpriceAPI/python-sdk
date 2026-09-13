"""#145 -- a human sentence in ``data.error`` is a message, never ``error.code``.

The API answers many failures with the JSend fail envelope,
``{"status": "fail", "data": {"error": ..., "message"?: ...}}`` (``render_fail``
in ``V1::BaseController``). ``data.error`` holds one of two things:

* a machine code, with the sentence in ``data.message``: ``VALIDATION_ERROR``,
  ``INTERVAL_FLOOR``, ``WATCH_LIMIT``, and the lower-snake ``invalid_code``,
  ``no_price_data`` and ``invalid_request`` that ``api_validations.rb`` and
  ``prices_controller.rb`` send (origin/main, 2026-09-13);
* the sentence itself, as every ``V1::FuelSurchargeController`` 400/404 does.

``error_from_response`` copied either one into ``error.code``, so a caller
branching on ``code`` saw a unique free-text string per request.

Bodies marked "live" are verbatim from ``api.oilpriceapi.com`` on 2026-09-13.
Client tests drive the REAL sync and async clients over a mocked transport.
"""

import asyncio
from unittest.mock import AsyncMock, patch

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
    ServerError,
    ValidationError,
    error_from_response,
)

# Not a credential: a fixture string. Every request here is mocked.
FIXTURE_KEY = "-".join(["fixture", "not", "a", "real", "key"])

MODES = ["sync", "async"]

# live: GET /v1/fuel-surcharge/nope/latest
UNKNOWN_CARRIER_404 = {
    "status": "fail",
    "data": {
        "error": "Unknown carrier 'nope'. Covered carriers: odfl, saia, estes, xpo, abf, tforce, averitt, southeastern-freight.",
        "covered_carriers": ["odfl", "saia", "estes", "xpo", "abf", "tforce", "averitt", "southeastern-freight"],
        "hint": "Call GET /v1/fuel-surcharge to list every covered carrier with its latest surcharge.",
    },
}

# live: POST /v1/subscriptions {"codes": [], "interval_seconds": 86400}
CODES_BLANK_422 = {
    "status": "fail",
    "data": {
        "error": "VALIDATION_ERROR",
        "message": "Codes can't be blank",
        "details": {"codes": ["can't be blank"]},
    },
}

# live: POST /v1/subscriptions {"interval_seconds": -5}; `upgrade.plans` trimmed to one entry.
INTERVAL_FLOOR_402 = {
    "status": "fail",
    "data": {
        "error": "INTERVAL_FLOOR",
        "message": "Your plan's minimum snapshot interval is 60s (requested -5s). Upgrade to poll faster.",
        "limit": 60,
        "current": -5,
        "upgrade_trigger": "interval_floor",
        "upgrade_url": "https://www.oilpriceapi.com/pricing?plan=enterprise_v2&utm_source=api&utm_medium=agent&utm_campaign=agent_min_interval",
        "upgrade": {
            "url": "https://www.oilpriceapi.com/pricing?plan=enterprise_v2&utm_source=api&utm_medium=agent&utm_campaign=agent_min_interval",
            "next_tier": "enterprise_v2",
            "plans": [{"plan": "developer", "requests": 10000, "watches": 3}],
        },
    },
}

# live: GET /v1/subscriptions/<unknown uuid>
NOT_FOUND_404 = {
    "error": {
        "code": "NOT_FOUND",
        "message": "Subscription not found",
        "status": 404,
        "request_id": "6598da0c-4289-470f-84f3-b4c3d56198b3",
        "docs": "https://docs.oilpriceapi.com#NOT_FOUND",
    }
}

# live: GET /v1/prices/latest?by_code=NOT_A_REAL_CODE_XYZ (lower-snake code + sentence,
# app/controllers/concerns/api_validations.rb).
INVALID_CODE_400 = {
    "status": "fail",
    "data": {
        "error": "invalid_code",
        "message": "Code 'NOT_A_REAL_CODE_XYZ' not found. No close match found. See /v1/commodities for all available codes.",
        "suggestions": [],
        "did_you_mean": [],
        "invalid_codes": ["NOT_A_REAL_CODE_XYZ"],
        "all_codes_url": "https://api.oilpriceapi.com/v1/commodities",
    },
}


def _response(status, body):
    request = httpx.Request(
        "GET",
        "https://api.oilpriceapi.com/v1/fuel-surcharge/nope/latest",
        headers={"Authorization": f"Token {FIXTURE_KEY}"},
    )
    return httpx.Response(status, json=body, request=request)


def _raised(mode, status, body):
    """Return the error the real client raises for ``body``."""
    response = _response(status, body)
    if mode == "sync":
        with OilPriceAPI(api_key=FIXTURE_KEY, max_retries=1) as client:
            with patch.object(client._client, "request", return_value=response):
                with pytest.raises(OilPriceAPIError) as info:
                    client.request("GET", "/v1/fuel-surcharge/nope/latest")
        return info.value

    async def go():
        async with AsyncOilPriceAPI(api_key=FIXTURE_KEY, max_retries=1) as client:
            with patch.object(client._client, "request", new=AsyncMock(return_value=response)):
                with pytest.raises(OilPriceAPIError) as info:
                    await client.request("GET", "/v1/fuel-surcharge/nope/latest")
        return info.value

    return asyncio.run(go())


# --- the defect ----------------------------------------------------------------


@pytest.mark.parametrize("mode", MODES)
def test_sentence_in_fail_envelope_is_the_message_not_the_code(mode):
    error = _raised(mode, 404, UNKNOWN_CARRIER_404)

    assert isinstance(error, DataNotFoundError)
    assert error.code is None
    assert error.machine_code is None
    assert error.message == UNKNOWN_CARRIER_404["data"]["error"]
    assert error.suggestions == UNKNOWN_CARRIER_404["data"]["covered_carriers"]
    assert error.raw_body == UNKNOWN_CARRIER_404


@pytest.mark.parametrize(
    ("status", "expected_type"),
    [
        (400, BadRequestError),
        (401, AuthenticationError),
        (402, PaymentRequiredError),
        (403, PermissionDeniedError),
        (404, DataNotFoundError),
        (422, ValidationError),
        (429, RateLimitError),
        (503, ServerError),
    ],
)
def test_no_status_class_turns_a_sentence_into_a_code(status, expected_type):
    body = {"status": "fail", "data": {"error": "period is not supported by the latest endpoint; use /v1/rig-counts/historical"}}

    error = error_from_response(_response(status, body))

    assert isinstance(error, expected_type)
    assert error.status_code == status
    assert error.code is None
    assert error.message == body["data"]["error"]


def test_sentence_without_the_status_key_is_not_a_code_either():
    body = {"data": {"error": "Parcel fuel-surcharge history requires a service_level parameter."}}

    error = error_from_response(_response(400, body))

    assert error.code is None
    assert error.message == body["data"]["error"]


# --- what must not change ------------------------------------------------------


@pytest.mark.parametrize("mode", MODES)
def test_upper_snake_code_is_the_code_and_message_is_the_sentence(mode):
    error = _raised(mode, 422, CODES_BLANK_422)

    assert isinstance(error, ValidationError)
    assert error.status_code == 422
    assert error.code == "VALIDATION_ERROR"
    assert error.machine_code == "VALIDATION_ERROR"
    assert error.message == "Codes can't be blank"


@pytest.mark.parametrize("mode", MODES)
def test_upgrade_trigger_keeps_code_message_and_remediation(mode):
    error = _raised(mode, 402, INTERVAL_FLOOR_402)

    assert isinstance(error, PaymentRequiredError)
    assert error.code == "INTERVAL_FLOOR"
    assert error.message.startswith("Your plan's minimum snapshot interval is 60s")
    assert error.remediation_url == INTERVAL_FLOOR_402["data"]["upgrade_url"]


@pytest.mark.parametrize("mode", MODES)
def test_lower_snake_code_the_api_sends_stays_the_code(mode):
    error = _raised(mode, 400, INVALID_CODE_400)

    assert isinstance(error, BadRequestError)
    assert error.code == "invalid_code"
    assert error.message == INVALID_CODE_400["data"]["message"]
    assert error.invalid_codes == ["NOT_A_REAL_CODE_XYZ"]


def test_code_with_no_sentence_is_both_code_and_message():
    error = error_from_response(_response(402, {"status": "fail", "data": {"error": "WATCH_LIMIT"}}))

    assert error.code == "WATCH_LIMIT"
    assert error.message == "WATCH_LIMIT"


@pytest.mark.parametrize("mode", MODES)
def test_canonical_nested_error_object_keeps_precedence(mode):
    error = _raised(mode, 404, NOT_FOUND_404)

    assert isinstance(error, DataNotFoundError)
    assert error.code == "NOT_FOUND"
    assert error.message == "Subscription not found"
    assert error.request_id == "6598da0c-4289-470f-84f3-b4c3d56198b3"


def test_error_object_nested_under_fail_data_keeps_precedence():
    body = {"status": "fail", "data": {"error": {"code": "DATA_NOT_AVAILABLE", "message": "Not yet published"}}}

    error = error_from_response(_response(404, body))

    assert error.code == "DATA_NOT_AVAILABLE"
    assert error.message == "Not yet published"


# --- redaction is unchanged ----------------------------------------------------


@pytest.mark.parametrize("mode", MODES)
def test_key_in_a_fail_sentence_is_redacted_and_not_used_as_code(mode):
    body = {"status": "fail", "data": {"error": f"API key {FIXTURE_KEY} cannot use this route"}}

    error = _raised(mode, 403, body)

    assert error.code is None
    assert error.message == "API key [REDACTED] cannot use this route"
    for rendered in (error.message, str(error), repr(error.raw_body), error.raw_text):
        assert FIXTURE_KEY not in rendered


@pytest.mark.parametrize("mode", MODES)
def test_key_in_a_fail_message_is_redacted_beside_a_machine_code(mode):
    body = {"status": "fail", "data": {"error": "VALIDATION_ERROR", "message": f"Token {FIXTURE_KEY} rejected"}}

    error = _raised(mode, 422, body)

    assert error.code == "VALIDATION_ERROR"
    # main redacts the whole "Token <key>" header value first; unchanged here.
    assert error.message == "[REDACTED] rejected"
    for rendered in (error.message, str(error), repr(error.raw_body), error.raw_text):
        assert FIXTURE_KEY not in rendered
