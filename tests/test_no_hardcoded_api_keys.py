"""Guard against committing real OilPriceAPI tokens in examples/tests."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCAN_PATHS = [
    ROOT / "README.md",
    ROOT / "CHANGELOG.md",
    ROOT / "docs",
    ROOT / "examples",
    ROOT / "monitoring",
    ROOT / "oilpriceapi",
    ROOT / "scripts",
    ROOT / "tests",
]
TEXT_SUFFIXES = {
    ".cfg",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".rst",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

TOKEN_RE = re.compile(r"(?<![A-Fa-f0-9])[A-Fa-f0-9]{64}(?![A-Fa-f0-9])")


def iter_text_files() -> list[Path]:
    files: list[Path] = []
    for path in SCAN_PATHS:
        if path.is_file():
            files.append(path)
            continue

        if not path.exists():
            continue

        for child in path.rglob("*"):
            if not child.is_file():
                continue
            if any(part in {".git", ".mypy_cache", ".pytest_cache", "__pycache__"} for part in child.parts):
                continue
            if child.suffix.lower() in TEXT_SUFFIXES:
                files.append(child)

    return sorted(set(files))


def test_no_hardcoded_oilpriceapi_tokens() -> None:
    findings: list[str] = []

    for path in iter_text_files():
        for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            for match in TOKEN_RE.finditer(line):
                token_hash = hashlib.sha256(match.group(0).encode("utf-8")).hexdigest()[:16]
                findings.append(f"{path.relative_to(ROOT)}:{line_number}: sha256:{token_hash}")

    assert findings == [], "Hardcoded OilPriceAPI-shaped token(s) found:\n" + "\n".join(findings)
