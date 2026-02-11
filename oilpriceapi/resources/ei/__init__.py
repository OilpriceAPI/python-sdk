"""
Energy Intelligence (EI) Resources

Energy Intelligence data resource modules.
"""

from typing import Dict, Any
from .rig_counts import EIRigCountsResource
from .oil_inventories import EIOilInventoriesResource
from .opec_production import EIOpecProductionResource
from .drilling_productivity import EIDrillingProductivityResource
from .forecasts import EIForecastsResource
from .well_permits import EIWellPermitsResource
from .frac_focus import EIFracFocusResource


class EnergyIntelligenceResource:
    """Resource for Energy Intelligence data operations."""

    def __init__(self, client):
        """Initialize Energy Intelligence resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

        # Initialize sub-resources
        self.rig_counts = EIRigCountsResource(client)
        self.oil_inventories = EIOilInventoriesResource(client)
        self.opec_production = EIOpecProductionResource(client)
        self.drilling_productivity = EIDrillingProductivityResource(client)
        self.forecasts = EIForecastsResource(client)
        self.well_permits = EIWellPermitsResource(client)
        self.frac_focus = EIFracFocusResource(client)

    def well_timeline(self, api_number: str) -> Dict[str, Any]:
        """Get well timeline data.

        Args:
            api_number: Well API number

        Returns:
            Well timeline data with all events

        Example:
            >>> timeline = client.ei.well_timeline("42-123-45678")
            >>> for event in timeline['events']:
            ...     print(f"{event['date']}: {event['type']}")
        """
        response = self.client.request(
            method="GET",
            path=f"/v1/ei/wells/{api_number}/timeline"
        )

        # Parse response
        if "data" in response:
            return response["data"]
        return response


__all__ = [
    "EnergyIntelligenceResource",
    "EIRigCountsResource",
    "EIOilInventoriesResource",
    "EIOpecProductionResource",
    "EIDrillingProductivityResource",
    "EIForecastsResource",
    "EIWellPermitsResource",
    "EIFracFocusResource",
]
