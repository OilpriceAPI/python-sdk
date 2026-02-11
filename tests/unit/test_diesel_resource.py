"""
Tests for Diesel Resource.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from oilpriceapi import OilPriceAPI
from oilpriceapi.exceptions import ValidationError
from oilpriceapi.models import (
    DieselPrice,
    DieselStation,
    DieselStationsResponse,
)


class TestDieselResourceGetPrice:
    """Test diesel.get_price() method."""

    @patch('httpx.Client.request')
    def test_get_price_success(self, mock_request):
        """Test getting diesel price for a state."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "regional_average": {
                "state": "CA",
                "price": 3.89,
                "currency": "USD",
                "unit": "gallon",
                "granularity": "state",
                "source": "EIA",
                "updated_at": "2025-12-15T10:00:00Z",
                "cached": False
            }
        }
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key="test_key")
        price = client.diesel.get_price("CA")

        assert isinstance(price, DieselPrice)
        assert price.state == "CA"
        assert price.price == 3.89
        assert price.currency == "USD"
        assert price.unit == "gallon"
        assert price.source == "EIA"
        assert price.granularity == "state"

    @patch('httpx.Client.request')
    def test_get_price_lowercase_conversion(self, mock_request):
        """Test that lowercase state codes are converted to uppercase."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "regional_average": {
                "state": "TX",
                "price": 3.45,
                "currency": "USD",
                "unit": "gallon",
                "granularity": "state",
                "source": "EIA",
                "updated_at": "2025-12-15T10:00:00Z"
            }
        }
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key="test_key")
        price = client.diesel.get_price("tx")  # lowercase

        # Check that the request was made with uppercase
        call_args = mock_request.call_args
        assert call_args[1]["params"]["state"] == "TX"

    def test_get_price_empty_state(self):
        """Test that empty state code raises ValidationError."""
        client = OilPriceAPI(api_key="test_key")

        with pytest.raises(ValidationError) as exc_info:
            client.diesel.get_price("")

        assert "2-letter US state code" in exc_info.value.message

    def test_get_price_invalid_length_short(self):
        """Test that 1-character state code raises ValidationError."""
        client = OilPriceAPI(api_key="test_key")

        with pytest.raises(ValidationError) as exc_info:
            client.diesel.get_price("C")

        assert "2-letter US state code" in exc_info.value.message

    def test_get_price_invalid_length_long(self):
        """Test that 3-character state code raises ValidationError."""
        client = OilPriceAPI(api_key="test_key")

        with pytest.raises(ValidationError) as exc_info:
            client.diesel.get_price("CAL")

        assert "2-letter US state code" in exc_info.value.message

    def test_get_price_non_string(self):
        """Test that non-string state code raises ValidationError."""
        client = OilPriceAPI(api_key="test_key")

        with pytest.raises(ValidationError) as exc_info:
            client.diesel.get_price(123)

        assert "must be a string" in exc_info.value.message

    def test_get_price_none(self):
        """Test that None state code raises ValidationError."""
        client = OilPriceAPI(api_key="test_key")

        with pytest.raises(ValidationError) as exc_info:
            client.diesel.get_price(None)

        assert "must be a string" in exc_info.value.message


class TestDieselResourceGetStations:
    """Test diesel.get_stations() method."""

    @patch('httpx.Client.request')
    def test_get_stations_success(self, mock_request):
        """Test getting nearby diesel stations."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "regional_average": {
                "price": 3.89,
                "currency": "USD",
                "unit": "gallon",
                "region": "California",
                "granularity": "regional",
                "source": "Google Maps"
            },
            "stations": [
                {
                    "name": "Chevron Station",
                    "address": "123 Main St, San Francisco, CA",
                    "location": {"lat": 37.7750, "lng": -122.4195},
                    "diesel_price": 3.75,
                    "formatted_price": "$3.75",
                    "currency": "USD",
                    "unit": "gallon",
                    "price_delta": -0.14,
                    "price_vs_average": "$0.14 cheaper than regional average",
                    "fuel_types": ["diesel", "regular", "premium"],
                    "last_updated": "2025-12-15T09:30:00Z"
                }
            ],
            "search_area": {
                "center": {"lat": 37.7749, "lng": -122.4194},
                "radius_meters": 8047,
                "radius_miles": 5.0
            },
            "metadata": {
                "total_stations": 1,
                "source": "Google Maps",
                "cached": False,
                "api_cost": 0.024,
                "timestamp": "2025-12-15T10:00:00Z"
            }
        }
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key="test_key")
        result = client.diesel.get_stations(lat=37.7749, lng=-122.4194)

        assert isinstance(result, DieselStationsResponse)
        assert result.regional_average.price == 3.89
        assert len(result.stations) == 1
        assert result.stations[0].name == "Chevron Station"
        assert result.stations[0].diesel_price == 3.75
        assert result.search_area.radius_miles == 5.0
        assert result.metadata.total_stations == 1

    @patch('httpx.Client.request')
    def test_get_stations_default_radius(self, mock_request):
        """Test that default radius is 8047 meters (5 miles)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "regional_average": {
                "price": 3.89,
                "currency": "USD",
                "unit": "gallon",
                "region": "California",
                "granularity": "regional",
                "source": "Google Maps"
            },
            "stations": [],
            "search_area": {
                "center": {"lat": 37.7749, "lng": -122.4194},
                "radius_meters": 8047,
                "radius_miles": 5.0
            },
            "metadata": {
                "total_stations": 0,
                "source": "Google Maps",
                "cached": True,
                "api_cost": 0,
                "timestamp": "2025-12-15T10:00:00Z"
            }
        }
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key="test_key")
        result = client.diesel.get_stations(lat=37.7749, lng=-122.4194)

        # Check that request was made with default radius
        call_args = mock_request.call_args
        assert call_args[1]["json"]["radius"] == 8047

    def test_get_stations_invalid_lat_low(self):
        """Test that latitude < -90 raises ValidationError."""
        client = OilPriceAPI(api_key="test_key")

        with pytest.raises(ValidationError) as exc_info:
            client.diesel.get_stations(lat=-91, lng=-122)

        assert "Latitude must be between -90 and 90" in exc_info.value.message

    def test_get_stations_invalid_lat_high(self):
        """Test that latitude > 90 raises ValidationError."""
        client = OilPriceAPI(api_key="test_key")

        with pytest.raises(ValidationError) as exc_info:
            client.diesel.get_stations(lat=91, lng=-122)

        assert "Latitude must be between -90 and 90" in exc_info.value.message

    def test_get_stations_invalid_lng_low(self):
        """Test that longitude < -180 raises ValidationError."""
        client = OilPriceAPI(api_key="test_key")

        with pytest.raises(ValidationError) as exc_info:
            client.diesel.get_stations(lat=37, lng=-181)

        assert "Longitude must be between -180 and 180" in exc_info.value.message

    def test_get_stations_invalid_lng_high(self):
        """Test that longitude > 180 raises ValidationError."""
        client = OilPriceAPI(api_key="test_key")

        with pytest.raises(ValidationError) as exc_info:
            client.diesel.get_stations(lat=37, lng=181)

        assert "Longitude must be between -180 and 180" in exc_info.value.message

    def test_get_stations_invalid_radius_negative(self):
        """Test that negative radius raises ValidationError."""
        client = OilPriceAPI(api_key="test_key")

        with pytest.raises(ValidationError) as exc_info:
            client.diesel.get_stations(lat=37, lng=-122, radius=-100)

        assert "Radius must be between 0 and 50000" in exc_info.value.message

    def test_get_stations_invalid_radius_too_large(self):
        """Test that radius > 50000 raises ValidationError."""
        client = OilPriceAPI(api_key="test_key")

        with pytest.raises(ValidationError) as exc_info:
            client.diesel.get_stations(lat=37, lng=-122, radius=50001)

        assert "Radius must be between 0 and 50000" in exc_info.value.message

    def test_get_stations_invalid_lat_type(self):
        """Test that non-numeric latitude raises ValidationError."""
        client = OilPriceAPI(api_key="test_key")

        with pytest.raises(ValidationError) as exc_info:
            client.diesel.get_stations(lat="invalid", lng=-122)

        assert "Latitude must be a number" in exc_info.value.message

    def test_get_stations_invalid_lng_type(self):
        """Test that non-numeric longitude raises ValidationError."""
        client = OilPriceAPI(api_key="test_key")

        with pytest.raises(ValidationError) as exc_info:
            client.diesel.get_stations(lat=37, lng="invalid")

        assert "Longitude must be a number" in exc_info.value.message

    def test_get_stations_invalid_radius_type(self):
        """Test that non-numeric radius raises ValidationError."""
        client = OilPriceAPI(api_key="test_key")

        with pytest.raises(ValidationError) as exc_info:
            client.diesel.get_stations(lat=37, lng=-122, radius="invalid")

        assert "Radius must be a number" in exc_info.value.message

    @patch('httpx.Client.request')
    def test_get_stations_custom_radius(self, mock_request):
        """Test getting stations with custom radius."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "regional_average": {
                "price": 3.89,
                "currency": "USD",
                "unit": "gallon",
                "region": "California",
                "granularity": "regional",
                "source": "Google Maps"
            },
            "stations": [],
            "search_area": {
                "center": {"lat": 37.7749, "lng": -122.4194},
                "radius_meters": 5000,
                "radius_miles": 3.1
            },
            "metadata": {
                "total_stations": 0,
                "source": "Google Maps",
                "cached": False,
                "api_cost": 0.024,
                "timestamp": "2025-12-15T10:00:00Z"
            }
        }
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key="test_key")
        result = client.diesel.get_stations(lat=37.7749, lng=-122.4194, radius=5000)

        # Check that request was made with custom radius
        call_args = mock_request.call_args
        assert call_args[1]["json"]["radius"] == 5000


class TestDieselResourceToDataFrame:
    """Test diesel.to_dataframe() method."""

    @patch('httpx.Client.request')
    def test_to_dataframe_state(self, mock_request):
        """Test converting single state price to DataFrame."""
        pytest.importorskip("pandas")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "regional_average": {
                "state": "CA",
                "price": 3.89,
                "currency": "USD",
                "unit": "gallon",
                "granularity": "state",
                "source": "EIA",
                "updated_at": "2025-12-15T10:00:00Z"
            }
        }
        mock_request.return_value = mock_response

        client = OilPriceAPI(api_key="test_key")
        df = client.diesel.to_dataframe(state="CA")

        assert len(df) == 1
        assert "state" in df.columns
        assert "price" in df.columns
        assert df.iloc[0]["state"] == "CA"
        assert df.iloc[0]["price"] == 3.89

    @patch('httpx.Client.request')
    def test_to_dataframe_multiple_states(self, mock_request):
        """Test converting multiple state prices to DataFrame."""
        pytest.importorskip("pandas")

        # Mock different responses for each state
        def mock_response_func(*args, **kwargs):
            state = kwargs["params"]["state"]
            response = Mock()
            response.status_code = 200

            prices = {"CA": 3.89, "TX": 3.45, "NY": 3.99}
            response.json.return_value = {
                "regional_average": {
                    "state": state,
                    "price": prices.get(state, 3.50),
                    "currency": "USD",
                    "unit": "gallon",
                    "granularity": "state",
                    "source": "EIA",
                    "updated_at": "2025-12-15T10:00:00Z"
                }
            }
            return response

        mock_request.side_effect = mock_response_func

        client = OilPriceAPI(api_key="test_key")
        df = client.diesel.to_dataframe(states=["CA", "TX", "NY"])

        assert len(df) == 3
        assert set(df["state"].values) == {"CA", "TX", "NY"}

    def test_to_dataframe_no_pandas(self):
        """Test that ImportError is raised when pandas not installed."""
        with patch.dict('sys.modules', {'pandas': None}):
            client = OilPriceAPI(api_key="test_key")

            with pytest.raises(ImportError) as exc_info:
                client.diesel.to_dataframe(state="CA")

            assert "pandas is required" in str(exc_info.value)

    def test_to_dataframe_no_params(self):
        """Test that ValueError is raised when no parameters provided."""
        pytest.importorskip("pandas")

        client = OilPriceAPI(api_key="test_key")

        with pytest.raises(ValueError) as exc_info:
            client.diesel.to_dataframe()

        assert "state/states" in str(exc_info.value) or "lat/lng" in str(exc_info.value)
