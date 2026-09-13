"""
Typed models for the calculated-metrics routes: ``/v1/spreads/*`` and
``/v1/indicators/*`` (#99).

Every model is typed from the production wire shape (captured 2026-09-13) and
from the serializers in ``app/services/calculated_metrics/`` on the API.

Conventions, applied throughout:

* A key the server always emits is **required**. If the server can emit it as
  ``null`` it is ``Optional[...]`` *without a default*, so a body that drops the
  key fails validation instead of being silently read as ``None``.
* A key the server only emits conditionally (for example ``data_stale``, the
  ``change_*`` deltas, or the inner fields of a block that is ``{}`` when there
  is too little history) is ``Optional[...] = None``. ``None`` there means "the
  server did not send it", never "false" or "zero".
* Values are kept exactly as sent: no rounding, unit conversion or clamping.
  Timestamps parse to timezone-aware ``datetime``; calendar dates to ``date``.
* Unknown keys are preserved (``extra="allow"``) so a field the API adds later
  is not dropped on the floor.
"""

from datetime import date, datetime
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "BasisSpread",
    "BasisSpreadHistory",
    "BasisSpreadPoint",
    "CftcCommercialPosition",
    "CftcPositioning",
    "CftcPositioningHistory",
    "CftcPositioningPoint",
    "CftcPositions",
    "CftcSpeculativePosition",
    "CrackSpread",
    "CrackSpreadAll",
    "CrackSpreadHistory",
    "CrackSpreadPoint",
    "CurveMonth",
    "CurveStructure",
    "CurveStructureSpreads",
    "EnergyEquivalent",
    "FuelSwitching",
    "FuelSwitchingComponents",
    "FuelSwitchingContext",
    "FuelSwitchingHistory",
    "FuelSwitchingPoint",
    "GasoilCrackConversion",
    "GasoilCrackLeg",
    "GasoilCrackSpread",
    "HistoryCoverage",
    "HistoryPeriod",
    "MarginCrudeInput",
    "MarginProduct",
    "MarketAnnotation",
    "MarketAnnotations",
    "MarketAnnotationsBatch",
    "MetricChanges",
    "OilParity",
    "PhysicalPremium",
    "PhysicalPremiumComponents",
    "PhysicalPremiumHistory",
    "PhysicalPremiumLeg",
    "PhysicalPremiumPoint",
    "PriceContext",
    "PriceContextDetail",
    "PricedLeg",
    "RefineryMargin",
    "RefineryMarginHistory",
    "RefineryMarginPoint",
    "RelatedSpread",
    "StorageAnalytics",
    "StorageAnomalies",
    "StorageCurrent",
    "StorageDrawRate",
    "StorageRange",
    "StorageSeasonal",
]


class _WireModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")


# ---------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------


class MetricChanges(_WireModel):
    """1-day / 1-week / 1-month deltas.

    The server only emits a pair when a prior value exists for that horizon,
    so every field is optional and an absent horizon stays ``None``.
    """

    change_1d: Optional[float] = None
    change_1d_pct: Optional[float] = None
    change_1w: Optional[float] = None
    change_1w_pct: Optional[float] = None
    change_1m: Optional[float] = None
    change_1m_pct: Optional[float] = None


class HistoryPeriod(_WireModel):
    """The window the server *applied* (it echoes defaults and its 2-year cap)."""

    start: date
    end: date


class HistoryCoverage(_WireModel):
    """What a history response actually contains, as opposed to what was asked."""

    from_: Optional[date] = Field(..., alias="from")
    to: Optional[date]
    observations: int
    complete: bool


class PricedLeg(_WireModel):
    """One priced input to a spread, e.g. ``{"code", "price", "unit"}``."""

    code: str
    price: float
    unit: str


# ---------------------------------------------------------------------------
# /v1/spreads/crack*
# ---------------------------------------------------------------------------


class CrackSpread(_WireModel):
    """``GET /v1/spreads/crack`` and each entry of ``/crack/all``.

    ``components`` is keyed ``crude`` + ``product`` for single-product cracks
    and ``crude`` + ``gasoline`` + ``diesel`` for the 3-2-1 composite.
    """

    spread_type: str
    crude_benchmark: str
    value: float
    unit: str
    components: Dict[str, PricedLeg]
    timestamp: datetime
    changes: MetricChanges
    data_stale: Optional[bool] = None
    stale_warning: Optional[str] = None


class CrackSpreadAll(_WireModel):
    """``GET /v1/spreads/crack/all``."""

    crude_benchmark: str
    spreads: List[CrackSpread]


class CrackSpreadPoint(_WireModel):
    """One day of crack history. The 3-2-1 composite carries ``gasoline`` and
    ``diesel``; single-product cracks carry ``product``."""

    date: date
    value: float
    crude: float
    product: Optional[float] = None
    gasoline: Optional[float] = None
    diesel: Optional[float] = None


class CrackSpreadHistory(_WireModel):
    """``GET /v1/spreads/crack/historical``."""

    spread_type: str
    crude_benchmark: str
    period: HistoryPeriod
    coverage: HistoryCoverage
    data_revised_at: Optional[datetime]
    count: int
    data: List[CrackSpreadPoint]


class GasoilCrackLeg(_WireModel):
    """A futures leg of the European gasoil crack, with its contract month."""

    code: str
    contract_month: Optional[str]
    updated_at: datetime
    price: float
    unit: str
    settlement_date: Optional[date] = None


class GasoilCrackConversion(_WireModel):
    """The tonne-to-barrel conversion the server applied."""

    barrels_per_tonne: float
    basis: str
    gasoil_usd_per_bbl: float


class GasoilCrackSpread(_WireModel):
    """``GET /v1/spreads/gasoil-crack`` (ICE Low Sulphur Gasoil vs ICE Brent)."""

    spread_type: str
    name: str
    value: float
    unit: str
    components: Dict[str, GasoilCrackLeg]
    conversion: GasoilCrackConversion
    timestamp: datetime
    updated_at: datetime
    data_stale: Optional[bool] = None
    stale_warning: Optional[str] = None


# ---------------------------------------------------------------------------
# /v1/spreads/basis*
# ---------------------------------------------------------------------------


class BasisSpread(_WireModel):
    """``GET /v1/spreads/basis`` and each entry of ``/basis/all``.

    ``components`` maps each leg's commodity code to its price.
    ``negative_streak_days`` is only sent for pairs that track it (WAHA_HH).
    """

    pair: str
    spread_name: str
    value: float
    unit: str
    components: Dict[str, float]
    signal: str
    timestamp: datetime
    percentile_1y: Optional[int]
    changes: MetricChanges
    negative_streak_days: Optional[int] = None
    data_stale: Optional[bool] = None
    stale_warning: Optional[str] = None


class BasisSpreadPoint(_WireModel):
    """One day of basis history: ``value = code_a - code_b``."""

    date: date
    value: float
    code_a: float
    code_b: float


class BasisSpreadHistory(_WireModel):
    """``GET /v1/spreads/basis/historical``."""

    pair: str
    period: HistoryPeriod
    count: int
    data: List[BasisSpreadPoint]


# ---------------------------------------------------------------------------
# /v1/spreads/curve-structure*
# ---------------------------------------------------------------------------


class CurveMonth(_WireModel):
    price: float
    contract: str


class CurveStructureSpreads(_WireModel):
    """Front-month minus later-month spreads. The server omits a horizon it
    could not compute, so ``m1_m3`` and ``m1_m12`` may be absent."""

    m1_m6: float
    m1_m3: Optional[float] = None
    m1_m12: Optional[float] = None


class CurveStructure(_WireModel):
    """``GET /v1/spreads/curve-structure`` and each entry of ``/all``."""

    commodity: str
    display_name: str
    structure: str
    severity: str
    term_slope_pct: float
    spreads: CurveStructureSpreads
    front_month: CurveMonth
    back_month_6: CurveMonth
    curve_points: int
    signal: str
    timestamp: datetime


# ---------------------------------------------------------------------------
# /v1/spreads/margin*
# ---------------------------------------------------------------------------


class MarginCrudeInput(_WireModel):
    code: str
    price: float


class MarginProduct(_WireModel):
    yield_pct: float
    price: float
    code: str


class RefineryMargin(_WireModel):
    """``GET /v1/spreads/margin`` and each entry of ``/margin/all``.

    ``product_basket`` only contains products the server had a price for.
    """

    index: str
    name: str
    margin_usd_bbl: float
    crude_input: MarginCrudeInput
    product_basket: Dict[str, MarginProduct]
    signal: str
    percentile_1y: Optional[int]
    changes: MetricChanges
    timestamp: datetime


class RefineryMarginPoint(_WireModel):
    date: date
    margin: float
    crude: float
    revenue: float


class RefineryMarginHistory(_WireModel):
    """``GET /v1/spreads/margin/historical``."""

    index: str
    period: HistoryPeriod
    count: int
    data: List[RefineryMarginPoint]


# ---------------------------------------------------------------------------
# /v1/spreads/physical-premium*
# ---------------------------------------------------------------------------


class PhysicalPremiumLeg(_WireModel):
    code: str
    price: float
    contract: Optional[str] = None


class PhysicalPremiumComponents(_WireModel):
    spot: PhysicalPremiumLeg
    futures: PhysicalPremiumLeg


class PhysicalPremium(_WireModel):
    """``GET /v1/spreads/physical-premium`` and each entry of ``/all``."""

    commodity: str
    name: str
    premium: float
    premium_pct: float
    unit: str
    components: PhysicalPremiumComponents
    signal: str
    elevated_streak_days: int
    percentile_1y: Optional[int]
    timestamp: datetime
    data_stale: Optional[bool] = None
    stale_warning: Optional[str] = None


class PhysicalPremiumPoint(_WireModel):
    date: date
    premium: float
    premium_pct: float
    spot: float
    futures: float


class PhysicalPremiumHistory(_WireModel):
    """``GET /v1/spreads/physical-premium/historical``."""

    commodity: str
    period: HistoryPeriod
    count: int
    data: List[PhysicalPremiumPoint]


# ---------------------------------------------------------------------------
# /v1/indicators/fuel-switching*
# ---------------------------------------------------------------------------


class OilParity(_WireModel):
    ratio_pct: float
    threshold_pct: float
    signal: str
    parity_price: float
    current_gas: float
    headroom_pct: float


class FuelSwitchingComponents(_WireModel):
    gas: PricedLeg
    crude: PricedLeg


class EnergyEquivalent(_WireModel):
    crude_per_mmbtu: float
    gas_premium_discount: float


class FuelSwitchingContext(_WireModel):
    """Trailing-year context. The server sends ``{}`` with fewer than 10
    observations, so every field is optional."""

    times_above_parity_last_year: Optional[int] = None
    pct_above_parity: Optional[float] = None
    avg_ratio_1y: Optional[float] = None
    max_ratio_1y: Optional[float] = None
    min_ratio_1y: Optional[float] = None
    data_points: Optional[int] = None


class FuelSwitching(_WireModel):
    """``GET /v1/indicators/fuel-switching``."""

    oil_parity: OilParity
    components: FuelSwitchingComponents
    energy_equivalent: EnergyEquivalent
    historical_context: FuelSwitchingContext
    timestamp: datetime


class FuelSwitchingPoint(_WireModel):
    date: date
    ratio_pct: float
    above_parity: bool
    gas_price: float
    crude_price: float


class FuelSwitchingHistory(_WireModel):
    """``GET /v1/indicators/fuel-switching/historical``."""

    gas_benchmark: str
    crude_benchmark: str
    period: HistoryPeriod
    count: int
    data: List[FuelSwitchingPoint]


# ---------------------------------------------------------------------------
# /v1/indicators/price-context
# ---------------------------------------------------------------------------


class PriceContextDetail(_WireModel):
    """Where the latest price sits. Every metric other than ``anomaly`` is only
    sent when the server had enough history to compute it."""

    anomaly: bool
    anomaly_reason: Optional[str] = None
    change_1d: Optional[float] = None
    change_1d_pct: Optional[float] = None
    change_1w: Optional[float] = None
    change_1w_pct: Optional[float] = None
    change_1m: Optional[float] = None
    change_1m_pct: Optional[float] = None
    high_52w: Optional[float] = None
    low_52w: Optional[float] = None
    percentile_1y: Optional[int] = None
    percentile_5y: Optional[int] = None


class RelatedSpread(_WireModel):
    """A spread related to the requested code (``spreads=related``).

    ``value`` is numeric for basis/crack/parity entries and a structure label
    (e.g. ``"backwardation"``) for the curve-structure entry, which carries
    ``slope`` and no ``unit``.
    """

    name: str
    value: Union[float, str]
    signal: Optional[str]
    unit: Optional[str] = None
    slope: Optional[float] = None


class PriceContext(_WireModel):
    """``GET /v1/indicators/price-context``."""

    code: str
    price: float
    timestamp: datetime
    context: PriceContextDetail
    related_spreads: Optional[List[RelatedSpread]] = None


# ---------------------------------------------------------------------------
# /v1/indicators/storage-analytics*
# ---------------------------------------------------------------------------


class StorageCurrent(_WireModel):
    volume_mmbbl: float
    utilization_pct: Optional[float]
    operational_capacity_mmbbl: float
    data_date: datetime
    timestamp: datetime


class StorageDrawRate(_WireModel):
    """``{}`` when the latest report has no weekly change."""

    weekly_mmbbl: Optional[float] = None
    annualized_mmbbl: Optional[float] = None
    type: Optional[str] = None
    days_to_depletion: Optional[int] = None


class StorageSeasonal(_WireModel):
    """``{}`` with fewer than three same-week observations in five years."""

    five_year_avg_mmbbl: Optional[float] = None
    five_year_min_mmbbl: Optional[float] = None
    five_year_max_mmbbl: Optional[float] = None
    deviation_from_avg_pct: Optional[float] = None
    position: Optional[str] = None


class StorageAnomalies(_WireModel):
    unusual_change: Optional[bool] = None
    unusual_change_detail: Optional[str] = None
    utilization_extreme: Optional[bool] = None
    utilization_detail: Optional[str] = None
    statistical_outlier: Optional[bool] = None
    z_score: Optional[float] = None


class StorageRange(_WireModel):
    """``{}`` when there is no data in the trailing 52 weeks."""

    high_mmbbl: Optional[float] = None
    low_mmbbl: Optional[float] = None


class StorageAnalytics(_WireModel):
    """``GET /v1/indicators/storage-analytics`` and each entry of ``/all``."""

    location: str
    name: str
    current: StorageCurrent
    draw_rate: StorageDrawRate
    seasonal: StorageSeasonal
    anomalies: StorageAnomalies
    range_52w: StorageRange
    signal: Optional[str]
    trading_implication: Optional[str]


# ---------------------------------------------------------------------------
# /v1/indicators/annotations*
# ---------------------------------------------------------------------------


class MarketAnnotation(_WireModel):
    """One notable condition. Extra fields depend on ``type``: ``anomaly``
    (``z_score``, ``mean_90d``), ``velocity`` (``pct_change_5d``, ``z_score``),
    ``streak`` (``direction``, ``streak_days``), ``record`` (``record_type``)."""

    type: str
    severity: str
    message: str
    z_score: Optional[float] = None
    mean_90d: Optional[float] = None
    pct_change_5d: Optional[float] = None
    direction: Optional[str] = None
    streak_days: Optional[int] = None
    record_type: Optional[str] = None


class MarketAnnotations(_WireModel):
    """``GET /v1/indicators/annotations``."""

    code: str
    price: float
    timestamp: datetime
    annotation_count: int
    annotations: List[MarketAnnotation]


class MarketAnnotationsBatch(_WireModel):
    """``GET /v1/indicators/annotations/batch``.

    ``annotated`` omits codes the server has no data for and codes with no
    annotations, so it can be shorter than ``total_codes``.
    """

    annotated: List[MarketAnnotations]
    total_codes: int
    codes_with_annotations: int


# ---------------------------------------------------------------------------
# /v1/indicators/cftc-positioning*
# ---------------------------------------------------------------------------


class CftcSpeculativePosition(_WireModel):
    net: int
    long: Optional[int]
    short: Optional[int]
    net_pct_of_oi: Optional[float]


class CftcCommercialPosition(_WireModel):
    net: Optional[int]


class CftcPositions(_WireModel):
    speculative: CftcSpeculativePosition
    commercial: CftcCommercialPosition
    open_interest: Optional[int]


class CftcPositioning(_WireModel):
    """``GET /v1/indicators/cftc-positioning`` and each entry of ``/all``."""

    commodity: str
    name: str
    report_date: date
    positioning: CftcPositions
    signal: str
    percentile_1y: Optional[int]
    week_change: Optional[int]
    timestamp: datetime


class CftcPositioningPoint(_WireModel):
    date: date
    spec_net: int
    open_interest: Optional[int]
    spec_net_pct_oi: Optional[float]


class CftcPositioningHistory(_WireModel):
    """``GET /v1/indicators/cftc-positioning/historical``."""

    commodity: str
    period: HistoryPeriod
    count: int
    data: List[CftcPositioningPoint]
