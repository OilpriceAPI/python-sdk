#!/usr/bin/env python3
"""Reject stale mutable claims from authored, generated, and packaged surfaces."""

import argparse
import csv
import re
from pathlib import Path
from typing import Iterable, Iterator, List, Match, Pattern, Sequence, Set, Tuple

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
_RATE_COUNT = r"\d[\d,]*"
_RATE_ACTION = r"(?:(?:api[- ]+)?(?:requests?|calls?|queries?|hits?|credits?)|reqs?\.?)"
_RATE_UNIT_SINGULAR = r"(?:second|sec|minute|min|hour|hr|day|week|month|year)"
_RATE_UNIT = rf"{_RATE_UNIT_SINGULAR}s?\.?"
_RATE_ADVERB = r"(?:secondly|minutely|hourly|daily|weekly|monthly|yearly)"
_RATE_DURATION = rf"(?:(?:a|an|one|any|rolling|{_RATE_COUNT})[- ]+){{0,3}}{_RATE_UNIT}"
_RATE_NUMBER_PATTERN = re.compile(rf"(?<![\w.]){_RATE_COUNT}(?![\w.])")
_RATE_ACTION_PATTERN = re.compile(rf"\b{_RATE_ACTION}\b", re.IGNORECASE)
_RATE_CADENCE_PATTERN = re.compile(
    rf"\b{_RATE_ADVERB}\b|"
    rf"(?:/[- ]*|\b(?:per|each|every|in|within|over|during|for)\b[- ]+)"
    rf"{_RATE_DURATION}\b|"
    rf"\b(?:a|an|one|any|rolling|{_RATE_COUNT})[- ]+{_RATE_UNIT}\b",
    re.IGNORECASE,
)
_RATE_BOUNDARY_PATTERN = re.compile(
    r"(?:\r?\n)+|\s+#\s+|[!?;]+(?:\s+|$)|\.(?:\s+|$)"
)
_HTML_TAG_PATTERN = re.compile(r"<[^>]{1,500}>")
_MAX_ACTION_COUNT_GAP = 64
_MAX_RATE_SPAN = 200
_MAX_TELEMETRY_REWARD_SPAN = 320
_TELEMETRY_IDENTITY_PATTERN = re.compile(
    r"\b(?:telemetry|app(?:lication)?[- ]+(?:metadata|url|name)|"
    r"app[_ -]?url|app[_ -]?name|x-app-(?:url|name))\b",
    re.IGNORECASE,
)
_TELEMETRY_STRONG_REWARD_PATTERN = re.compile(
    r"\b(?:bonus|increase(?:s|d)?|unlock(?:s|ed)?|"
    r"earn(?:s|ed)?|grant(?:s|ed)?|reward(?:s|ed)?|boost(?:s|ed)?)\b",
    re.IGNORECASE,
)
_TELEMETRY_MODIFIER_REWARD_PATTERN = re.compile(
    r"\b(?:more|extra|additional)\b", re.IGNORECASE
)
_TELEMETRY_QUOTA_SIGNAL_PATTERN = re.compile(
    r"\b(?:api[- ]+)?(?:requests?|calls?|quota|limits?|allowances?|credits?)\b|"
    r"(?<![\w.])\d+(?:\.\d+)?\s*%",
    re.IGNORECASE,
)
_TELEMETRY_MODIFIER_GAP_WORDS = {
    "account",
    "annual",
    "api",
    "call",
    "daily",
    "hourly",
    "monthly",
    "quota",
    "rate",
    "request",
    "usage",
}
_MAX_STRONG_REWARD_SPAN = 160
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


def _bounded_rate_segments(text: str) -> Iterator[Tuple[int, str]]:
    start = 0
    for boundary in _RATE_BOUNDARY_PATTERN.finditer(text):
        segment = text[start : boundary.start()]
        if segment.strip():
            yield start, segment
        start = boundary.end()
    if text[start:].strip():
        yield start, text[start:]


def _token_gap(left: Match[str], right: Match[str]) -> int:
    if left.end() <= right.start():
        return right.start() - left.end()
    if right.end() <= left.start():
        return left.start() - right.end()
    return 0


def _claim_span(
    action: Match[str], count: Match[str], cadence: Match[str]
) -> Tuple[int, int]:
    return (
        min(action.start(), count.start(), cadence.start()),
        max(action.end(), count.end(), cadence.end()),
    )


def _fixed_rate_claims(text: str) -> List[str]:
    """Find count + API action + cadence triples in a bounded sentence window."""
    claims: List[str] = []
    seen: Set[Tuple[int, str]] = set()

    for segment_offset, segment in _bounded_rate_segments(text):
        searchable = _HTML_TAG_PATTERN.sub(" ", segment)
        counts = list(_RATE_NUMBER_PATTERN.finditer(searchable))
        cadences = list(_RATE_CADENCE_PATTERN.finditer(searchable))
        if not counts or not cadences:
            continue
        allowance_counts = [
            count
            for count in counts
            if not any(
                cadence.start() <= count.start() and count.end() <= cadence.end()
                for cadence in cadences
            )
        ]
        if not allowance_counts:
            continue

        for action in _RATE_ACTION_PATTERN.finditer(searchable):
            nearby_counts = [
                count
                for count in allowance_counts
                if _token_gap(action, count) <= _MAX_ACTION_COUNT_GAP
            ]
            if not nearby_counts:
                continue
            count = min(nearby_counts, key=lambda token: _token_gap(action, token))

            bounded_cadences = [
                cadence
                for cadence in cadences
                if _claim_span(action, count, cadence)[1]
                - _claim_span(action, count, cadence)[0]
                <= _MAX_RATE_SPAN
            ]
            if not bounded_cadences:
                continue
            cadence = min(
                bounded_cadences,
                key=lambda token: _claim_span(action, count, token)[1]
                - _claim_span(action, count, token)[0],
            )
            claim_start, claim_end = _claim_span(action, count, cadence)
            claim = re.sub(r"\s+", " ", searchable[claim_start:claim_end]).strip()
            key = (segment_offset + claim_start, claim)
            if key not in seen:
                seen.add(key)
                claims.append(claim)
    return claims


def _telemetry_reward_claims(text: str) -> List[str]:
    """Find attribution identity + reward + quota signals in one bounded sentence."""
    claims: List[str] = []
    seen: Set[Tuple[int, str]] = set()

    for segment_offset, segment in _bounded_rate_segments(text):
        searchable = _HTML_TAG_PATTERN.sub(" ", segment)
        identities = list(_TELEMETRY_IDENTITY_PATTERN.finditer(searchable))
        quota_signals = list(_TELEMETRY_QUOTA_SIGNAL_PATTERN.finditer(searchable))
        strong_rewards = list(_TELEMETRY_STRONG_REWARD_PATTERN.finditer(searchable))
        modifier_rewards = list(_TELEMETRY_MODIFIER_REWARD_PATTERN.finditer(searchable))
        reward_pairs: List[Tuple[int, int]] = []
        for reward in strong_rewards:
            for quota_signal in quota_signals:
                start = min(reward.start(), quota_signal.start())
                end = max(reward.end(), quota_signal.end())
                if end - start <= _MAX_STRONG_REWARD_SPAN:
                    reward_pairs.append((start, end))
        for reward in modifier_rewards:
            for quota_signal in quota_signals:
                if reward.end() > quota_signal.start():
                    continue
                gap = searchable[reward.end() : quota_signal.start()]
                gap_words = re.findall(r"[a-z]+", gap.lower())
                if len(gap) <= 48 and all(
                    word in _TELEMETRY_MODIFIER_GAP_WORDS for word in gap_words
                ):
                    reward_pairs.append((reward.start(), quota_signal.end()))
        for identity in identities:
            candidates = [
                (min(identity.start(), start), max(identity.end(), end))
                for start, end in reward_pairs
                if max(identity.end(), end) - min(identity.start(), start)
                <= _MAX_TELEMETRY_REWARD_SPAN
            ]
            if not candidates:
                continue
            start, end = min(candidates, key=lambda span: span[1] - span[0])
            claim = re.sub(r"\s+", " ", searchable[start:end]).strip()
            key = (segment_offset + start, claim)
            if key not in seen:
                seen.add(key)
                claims.append(claim)
    return claims


def _claim_failures(root: Path, surfaces: Iterable[Path]) -> List[str]:
    failures: List[str] = []
    for path in surfaces:
        text = path.read_text(encoding="utf-8")
        for label, pattern in BLOCKED:
            for match in pattern.finditer(text):
                failures.append(
                    f"{path.relative_to(root)}: {label} matched {match.group(0)!r}"
                )
        for claim in _fixed_rate_claims(text):
            failures.append(
                f"{path.relative_to(root)}: fixed demo rate matched {claim!r}"
            )
        for claim in _telemetry_reward_claims(text):
            failures.append(
                f"{path.relative_to(root)}: telemetry quota reward matched {claim!r}"
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
