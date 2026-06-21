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
        assert normalize_futures_slug("ICE-BRENT") == "ice-brent"
        assert normalize_futures_slug("Natural-Gas") == "natural-gas"

    @pytest.mark.parametrize(
        "code,expected",
        [
            ("BZ", "ice-brent"),
            ("CL", "ice-wti"),
            ("G", "ice-gasoil"),
            ("QS", "ice-gasoil"),
            ("NG", "natural-gas"),
            ("TTF", "ttf-gas"),
            ("JKM", "lng-jkm"),
            ("EUA", "eua-carbon"),
            ("UKA", "uk-carbon"),
        ],
    )
    def test_contract_code_to_slug(self, code, expected):
        assert normalize_futures_slug(code) == expected
        assert normalize_futures_slug(code.lower()) == expected

    @pytest.mark.parametrize(
        "code,expected",
        [
            ("CL.1", "ice-wti"),
            ("BZ.1", "ice-brent"),
            ("CL1!", "ice-wti"),
            ("NG-2025-12", "natural-gas"),
            ("BZ_2026_01", "ice-brent"),
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
