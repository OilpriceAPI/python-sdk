"""
Well Production Resource

US well production data operations (beta).

Covers the `/v1/well-production*` endpoints: national/state monthly
production aggregates (EIA API v2), per-well production history where
state regulatory data has been collected, and permit-to-production
cycle-time analytics.

Note: well-level coverage is beta and limited to the states listed in
the summary's ``coverage.well_level_states_with_data``. This is NOT a
complete US well-level production dataset. Access requires a plan with
the Drilling Intelligence feature; other plans receive a 403
``ENTERPRISE_REQUIRED`` error.
"""

from typing import Any, Dict, Optional, cast

from ..resource_validators import normalize_api_number


class WellProductionResource:
    """Resource for US well production data (beta)."""

    def __init__(self, client: Any) -> None:
        """Initialize well production resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def summary(self) -> Dict[str, Any]:
        """Get the national production overview.

        Returns the latest national rollup, top producing states, data
        sources, and coverage metadata.

        Returns:
            Summary dict with ``national``, ``top_states``,
            ``data_sources``, and ``coverage`` keys.

        Example:
            >>> overview = client.well_production.summary()
            >>> for state in overview["top_states"]:
            ...     print(f"{state['state']}: {state['oil_bbl']} bbl")
        """
        response = self.client.request(
            method="GET",
            path="/v1/well-production"
        )

        # Parse response
        if "data" in response:
            return cast(Dict[str, Any], response["data"])
        return cast(Dict[str, Any], response)

    def states(self, period: Optional[str] = None, **params: Any) -> Dict[str, Any]:
        """Get state-level production for a month.

        Args:
            period: Optional month in ``YYYY-MM`` format. Defaults to the
                latest available month.
            **params: Additional query parameters.

        Returns:
            Dict with ``period``, ``count``, and a ``states`` list ordered
            by oil production descending.

        Example:
            >>> result = client.well_production.states(period="2026-04")
            >>> for state in result["states"]:
            ...     print(f"{state['state']}: {state['oil_bpd']} bpd")
        """
        if period is not None:
            params["period"] = period
        response = self.client.request(
            method="GET",
            path="/v1/well-production/states",
            params=params
        )

        # Parse response
        if "data" in response:
            return cast(Dict[str, Any], response["data"])
        return cast(Dict[str, Any], response)

    def state(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **params: Any,
    ) -> Dict[str, Any]:
        """Get production history for a specific state.

        Args:
            code: Two-letter state code, e.g. ``"TX"``.
            start_date: Optional ``YYYY-MM-DD`` range start (default: 2 years ago).
            end_date: Optional ``YYYY-MM-DD`` range end (default: today).
            **params: Additional query parameters.

        Returns:
            Dict with ``state``, ``period`` (start/end), ``count``, and a
            ``data`` list of monthly production records.

        Raises:
            DataNotFoundError: If no production data exists for the state.

        Example:
            >>> tx = client.well_production.state("TX", start_date="2026-01-01")
            >>> for month in tx["data"]:
            ...     print(f"{month['period']}: {month['oil_bbl']} bbl")
        """
        if start_date is not None:
            params["start_date"] = start_date
        if end_date is not None:
            params["end_date"] = end_date
        response = self.client.request(
            method="GET",
            path=f"/v1/well-production/states/{code}",
            params=params
        )

        # Parse response
        if "data" in response:
            return cast(Dict[str, Any], response["data"])
        return cast(Dict[str, Any], response)

    def well(self, api_number: str) -> Dict[str, Any]:
        """Get production history for a specific well (beta).

        Args:
            api_number: 14-digit API well number. Separators such as dashes
                are stripped automatically (``"42-285-34329-00-00"`` is OK).

        Returns:
            Dict with ``api_number``, ``operator``, ``well_name``,
            ``state``, ``count``, and a ``data`` list of monthly records.

        Raises:
            ValueError: If the API number is not 14 digits after
                removing separators.
            DataNotFoundError: If no production data exists for the well.

        Example:
            >>> well = client.well_production.well("42285343290000")
            >>> print(f"{well['well_name']} ({well['operator']})")
        """
        normalized = normalize_api_number(api_number)
        response = self.client.request(
            method="GET",
            path=f"/v1/well-production/wells/{normalized}"
        )

        # Parse response
        if "data" in response:
            return cast(Dict[str, Any], response["data"])
        return cast(Dict[str, Any], response)

    def top_producers(
        self,
        state_code: str = "TX",
        limit: int = 20,
        months: Optional[int] = None,
        **params: Any,
    ) -> Dict[str, Any]:
        """Get top producing wells for a state (beta).

        Args:
            state_code: Two-letter state code (default ``"TX"``).
            limit: Maximum wells to return (server caps at 100).
            months: Optional lookback window in months (default 12).
            **params: Additional query parameters.

        Returns:
            Dict with ``state``, ``period``, ``count``, and a ``producers``
            list of wells with total oil/gas volumes.

        Example:
            >>> top = client.well_production.top_producers("NM", limit=10)
            >>> for well in top["producers"]:
            ...     print(f"{well['well_name']}: {well['total_oil_bbl']} bbl")
        """
        params["state_code"] = state_code
        params["limit"] = limit
        if months is not None:
            params["months"] = months
        response = self.client.request(
            method="GET",
            path="/v1/well-production/top-producers",
            params=params
        )

        # Parse response
        if "data" in response:
            return cast(Dict[str, Any], response["data"])
        return cast(Dict[str, Any], response)

    def cycle_time(
        self,
        state: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        operator: Optional[str] = None,
        formation: Optional[str] = None,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        radius_miles: Optional[float] = None,
        **params: Any,
    ) -> Dict[str, Any]:
        """Get permit-to-production cycle time analysis (beta).

        Args:
            state: Optional two-letter state code filter.
            start_date: Optional ``YYYY-MM-DD`` permit-date range start.
            end_date: Optional ``YYYY-MM-DD`` permit-date range end.
            operator: Optional operator name filter.
            formation: Optional formation name filter.
            lat: Optional latitude for a geographic cohort.
            lng: Optional longitude for a geographic cohort.
            radius_miles: Optional radius (miles) around lat/lng.
            **params: Additional query parameters.

        Returns:
            Dict with ``well_count``, ``cycle_time_stats`` (median/p25/p75/
            p90 days), ``quarterly_cohorts``, and fastest/slowest wells.

        Raises:
            DataNotFoundError: If no wells match the filters.

        Example:
            >>> ct = client.well_production.cycle_time(state="TX")
            >>> print(f"Median: {ct['cycle_time_stats']['median_days']} days")
        """
        filters: Dict[str, Any] = {
            "state": state,
            "start_date": start_date,
            "end_date": end_date,
            "operator": operator,
            "formation": formation,
            "lat": lat,
            "lng": lng,
            "radius_miles": radius_miles,
        }
        params.update({k: v for k, v in filters.items() if v is not None})
        response = self.client.request(
            method="GET",
            path="/v1/well-production/cycle-time",
            params=params
        )

        # Parse response
        if "data" in response:
            return cast(Dict[str, Any], response["data"])
        return cast(Dict[str, Any], response)

    def cycle_time_cohorts(
        self,
        state: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        radius_miles: Optional[float] = None,
        group_by: Optional[str] = None,
        **params: Any,
    ) -> Dict[str, Any]:
        """Compare cycle times across cohorts (beta).

        Args:
            state: Optional two-letter state code filter.
            start_date: Optional ``YYYY-MM-DD`` permit-date range start.
            end_date: Optional ``YYYY-MM-DD`` permit-date range end.
            lat: Optional latitude for a geographic cohort.
            lng: Optional longitude for a geographic cohort.
            radius_miles: Optional radius (miles) around lat/lng.
            group_by: Cohort grouping field (default ``"quarter"``).
            **params: Additional query parameters.

        Returns:
            Dict with ``group_by`` and a ``cohorts`` mapping of cohort key
            to well counts and cycle-time stats.

        Example:
            >>> cohorts = client.well_production.cycle_time_cohorts(state="TX")
            >>> for quarter, stats in cohorts["cohorts"].items():
            ...     print(f"{quarter}: {stats['stats']['median_days']} days")
        """
        filters: Dict[str, Any] = {
            "state": state,
            "start_date": start_date,
            "end_date": end_date,
            "lat": lat,
            "lng": lng,
            "radius_miles": radius_miles,
            "group_by": group_by,
        }
        params.update({k: v for k, v in filters.items() if v is not None})
        response = self.client.request(
            method="GET",
            path="/v1/well-production/cycle-time/cohorts",
            params=params
        )

        # Parse response
        if "data" in response:
            return cast(Dict[str, Any], response["data"])
        return cast(Dict[str, Any], response)
