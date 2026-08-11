"""Unit tests for futures slug normalization (no network)."""

import pytest

from oilpriceapi.resources._futures_slug import (
    CONTRACT_CODE_TO_SLUG,
    VALID_SLUGS,
    normalize_futures_slug,
)


class TestNormalizeFuturesSlug:
    def test_canonical_slug_passthrough(self):
        for slug in VALID_SLUGS:
            assert normalize_futures_slug(slug) == slug

    def test_slug_case_insensitive(self):
        assert normalize_futures_slug("BRENT") == "brent"
        assert normalize_futures_slug("Natural-Gas") == "natural-gas"

    @pytest.mark.parametrize(
        "legacy,expected",
        [
            ("ice-brent", "brent"),
            ("ICE-BRENT", "brent"),
            ("ice-wti", "wti"),
            ("ice-gasoil", "gasoil"),
            ("eua-carbon", "eu-carbon"),
        ],
    )
    def test_legacy_venue_slug_normalizes_to_generic_route(self, legacy, expected):
        assert normalize_futures_slug(legacy) == expected

    @pytest.mark.parametrize(
        "code,expected",
        [
            ("BZ", "brent"),
            ("CL", "wti"),
            ("G", "gasoil"),
            ("QS", "gasoil"),
            ("NG", "natural-gas"),
            ("TTF", "ttf-gas"),
            ("JKM", "lng-jkm"),
            ("EUA", "eu-carbon"),
            ("EU_CARBON", "eu-carbon"),
            ("UKA", "uk-carbon"),
            ("UK_CARBON", "uk-carbon"),
        ],
    )
    def test_contract_code_to_slug(self, code, expected):
        assert normalize_futures_slug(code) == expected
        assert normalize_futures_slug(code.lower()) == expected

    @pytest.mark.parametrize(
        "code,expected",
        [
            ("CL.1", "wti"),
            ("BZ.1", "brent"),
            ("CL1!", "wti"),
            ("NG-2025-12", "natural-gas"),
            ("BZ_2026_01", "brent"),
        ],
    )
    def test_contract_code_with_suffix(self, code, expected):
        assert normalize_futures_slug(code) == expected

    def test_continuous_slug_passthrough(self):
        assert normalize_futures_slug("continuous/brent") == "continuous/brent"
        assert normalize_futures_slug("continuous/wti") == "continuous/wti"

    @pytest.mark.parametrize("bad", ["", "   ", "ZZZ", "not-a-slug", "FOO.1"])
    def test_invalid_raises_value_error(self, bad):
        with pytest.raises(ValueError):
            normalize_futures_slug(bad)

    def test_mapping_targets_are_valid_slugs(self):
        for slug in CONTRACT_CODE_TO_SLUG.values():
            assert slug in VALID_SLUGS
