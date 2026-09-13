"""
Fuel Surcharge Resource

Carrier fuel surcharges for LTL freight and parcel shipping (#101).

``list``, ``latest`` and ``history`` cover LTL carriers (Old Dominion, Saia,
Estes, XPO, ABF, TForce, Averitt, Southeastern Freight). The ``parcel_*``
methods cover parcel carriers (UPS, FedEx, DHL), which publish one surcharge
per service level.

Each rate carries the carrier's own ``effective_date`` and the ``source`` URL
and ``retrieved_at`` time of the retrieval it came from. The API serves the
latest stored row as-is; a stale row keeps its real dates, and a carrier with
no retrieved data raises ``DataNotFoundError`` instead of returning a rate.

The API does not feature-gate these routes by plan. Standard authentication
and request limits apply.
"""

from typing import Any, List, Optional

from .._fuel_surcharge_common import (
    LTL_LIST_PATH,
    PARCEL_LIST_PATH,
    carrier_path,
    history_params,
    parcel_carrier_path,
    parcel_history_params,
    parse_history,
    parse_parcel_carrier,
    parse_parcel_carrier_list,
    parse_rate,
    parse_rate_list,
    validate_slug,
)
from ..models import FuelSurchargeHistoryPage, FuelSurchargeRate, ParcelFuelSurchargeCarrier


class FuelSurchargeResource:
    """Resource for LTL and parcel carrier fuel surcharges."""

    def __init__(self, client: Any) -> None:
        """Initialize fuel surcharge resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    # --- LTL ---------------------------------------------------------------

    def list(self) -> List[FuelSurchargeRate]:
        """Latest LTL surcharge for every carrier that has data.

        Returns:
            One ``FuelSurchargeRate`` per carrier. Carriers with no retrieved
            data are absent, not zero.

        Example:
            >>> for rate in client.fuel_surcharge.list():
            ...     print(rate.carrier, rate.surcharge_percent, rate.effective_date)
        """
        response = self.client.request(method="GET", path=LTL_LIST_PATH)
        return parse_rate_list(response, subject="fuel-surcharge list")

    def latest(self, carrier: str) -> FuelSurchargeRate:
        """Latest LTL surcharge for one carrier.

        Args:
            carrier: Public carrier slug, e.g. ``"odfl"`` or ``"southeastern-freight"``.

        Raises:
            ValidationError: The slug is empty or not a slug (no request sent).
            DataNotFoundError: Unknown, not-yet-covered, or no data retrieved.
                ``error.suggestions`` lists the covered carriers.

        Example:
            >>> rate = client.fuel_surcharge.latest("odfl")
            >>> print(rate.surcharge_percent, rate.effective_date, rate.source)
        """
        path = carrier_path(carrier, "latest")
        response = self.client.request(method="GET", path=path)
        return parse_rate(response, mode="ltl", subject="fuel-surcharge latest", carrier=carrier)

    def history(
        self,
        carrier: str,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> FuelSurchargeHistoryPage:
        """Weekly LTL surcharge history for one carrier, newest first.

        Args:
            carrier: Public carrier slug.
            page: Page number, 1 or more. Server default is 1.
            per_page: Rows per page, 1 to 100. Server default is 100.

        Returns:
            ``FuelSurchargeHistoryPage`` with ``history`` rows and the server's
            ``meta`` (``page``, ``per_page``, ``total_count``, ``total_pages``).

        Raises:
            ValidationError: Bad slug or out-of-range pagination (no request sent).
            DataNotFoundError: Unknown carrier or no data retrieved.

        Example:
            >>> page = client.fuel_surcharge.history("odfl", per_page=10)
            >>> print(page.meta.total_count)
        """
        path = carrier_path(carrier, "history")
        params = history_params(page, per_page)
        response = self.client.request(method="GET", path=path, params=params or None)
        return parse_history(
            response, mode="ltl", subject="fuel-surcharge history", carrier=carrier
        )

    # --- parcel --------------------------------------------------------------

    def parcel_list(self) -> List[ParcelFuelSurchargeCarrier]:
        """Latest parcel surcharge per service level, for every parcel carrier.

        Example:
            >>> for carrier in client.fuel_surcharge.parcel_list():
            ...     for rate in carrier.service_levels:
            ...         print(carrier.carrier, rate.service_level, rate.surcharge_percent)
        """
        response = self.client.request(method="GET", path=PARCEL_LIST_PATH)
        return parse_parcel_carrier_list(response, subject="parcel fuel-surcharge list")

    def parcel_latest(self, carrier: str) -> ParcelFuelSurchargeCarrier:
        """Latest surcharge for every service level of one parcel carrier.

        Args:
            carrier: Parcel carrier slug, e.g. ``"ups"``.

        Example:
            >>> ups = client.fuel_surcharge.parcel_latest("ups")
            >>> [rate.service_level for rate in ups.service_levels]
        """
        path = parcel_carrier_path(carrier, "latest")
        response = self.client.request(method="GET", path=path)
        return parse_parcel_carrier(
            response, subject="parcel fuel-surcharge latest", carrier=carrier
        )

    def parcel_latest_rate(self, carrier: str, service_level: str) -> FuelSurchargeRate:
        """Latest surcharge for one parcel carrier and service level.

        Args:
            carrier: Parcel carrier slug, e.g. ``"ups"``.
            service_level: Service level, e.g. ``"ground"``. Use
                ``parcel_latest`` to see which levels a carrier publishes.

        Raises:
            DataNotFoundError: No data for that carrier and service level.

        Example:
            >>> rate = client.fuel_surcharge.parcel_latest_rate("ups", "ground")
        """
        path = parcel_carrier_path(carrier, "latest")
        params = {"service_level": validate_slug(service_level, "service_level")}
        response = self.client.request(method="GET", path=path, params=params)
        return parse_rate(
            response,
            mode="parcel",
            subject="parcel fuel-surcharge latest",
            carrier=carrier,
            service_level=service_level,
        )

    def parcel_history(
        self,
        carrier: str,
        service_level: str,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> FuelSurchargeHistoryPage:
        """Weekly surcharge history for one parcel carrier and service level.

        Args:
            carrier: Parcel carrier slug.
            service_level: Required by the API, e.g. ``"ground"``.
            page: Page number, 1 or more.
            per_page: Rows per page, 1 to 100.

        Example:
            >>> page = client.fuel_surcharge.parcel_history("ups", "ground", per_page=4)
        """
        path = parcel_carrier_path(carrier, "history")
        params = parcel_history_params(service_level, page, per_page)
        response = self.client.request(method="GET", path=path, params=params)
        return parse_history(
            response,
            mode="parcel",
            subject="parcel fuel-surcharge history",
            carrier=carrier,
            service_level=service_level,
        )
