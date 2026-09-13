"""Shared request building and response parsing for the calculated-metrics
routes (``/v1/spreads/*`` and ``/v1/indicators/*``, #99).

The sync and async resources are thin wrappers over this module: each public
method builds a :class:`MetricsCall` here (path, query parameters, parser),
sends it with its own client, and hands the decoded body back to the parser.
That keeps validation, parameter names and envelope handling identical across
both clients by construction rather than by copy.

Two rules are enforced here and nowhere else:

* **Arguments are validated before any request is sent.** A blank selector or
  an unparseable date raises ``ValidationError`` locally, with
  ``status_code=None`` because nothing was sent. The API would otherwise
  fall back to a default window, or answer an unknown selector on a history
  route with an empty HTTP 200 -- neither is a result the caller asked for.
* **A malformed success body raises.** A 200 whose envelope, collection or
  record does not match the typed model raises
  ``OilPriceAPIError(code="MALFORMED_RESPONSE")`` carrying the raw body. Nothing
  is defaulted to ``0``, ``""`` or "now".
"""

import json
from datetime import date, datetime
from typing import Any, Callable, Dict, Generic, List, Optional, Sequence, Type, TypeVar, Union

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from ..exceptions import OilPriceAPIError, ValidationError
from ..metrics_models import (
    BasisSpread,
    BasisSpreadHistory,
    CftcPositioning,
    CftcPositioningHistory,
    CrackSpread,
    CrackSpreadAll,
    CrackSpreadHistory,
    CurveStructure,
    FuelSwitching,
    FuelSwitchingHistory,
    GasoilCrackSpread,
    MarketAnnotations,
    MarketAnnotationsBatch,
    PhysicalPremium,
    PhysicalPremiumHistory,
    PriceContext,
    RefineryMargin,
    RefineryMarginHistory,
    StorageAnalytics,
)
from ..resource_validators import format_date

T = TypeVar("T")
M = TypeVar("M", bound=BaseModel)

DateInput = Union[str, date, datetime]

#: ``/v1/indicators/annotations/batch`` annotates only the first 20 codes and
#: silently drops the rest while still reporting ``total_codes``.
ANNOTATIONS_BATCH_MAX_CODES = 20


class MetricsCall(Generic[T]):
    """One GET request against a calculated-metrics route."""

    __slots__ = ("path", "params", "subject", "parse")

    def __init__(
        self,
        path: str,
        params: Dict[str, str],
        subject: str,
        parse: Callable[[Any], T],
    ) -> None:
        self.path = path
        self.params = params
        self.subject = subject
        self.parse = parse


def run_sync(client: Any, call: "MetricsCall[T]") -> T:
    """Send ``call`` with a sync client and parse the body."""
    try:
        response = client.request(method="GET", path=call.path, params=call.params)
    except json.JSONDecodeError as exc:
        raise _malformed(call.subject, None, "the body is not valid JSON") from exc
    return call.parse(response)


async def run_async(client: Any, call: "MetricsCall[T]") -> T:
    """Send ``call`` with an async client and parse the body."""
    try:
        response = await client.request(method="GET", path=call.path, params=call.params)
    except json.JSONDecodeError as exc:
        raise _malformed(call.subject, None, "the body is not valid JSON") from exc
    return call.parse(response)


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def _malformed(subject: str, response: Any, detail: str) -> OilPriceAPIError:
    return OilPriceAPIError(
        "Malformed %s response: %s" % (subject, detail),
        code="MALFORMED_RESPONSE",
        raw_body=response,
    )


def _envelope_data(response: Any, subject: str) -> Dict[str, Any]:
    if not isinstance(response, dict):
        raise _malformed(subject, response, "expected a JSON object")
    status = response.get("status")
    if status is not None and status != "success":
        raise _malformed(subject, response, "status is %r, not 'success'" % (status,))
    data = response.get("data")
    if not isinstance(data, dict):
        raise _malformed(subject, response, "expected a 'data' object")
    return data


def _build(model: Type[M], payload: Dict[str, Any], response: Any, subject: str) -> M:
    try:
        return model.model_validate(payload)
    except PydanticValidationError as exc:
        first = exc.errors()[0]
        location = ".".join(str(part) for part in first.get("loc", ())) or "record"
        raise _malformed(subject, response, "%s: %s" % (location, first.get("msg"))) from exc


def _object_parser(model: Type[M], subject: str) -> Callable[[Any], M]:
    def parse(response: Any) -> M:
        return _build(model, _envelope_data(response, subject), response, subject)

    return parse


def _collection_parser(model: Type[M], key: str, subject: str) -> Callable[[Any], List[M]]:
    def parse(response: Any) -> List[M]:
        rows = _envelope_data(response, subject).get(key)
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise _malformed(subject, response, "expected a '%s' list of records" % key)
        return [_build(model, row, response, subject) for row in rows]

    return parse


def _object(path: str, params: Dict[str, str], model: Type[M], subject: str) -> "MetricsCall[M]":
    return MetricsCall(path, params, subject, _object_parser(model, subject))


def _collection(path: str, key: str, model: Type[M], subject: str) -> "MetricsCall[List[M]]":
    return MetricsCall(path, {}, subject, _collection_parser(model, key, subject))


# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------


def _refuse(message: str, field: str, value: Any) -> ValidationError:
    """Build a local refusal.

    Matches ``_url._reject``: a ``ValidationError`` (so the documented
    ``except OilPriceAPIError`` catch-all sees it) with ``status_code=None``,
    because no request was sent and there is no HTTP status to report (#123).
    """
    return ValidationError(message=message, field=field, value=value, status_code=None)


def _text(name: str, value: Any, *, required: bool) -> Optional[str]:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip():
        raise _refuse("%s must be a non-empty string" % name, name, value)
    return value.strip()


def _params(**values: Optional[str]) -> Dict[str, str]:
    return {key: value for key, value in values.items() if value is not None}


def _date(name: str, value: Optional[DateInput]) -> Optional[str]:
    if value is None:
        return None
    try:
        return format_date(value)
    except ValueError as exc:
        # format_date is shared with older resources and raises ValueError;
        # these new methods report the refusal in the SDK's own error type.
        raise _refuse("%s: %s" % (name, exc), name, value) from exc


def _window(start_date: Optional[DateInput], end_date: Optional[DateInput]) -> Dict[str, str]:
    start = _date("start_date", start_date)
    end = _date("end_date", end_date)
    if start is not None and end is not None and start > end:
        raise _refuse(
            "start_date (%s) must be on or before end_date (%s)" % (start, end),
            "start_date",
            start_date,
        )
    return _params(start_date=start, end_date=end)


# ---------------------------------------------------------------------------
# Spreads
# ---------------------------------------------------------------------------


def crack(spread_type: Optional[str] = None, crude: Optional[str] = None) -> "MetricsCall[CrackSpread]":
    params = _params(
        type=_text("spread_type", spread_type, required=False),
        crude=_text("crude", crude, required=False),
    )
    return _object("/v1/spreads/crack", params, CrackSpread, "crack spread")


def crack_historical(
    spread_type: Optional[str] = None,
    crude: Optional[str] = None,
    start_date: Optional[DateInput] = None,
    end_date: Optional[DateInput] = None,
) -> "MetricsCall[CrackSpreadHistory]":
    params = _params(
        type=_text("spread_type", spread_type, required=False),
        crude=_text("crude", crude, required=False),
    )
    params.update(_window(start_date, end_date))
    return _object("/v1/spreads/crack/historical", params, CrackSpreadHistory, "crack spread history")


def crack_all(crude: Optional[str] = None) -> "MetricsCall[CrackSpreadAll]":
    params = _params(crude=_text("crude", crude, required=False))
    return _object("/v1/spreads/crack/all", params, CrackSpreadAll, "crack spread list")


def gasoil_crack() -> "MetricsCall[GasoilCrackSpread]":
    return _object("/v1/spreads/gasoil-crack", {}, GasoilCrackSpread, "gasoil crack")


def basis(pair: str) -> "MetricsCall[BasisSpread]":
    params = _params(pair=_text("pair", pair, required=True))
    return _object("/v1/spreads/basis", params, BasisSpread, "basis spread")


def basis_historical(
    pair: str,
    start_date: Optional[DateInput] = None,
    end_date: Optional[DateInput] = None,
) -> "MetricsCall[BasisSpreadHistory]":
    params = _params(pair=_text("pair", pair, required=True))
    params.update(_window(start_date, end_date))
    return _object("/v1/spreads/basis/historical", params, BasisSpreadHistory, "basis spread history")


def basis_all() -> "MetricsCall[List[BasisSpread]]":
    return _collection("/v1/spreads/basis/all", "spreads", BasisSpread, "basis spread list")


def curve_structure(commodity: str) -> "MetricsCall[CurveStructure]":
    params = _params(commodity=_text("commodity", commodity, required=True))
    return _object("/v1/spreads/curve-structure", params, CurveStructure, "curve structure")


def curve_structure_all() -> "MetricsCall[List[CurveStructure]]":
    return _collection(
        "/v1/spreads/curve-structure/all", "commodities", CurveStructure, "curve structure list"
    )


def margin(index: Optional[str] = None) -> "MetricsCall[RefineryMargin]":
    params = _params(index=_text("index", index, required=False))
    return _object("/v1/spreads/margin", params, RefineryMargin, "refinery margin")


def margin_historical(
    index: Optional[str] = None,
    start_date: Optional[DateInput] = None,
    end_date: Optional[DateInput] = None,
) -> "MetricsCall[RefineryMarginHistory]":
    params = _params(index=_text("index", index, required=False))
    params.update(_window(start_date, end_date))
    return _object(
        "/v1/spreads/margin/historical", params, RefineryMarginHistory, "refinery margin history"
    )


def margin_all() -> "MetricsCall[List[RefineryMargin]]":
    return _collection("/v1/spreads/margin/all", "margins", RefineryMargin, "refinery margin list")


def physical_premium(commodity: Optional[str] = None) -> "MetricsCall[PhysicalPremium]":
    params = _params(commodity=_text("commodity", commodity, required=False))
    return _object("/v1/spreads/physical-premium", params, PhysicalPremium, "physical premium")


def physical_premium_historical(
    commodity: Optional[str] = None,
    start_date: Optional[DateInput] = None,
    end_date: Optional[DateInput] = None,
) -> "MetricsCall[PhysicalPremiumHistory]":
    params = _params(commodity=_text("commodity", commodity, required=False))
    params.update(_window(start_date, end_date))
    return _object(
        "/v1/spreads/physical-premium/historical",
        params,
        PhysicalPremiumHistory,
        "physical premium history",
    )


def physical_premium_all() -> "MetricsCall[List[PhysicalPremium]]":
    return _collection(
        "/v1/spreads/physical-premium/all", "premiums", PhysicalPremium, "physical premium list"
    )


# ---------------------------------------------------------------------------
# Indicators
# ---------------------------------------------------------------------------


def fuel_switching(gas: Optional[str] = None, crude: Optional[str] = None) -> "MetricsCall[FuelSwitching]":
    params = _params(
        gas=_text("gas", gas, required=False),
        crude=_text("crude", crude, required=False),
    )
    return _object("/v1/indicators/fuel-switching", params, FuelSwitching, "fuel switching")


def fuel_switching_historical(
    gas: Optional[str] = None,
    crude: Optional[str] = None,
    start_date: Optional[DateInput] = None,
    end_date: Optional[DateInput] = None,
) -> "MetricsCall[FuelSwitchingHistory]":
    params = _params(
        gas=_text("gas", gas, required=False),
        crude=_text("crude", crude, required=False),
    )
    params.update(_window(start_date, end_date))
    return _object(
        "/v1/indicators/fuel-switching/historical",
        params,
        FuelSwitchingHistory,
        "fuel switching history",
    )


def price_context(code: str, related_spreads: bool = False) -> "MetricsCall[PriceContext]":
    params = _params(code=_text("code", code, required=True))
    if related_spreads:
        params["spreads"] = "related"
    return _object("/v1/indicators/price-context", params, PriceContext, "price context")


def storage_analytics(location: Optional[str] = None) -> "MetricsCall[StorageAnalytics]":
    params = _params(location=_text("location", location, required=False))
    return _object("/v1/indicators/storage-analytics", params, StorageAnalytics, "storage analytics")


def storage_analytics_all() -> "MetricsCall[List[StorageAnalytics]]":
    return _collection(
        "/v1/indicators/storage-analytics/all", "locations", StorageAnalytics, "storage analytics list"
    )


def annotations(code: str) -> "MetricsCall[MarketAnnotations]":
    params = _params(code=_text("code", code, required=True))
    return _object("/v1/indicators/annotations", params, MarketAnnotations, "market annotations")


def annotations_batch(codes: Sequence[str]) -> "MetricsCall[MarketAnnotationsBatch]":
    if isinstance(codes, str) or not isinstance(codes, Sequence):
        raise _refuse("codes must be a list of commodity codes", "codes", codes)
    if not codes:
        raise _refuse("codes must contain at least one commodity code", "codes", codes)
    if len(codes) > ANNOTATIONS_BATCH_MAX_CODES:
        raise _refuse(
            "codes accepts at most %d commodity codes per call (got %d); the API "
            "silently ignores the rest" % (ANNOTATIONS_BATCH_MAX_CODES, len(codes)),
            "codes",
            codes,
        )
    cleaned: List[str] = []
    for code in codes:
        if not isinstance(code, str) or not code.strip():
            raise _refuse("each code must be a non-empty string", "codes", code)
        text = code.strip()
        if "," in text:
            raise _refuse("commodity codes may not contain ',' (got %r)" % text, "codes", text)
        cleaned.append(text)
    params = {"codes": ",".join(cleaned)}
    return _object(
        "/v1/indicators/annotations/batch", params, MarketAnnotationsBatch, "market annotations batch"
    )


def cftc_positioning(commodity: Optional[str] = None) -> "MetricsCall[CftcPositioning]":
    params = _params(commodity=_text("commodity", commodity, required=False))
    return _object("/v1/indicators/cftc-positioning", params, CftcPositioning, "CFTC positioning")


def cftc_positioning_historical(
    commodity: Optional[str] = None,
    start_date: Optional[DateInput] = None,
    end_date: Optional[DateInput] = None,
) -> "MetricsCall[CftcPositioningHistory]":
    params = _params(commodity=_text("commodity", commodity, required=False))
    params.update(_window(start_date, end_date))
    return _object(
        "/v1/indicators/cftc-positioning/historical",
        params,
        CftcPositioningHistory,
        "CFTC positioning history",
    )


def cftc_positioning_all() -> "MetricsCall[List[CftcPositioning]]":
    return _collection(
        "/v1/indicators/cftc-positioning/all", "commodities", CftcPositioning, "CFTC positioning list"
    )
