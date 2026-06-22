"""Documentation contract tests for the SDK Performance Guide (issue #26).

Issue #26 ("[Q2-P2] Document SDK performance characteristics and best
practices") defines five acceptance criteria:

    - [ ] Performance guide added to docs
    - [ ] Best practices documented
    - [ ] Troubleshooting guide added
    - [ ] Examples updated with performance notes
    - [ ] README links to performance guide

These tests encode each criterion as an executable assertion so the
documentation cannot silently regress. They are pure filesystem checks
(no network, no API key) and therefore run in the default `unit` gate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Repo root is two levels up from this file: tests/unit/ -> repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]
PERF_GUIDE = REPO_ROOT / "docs" / "PERFORMANCE_GUIDE.md"
README = REPO_ROOT / "README.md"
MKDOCS = REPO_ROOT / "mkdocs.yml"


@pytest.fixture(scope="module")
def perf_guide_text() -> str:
    assert PERF_GUIDE.exists(), f"Performance guide missing at {PERF_GUIDE}"
    return PERF_GUIDE.read_text(encoding="utf-8")


# --- Criterion 1: Performance guide added to docs --------------------------


def test_performance_guide_exists() -> None:
    """A dedicated performance guide must live under docs/."""
    assert PERF_GUIDE.exists(), f"Expected performance guide at {PERF_GUIDE}"
    assert PERF_GUIDE.stat().st_size > 0, "Performance guide must not be empty"


def test_performance_guide_documents_expected_response_times(
    perf_guide_text: str,
) -> None:
    """The guide must set expectations for query latency and timeouts."""
    lowered = perf_guide_text.lower()
    assert "expected performance" in lowered or "expected response" in lowered
    assert "timeout" in lowered
    # Concrete latency baselines users can compare against.
    assert "ms" in perf_guide_text
    assert "<500ms" in perf_guide_text or "500ms" in perf_guide_text


# --- Criterion 2: Best practices documented --------------------------------


def test_best_practices_documented(perf_guide_text: str) -> None:
    lowered = perf_guide_text.lower()
    assert "optimization" in lowered or "best practice" in lowered
    # Core best-practice levers called out in the issue.
    assert "per_page" in perf_guide_text, "Pagination guidance missing"
    assert "async" in lowered, "Async/parallel guidance missing"
    assert "context manager" in lowered or "with OilPriceAPI" in perf_guide_text


# --- Criterion 3: Troubleshooting guide added ------------------------------


def test_troubleshooting_section_present(perf_guide_text: str) -> None:
    lowered = perf_guide_text.lower()
    assert "troubleshooting" in lowered, "Troubleshooting section missing"
    assert "timeout" in lowered


# --- Criterion 4: Examples updated with performance notes ------------------


def test_guide_contains_runnable_examples(perf_guide_text: str) -> None:
    """Guidance must include concrete, copy-pasteable code examples."""
    assert "```python" in perf_guide_text, "Guide must include python examples"
    # Both a slow anti-pattern and a fast recommended pattern.
    assert "historical.get(" in perf_guide_text


# --- Criterion 5: README links to performance guide ------------------------


def test_readme_links_to_performance_guide() -> None:
    """README must link to docs/PERFORMANCE_GUIDE.md so users can find it."""
    assert README.exists(), f"README missing at {README}"
    text = README.read_text(encoding="utf-8")
    assert "docs/PERFORMANCE_GUIDE.md" in text, (
        "README must link to docs/PERFORMANCE_GUIDE.md "
        "(acceptance criterion: 'README links to performance guide')"
    )


# --- Discoverability: guide wired into the docs site nav -------------------


def test_performance_guide_in_mkdocs_nav() -> None:
    """The guide must be reachable from the published docs site navigation."""
    assert MKDOCS.exists(), f"mkdocs.yml missing at {MKDOCS}"
    text = MKDOCS.read_text(encoding="utf-8")
    assert "PERFORMANCE_GUIDE.md" in text, (
        "mkdocs.yml nav must include PERFORMANCE_GUIDE.md so the guide is "
        "discoverable on the docs site"
    )
