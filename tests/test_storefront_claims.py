from pathlib import Path

from scripts.validate_storefront_claims import (
    discover_public_surfaces,
    validate,
    validate_package,
)

ROOT = Path(__file__).resolve().parents[1]


def test_storefront_claims_match_reviewed_contract() -> None:
    assert validate() == []


def test_discovers_docs_examples_and_nested_package_source() -> None:
    surfaces = {path.relative_to(ROOT).as_posix() for path in discover_public_surfaces()}

    assert "EXAMPLES.md" in surfaces
    assert "docs/index.md" in surfaces
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

    assert any("oilpriceapi/future.py" in failure for failure in validate_package(tmp_path))
