"""
Shared validation helpers and constants for resource classes.

Both sync (resources/) and async (async_resources.py) classes import from here
so validation logic lives in one place and the only difference between sync and
async resources is the HTTP call (sync vs await).
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Mapping, Union

# ---------------------------------------------------------------------------
# Alert operators
# ---------------------------------------------------------------------------

VALID_OPERATORS = [
    'greater_than',
    'less_than',
    'equals',
    'greater_than_or_equal',
    'less_than_or_equal',
]


# ---------------------------------------------------------------------------
# Date formatting
# ---------------------------------------------------------------------------

_ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def format_date(date_input: Union[str, date, datetime]) -> str:
    """Normalize a date/datetime/str value to a strict ISO-8601 date.

    Used by futures, storage, rig_counts, and bunker_fuels resources to
    convert the flexible ``start_date`` / ``end_date`` parameters before
    passing them as query-string values.

    Args:
        date_input: A ``YYYY-MM-DD`` string, a ``datetime.date``, or a
            ``datetime.datetime`` object. Datetime values are reduced to
            their calendar date.

    Returns:
        An ISO-8601 date string, e.g. ``"2024-01-15"``.

    Raises:
        ValueError: If *date_input* is not a supported type, is not exactly
            ``YYYY-MM-DD``, or is not a real calendar date.
    """
    if isinstance(date_input, str):
        if not _ISO_DATE_PATTERN.fullmatch(date_input):
            raise ValueError("Date strings must use YYYY-MM-DD format")
        try:
            date.fromisoformat(date_input)
        except ValueError:
            raise ValueError(
                "Date strings must use YYYY-MM-DD format and contain a valid calendar date"
            )
        return date_input
    elif isinstance(date_input, datetime):
        return date_input.date().isoformat()
    elif isinstance(date_input, date):
        return date_input.isoformat()
    else:
        raise ValueError(
            "Invalid date type; dates must be YYYY-MM-DD strings, "
            "datetime.date, or datetime.datetime values"
        )


# ---------------------------------------------------------------------------
# Commodity catalog search
# ---------------------------------------------------------------------------

_SEARCH_FIELDS = (
    "code",
    "name",
    "category",
    "description",
    "currency",
    "unit",
    "source",
)
_SEARCH_SEPARATOR_PATTERN = re.compile(r"[^a-z0-9]+")


def _normalize_search_text(value: Any) -> str:
    return _SEARCH_SEPARATOR_PATTERN.sub(" ", str(value).lower()).strip()


def extract_commodity_catalog(value: Any) -> List[Dict[str, Any]]:
    """Normalize direct and nested API catalog response shapes to a list."""
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, Mapping)]
    if isinstance(value, Mapping):
        if "commodities" in value:
            return extract_commodity_catalog(value["commodities"])
        if "data" in value:
            return extract_commodity_catalog(value["data"])
    return []


def search_commodity_catalog(
    catalog: Iterable[Mapping[str, Any]],
    query: str,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Search a freshly fetched commodity catalog without a frozen code list.

    Results are ranked by exact/prefix code matches, whole-query matches, then
    token coverage across code, name, category, description, currency, unit,
    and source. Non-mapping catalog entries are ignored.
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Commodity search query must be a non-empty string")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("Commodity search limit must be an integer from 1 to 100")

    normalized_query = _normalize_search_text(query)
    query_tokens = normalized_query.split()
    ranked = []

    for index, item in enumerate(catalog):
        if not isinstance(item, Mapping):
            continue

        normalized_fields = {
            field: _normalize_search_text(item.get(field, ""))
            for field in _SEARCH_FIELDS
        }
        code = normalized_fields["code"]
        searchable = " ".join(value for value in normalized_fields.values() if value)
        token_hits = sum(token in searchable for token in query_tokens)
        if normalized_query not in searchable and token_hits == 0:
            continue

        score = token_hits * 100
        if normalized_query == code:
            score += 10_000
        elif code.startswith(normalized_query):
            score += 5_000
        elif normalized_query in code:
            score += 3_000
        if normalized_query == normalized_fields["name"]:
            score += 2_000
        elif normalized_query in normalized_fields["name"]:
            score += 1_000

        ranked.append(
            (
                -score,
                str(item.get("code", "")),
                index,
                dict(item),
            )
        )

    ranked.sort(key=lambda result: result[:3])
    return [result[3] for result in ranked[:limit]]


# ---------------------------------------------------------------------------
# Well production API numbers
# ---------------------------------------------------------------------------

API_NUMBER_LENGTH = 14


def normalize_api_number(api_number: str) -> str:
    """Normalise a well API number to the 14-digit form the API expects.

    Strips any non-digit separators (dashes, spaces) and validates the
    length client-side so callers get an immediate, descriptive error
    instead of a 400 round-trip.

    Args:
        api_number: A well API number, e.g. ``"42285343290000"`` or
            ``"42-285-34329-00-00"``.

    Returns:
        The 14-digit API number string.

    Raises:
        ValueError: If the value does not contain exactly 14 digits.
    """
    digits = "".join(ch for ch in str(api_number) if ch.isdigit())
    if len(digits) != API_NUMBER_LENGTH:
        raise ValueError(
            f"API number must be {API_NUMBER_LENGTH} digits, "
            f"got {len(digits)} from {api_number!r}"
        )
    return digits
