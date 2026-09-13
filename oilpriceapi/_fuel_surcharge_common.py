"""Shared request validation and response parsing for fuel surcharges (#101).

The sync ``FuelSurchargeResource`` and the async ``AsyncFuelSurchargeResource``
both go through this module, so the two clients build identical requests and
reject identical responses.

Routes (``V1::FuelSurchargeController`` on the API):

* ``GET /v1/fuel-surcharge``                      latest LTL rate per carrier
* ``GET /v1/fuel-surcharge/{carrier}/latest``     latest LTL rate
* ``GET /v1/fuel-surcharge/{carrier}/history``    weekly LTL series, paginated
* ``GET /v1/fuel-surcharge/parcel``               latest parcel rates by carrier
* ``GET /v1/fuel-surcharge/parcel/{carrier}/latest[?service_level=]``
* ``GET /v1/fuel-surcharge/parcel/{carrier}/history?service_level=``

Every success body is ``{"status": "success", "data": {...}}``. A success body
that does not carry what the route promises raises
``OilPriceAPIError(code="MALFORMED_RESPONSE")``; nothing is defaulted.
"""

import re
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from .exceptions import OilPriceAPIError, ValidationError
from .models import (
    FuelSurchargeHistoryPage,
    FuelSurchargeRate,
    ParcelFuelSurchargeCarrier,
)

__all__ = [
    "MAX_PER_PAGE",
    "LTL_LIST_PATH",
    "PARCEL_LIST_PATH",
    "carrier_path",
    "parcel_carrier_path",
    "validate_slug",
    "history_params",
    "parcel_history_params",
    "parse_rate",
    "parse_rate_list",
    "parse_history",
    "parse_parcel_carrier",
    "parse_parcel_carrier_list",
]

#: The API caps ``per_page`` at 100 and silently clamps anything larger.
MAX_PER_PAGE = 100

LTL_LIST_PATH = "/v1/fuel-surcharge"
PARCEL_LIST_PATH = "/v1/fuel-surcharge/parcel"

# Public carrier slugs are lowercase and hyphenated (``southeastern-freight``);
# parcel service levels use underscores (``international_air_export``). Either
# way a path segment or query value made of anything else -- a slash, a ``?``,
# whitespace, ``..`` -- is refused before a request is built.
_SEGMENT = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9_-]*[A-Za-z0-9])?$")

M = TypeVar("M", bound=BaseModel)


def validate_slug(value: Any, field: str) -> str:
    """Return ``value`` if it is a safe carrier slug / service level.

    Raises:
        ValidationError: locally, with ``status_code=None`` -- no request is sent.
    """
    if not isinstance(value, str) or not _SEGMENT.match(value):
        raise ValidationError(
            f"{field} must be a non-empty slug of letters, digits, '-' or '_' "
            f"(for example 'odfl' or 'ground'), got {value!r}",
            field=field,
            value=value,
            status_code=None,
        )
    return value


def carrier_path(carrier: str, action: str) -> str:
    return f"/v1/fuel-surcharge/{validate_slug(carrier, 'carrier')}/{action}"


def parcel_carrier_path(carrier: str, action: str) -> str:
    return f"/v1/fuel-surcharge/parcel/{validate_slug(carrier, 'carrier')}/{action}"


def _positive_int(value: Any, field: str, maximum: Optional[int] = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1 or (
        maximum is not None and value > maximum
    ):
        bound = f"between 1 and {maximum}" if maximum is not None else "at least 1"
        raise ValidationError(
            f"{field} must be an integer {bound}, got {value!r}. The API silently "
            f"clamps out-of-range values, so the SDK refuses them instead of "
            f"returning a different page than the one requested.",
            field=field,
            value=value,
            status_code=None,
        )
    return value


def history_params(page: Optional[int], per_page: Optional[int]) -> Dict[str, Any]:
    """Build LTL history query params; omitted arguments are not sent."""
    return _pagination({}, page, per_page)


def parcel_history_params(
    service_level: Any, page: Optional[int], per_page: Optional[int]
) -> Dict[str, Any]:
    """Build parcel history query params. ``service_level`` is required by the API."""
    return _pagination(
        {"service_level": validate_slug(service_level, "service_level")}, page, per_page
    )


def _pagination(
    params: Dict[str, Any], page: Optional[int], per_page: Optional[int]
) -> Dict[str, Any]:
    if page is not None:
        params["page"] = _positive_int(page, "page")
    if per_page is not None:
        params["per_page"] = _positive_int(per_page, "per_page", MAX_PER_PAGE)
    return params


# --- response parsing ----------------------------------------------------------


def _malformed(subject: str, detail: str, response: Any) -> OilPriceAPIError:
    return OilPriceAPIError(
        f"Malformed {subject} response: {detail}",
        code="MALFORMED_RESPONSE",
        raw_body=response,
    )


def _data(response: Any, subject: str) -> Dict[str, Any]:
    data = response.get("data") if isinstance(response, dict) else None
    if not isinstance(data, dict):
        raise _malformed(subject, "expected a 'data' object", response)
    return data


def _build(model: Type[M], value: Any, subject: str, response: Any) -> M:
    try:
        return model.model_validate(value)
    except PydanticValidationError as error:
        detail = "; ".join(
            "%s: %s" % (".".join(str(part) for part in err["loc"]) or "<root>", err["msg"])
            for err in error.errors()
        )
        raise _malformed(subject, detail, response) from None


def _check_rate(
    rate: FuelSurchargeRate,
    *,
    mode: str,
    subject: str,
    response: Any,
    carrier: Optional[str] = None,
    service_level: Optional[str] = None,
) -> FuelSurchargeRate:
    if rate.mode != mode:
        raise _malformed(subject, f"expected mode {mode!r}, got {rate.mode!r}", response)
    if carrier is not None and rate.carrier.lower() != carrier.lower():
        raise _malformed(subject, f"expected carrier {carrier!r}, got {rate.carrier!r}", response)
    if mode == "parcel" and not rate.service_level:
        raise _malformed(subject, "parcel rate is missing service_level", response)
    if service_level is not None and (rate.service_level or "").lower() != service_level.lower():
        raise _malformed(
            subject,
            f"expected service_level {service_level!r}, got {rate.service_level!r}",
            response,
        )
    return rate


def parse_rate(
    response: Any,
    *,
    mode: str,
    subject: str,
    carrier: Optional[str] = None,
    service_level: Optional[str] = None,
) -> FuelSurchargeRate:
    """One rate object (``/latest``)."""
    rate = _build(FuelSurchargeRate, _data(response, subject), subject, response)
    return _check_rate(
        rate,
        mode=mode,
        subject=subject,
        response=response,
        carrier=carrier,
        service_level=service_level,
    )


def _collection(response: Any, key: str, subject: str) -> List[Any]:
    rows = _data(response, subject).get(key)
    if not isinstance(rows, list):
        raise _malformed(subject, f"expected a '{key}' list", response)
    return rows


def parse_rate_list(response: Any, *, subject: str) -> List[FuelSurchargeRate]:
    """``data.carriers`` from the LTL list route. An empty list is valid."""
    rows = _collection(response, "carriers", subject)
    return [
        _check_rate(
            _build(FuelSurchargeRate, row, subject, response),
            mode="ltl",
            subject=subject,
            response=response,
        )
        for row in rows
    ]


def parse_history(
    response: Any,
    *,
    mode: str,
    subject: str,
    carrier: str,
    service_level: Optional[str] = None,
) -> FuelSurchargeHistoryPage:
    """``data.history`` + ``data.meta`` from a history route."""
    data = _data(response, subject)
    if not isinstance(data.get("history"), list):
        raise _malformed(subject, "expected a 'history' list", response)
    if not isinstance(data.get("meta"), dict):
        raise _malformed(subject, "expected a 'meta' pagination object", response)
    page = _build(FuelSurchargeHistoryPage, data, subject, response)
    for rate in page.history:
        _check_rate(
            rate,
            mode=mode,
            subject=subject,
            response=response,
            carrier=carrier,
            service_level=service_level,
        )
    return page


def _check_parcel_carrier(
    carrier: ParcelFuelSurchargeCarrier, subject: str, response: Any
) -> ParcelFuelSurchargeCarrier:
    if carrier.mode != "parcel":
        raise _malformed(subject, f"expected mode 'parcel', got {carrier.mode!r}", response)
    for rate in carrier.service_levels:
        _check_rate(rate, mode="parcel", subject=subject, response=response, carrier=carrier.carrier)
    return carrier


def parse_parcel_carrier(response: Any, *, subject: str, carrier: str) -> ParcelFuelSurchargeCarrier:
    """A parcel carrier with its latest rate per service level."""
    data = _data(response, subject)
    if not isinstance(data.get("service_levels"), list):
        raise _malformed(subject, "expected a 'service_levels' list", response)
    parsed = _build(ParcelFuelSurchargeCarrier, data, subject, response)
    if parsed.carrier.lower() != carrier.lower():
        raise _malformed(subject, f"expected carrier {carrier!r}, got {parsed.carrier!r}", response)
    return _check_parcel_carrier(parsed, subject, response)


def parse_parcel_carrier_list(response: Any, *, subject: str) -> List[ParcelFuelSurchargeCarrier]:
    """``data.carriers`` from the parcel list route. An empty list is valid."""
    rows = _collection(response, "carriers", subject)
    return [
        _check_parcel_carrier(
            _build(ParcelFuelSurchargeCarrier, row, subject, response), subject, response
        )
        for row in rows
    ]
