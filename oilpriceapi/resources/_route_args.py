"""Argument shaping shared by the sync and async storage and bunker resources.

Each guard runs before any request is sent, so a missing or invalid argument
raises ``ValidationError(status_code=None)`` instead of a confusing 400/404.
"""

from typing import Any, Dict, Optional

from ..exceptions import ValidationError

# GET /v1/storage/history/:code accepts exactly these (StorageController#valid_storage_code?).
STORAGE_HISTORY_CODES = (
    "CUSHING_STORAGE",
    "US_SPR",
    "SINGAPORE_STORAGE_TOTAL",
    "ARA_STORAGE_TOTAL",
)
_STORAGE_ALIASES = {"CUSHING": "CUSHING_STORAGE", "SPR": "US_SPR"}
STORAGE_HISTORY_PERIODS = ("7d", "30d", "90d", "1y", "all")

# Prefix of the series code each grade appears under in historical_data,
# e.g. VLSFO_SGSIN_USD, MGO_05S_SGSIN_USD, HFO_380_SGSIN_USD.
_BUNKER_GRADE_PREFIX = {
    "VLSFO": "VLSFO_",
    "MGO": "MGO_",
    "HFO380": "HFO_380_",
    "HFO_380": "HFO_380_",
    "IFO380": "HFO_380_",
}


def storage_history_code(code: str) -> str:
    normalized = (code or "").strip().upper()
    normalized = _STORAGE_ALIASES.get(normalized, normalized)
    if normalized not in STORAGE_HISTORY_CODES:
        raise ValidationError(
            f"Unknown storage code {code!r}. Use one of "
            f"{', '.join(STORAGE_HISTORY_CODES)} (or 'cushing' / 'spr').",
            field="code",
            value=code,
            status_code=None,
        )
    return normalized


def storage_history_period(period: str) -> str:
    if period not in STORAGE_HISTORY_PERIODS:
        raise ValidationError(
            f"Unknown period {period!r}. Use one of {', '.join(STORAGE_HISTORY_PERIODS)}.",
            field="period",
            value=period,
            status_code=None,
        )
    return period


def bunker_port_code(port: str) -> str:
    normalized = (port or "").strip().upper()
    if not normalized:
        raise ValidationError(
            "A port code is required (e.g. 'SIN' or 'SGSIN').",
            field="port",
            value=port,
            status_code=None,
        )
    return normalized


def bunker_spread_params(from_port: str, to_port: str, grade: Optional[str]) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "from": bunker_port_code(from_port),
        "to": bunker_port_code(to_port),
    }
    if grade:
        params["grade"] = grade.upper()
    return params


def bunker_grade_prefix(fuel_type: Optional[str]) -> Optional[str]:
    if not fuel_type:
        return None
    prefix = _BUNKER_GRADE_PREFIX.get(fuel_type.strip().upper())
    if prefix is None:
        raise ValidationError(
            f"Unknown fuel_type {fuel_type!r}. Use 'vlsfo', 'mgo' or 'hfo380'.",
            field="fuel_type",
            value=fuel_type,
            status_code=None,
        )
    return prefix


def filter_bunker_history(data: Any, prefix: Optional[str]) -> Any:
    """Keep only ``historical_data`` records for one grade (see ``bunker_grade_prefix``)."""
    if prefix is None or not isinstance(data, dict):
        return data
    records = data.get("historical_data") or []
    return {
        **data,
        "historical_data": [
            r for r in records if str(r.get("code", "")).startswith(prefix)
        ],
    }
