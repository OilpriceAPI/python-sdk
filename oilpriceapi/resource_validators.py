"""
Shared validation helpers and constants for resource classes.

Both sync (resources/) and async (async_resources.py) classes import from here
so validation logic lives in one place and the only difference between sync and
async resources is the HTTP call (sync vs await).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Union


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

def format_date(date_input: Union[str, date, datetime]) -> str:
    """Normalise a date/datetime/str value to an ISO-8601 date string.

    Used by futures, storage, rig_counts, and bunker_fuels resources to
    convert the flexible ``start_date`` / ``end_date`` parameters before
    passing them as query-string values.

    Args:
        date_input: A string (returned as-is), a ``datetime.date``, or a
            ``datetime.datetime`` object.

    Returns:
        An ISO-8601 date string, e.g. ``"2024-01-15"``.

    Raises:
        ValueError: If *date_input* is not one of the supported types.
    """
    if isinstance(date_input, str):
        return date_input
    elif isinstance(date_input, datetime):
        return date_input.date().isoformat()
    elif isinstance(date_input, date):
        return date_input.isoformat()
    else:
        raise ValueError(f"Invalid date type: {type(date_input)}")
