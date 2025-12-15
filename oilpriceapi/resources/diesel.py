"""
Diesel Prices Resource

State-level diesel averages and station-level pricing operations.
"""

from typing import Optional, List, Union
from datetime import datetime

from ..models import DieselPrice, DieselStation, DieselStationsResponse
from ..exceptions import ValidationError


class DieselResource:
    """Resource for diesel price operations.

    Provides access to state-level diesel price averages and station-level pricing.

    Example:
        >>> # Get state average (free tier)
        >>> price = client.diesel.get_price("CA")
        >>> print(f"California diesel: ${price.price:.2f}/gallon")

        >>> # Get nearby stations (paid tiers)
        >>> result = client.diesel.get_stations(lat=37.7749, lng=-122.4194)
        >>> print(f"Found {len(result.stations)} stations")
    """

    def __init__(self, client):
        """Initialize diesel resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def get_price(self, state: str) -> DieselPrice:
        """Get average diesel price for a US state.

        Returns EIA state-level average diesel price. This endpoint is free
        and included in all tiers.

        Args:
            state: Two-letter US state code (e.g., "CA", "TX", "NY")

        Returns:
            DieselPrice object with state average price

        Raises:
            ValidationError: If state code is invalid
            DataNotFoundError: If state not found
            AuthenticationError: If API key is invalid
            RateLimitError: If rate limit exceeded

        Example:
            >>> price = client.diesel.get_price("CA")
            >>> print(f"California: ${price.price:.2f}/gallon")
            >>> print(f"Source: {price.source}")
            >>> print(f"Updated: {price.updated_at}")

            >>> # Access all fields
            >>> print(f"State: {price.state}")
            >>> print(f"Currency: {price.currency}")
            >>> print(f"Unit: {price.unit}")
            >>> print(f"Granularity: {price.granularity}")
        """
        # Validate state code
        if not state or not isinstance(state, str):
            raise ValidationError(
                message="State code must be a string",
                field="state",
                value=state
            )

        if len(state) != 2:
            raise ValidationError(
                message="State code must be a 2-letter US state code (e.g., 'CA', 'TX')",
                field="state",
                value=state
            )

        # Make API request
        response = self.client.request(
            method="GET",
            path="/v1/diesel-prices",
            params={"state": state.upper()}
        )

        # Parse response - API returns { regional_average: {...} }
        if "regional_average" in response:
            price_data = response["regional_average"]
        elif "data" in response:
            price_data = response["data"]
        else:
            price_data = response

        return DieselPrice(**price_data)

    def get_stations(
        self,
        lat: float,
        lng: float,
        radius: Optional[float] = 8047
    ) -> DieselStationsResponse:
        """Get nearby diesel stations with current pricing.

        Returns station-level diesel prices within specified radius using Google Maps data.

        **Tier Requirements:** Available on paid tiers (Exploration and above)

        **Pricing Tiers:**
        - Exploration: 100 station queries/month
        - Starter: 500 station queries/month
        - Professional: 2,000 station queries/month
        - Business: 5,000 station queries/month

        **Caching:** Results are cached for 24 hours to minimize costs.

        Args:
            lat: Latitude (-90 to 90)
            lng: Longitude (-180 to 180)
            radius: Search radius in meters (default: 8047 = 5 miles, max: 50000)

        Returns:
            DieselStationsResponse with nearby stations and regional average

        Raises:
            ValidationError: If coordinates or radius are invalid
            AuthenticationError: If API key is invalid
            RateLimitError: If monthly station query limit exceeded (429)
            OilPriceAPIError: If tier doesn't support station queries (403)

        Example:
            >>> # Get stations near San Francisco
            >>> result = client.diesel.get_stations(
            ...     lat=37.7749,
            ...     lng=-122.4194,
            ...     radius=8047  # 5 miles
            ... )
            >>>
            >>> print(f"Regional avg: ${result.regional_average.price:.2f}/gal")
            >>> print(f"Found {len(result.stations)} stations")
            >>>
            >>> # Find cheapest station
            >>> cheapest = min(result.stations, key=lambda s: s.diesel_price)
            >>> print(f"Cheapest: {cheapest.name} at {cheapest.formatted_price}")
            >>>
            >>> # Print all stations
            >>> for station in result.stations:
            ...     print(f"{station.name}: {station.formatted_price}")
            ...     print(f"  {station.address}")
            ...     print(f"  {station.price_vs_average}")
        """
        # Validate coordinates
        if not isinstance(lat, (int, float)):
            raise ValidationError(
                message="Latitude must be a number",
                field="lat",
                value=lat
            )

        if not isinstance(lng, (int, float)):
            raise ValidationError(
                message="Longitude must be a number",
                field="lng",
                value=lng
            )

        if lat < -90 or lat > 90:
            raise ValidationError(
                message="Latitude must be between -90 and 90",
                field="lat",
                value=lat
            )

        if lng < -180 or lng > 180:
            raise ValidationError(
                message="Longitude must be between -180 and 180",
                field="lng",
                value=lng
            )

        # Validate radius
        if radius is not None:
            if not isinstance(radius, (int, float)):
                raise ValidationError(
                    message="Radius must be a number",
                    field="radius",
                    value=radius
                )

            if radius < 0 or radius > 50000:
                raise ValidationError(
                    message="Radius must be between 0 and 50000 meters",
                    field="radius",
                    value=radius
                )

        # Make API request (POST method for stations endpoint)
        response = self.client.request(
            method="POST",
            path="/v1/diesel-prices/stations",
            json_data={
                "lat": lat,
                "lng": lng,
                "radius": radius
            }
        )

        return DieselStationsResponse(**response)

    def to_dataframe(
        self,
        state: Optional[str] = None,
        states: Optional[List[str]] = None,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        radius: Optional[float] = 8047
    ):
        """Get diesel price data as a pandas DataFrame.

        Note: Requires pandas to be installed.

        Args:
            state: Single state code for state averages
            states: Multiple state codes for state averages
            lat: Latitude for station-level data
            lng: Longitude for station-level data
            radius: Search radius in meters (for station-level data)

        Returns:
            pandas DataFrame with diesel price data

        Example:
            >>> # State averages DataFrame
            >>> df = client.diesel.to_dataframe(
            ...     states=["CA", "TX", "NY", "FL"]
            ... )
            >>> print(df[["state", "price", "updated_at"]])
            >>>
            >>> # Station-level DataFrame
            >>> df = client.diesel.to_dataframe(
            ...     lat=37.7749,
            ...     lng=-122.4194,
            ...     radius=8047
            ... )
            >>> print(df[["name", "diesel_price", "price_delta"]])
            >>>
            >>> # Plot state averages
            >>> df.plot(x="state", y="price", kind="bar", title="Diesel Prices by State")
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "pandas is required for DataFrame support. "
                "Install with: pip install oilpriceapi[pandas]"
            )

        # Station-level data
        if lat is not None and lng is not None:
            result = self.get_stations(lat=lat, lng=lng, radius=radius)

            # Convert stations to DataFrame
            stations_data = [station.model_dump() for station in result.stations]
            df = pd.DataFrame(stations_data)

            # Add regional average as column
            df["regional_average"] = result.regional_average.price

            # Flatten location column
            if "location" in df.columns:
                df["latitude"] = df["location"].apply(lambda x: x["lat"] if isinstance(x, dict) else x.lat)
                df["longitude"] = df["location"].apply(lambda x: x["lng"] if isinstance(x, dict) else x.lng)
                df.drop("location", axis=1, inplace=True)

            return df

        # State averages
        if state:
            price = self.get_price(state)
            df = pd.DataFrame([price.model_dump()])
        elif states:
            prices = []
            for st in states:
                try:
                    price = self.get_price(st)
                    prices.append(price.model_dump())
                except Exception as e:
                    # Skip failed states
                    import logging
                    logging.warning(f"Failed to fetch diesel price for {st}: {e}")
                    continue

            df = pd.DataFrame(prices)
        else:
            raise ValueError(
                "Either state/states (for state averages) or lat/lng (for station data) must be specified"
            )

        # Set updated_at as index for state averages
        if "updated_at" in df.columns:
            df["updated_at"] = pd.to_datetime(df["updated_at"])
            df.set_index("updated_at", inplace=True)

        return df
