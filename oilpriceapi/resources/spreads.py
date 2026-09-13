"""
Spreads Resource

Typed access to the calculated spread routes under ``/v1/spreads/*`` (#99):
crack spreads, the European gasoil crack, basis differentials, futures curve
structure, refinery margins and physical-vs-futures premiums.

These are server-side calculations over OilPriceAPI price series, distinct
from :mod:`oilpriceapi.resources.analysis`, which computes locally. Access
requires a paid plan (Developer and above); other plans receive
``PermissionDeniedError`` with code ``PREMIUM_REQUIRED``.

Every method validates its arguments before sending, returns a typed model
built from the response, and raises ``OilPriceAPIError`` with code
``MALFORMED_RESPONSE`` if a successful response does not match that model.
"""

from typing import Any, List, Optional

from ..metrics_models import (
    BasisSpread,
    BasisSpreadHistory,
    CrackSpread,
    CrackSpreadAll,
    CrackSpreadHistory,
    CurveStructure,
    GasoilCrackSpread,
    PhysicalPremium,
    PhysicalPremiumHistory,
    RefineryMargin,
    RefineryMarginHistory,
)
from . import _calculated_metrics as ops
from ._calculated_metrics import DateInput


class SpreadsResource:
    """Resource for ``/v1/spreads/*``."""

    def __init__(self, client: Any) -> None:
        """Initialize spreads resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    # -- crack ----------------------------------------------------------------

    def crack(self, spread_type: Optional[str] = None, crude: Optional[str] = None) -> CrackSpread:
        """Get the latest crack spread.

        Args:
            spread_type: ``"3-2-1"``, ``"jet"``, ``"diesel"`` or ``"gasoline"``.
                Omit to use the server default (``"3-2-1"``).
            crude: Crude benchmark code, e.g. ``"WTI_USD"``. Omit to use the
                server default (``"BRENT_CRUDE_USD"``).

        Returns:
            CrackSpread with ``value`` and ``unit`` (USD/bbl), the priced
            ``components``, the oldest input ``timestamp`` and ``changes``.

        Raises:
            ValueError: If an argument is blank.
            DataNotFoundError: Unknown spread type, or no data for an input.

        Example:
            >>> crack = client.spreads.crack(spread_type="diesel", crude="WTI_USD")
            >>> print(crack.value, crack.unit, crack.timestamp)
        """
        return ops.run_sync(self.client, ops.crack(spread_type, crude))

    def crack_historical(
        self,
        spread_type: Optional[str] = None,
        crude: Optional[str] = None,
        start_date: Optional[DateInput] = None,
        end_date: Optional[DateInput] = None,
    ) -> CrackSpreadHistory:
        """Get daily crack spread history.

        Args:
            spread_type: Spread type; server default ``"3-2-1"``.
            crude: Crude benchmark code; server default ``"BRENT_CRUDE_USD"``.
            start_date: ``YYYY-MM-DD``, ``date`` or ``datetime``. Server default
                is 30 days ago; the server caps the window at two years.
            end_date: ``YYYY-MM-DD``, ``date`` or ``datetime``; default today.

        Returns:
            CrackSpreadHistory. ``period`` is the window the server applied and
            ``coverage`` describes what was actually returned -- compare them
            before assuming the full window is present. ``data_revised_at``
            changes when the underlying inputs are restated.

        Raises:
            ValueError: Blank selector, invalid date, or start after end.
        """
        return ops.run_sync(
            self.client, ops.crack_historical(spread_type, crude, start_date, end_date)
        )

    def crack_all(self, crude: Optional[str] = None) -> CrackSpreadAll:
        """Get every crack spread type for one crude benchmark.

        Types without data are omitted by the server rather than returned empty.
        """
        return ops.run_sync(self.client, ops.crack_all(crude))

    def gasoil_crack(self) -> GasoilCrackSpread:
        """Get the European gasoil crack (ICE Low Sulphur Gasoil vs ICE Brent).

        The gasoil leg is quoted in USD/tonne; ``conversion`` states the
        barrels-per-tonne factor used to express the spread in USD/bbl, and each
        leg names its ``contract_month``.
        """
        return ops.run_sync(self.client, ops.gasoil_crack())

    # -- basis ----------------------------------------------------------------

    def basis(self, pair: str) -> BasisSpread:
        """Get the latest basis spread for a pair.

        Args:
            pair: Pair key, e.g. ``"BRENT_WTI"``, ``"WAHA_HH"``, ``"TTF_HH"``.

        Raises:
            ValueError: If ``pair`` is blank.
            DataNotFoundError: Unknown pair (the message lists valid pairs).

        Example:
            >>> spread = client.spreads.basis("BRENT_WTI")
            >>> spread.components
            {'BRENT_CRUDE_USD': 104.32, 'WTI_USD': 99.99}
        """
        return ops.run_sync(self.client, ops.basis(pair))

    def basis_historical(
        self,
        pair: str,
        start_date: Optional[DateInput] = None,
        end_date: Optional[DateInput] = None,
    ) -> BasisSpreadHistory:
        """Get daily basis spread history for a pair.

        Note: the API answers an unknown ``pair`` on this route with an empty
        200 rather than a 404, so ``count == 0`` can mean a misspelled pair.
        Use :meth:`basis_all` to list valid pairs.
        """
        return ops.run_sync(self.client, ops.basis_historical(pair, start_date, end_date))

    def basis_all(self) -> List[BasisSpread]:
        """Get the latest value for every basis pair with data."""
        return ops.run_sync(self.client, ops.basis_all())

    # -- curve structure ------------------------------------------------------

    def curve_structure(self, commodity: str) -> CurveStructure:
        """Get futures curve structure (backwardation/contango) for a market.

        Args:
            commodity: ``"ICE_BRENT"``, ``"ICE_WTI"``, ``"ICE_GASOIL"``,
                ``"NYMEX_NG"`` or ``"ICE_TTF"``.
        """
        return ops.run_sync(self.client, ops.curve_structure(commodity))

    def curve_structure_all(self) -> List[CurveStructure]:
        """Get curve structure for every market with a usable curve."""
        return ops.run_sync(self.client, ops.curve_structure_all())

    # -- refinery margin ------------------------------------------------------

    def margin(self, index: Optional[str] = None) -> RefineryMargin:
        """Get the latest refinery margin.

        Args:
            index: ``"usgc"``, ``"singapore"`` or ``"nwe"``; server default
                ``"usgc"``.
        """
        return ops.run_sync(self.client, ops.margin(index))

    def margin_historical(
        self,
        index: Optional[str] = None,
        start_date: Optional[DateInput] = None,
        end_date: Optional[DateInput] = None,
    ) -> RefineryMarginHistory:
        """Get daily refinery margin history (unknown ``index`` returns empty)."""
        return ops.run_sync(self.client, ops.margin_historical(index, start_date, end_date))

    def margin_all(self) -> List[RefineryMargin]:
        """Get the latest margin for every index with data."""
        return ops.run_sync(self.client, ops.margin_all())

    # -- physical premium -----------------------------------------------------

    def physical_premium(self, commodity: Optional[str] = None) -> PhysicalPremium:
        """Get the latest physical (spot) vs futures premium.

        Args:
            commodity: ``"BRENT"`` or ``"WTI"``; server default ``"BRENT"``.
        """
        return ops.run_sync(self.client, ops.physical_premium(commodity))

    def physical_premium_historical(
        self,
        commodity: Optional[str] = None,
        start_date: Optional[DateInput] = None,
        end_date: Optional[DateInput] = None,
    ) -> PhysicalPremiumHistory:
        """Get daily physical premium history. An empty ``data`` list is a
        valid result when the server has no overlapping spot/futures days."""
        return ops.run_sync(
            self.client, ops.physical_premium_historical(commodity, start_date, end_date)
        )

    def physical_premium_all(self) -> List[PhysicalPremium]:
        """Get the latest premium for every commodity with data."""
        return ops.run_sync(self.client, ops.physical_premium_all())
