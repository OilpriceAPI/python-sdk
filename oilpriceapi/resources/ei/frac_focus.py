"""
EI FracFocus Resource

Energy Intelligence FracFocus data operations.
"""

from typing import Any, Dict, List

from ._envelopes import ei_data, unwrap_ei_collection, unwrap_ei_object


class EIFracFocusResource:
    """Resource for Energy Intelligence FracFocus data."""

    def __init__(self, client):
        """Initialize EI FracFocus resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def list(self, **params) -> List[Dict[str, Any]]:
        """Get all FracFocus data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            The ``frac_focus_disclosures`` list from ``data``. Each record
            has ``upload_key``, ``api_number``, ``state_code``, ``county``,
            ``operator``, ``well_name``, ``location``, ``job``, ``water``,
            ``chemicals`` and ``provenance``. Pagination lives in
            ``data['meta']`` and is not returned here.

        Example:
            >>> records = client.ei.frac_focus.list()
            >>> for record in records:
            ...     print(f"{record['operator']}: {record['well_name']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/frac-focus",
            params=params
        )

        return unwrap_ei_collection(
            response,
            collection="frac_focus_disclosures",
            subject="frac-focus list",
        )

    def get(self, id: str) -> Dict[str, Any]:
        """Get a specific FracFocus record by ID.

        Args:
            id: FracFocus record ID

        Returns:
            The disclosure record from ``data['frac_focus_disclosure']``,
            with ``upload_key``, ``api_number``, ``well_name``,
            ``operator``, ``location``, ``job``, ``water``, ``chemicals``,
            ``additives`` and ``provenance``.

        Example:
            >>> record = client.ei.frac_focus.get("ec7d19aa-2004-4e39-bd88-e660230cf74e")
            >>> print(f"Operator: {record['operator']}")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/ei/frac-focus/{id}"
        )

        return unwrap_ei_object(
            response,
            key="frac_focus_disclosure",
            subject="frac-focus record",
        )

    def latest(self) -> Dict[str, Any]:
        """Get latest FracFocus data.

        Returns:
            The latest-disclosures envelope: an object with
            ``frac_focus_disclosures`` (the list of records) and ``meta``
            (pagination). This endpoint returns the envelope, not a bare
            list, so the pagination counters stay reachable.

        Example:
            >>> latest = client.ei.frac_focus.latest()
            >>> print(f"Recent jobs: {len(latest['frac_focus_disclosures'])}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/frac-focus/latest"
        )

        return ei_data(response)

    def summary(self) -> Dict[str, Any]:
        """Get FracFocus summary.

        Returns:
            Object with ``period_days``, ``total_disclosures``, ``by_state``,
            ``top_operators``, ``water_usage``, ``monthly_trend`` and
            ``last_updated``.

        Example:
            >>> summary = client.ei.frac_focus.summary()
            >>> print(f"Total jobs: {summary['total_disclosures']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/frac-focus/summary"
        )

        return ei_data(response)

    def by_state(self, **params) -> List[Dict[str, Any]]:
        """Get FracFocus data by state.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            The ``frac_focus_disclosures`` list from ``data``.

        Example:
            >>> records = client.ei.frac_focus.by_state(state="TX")
            >>> for record in records:
            ...     print(f"{record['county']}: {record['well_name']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/frac-focus/by-state",
            params=params
        )

        return unwrap_ei_collection(
            response,
            collection="frac_focus_disclosures",
            subject="frac-focus by-state",
        )

    def by_operator(self, **params) -> List[Dict[str, Any]]:
        """Get FracFocus data by operator.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            The ``frac_focus_disclosures`` list from ``data``.

        Example:
            >>> records = client.ei.frac_focus.by_operator(operator="Chesapeake")
            >>> for record in records:
            ...     print(f"{record['well_name']}: {record['state_code']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/frac-focus/by-operator",
            params=params
        )

        return unwrap_ei_collection(
            response,
            collection="frac_focus_disclosures",
            subject="frac-focus by-operator",
        )

    def by_chemical(self, **params) -> List[Dict[str, Any]]:
        """Get FracFocus data by chemical.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            The ``frac_focus_disclosures`` list from ``data``.

        Example:
            >>> records = client.ei.frac_focus.by_chemical(cas="7732-18-5")
            >>> for record in records:
            ...     print(f"{record['operator']}: {record['well_name']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/frac-focus/by-chemical",
            params=params
        )

        return unwrap_ei_collection(
            response,
            collection="frac_focus_disclosures",
            subject="frac-focus by-chemical",
        )

    def search(self, query: str, **params) -> List[Dict[str, Any]]:
        """Search FracFocus data.

        Args:
            query: Search query string
            **params: Optional query parameters for filtering

        Returns:
            The ``frac_focus_disclosures`` list from ``data``.

        Example:
            >>> results = client.ei.frac_focus.search("Eagle Ford")
            >>> for result in results:
            ...     print(f"{result['operator']}: {result['well_name']}")
        """
        params["query"] = query
        response = self.client.request(
            method="GET",
            path="/v1/ei/frac-focus/search",
            params=params
        )

        return unwrap_ei_collection(
            response,
            collection="frac_focus_disclosures",
            subject="frac-focus search",
        )

    def chemicals(self, id: str) -> List[Dict[str, Any]]:
        """Get chemicals for a specific FracFocus record.

        Args:
            id: FracFocus record ID

        Returns:
            The ``chemicals`` list from ``data``. Each record has ``cas``,
            ``name``, ``mass``, ``percent_hf_job`` and
            ``percent_additive``. ``additives``, ``cas_numbers`` and
            ``suppliers`` sit beside it in the envelope.

        Example:
            >>> chemicals = client.ei.frac_focus.chemicals("ec7d19aa-2004-4e39-bd88-e660230cf74e")
            >>> for chemical in chemicals:
            ...     print(f"{chemical['name']}: {chemical['percent_hf_job']}%")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/ei/frac-focus/{id}/chemicals"
        )

        return unwrap_ei_collection(
            response, collection="chemicals", subject="frac-focus chemicals"
        )

    def for_well(self, api_number: str) -> List[Dict[str, Any]]:
        """Get FracFocus data for a specific well.

        Args:
            api_number: Well API number

        Returns:
            The ``frac_focus_disclosures`` list from ``data``.

        Example:
            >>> records = client.ei.frac_focus.for_well("33053090090000")
            >>> for record in records:
            ...     print(f"{record['well_name']}: {record['job']}")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/ei/frac-focus/for-well/{api_number}"
        )

        return unwrap_ei_collection(
            response,
            collection="frac_focus_disclosures",
            subject="frac-focus for-well",
        )
