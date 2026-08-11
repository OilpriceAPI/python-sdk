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


def test_publish_gate_audits_and_installs_the_built_wheel() -> None:
    workflow = (ROOT / ".github" / "workflows" / "publish.yml").read_text()

    assert "pip-audit" in workflow
    assert "scripts/clean-wheel-smoke.sh" in workflow


def test_packaging_configuration_uses_current_metadata_forms() -> None:
    project = (ROOT / "pyproject.toml").read_text()

    assert 'license = "MIT"' in project
    assert "License :: OSI Approved :: MIT License" not in project
    assert "[tool.ruff.lint]" in project
