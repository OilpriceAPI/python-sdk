"""
Live contract tests for the public demo endpoints.

These hit the REAL, no-authentication demo API:

    GET https://api.oilpriceapi.com/v1/demo/prices
    GET https://api.oilpriceapi.com/v1/demo/commodities

They require no API key, but they DO require network access, so they live under
tests/integration/ and are marked ``live`` — the default unit gate ignores this
directory (``pytest tests/ --ignore=tests/integration``). Run explicitly with:

    pytest tests/integration/test_demo_contract.py -m live

Purpose: prove the SDK's DemoResource parses the real response envelope
(``{"status": ..., "data": {prices|commodities, meta}}``) and that the live
contract still holds (the original nine demo codes remain available,
BRENT_CRUDE_USD is plausible, the catalogue is large, and
``meta.free_commodities`` is internally consistent).
"""

import math
import os
from typing import Callable, TypeVar

import httpx
import pytest

from oilpriceapi.resources.demo import DemoResource

pytestmark = pytest.mark.live

DEMO_BASE_URL = os.environ.get("OILPRICEAPI_BASE_URL", "https://api.oilpriceapi.com")
CORE_DEMO_CODES = {
    "BRENT_CRUDE_USD",
    "WTI_USD",
    "NATURAL_GAS_USD",
    "GOLD_USD",
    "EUR_USD",
    "GBP_USD",
    "HEATING_OIL_USD",
    "GASOLINE_USD",
    "DIESEL_USD",
}
T = TypeVar("T")


@pytest.fixture(scope="module")
def demo() -> DemoResource:
    """A standalone (no API key) demo resource pointed at the live API."""
    return DemoResource(base_url=DEMO_BASE_URL)


def _run_live_request(operation: Callable[[], T]) -> T:
    """Run an always-on synthetic request; every request failure is signal."""
    return operation()


class TestMonitorFailureSemantics:
    @pytest.mark.parametrize("failure_kind", ["status", "transport", "os"])
    def test_request_failures_cannot_skip_the_hosted_monitor(
        self, failure_kind: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        request = httpx.Request("GET", f"{DEMO_BASE_URL}/v1/demo/prices")
        if failure_kind == "status":
            response = httpx.Response(503, request=request)
            error: Exception = httpx.HTTPStatusError(
                "Service Unavailable", request=request, response=response
            )
        elif failure_kind == "transport":
            error = httpx.ConnectError("connection failed", request=request)
        else:
            error = OSError("network unavailable")

        def fail_request() -> None:
            raise error

        def fail_if_skipped(reason: str) -> None:
            pytest.fail(f"hosted monitor converted {failure_kind} failure to skip: {reason}")

        monkeypatch.setattr(pytest, "skip", fail_if_skipped)
        with pytest.raises(type(error)):
            _run_live_request(fail_request)


class TestDemoPricesContract:
    def test_prices_envelope_and_parsing(self, demo: DemoResource) -> None:
        """DemoResource.prices() parses the real {status, data:{prices, meta}} envelope."""
        data = _run_live_request(demo.prices)

        # data is the unwrapped `data` payload from the envelope.
        assert "prices" in data
        assert "meta" in data

        prices = data["prices"]
        assert isinstance(prices, list)

        by_code = {p["code"]: p for p in prices}
        assert len(by_code) == len(prices)
        # The demo catalogue may grow. Its original core must remain usable.
        assert CORE_DEMO_CODES <= by_code.keys()

        for code in CORE_DEMO_CODES:
            row = by_code[code]
            assert row["code"] == code
            assert isinstance(row["name"], str) and row["name"]
            assert isinstance(row["currency"], str) and row["currency"]
            assert isinstance(row["updated_at"], str) and row["updated_at"]
            price = float(row["price"])
            assert math.isfinite(price) and price > 0

        brent_price = float(by_code["BRENT_CRUDE_USD"]["price"])
        # Sanity-check Brent is in a plausible band (~$80, allow wide drift).
        assert 30 < brent_price < 200

    def test_prices_meta_demo_mode(self, demo: DemoResource) -> None:
        """The demo prices meta block flags demo mode and lists free commodities."""
        data = _run_live_request(demo.prices)

        meta = data["meta"]
        assert meta.get("demo_mode") is True
        assert meta.get("available_commodities", 0) >= len(CORE_DEMO_CODES)


class TestDemoCommoditiesContract:
    def test_commodities_envelope_and_count(self, demo: DemoResource) -> None:
        """DemoResource.commodities() parses {status, data:{commodities, meta}}; 442 total."""
        data = _run_live_request(demo.commodities)

        assert "commodities" in data
        assert "meta" in data

        catalog = data["commodities"]
        assert isinstance(catalog, dict)  # grouped by category

        meta = data["meta"]
        # Contract: meta.total agrees with the flattened catalog size and the
        # catalog is large (400+). Do NOT pin the exact count — the live
        # catalog legitimately grows/shrinks (442 when written, 436 on
        # 2026-07-03), and an exact pin turns catalog curation into failures.
        flattened = sum(len(v) for v in catalog.values())
        assert meta["total"] == flattened
        assert meta["total"] >= 400

        # The configured free list may grow, but it must preserve the core and
        # remain duplicate-free instead of pinning mutable catalogue size.
        assert "free_commodities" in meta
        free_codes = set(meta["free_commodities"])
        assert len(free_codes) == len(meta["free_commodities"])
        assert CORE_DEMO_CODES <= free_codes
        assert len(free_codes) >= len(CORE_DEMO_CODES)

    def test_commodities_codes_filter(self, demo: DemoResource) -> None:
        """Passing codes= returns only the requested free-tier prices."""
        data = _run_live_request(lambda: demo.prices(codes=["BRENT_CRUDE_USD", "WTI_USD"]))

        codes = {p["code"] for p in data["prices"]}
        assert codes == {"BRENT_CRUDE_USD", "WTI_USD"}
