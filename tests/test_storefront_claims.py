from scripts.validate_storefront_claims import validate


def test_storefront_claims_match_reviewed_contract() -> None:
    assert validate() == []
