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

import os

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


@pytest.fixture(scope="module")
def demo() -> DemoResource:
    """A standalone (no API key) demo resource pointed at the live API."""
    return DemoResource(base_url=DEMO_BASE_URL)


def _skip_on_network_error(exc: Exception) -> None:
    pytest.skip(f"live demo API unreachable: {exc}")


class TestDemoPricesContract:
    def test_prices_envelope_and_parsing(self, demo: DemoResource) -> None:
        """DemoResource.prices() parses the real {status, data:{prices, meta}} envelope."""
        try:
            data = demo.prices()
        except (httpx.HTTPError, OSError) as exc:  # pragma: no cover - network
            _skip_on_network_error(exc)

        # data is the unwrapped `data` payload from the envelope.
        assert "prices" in data
        assert "meta" in data

        prices = data["prices"]
        assert isinstance(prices, list)

        by_code = {p["code"]: p for p in prices}
        # The demo catalogue may grow. Its original core must remain usable.
        assert CORE_DEMO_CODES <= by_code.keys()

        brent = by_code["BRENT_CRUDE_USD"]
        # Each price row carries the documented fields.
        for field in ("code", "name", "price", "currency", "updated_at"):
            assert field in brent
        # Sanity-check Brent is in a plausible band (~$80, allow wide drift).
        assert 30 < float(brent["price"]) < 200

    def test_prices_meta_demo_mode(self, demo: DemoResource) -> None:
        """The demo prices meta block flags demo mode and lists free commodities."""
        try:
            data = demo.prices()
        except (httpx.HTTPError, OSError) as exc:  # pragma: no cover - network
            _skip_on_network_error(exc)

        meta = data["meta"]
        assert meta.get("demo_mode") is True
        assert meta.get("available_commodities", 0) >= len(CORE_DEMO_CODES)


class TestDemoCommoditiesContract:
    def test_commodities_envelope_and_count(self, demo: DemoResource) -> None:
        """DemoResource.commodities() parses {status, data:{commodities, meta}}; 442 total."""
        try:
            data = demo.commodities()
        except (httpx.HTTPError, OSError) as exc:  # pragma: no cover - network
            _skip_on_network_error(exc)

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
        try:
            data = demo.prices(codes=["BRENT_CRUDE_USD", "WTI_USD"])
        except (httpx.HTTPError, OSError) as exc:  # pragma: no cover - network
            _skip_on_network_error(exc)

        codes = {p["code"] for p in data["prices"]}
        assert codes == {"BRENT_CRUDE_USD", "WTI_USD"}
