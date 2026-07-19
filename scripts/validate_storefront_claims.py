#!/usr/bin/env python3
"""Reject stale mutable claims from files rendered by PyPI and GitHub."""

import re
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[1]
SURFACES = (
    ROOT / "README.md",
    ROOT / "pyproject.toml",
    ROOT / "oilpriceapi" / "__init__.py",
)
BLOCKED = (
    re.compile(r"\breal[ -]?time\b", re.IGNORECASE),
    re.compile(r"\b(?:110|200|500)\+\s+(?:commodit|endpoint|tool)", re.IGNORECASE),
    re.compile(r"\b2m\+?\s+api requests", re.IGNORECASE),
    re.compile(r"\b(?:every|updated|refresh(?:ed)?)\s+(?:in\s+)?5 minutes\b", re.IGNORECASE),
    re.compile(r"\b(?:99\.\d+%|fortune 500|trading[- ]grade)\b", re.IGNORECASE),
    re.compile(r"\b(?:1,000|100)\s+requests?(?:/month|\s+per month|\s+\(lifetime\))", re.IGNORECASE),
    re.compile(r"\bunlimited\s+(?:history|webhooks?|requests?|commodit)", re.IGNORECASE),
)
CONTRACT = "https://api.oilpriceapi.com/product-facts.json"


def validate() -> List[str]:
    failures = []
    for path in SURFACES:
        text = path.read_text()
        for pattern in BLOCKED:
            if pattern.search(text):
                failures.append(f"{path.relative_to(ROOT)}: blocked claim matched {pattern.pattern}")

    readme = (ROOT / "README.md").read_text()
    if CONTRACT not in readme:
        failures.append("README.md: reviewed product-facts contract is not linked")

    project = (ROOT / "pyproject.toml").read_text()
    version_file = (ROOT / "oilpriceapi" / "version.py").read_text()
    project_match = re.search(r'^version = "([^"]+)"', project, re.MULTILINE)
    module_match = re.search(r'^__version__ = "([^"]+)"', version_file, re.MULTILINE)
    if not project_match or not module_match or project_match.group(1) != module_match.group(1):
        failures.append("package version differs between pyproject.toml and oilpriceapi/version.py")
    return failures


def main() -> None:
    failures = validate()
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"validated {len(SURFACES)} Python storefront surfaces")


if __name__ == "__main__":
    main()
