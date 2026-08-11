import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_release_documentation_matches_the_automated_gate() -> None:
    checklist = (ROOT / ".github" / "PRE_RELEASE_CHECKLIST.md").read_text()
    changelog = (ROOT / "CHANGELOG.md").read_text()

    referenced_scripts = re.findall(r"(?:^|\s)(\./scripts/[A-Za-z0-9_.-]+)", checklist)
    missing = [path for path in referenced_scripts if not (ROOT / path).exists()]

    assert missing == []
    assert "oilpriceapi/version.py" in checklist
    assert "twine upload" not in checklist
    assert changelog.count("## [Unreleased]") == 1


def test_examples_use_the_canonical_free_quota() -> None:
    examples = (ROOT / "EXAMPLES.md").read_text()

    assert "50 requests/day" in examples
    assert not re.search(r"free requests?/(?:month|monthly)", examples, re.IGNORECASE)


def test_publish_gate_audits_and_installs_the_built_wheel() -> None:
    workflow = (ROOT / ".github" / "workflows" / "publish.yml").read_text()
    smoke = (ROOT / "scripts" / "clean-wheel-smoke.sh").read_text()

    assert "pip-audit" in workflow
    assert "scripts/clean-wheel-smoke.sh" in workflow
    assert "continue-on-error: true" not in workflow
    assert "from oilpriceapi.version import SDK_VERSION" not in smoke
    assert "--package-root" in smoke


def test_packaging_configuration_remains_compatible_with_supported_python() -> None:
    project = (ROOT / "pyproject.toml").read_text()

    # Python 3.8 resolves a setuptools release whose schema does not yet accept
    # the PEP 639 string form. Keep the PEP 621 table while 3.8 is supported.
    assert 'requires = ["setuptools>=70.1,<77", "wheel"]' in project
    assert 'license = {file = "LICENSE"}' in project
    assert 'requires-python = ">=3.8"' in project
    assert "[tool.ruff.lint]" in project


def test_manifest_has_no_noop_exclusion_patterns() -> None:
    manifest = (ROOT / "MANIFEST.in").read_text()

    for stale in ("global-exclude", "exclude test_sdk_live.py", "prune "):
        assert stale not in manifest
