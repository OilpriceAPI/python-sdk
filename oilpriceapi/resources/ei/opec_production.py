"""
EI OPEC Production Resource

Energy Intelligence OPEC production data operations.
"""

from typing import Any, Dict, List

from ._envelopes import ei_data, unwrap_ei_collection


class EIOpecProductionResource:
    """Resource for Energy Intelligence OPEC production data."""

    def __init__(self, client):
        """Initialize EI OPEC production resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def list(self, **params) -> List[Dict[str, Any]]:
        """Get all OPEC production data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            List of OPEC production records

        Example:
            >>> production = client.ei.opec_production.list()
            >>> for record in production:
            ...     print(f"{record['country']}: {record['production']} bpd")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/opec_productions",
            params=params
        )

        return ei_data(response)

    def get(self, id: str) -> Dict[str, Any]:
        """Get a specific OPEC production record by ID.

        Args:
            id: OPEC production record ID

        Returns:
            OPEC production record details

        Example:
            >>> record = client.ei.opec_production.get("123")
            >>> print(f"Production: {record['production']} bpd")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/ei/opec_productions/{id}"
        )

        return ei_data(response)

    def latest(self) -> Dict[str, Any]:
        """Get latest OPEC production data.

        Returns:
            Report object with ``id``, ``report_month``,
            ``publication_month``, ``production_month``, ``source``,
            ``opec_total``, ``countries`` and ``headline``.

        Example:
            >>> latest = client.ei.opec_production.latest()
            >>> print(f"OPEC total: {latest['opec_total']} mbpd")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/opec_productions/latest"
        )

        return ei_data(response)

    def total(self) -> Dict[str, Any]:
        """Get total OPEC production.

        Returns:
            Object with ``latest``, ``history`` and ``trend``.

        Example:
            >>> total = client.ei.opec_production.total()
            >>> print(total['trend'])
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/opec_productions/total"
        )

        return ei_data(response)

    def by_country(self, **params) -> List[Dict[str, Any]]:
        """Get OPEC production by country.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            The ``countries`` list from ``data``. Each record has
            ``country``, ``name``, ``report_month``, ``publication_month``,
            ``production_month`` and ``production_mbpd``.

        Example:
            >>> countries = client.ei.opec_production.by_country()
            >>> for country in countries:
            ...     print(f"{country['name']}: {country['production_mbpd']} mbpd")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/opec_productions/by_country",
            params=params
        )

        return unwrap_ei_collection(
            response, collection="countries", subject="OPEC by-country"
        )

    def historical(self, **params) -> List[Dict[str, Any]]:
        """Get historical OPEC production data.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            The ``records`` list from ``data``. Each record has
            ``report_month``, ``publication_month``, ``production_month``
            and ``production_mbpd``.

        Example:
            >>> history = client.ei.opec_production.historical(country="saudi_arabia")
            >>> for record in history:
            ...     print(f"{record['production_month']}: {record['production_mbpd']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/opec_productions/historical",
            params=params
        )

        return unwrap_ei_collection(
            response, collection="records", subject="OPEC historical"
        )

    def top_producers(self, **params) -> List[Dict[str, Any]]:
        """Get top OPEC producers.

        Args:
            **params: Optional query parameters for filtering

        Returns:
            The ``producers`` list from ``data``. Each record has ``rank``,
            ``country``, ``name``, ``production_mbpd``, ``share_of_opec``,
            ``publication_month`` and ``production_month``.

        Example:
            >>> producers = client.ei.opec_production.top_producers()
            >>> for producer in producers:
            ...     print(f"{producer['rank']}. {producer['name']}")
        """
        response = self.client.request(
            method="GET",
            path="/v1/ei/opec_productions/top_producers",
            params=params
        )

        return unwrap_ei_collection(
            response, collection="producers", subject="OPEC top-producers"
        )
