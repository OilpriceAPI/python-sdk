from pathlib import Path

from scripts.validate_storefront_claims import (
    discover_installed_surfaces,
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
        '{"allowance": "1,000 API requests/month"}\n'
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
