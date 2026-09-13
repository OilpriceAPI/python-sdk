"""
EI Well Permits Resource

Energy Intelligence well permit data operations.
"""

from typing import Any, Dict, List, Optional

from ._envelopes import ei_data, unwrap_ei_collection, unwrap_ei_object


def unwrap_well_permit_search_response(response: Any) -> List[Dict[str, Any]]:
    """Return a typed permit list or fail on an unknown successful shape.

    Kept as a named entry point because it is already public; the shape
    knowledge now lives in the shared EI envelope helper so search and every
    other permit collection stay in step.
    """
    return unwrap_ei_collection(
        response, collection="well_permits", subject="well-permit search"
    )


class EIWellPermitsResource:
    """Resource for Energy Intelligence well permit data."""

    def __init__(self, client):
        """Initialize EI well permits resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def list(self, **params) -> List[Dict[str, Any]]:
        """Get all well permit data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            The ``well_permits`` list from ``data``. Each record has
            ``api_number``, ``state_code``, ``county``, ``permit_number``,
            ``permit_type``, ``permit_status``, ``permit_date``,
            ``operator``, ``well``, ``location``, ``target`` and
            ``provenance``. Pagination lives in ``data['meta']`` and is not
            returned here.

        Example:
            >>> permits = client.ei.well_permits.list()
            >>> for permit in permits:
            ...     print(f"{permit['operator']['name']}: {permit['well']['name']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/well-permits",
            params=params
        )

        return unwrap_ei_collection(
            response, collection="well_permits", subject="well-permit list"
        )

    def get(self, id: str) -> Dict[str, Any]:
        """Get a specific well permit record by ID.

        Args:
            id: Well permit record ID

        Returns:
            The permit record from ``data['well_permit']``.

        Example:
            >>> permit = client.ei.well_permits.get("05123534110000")
            >>> print(f"Operator: {permit['operator']['name']}")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/ei/well-permits/{id}"
        )

        return unwrap_ei_object(
            response, key="well_permit", subject="well-permit record"
        )

    def latest(self) -> Dict[str, Any]:
        """Get latest well permit data.

        Returns:
            The latest-permits envelope: an object with ``well_permits``
            (the list of records) and ``meta`` (pagination and freshness).
            This endpoint returns the envelope, not a bare list, so the
            freshness counters stay reachable.

        Example:
            >>> latest = client.ei.well_permits.latest()
            >>> print(f"Recent permits: {len(latest['well_permits'])}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/well-permits/latest"
        )

        return ei_data(response)

    def summary(self) -> Dict[str, Any]:
        """Get well permit summary.

        Returns:
            Object with ``period_days``, ``total_permits``, ``by_state``,
            ``top_operators``, ``top_formations``, ``by_permit_type``,
            ``weekly_trend``, ``last_updated`` and the staleness fields
            ``as_of``, ``data_age_days``, ``stale`` and ``stale_states``.

        Example:
            >>> summary = client.ei.well_permits.summary()
            >>> print(f"Total permits: {summary['total_permits']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/well-permits/summary"
        )

        return ei_data(response)

    def by_state(self, **params) -> List[Dict[str, Any]]:
        """Get well permits by state.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            The ``well_permits`` list from ``data``.

        Example:
            >>> permits = client.ei.well_permits.by_state(state="TX")
            >>> for permit in permits:
            ...     print(f"{permit['county']}: {permit['permit_number']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/well-permits/by-state",
            params=params
        )

        return unwrap_ei_collection(
            response, collection="well_permits", subject="well-permit by-state"
        )

    def by_operator(self, **params) -> List[Dict[str, Any]]:
        """Get well permits by operator.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            The ``well_permits`` list from ``data``.

        Example:
            >>> permits = client.ei.well_permits.by_operator(operator="Chesapeake")
            >>> for permit in permits:
            ...     print(f"{permit['well']['name']}: {permit['state_code']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/well-permits/by-operator",
            params=params
        )

        return unwrap_ei_collection(
            response,
            collection="well_permits",
            subject="well-permit by-operator",
        )

    def by_formation(self, **params) -> List[Dict[str, Any]]:
        """Get well permits by formation.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            The ``well_permits`` list from ``data``.

        Example:
            >>> permits = client.ei.well_permits.by_formation(formation="Wolfcamp")
            >>> for permit in permits:
            ...     print(f"{permit['well']['name']}: {permit['target']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/well-permits/by-formation",
            params=params
        )

        return unwrap_ei_collection(
            response,
            collection="well_permits",
            subject="well-permit by-formation",
        )

    def search(
        self,
        query: Optional[str] = None,
        **params: Any,
    ) -> List[Dict[str, Any]]:
        """Search well permits.

        Args:
            query: Optional legacy free-form query string.
            **params: Live search filters such as ``states``, ``county``,
                ``well_name``, ``permit_type``, and date or radius fields.

        Returns:
            List of matching permit records

        Example:
            >>> results = client.ei.well_permits.search(states="TX", well_name="Eagle")
            >>> for result in results:
            ...     print(f"{result['operator']['name']}: {result['state_code']}")
        """
        if query is not None:
            params["query"] = query
        response = self.client.request(
            method="GET",
            path="/v1/ei/well-permits/search",
            params=params
        )

        return unwrap_well_permit_search_response(response)
