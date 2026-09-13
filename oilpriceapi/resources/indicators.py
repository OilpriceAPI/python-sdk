"""
Indicators Resource

Typed access to the market indicator routes under ``/v1/indicators/*`` (#99):
gas-to-oil fuel-switching parity, enriched price context, storage analytics,
market annotations and CFTC Commitments of Traders positioning.

Access requires a paid plan (Developer and above); other plans receive
``PermissionDeniedError`` with code ``PREMIUM_REQUIRED``.

``/v1/indicators/congressional-trades`` is intentionally not exposed: it has
never returned data in production (HTTP 404 ``DATA_NOT_AVAILABLE``), so there
is no observed response shape to type.
"""

from typing import Any, List, Optional, Sequence

from ..metrics_models import (
    CftcPositioning,
    CftcPositioningHistory,
    FuelSwitching,
    FuelSwitchingHistory,
    MarketAnnotations,
    MarketAnnotationsBatch,
    PriceContext,
    StorageAnalytics,
)
from . import _calculated_metrics as ops
from ._calculated_metrics import DateInput


class IndicatorsResource:
    """Resource for ``/v1/indicators/*``."""

    def __init__(self, client: Any) -> None:
        """Initialize indicators resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def fuel_switching(self, gas: Optional[str] = None, crude: Optional[str] = None) -> FuelSwitching:
        """Get gas-to-oil parity (fuel-switching economics).

        Args:
            gas: ``"NATURAL_GAS_USD"``, ``"DUTCH_TTF_NATURAL_GAS_USD"`` or
                ``"NATURAL_GAS_WAHA"``; server default ``"NATURAL_GAS_USD"``.
            crude: ``"BRENT_CRUDE_USD"``, ``"WTI_USD"`` or ``"BRENT_SPOT_USD"``;
                server default ``"BRENT_CRUDE_USD"``.

        Example:
            >>> parity = client.indicators.fuel_switching()
            >>> print(parity.oil_parity.ratio_pct, parity.oil_parity.signal)
        """
        return ops.run_sync(self.client, ops.fuel_switching(gas, crude))

    def fuel_switching_historical(
        self,
        gas: Optional[str] = None,
        crude: Optional[str] = None,
        start_date: Optional[DateInput] = None,
        end_date: Optional[DateInput] = None,
    ) -> FuelSwitchingHistory:
        """Get daily gas-to-oil parity history (server default: last 90 days)."""
        return ops.run_sync(
            self.client, ops.fuel_switching_historical(gas, crude, start_date, end_date)
        )

    def price_context(self, code: str, related_spreads: bool = False) -> PriceContext:
        """Get the latest price with historical context for a commodity code.

        Args:
            code: Commodity code, e.g. ``"BRENT_CRUDE_USD"``.
            related_spreads: Also return the spreads related to ``code``.

        Returns:
            PriceContext. Context metrics the server could not compute (not
            enough history) are ``None``; ``context.anomaly`` is always set.

        Raises:
            ValueError: If ``code`` is blank.
            DataNotFoundError: No data for ``code``.
        """
        return ops.run_sync(self.client, ops.price_context(code, related_spreads))

    def storage_analytics(self, location: Optional[str] = None) -> StorageAnalytics:
        """Get storage analytics for ``"CUSHING"`` (server default) or ``"SPR"``."""
        return ops.run_sync(self.client, ops.storage_analytics(location))

    def storage_analytics_all(self) -> List[StorageAnalytics]:
        """Get storage analytics for every location with data."""
        return ops.run_sync(self.client, ops.storage_analytics_all())

    def annotations(self, code: str) -> MarketAnnotations:
        """Get notable-condition annotations (anomaly, velocity, streak,
        52-week record) for a commodity code."""
        return ops.run_sync(self.client, ops.annotations(code))

    def annotations_batch(self, codes: Sequence[str]) -> MarketAnnotationsBatch:
        """Get annotations for up to 20 commodity codes in one request.

        The server leaves out codes it has no data for and codes with no
        annotations. More than 20 codes raises ``ValueError`` locally, because
        the API silently annotates only the first 20.
        """
        return ops.run_sync(self.client, ops.annotations_batch(codes))

    def cftc_positioning(self, commodity: Optional[str] = None) -> CftcPositioning:
        """Get the latest CFTC Commitments of Traders positioning.

        Args:
            commodity: ``"WTI"`` (server default), ``"BRENT"``,
                ``"NATURAL_GAS"``, ``"HEATING_OIL"`` or ``"GASOLINE"``.
                Components the report does not publish for a market are ``None``.
        """
        return ops.run_sync(self.client, ops.cftc_positioning(commodity))

    def cftc_positioning_historical(
        self,
        commodity: Optional[str] = None,
        start_date: Optional[DateInput] = None,
        end_date: Optional[DateInput] = None,
    ) -> CftcPositioningHistory:
        """Get weekly CFTC speculative net positioning history."""
        return ops.run_sync(
            self.client, ops.cftc_positioning_historical(commodity, start_date, end_date)
        )

    def cftc_positioning_all(self) -> List[CftcPositioning]:
        """Get the latest positioning for every market with data."""
        return ops.run_sync(self.client, ops.cftc_positioning_all())
