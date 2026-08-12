from pathlib import Path
from typing import List

import pytest

from scripts.validate_storefront_claims import (
    discover_installed_surfaces,
    discover_public_surfaces,
    validate,
    validate_package,
)

ROOT = Path(__file__).resolve().parents[1]


def _installed_text_failures(tmp_path: Path, text: str) -> List[str]:
    package = tmp_path / "oilpriceapi"
    dist_info = tmp_path / "oilpriceapi-9.9.9.dist-info"
    package.mkdir()
    dist_info.mkdir()
    (package / "version.py").write_text('__version__ = "9.9.9"\n')
    (package / "future.txt").write_text(text)
    (dist_info / "METADATA").write_text(
        "Metadata-Version: 2.1\n"
        "Name: oilpriceapi\n"
        "Version: 9.9.9\n\n"
        "https://api.oilpriceapi.com/product-facts.json\n"
    )
    (dist_info / "RECORD").write_text(
        "oilpriceapi/version.py,,\n"
        "oilpriceapi/future.txt,,\n"
        "oilpriceapi-9.9.9.dist-info/METADATA,,\n"
        "oilpriceapi-9.9.9.dist-info/RECORD,,\n"
    )
    return validate_package(tmp_path)


def _authored_text_failures(tmp_path: Path, text: str) -> List[str]:
    package = tmp_path / "oilpriceapi" / "future"
    package.mkdir(parents=True)
    (tmp_path / "README.md").write_text(
        "https://api.oilpriceapi.com/product-facts.json\n"
    )
    (tmp_path / "EXAMPLES.md").write_text("Reviewed examples.\n")
    (tmp_path / "CHANGELOG.md").write_text("Reviewed history.\n")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "oilpriceapi"\nversion = "9.9.9"\n'
    )
    (tmp_path / "oilpriceapi" / "version.py").write_text(
        '__version__ = "9.9.9"\n'
    )
    (package / "types.pyi").write_text(text)
    return validate(tmp_path)


def test_storefront_claims_match_reviewed_contract() -> None:
    assert validate() == []


def test_discovers_docs_examples_and_nested_package_source() -> None:
    surfaces = {path.relative_to(ROOT).as_posix() for path in discover_public_surfaces()}

    assert "EXAMPLES.md" in surfaces
    assert "docs/index.md" in surfaces
    assert "docs/index.html" in surfaces
    assert "oilpriceapi/streaming/client.py" in surfaces


def test_rejects_claim_introduced_only_in_installed_wheel(tmp_path: Path) -> None:
    package = tmp_path / "oilpriceapi"
    dist_info = tmp_path / "oilpriceapi-9.9.9.dist-info"
    package.mkdir()
    dist_info.mkdir()
    (package / "version.py").write_text('__version__ = "9.9.9"\n')
    (package / "future.py").write_text('"""Guaranteed 99.9% uptime."""\n')
    (dist_info / "METADATA").write_text(
        "Metadata-Version: 2.1\n"
        "Name: oilpriceapi\n"
        "Version: 9.9.9\n\n"
        "https://api.oilpriceapi.com/product-facts.json\n"
    )
    (dist_info / "RECORD").write_text(
        "oilpriceapi/version.py,,\n"
        "oilpriceapi/future.py,,\n"
        "oilpriceapi-9.9.9.dist-info/METADATA,,\n"
        "oilpriceapi-9.9.9.dist-info/RECORD,,\n"
    )

    assert any("oilpriceapi/future.py" in failure for failure in validate_package(tmp_path))


def test_rejects_claim_in_future_installed_package_data(tmp_path: Path) -> None:
    package = tmp_path / "oilpriceapi"
    dist_info = tmp_path / "oilpriceapi-9.9.9.dist-info"
    package.mkdir()
    (package / "docs").mkdir()
    (package / "__pycache__").mkdir()
    dist_info.mkdir()
    (package / "version.py").write_text('__version__ = "9.9.9"\n')
    (package / "py.typed").write_text("")
    (package / "types.pyi").write_text(
        '"""Free-tier access includes the full commodity catalog and all latest prices. '
        'Endpoint is free and included in all tiers. Available on paid tiers. '
        'Monthly station query limit applies."""\n'
    )
    (package / "docs" / "catalog.json").write_text(
        '{"allowance": "1,000 API requests/month", '
        '"daily_allowance": "50 requests/day"}\n'
    )
    (package / "__pycache__" / "version.cpython-312.pyc").write_bytes(b"\x00\xff")
    (dist_info / "METADATA").write_text(
        "Metadata-Version: 2.1\n"
        "Name: oilpriceapi\n"
        "Version: 9.9.9\n\n"
        "https://api.oilpriceapi.com/product-facts.json\n"
    )
    (dist_info / "RECORD").write_text(
        "oilpriceapi/version.py,,\n"
        "oilpriceapi/py.typed,,\n"
        "oilpriceapi/types.pyi,,\n"
        "oilpriceapi/docs/catalog.json,,\n"
        "oilpriceapi/__pycache__/version.cpython-312.pyc,,\n"
        "oilpriceapi-9.9.9.dist-info/METADATA,,\n"
        "oilpriceapi-9.9.9.dist-info/RECORD,,\n"
    )

    surfaces = {
        path.relative_to(tmp_path).as_posix()
        for path in discover_installed_surfaces(tmp_path)
    }
    failures = validate_package(tmp_path)

    assert "oilpriceapi/types.pyi" in surfaces
    assert "oilpriceapi/docs/catalog.json" in surfaces
    assert not any("__pycache__" in surface for surface in surfaces)
    assert any(
        "oilpriceapi/types.pyi" in failure
        and "free-tier claim" in failure
        and "matched 'Free-tier'" in failure
        for failure in failures
    )
    assert any(
        "oilpriceapi/types.pyi" in failure and "unreviewed plan name" in failure
        for failure in failures
    )
    assert any(
        "oilpriceapi/types.pyi" in failure and "fixed allowance" in failure
        for failure in failures
    )
    assert any(
        "oilpriceapi/types.pyi" in failure and "universal catalog" in failure
        for failure in failures
    )
    assert any("oilpriceapi/docs/catalog.json" in failure for failure in failures)
    assert any(
        "oilpriceapi/docs/catalog.json" in failure
        and "fixed demo rate" in failure
        and "matched '50 requests/day'" in failure
        for failure in failures
    )


def test_rejects_telemetry_quota_reward_in_future_nested_authored_source(
    tmp_path: Path,
) -> None:
    failures = _authored_text_failures(
        tmp_path,
        '"""Application telemetry unlocks additional API calls for your app."""\n',
    )

    assert any(
        "oilpriceapi/future/types.pyi" in failure
        and "telemetry quota reward" in failure
        for failure in failures
    ), failures


@pytest.mark.parametrize(
    "claim",
    [
        "Add optional telemetry headers (10% bonus for app_url!).",
        "App telemetry may unlock a 10% bonus to your request limit.",
        "X-App-URL earns extra request credits.",
        "More requests are granted when application metadata is sent.",
        "Sending app_url increases your quota allowance.",
    ],
)
def test_rejects_telemetry_quota_rewards_in_future_wheel_text(
    tmp_path: Path, claim: str
) -> None:
    failures = _installed_text_failures(tmp_path, claim)

    assert any("telemetry quota reward" in failure for failure in failures), failures


@pytest.mark.parametrize(
    "text",
    [
        "Optional telemetry headers identify SDK usage.",
        "Application metadata supports usage attribution; entitlements come from Product Facts.",
        "X-App-URL and X-App-Name are optional attribution headers.",
        "Telemetry sends extra application metadata with API requests.",
    ],
)
def test_allows_telemetry_attribution_without_a_quota_reward(
    tmp_path: Path, text: str
) -> None:
    assert _installed_text_failures(tmp_path, text) == []


@pytest.mark.parametrize(
    "claim",
    [
        "50 API calls/day",
        "50 calls per day",
        "50 requests daily",
        "daily limit of 50 requests",
        "50-request daily allowance",
        "100 API calls hourly",
        "hourly request quota: 100 calls",
        "3 reqs/minute",
        "50 calls each day",
        "100 API requests every hour",
        "daily cap is 50 calls",
        "50-call-per-day allowance",
        "50 requests per 24 hours",
        "50 requests every 24 hours",
        "50 API calls in a day",
        "daily 50-request limit",
        "24-hour quota of 50 calls",
        "API call rate limit is 200 every hour",
        "weekly 5,000-credit allowance",
        "2,000 queries per 30 days",
        "50/day API calls",
        "50 daily API calls",
        "API calls: 50 per day",
        "API calls daily: 50",
        "daily API calls: 50",
        "50 requests over a rolling 24-hour window",
        "50 API calls during any one-hour period",
        "50 request limit per day",
        "50-call limit per day",
        "50 requests allowed daily",
        "<p>daily <strong>50</strong> API calls</p>",
    ],
)
def test_rejects_fixed_rate_aliases_in_installed_text(tmp_path: Path, claim: str) -> None:
    failures = _installed_text_failures(tmp_path, claim)

    assert any("fixed demo rate" in failure for failure in failures), failures


def test_reports_one_failure_for_overlapping_monthly_rate(tmp_path: Path) -> None:
    failures = _installed_text_failures(tmp_path, "50 API requests per month")

    matching = [failure for failure in failures if "50 API requests per month" in failure]
    assert len(matching) == 1, failures


@pytest.mark.parametrize(
    "text",
    [
        "SDK version 1.12.4 supports Python 3.8.",
        "Run 50 tests daily.",
        "The response contains 50 records per page.",
        "Retry attempt 50 failed.",
        "Daily 50-test limit.",
        "A 24-hour test window contains 50 assertions.",
        "The monthly report contains 50 records.",
        "1 week queries",
        "return 120  # 2 minutes for year queries",
        "50 records are returned. Requests include timestamps updated daily.",
    ],
)
def test_fixed_rate_aliases_do_not_match_versions_or_test_counts(
    tmp_path: Path, text: str
) -> None:
    assert _installed_text_failures(tmp_path, text) == []
