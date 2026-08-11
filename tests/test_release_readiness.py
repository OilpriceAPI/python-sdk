import re
import subprocess
import sys
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"
DEFAULT_BRANCH_IF = (
    "if: github.ref == format('refs/heads/{0}', "
    "github.event.repository.default_branch)"
)


def _checkout_step_blocks(workflow: str) -> List[str]:
    lines = workflow.splitlines()
    blocks: List[str] = []

    for index, line in enumerate(lines):
        match = re.match(
            r"^(\s*)(?:-\s+)?uses:\s*actions/checkout@[0-9a-f]{40}(?:\s*#.*)?$",
            line,
        )
        if match is None:
            continue
        uses_indent = len(match.group(1))
        indent = uses_indent if line.lstrip().startswith("- ") else uses_indent - 2
        start = index
        while start >= 0 and not re.match(rf"^\s{{{indent}}}-\s+", lines[start]):
            start -= 1
        assert start >= 0, f"checkout action at line {index + 1} is outside a step"

        end = start + 1
        while end < len(lines) and not re.match(rf"^\s{{{indent}}}-\s+", lines[end]):
            end += 1
        blocks.append("\n".join(lines[start:end]))

    return blocks


def _checkout_step_is_hardened(block: str) -> bool:
    lines = block.splitlines()
    step = re.match(r"^(\s*)-\s+", lines[0])
    assert step is not None
    step_indent = len(step.group(1))
    with_indent = step_indent + 2
    value_indent = with_indent + 2
    inside_with = False

    for line in lines[1:]:
        if re.match(rf"^\s{{{with_indent}}}with:\s*(?:#.*)?$", line):
            inside_with = True
            continue
        if inside_with and re.match(rf"^\s{{{with_indent}}}\S", line):
            inside_with = False
        if inside_with and re.match(
            rf"^\s{{{value_indent}}}persist-credentials:\s*false\s*(?:#.*)?$",
            line,
        ):
            return True

    return False


def test_release_documentation_matches_the_automated_gate() -> None:
    checklist = (ROOT / ".github" / "PRE_RELEASE_CHECKLIST.md").read_text()
    changelog = (ROOT / "CHANGELOG.md").read_text()

    referenced_scripts = re.findall(r"(?:^|\s)(\./scripts/[A-Za-z0-9_.-]+)", checklist)
    missing = [path for path in referenced_scripts if not (ROOT / path).exists()]

    assert missing == []
    assert "oilpriceapi/version.py" in checklist
    assert "twine upload" not in checklist
    assert changelog.count("## [Unreleased]") == 1


def test_examples_defer_mutable_allowances_to_product_facts() -> None:
    examples = (ROOT / "EXAMPLES.md").read_text()

    assert "https://api.oilpriceapi.com/product-facts.json" in examples
    assert not re.search(
        r"\b\d[\d,]*\s+(?:api\s+)?requests?\s*(?:/|per\s+)"
        r"(?:minute|hour|day|month)s?\b",
        examples,
        re.IGNORECASE,
    )


def test_packaged_futures_examples_prefer_instrument_generic_slugs() -> None:
    for path in (
        "oilpriceapi/resources/futures.py",
        "oilpriceapi/async_resources.py",
    ):
        source = (ROOT / path).read_text()
        example_lines = re.findall(r"(?m)^\s*(?:>>>|\.\.\.)\s+.*$", source)
        examples = "\n".join(example_lines)

        for example_line in example_lines:
            assert not re.search(r"[\"'](?:ice|eua)-", example_line)
        for canonical_slug in ("brent", "wti", "gasoil", "eu-carbon"):
            assert canonical_slug in examples, (
                f"{path} examples omit {canonical_slug}"
            )


def test_publish_gate_audits_and_installs_the_built_wheel() -> None:
    workflow = (ROOT / ".github" / "workflows" / "publish.yml").read_text()
    smoke = (ROOT / "scripts" / "clean-wheel-smoke.sh").read_text()

    assert "pip-audit" in workflow
    assert "scripts/clean-wheel-smoke.sh" in workflow
    assert "continue-on-error: true" not in workflow
    assert "from oilpriceapi.version import SDK_VERSION" not in smoke
    assert "--package-root" in smoke
    assert 'oilpriceapi-${expected_version}-py3-none-any.whl' in smoke
    assert "-name '*.whl' -print -quit" not in smoke


def test_oidc_publisher_consumes_only_the_verified_artifact() -> None:
    workflow = (ROOT / ".github" / "workflows" / "publish.yml").read_text()
    jobs = re.split(r"(?m)(?=^  [a-z][a-z0-9_-]*:\n)", workflow)
    publish = next(section for section in jobs if section.startswith("  publish:\n"))
    action_refs = re.findall(r"uses:\s+[^@\s]+@([^\s#]+)", workflow)

    assert "Verify release tag matches package version and protected main" in workflow
    assert "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a" in workflow
    assert "actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c" in workflow
    assert "pypa/gh-action-pypi-publish@dc37677b2e1c63e2034f94d8a5b11f265b73ba33" in publish
    assert "id-token: write" in publish
    assert "sha256sum -c artifact.sha256" in publish
    assert "cmp -s" in publish
    assert "find dist snippets -type l" in publish
    for forbidden in (
        "actions/checkout@",
        "actions/setup-python@",
        "pip install",
        "python -m",
        "pytest",
        "scripts/",
    ):
        assert forbidden not in publish
    assert action_refs
    assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref in action_refs)
    assert "Verify exact public PyPI hashes" in workflow
    assert workflow.count("python scripts/package_version.py") == 2
    assert "seq 1 24" in workflow
    assert "sleep_seconds" in workflow


def test_package_version_helper_reads_the_project_version() -> None:
    helper = ROOT / "scripts" / "package_version.py"

    assert helper.is_file()
    result = subprocess.run(
        [sys.executable, str(helper)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "1.12.6"


def test_every_workflow_pins_actions_and_hardens_each_checkout_step() -> None:
    workflows = sorted({*WORKFLOW_DIR.glob("*.yml"), *WORKFLOW_DIR.glob("*.yaml")})

    assert workflows
    for path in workflows:
        workflow = path.read_text()
        action_refs = re.findall(r"uses:\s+[^@\s]+@([^\s#]+)", workflow)
        assert action_refs, f"{path.name} contains no action reference"
        assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref in action_refs), path.name

        checkout_blocks = _checkout_step_blocks(workflow)
        if "actions/checkout@" in workflow:
            assert checkout_blocks, f"{path.name} checkout is not pinned"
        for block in checkout_blocks:
            assert _checkout_step_is_hardened(block), (
                f"{path.name} checkout retains credentials:\n{block}"
            )


def test_checkout_hardening_cannot_be_borrowed_from_an_env_mapping() -> None:
    workflow = """steps:
  - name: Checkout
    uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1
    with:
      fetch-depth: 0
    env:
      persist-credentials: false
"""
    blocks = _checkout_step_blocks(workflow)

    assert len(blocks) == 1
    assert not _checkout_step_is_hardened(blocks[0])


def test_secret_and_identity_workflows_only_run_default_branch_code() -> None:
    live = (WORKFLOW_DIR / "live-tests.yml").read_text()
    weekly = (WORKFLOW_DIR / "weekly-health.yml").read_text()
    pages = (WORKFLOW_DIR / "github-pages.yml").read_text()

    assert live.count(DEFAULT_BRANCH_IF) == 2
    assert "OILPRICEAPI_TEST_KEY is required" in live
    assert "exit 0" not in live
    assert DEFAULT_BRANCH_IF in weekly
    assert DEFAULT_BRANCH_IF in pages


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


def test_readme_documents_coverage_gated_permit_to_production() -> None:
    readme = (ROOT / "README.md").read_text()
    project = (ROOT / "pyproject.toml").read_text()

    for required in (
        '"well_level_states_with_data"',
        "client.ei.well_permits.search",
        "client.well_production.well",
        "except DataNotFoundError:",
        "if not isinstance(summary, dict):",
        "api_number.isascii()",
        "api_number.isdigit()",
        "len(api_number) != 14",
        "An empty permit search or production history is a valid data state.",
    ):
        assert required in readme

    for keyword in ('"well permits"', '"drilling data"', '"oil well production"'):
        assert keyword in project
