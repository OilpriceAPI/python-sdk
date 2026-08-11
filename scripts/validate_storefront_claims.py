#!/usr/bin/env python3
"""Reject stale mutable claims from authored, generated, and packaged surfaces."""

import argparse
import csv
import re
from pathlib import Path
from typing import Iterable, List, Pattern, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = "https://api.oilpriceapi.com/product-facts.json"
BINARY_SUFFIXES = {
    ".a",
    ".class",
    ".dll",
    ".dylib",
    ".o",
    ".pyd",
    ".pyc",
    ".pyo",
    ".so",
}
BLOCKED: Sequence[Tuple[str, Pattern[str]]] = (
    ("real-time claim", re.compile(r"\breal[ -]?time\b", re.IGNORECASE)),
    (
        "fixed catalog total",
        re.compile(r"\b\d+\+\s+(?:commodit|endpoint|tool|api)", re.IGNORECASE),
    ),
    ("fixed traffic total", re.compile(r"\b2m\+?\s+api requests", re.IGNORECASE)),
    (
        "fixed update cadence",
        re.compile(
            r"\b(?:every|updated|refresh(?:ed)?)\s+(?:in\s+)?\d+\s+minutes\b",
            re.IGNORECASE,
        ),
    ),
    ("uptime or SLA", re.compile(r"\b\d+(?:\.\d+)?%\s+uptime\b|\bSLA\b", re.IGNORECASE)),
    (
        "price comparison",
        re.compile(r"\bbloomberg\b|\b\d+(?:\.\d+)?%\s+less\s+cost\b", re.IGNORECASE),
    ),
    (
        "unreviewed plan name",
        re.compile(
            r"\bprofessional(?:\+|\s+plan)\b|\bprofessional\*{0,2}\s*:|"
            r"\bstarter plan\b|\bscale tier\b|\bpaid tiers?\b|"
            r"\bexploration(?:\s+(?:plan|tier|and above))?\b",
            re.IGNORECASE,
        ),
    ),
    (
        "unreviewed plan price",
        re.compile(r"\$\d+(?:\.\d+)?\s*(?:/|per\s+)(?:mo(?:nth)?|year)\b", re.IGNORECASE),
    ),
    (
        "fixed allowance",
        re.compile(
            r"\b\d[\d,]*\s+(?:free\s+)?(?:api\s+requests?|station\s+queries?)"
            r"\s*(?:/|per\s+)month\b|"
            r"\bmonthly\s+station\s+(?:query|request)\s+limit\b",
            re.IGNORECASE,
        ),
    ),
    (
        "quota promise",
        re.compile(
            r"\bdoes\s+not\s+consume.{0,40}\bquota\b|"
            r"\bunlimited\s+(?:history|webhooks?|requests?|commodit)",
            re.IGNORECASE,
        ),
    ),
    (
        "universal catalog",
        re.compile(
            r"\ball\s+(?:(?:available|latest|bunker|fuel|current|supported|free[- ]tier)\s+){0,4}"
            r"(?:prices|commodities)\b|\bfull\s+(?:demo\s+)?commodity\s+catalog(?:ue)?\b",
            re.IGNORECASE,
        ),
    ),
    (
        "free-tier claim",
        re.compile(
            r"\bfree[- ]tier\b|\bfree[- ]api[- ]key\b|"
            r"\b(?:endpoint|access)\s+is\s+free\b|\bincluded\s+in\s+all\s+tiers\b",
            re.IGNORECASE,
        ),
    ),
    (
        "fixed demo rate",
        re.compile(
            r"\b\d+\s+(?:requests?|reqs?\.?)\s*(?:(?:per|an?)\s+|/\s*)"
            r"(?:minutes?|mins?|hours?|hrs?|days?)\b",
            re.IGNORECASE,
        ),
    ),
)


def discover_public_surfaces(root: Path = ROOT) -> List[Path]:
    surfaces = [root / "README.md", root / "EXAMPLES.md", root / "pyproject.toml"]
    for directory in (root / "docs", root / "oilpriceapi"):
        surfaces.extend(path for path in directory.rglob("*") if _is_public_text(path))
    return sorted(set(surfaces))


def _is_public_text(path: Path) -> bool:
    if not path.is_file() or path.suffix.lower() in BINARY_SUFFIXES:
        return False
    try:
        path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    return True


def discover_installed_surfaces(package_root: Path) -> List[Path]:
    """Return every UTF-8 customer-readable file recorded in the wheel manifest."""
    package_root = package_root.resolve()
    record_files = sorted(package_root.glob("oilpriceapi-*.dist-info/RECORD"))
    if len(record_files) != 1:
        return []

    surfaces: List[Path] = []
    with record_files[0].open(encoding="utf-8", newline="") as record:
        for row in csv.reader(record):
            if not row:
                continue
            path = (package_root / row[0]).resolve()
            try:
                path.relative_to(package_root)
            except ValueError:
                continue
            if not _is_public_text(path):
                continue
            surfaces.append(path)
    return sorted(set(surfaces))


def _claim_failures(root: Path, surfaces: Iterable[Path]) -> List[str]:
    failures: List[str] = []
    for path in surfaces:
        text = path.read_text(encoding="utf-8")
        for label, pattern in BLOCKED:
            match = pattern.search(text)
            if match:
                failures.append(
                    f"{path.relative_to(root)}: {label} matched {match.group(0)!r}"
                )
    return failures


def validate(root: Path = ROOT) -> List[str]:
    failures = _claim_failures(root, discover_public_surfaces(root))

    readme = (root / "README.md").read_text()
    if CONTRACT not in readme:
        failures.append("README.md: reviewed product-facts contract is not linked")

    project = (root / "pyproject.toml").read_text()
    version_file = (root / "oilpriceapi" / "version.py").read_text()
    project_match = re.search(r'^version = "([^"]+)"', project, re.MULTILINE)
    module_match = re.search(r'^__version__ = "([^"]+)"', version_file, re.MULTILINE)
    if not project_match or not module_match or project_match.group(1) != module_match.group(1):
        failures.append("package version differs between pyproject.toml and oilpriceapi/version.py")
    return failures


def validate_package(package_root: Path) -> List[str]:
    package_root = package_root.resolve()
    package_dir = package_root / "oilpriceapi"
    metadata_files = sorted(package_root.glob("oilpriceapi-*.dist-info/METADATA"))
    record_files = sorted(package_root.glob("oilpriceapi-*.dist-info/RECORD"))
    surfaces = discover_installed_surfaces(package_root)
    failures = _claim_failures(package_root, surfaces)

    if len(metadata_files) != 1:
        failures.append("installed artifact must contain exactly one oilpriceapi METADATA file")
        return failures
    if len(record_files) != 1:
        failures.append("installed artifact must contain exactly one oilpriceapi RECORD file")
        return failures

    metadata = metadata_files[0].read_text()
    if CONTRACT not in metadata:
        failures.append("installed METADATA: reviewed product-facts contract is not linked")

    version_file = (package_dir / "version.py").read_text()
    module_match = re.search(r'^__version__ = "([^"]+)"', version_file, re.MULTILINE)
    metadata_match = re.search(r"^Version: ([^\s]+)$", metadata, re.MULTILINE)
    if not module_match or not metadata_match or module_match.group(1) != metadata_match.group(1):
        failures.append("installed METADATA version differs from oilpriceapi/version.py")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path)
    args = parser.parse_args()

    failures = validate_package(args.package_root) if args.package_root else validate()
    if failures:
        raise SystemExit("\n".join(failures))
    if args.package_root:
        print("validated exact installed Python artifact claims")
    else:
        print(f"validated {len(discover_public_surfaces())} public surfaces")


if __name__ == "__main__":
    main()
