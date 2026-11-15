"""The historical-access 402 must surface its upgrade link (api#10744).

From 2026-11-16 /v1/prices/historical and /v1/prices/history join the paid
gate. The API sends the link as ``upgrade.url``; there is no top-level
``upgrade_url``. Body shape copied from V1::PricesController
#require_paid_tier_for_historical on oilpriceapi-api main.
"""

import httpx
import pytest
from click.testing import CliRunner
from unittest.mock import patch

from oilpriceapi.exceptions import PaymentRequiredError, error_from_response

UPGRADE_URL = (
    "https://www.oilpriceapi.com/pricing"
    "?utm_source=api&utm_medium=402&utm_campaign=historical_gate&ref=1"
)

GATE_402_BODY = {
    "status": "error",
    "code": "UPGRADE_REQUIRED",
    "error": "Historical data requires paid access",
    "error_code": "UPGRADE_REQUIRED",
    "message": (
        "Historical price data (past_day, past_week, past_month, past_year, "
        "historical, history) requires a paid plan. Latest prices "
        "(/v1/prices/latest) are available on the Free tier."
    ),
    "reason": "not_entitled",
    "blocked": {
        "feature": "historical",
        "endpoint": "/v1/prices/historical",
        "requires_paid_plan": ["/v1/prices/historical", "/v1/prices/history"],
    },
    "upgrade": {"url": UPGRADE_URL, "recommended_plan": "Exploration"},
}


def _response(body):
    request = httpx.Request("GET", "https://api.oilpriceapi.com/v1/prices/historical")
    return httpx.Response(402, json=body, request=request)


def test_gate_402_maps_nested_upgrade_url_to_remediation_url():
    error = error_from_response(_response(GATE_402_BODY))

    assert isinstance(error, PaymentRequiredError)
    assert error.status_code == 402
    assert error.code == "UPGRADE_REQUIRED"
    assert error.remediation_url == UPGRADE_URL
    assert "requires a paid plan" in error.message


def test_top_level_upgrade_url_still_wins():
    body = dict(GATE_402_BODY, upgrade_url="https://example.test/top")
    assert error_from_response(_response(body)).remediation_url == "https://example.test/top"


def test_402_without_any_link_leaves_remediation_url_empty():
    body = {k: v for k, v in GATE_402_BODY.items() if k != "upgrade"}
    assert error_from_response(_response(body)).remediation_url is None


def test_non_mapping_upgrade_value_is_ignored():
    body = dict(GATE_402_BODY, upgrade="see pricing")
    assert error_from_response(_response(body)).remediation_url is None


def test_cli_historical_prints_upgrade_path_not_traceback(monkeypatch):
    pytest.importorskip("click")
    pytest.importorskip("rich")
    from oilpriceapi import cli

    error = error_from_response(_response(GATE_402_BODY))

    class FakeHistorical:
        def get(self, *args, **kwargs):
            raise error

    class FakeClient:
        historical = FakeHistorical()

    monkeypatch.setenv("OILPRICEAPI_KEY", "test-key")
    with patch.object(cli, "_get_client", return_value=FakeClient()):
        result = CliRunner().invoke(cli.main, ["historical", "WTI_USD", "--days", "30"])

    assert result.exit_code == 1
    assert "Traceback" not in result.output
    assert "[402]" in result.output
    assert "requires a paid plan" in result.output
    assert "oilprice price BRENT_CRUDE_USD" in result.output
    assert "Upgrade: https://www.oilpriceapi.com/pricing" in result.output
    assert result.exception is None or isinstance(result.exception, SystemExit)


def test_cli_quota_402_does_not_claim_latest_still_works(monkeypatch):
    # A free account over quota is refused on /v1/prices/latest too
    # (admission reason free_tier_quota_exceeded), so the "latest prices still
    # work" hint would be false there. Only the history gate gets it.
    pytest.importorskip("click")
    pytest.importorskip("rich")
    from oilpriceapi import cli

    body = {
        "status": "error",
        "code": "REQUEST_LIMIT_EXCEEDED",
        "error": "Monthly request limit reached",
        "message": "Free tier limit of 50 requests reached.",
        "upgrade_url": "https://www.oilpriceapi.com/pricing",
    }
    error = error_from_response(_response(body))

    class FakeHistorical:
        def get(self, *args, **kwargs):
            raise error

    class FakeClient:
        historical = FakeHistorical()

    monkeypatch.setenv("OILPRICEAPI_KEY", "test-key")
    with patch.object(cli, "_get_client", return_value=FakeClient()):
        result = CliRunner().invoke(cli.main, ["historical", "WTI_USD"])

    assert result.exit_code == 1
    assert "Latest prices still work" not in result.output
    assert "Upgrade: https://www.oilpriceapi.com/pricing" in result.output
