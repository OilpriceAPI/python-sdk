#!/usr/bin/env python3
"""Print the canonical package version from pyproject.toml."""

import re
from pathlib import Path


def package_version(project: Path) -> str:
    match = re.search(
        r'^version = "([^"]+)"$',
        project.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    if match is None:
        raise SystemExit("package version not found")
    return match.group(1)


if __name__ == "__main__":
    print(package_version(Path(__file__).resolve().parents[1] / "pyproject.toml"))
