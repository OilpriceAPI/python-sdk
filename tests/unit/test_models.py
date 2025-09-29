"""
Unit tests for data models.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from oilpriceapi.models import (
    Price,
    PriceResponse,
    HistoricalPrice,
    HistoricalResponse,
    PaginationMeta,
    Commodity,
    ApiStatus,
    UsageStats,
)


class TestPriceModel:
    """Test Price model."""

    def test_price_creation(self, sample_price_data):
        """Test creating a Price instance."""
        price = Price(**sample_price_data)

        assert price.commodity == "BRENT_CRUDE_USD"
        assert price.value == 75.50
        assert price.currency == "USD"
        assert price.unit == "barrel"
        assert isinstance(price.timestamp, datetime)
        assert price.change == 1.25
        assert price.change_percent == 1.68

    def test_price_minimal_data(self):
        """Test Price with minimal required fields."""
        price = Price(
            commodity="WTI_USD",
            value=70.25,
            currency="USD",
            unit="barrel",
            timestamp=datetime.now(),
        )

        assert price.commodity == "WTI_USD"
        assert price.value == 70.25
        assert price.change is None
        assert price.change_percent is None

    def test_price_is_up(self):
        """Test is_up property."""
        price_up = Price(
            commodity="TEST",
            value=100,
            currency="USD",
            unit="unit",
            timestamp=datetime.now(),
            change=1.5,
        )
        assert price_up.is_up is True
        assert price_up.is_down is False

    def test_price_is_down(self):
        """Test is_down property."""
        price_down = Price(
            commodity="TEST",
            value=100,
            currency="USD",
            unit="unit",
            timestamp=datetime.now(),
            change=-2.0,
        )
        assert price_down.is_up is False
        assert price_down.is_down is True

    def test_price_string_representation_up(self):
        """Test string representation with positive change."""
        price = Price(
            commodity="BRENT_CRUDE_USD",
            value=75.50,
            currency="USD",
            unit="barrel",
            timestamp=datetime.now(),
            change=1.25,
            change_percent=1.68,
        )

        result = str(price)
        assert "BRENT_CRUDE_USD" in result
        assert "USD75.50" in result
        assert "↑" in result
        assert "1.68%" in result

    def test_price_string_representation_down(self):
        """Test string representation with negative change."""
        price = Price(
            commodity="WTI_USD",
            value=70.25,
            currency="USD",
            unit="barrel",
            timestamp=datetime.now(),
            change=-0.75,
            change_percent=-1.06,
        )

        result = str(price)
        assert "WTI_USD" in result
        assert "↓" in result
        assert "1.06%" in result

    def test_price_timestamp_parsing_iso_z(self):
        """Test timestamp parsing with Z suffix."""
        price = Price(
            commodity="TEST",
            value=100,
            currency="USD",
            unit="unit",
            timestamp="2024-01-15T10:00:00Z",
        )
        assert isinstance(price.timestamp, datetime)
        assert price.timestamp.year == 2024
        assert price.timestamp.month == 1
        assert price.timestamp.day == 15

    def test_price_timestamp_parsing_iso_offset(self):
        """Test timestamp parsing with timezone offset."""
        price = Price(
            commodity="TEST",
            value=100,
            currency="USD",
            unit="unit",
            timestamp="2024-01-15T10:00:00+00:00",
        )
        assert isinstance(price.timestamp, datetime)

    def test_price_change_percent_alias(self):
        """Test change_percentage alias works."""
        data = {
            "commodity": "TEST",
            "value": 100,
            "currency": "USD",
            "unit": "unit",
            "timestamp": datetime.now(),
            "change_percentage": 2.5,  # Using alias
        }
        price = Price(**data)
        assert price.change_percent == 2.5


class TestHistoricalPriceModel:
    """Test HistoricalPrice model."""

    def test_historical_price_creation(self, sample_historical_price_data):
        """Test creating HistoricalPrice."""
        price = HistoricalPrice(**sample_historical_price_data)

        assert isinstance(price.date, datetime)
        assert price.commodity == "BRENT_CRUDE_USD"
        assert price.value == 75.50
        assert price.unit == "barrel"
        assert price.type_name == "spot_price"

    def test_historical_price_field_aliases(self):
        """Test field aliases work correctly."""
        data = {
            "created_at": "2024-01-01T10:00:00Z",
            "commodity_name": "WTI_USD",
            "price": 70.25,
            "unit_of_measure": "barrel",
        }
        price = HistoricalPrice(**data)

        assert price.date is not None
        assert price.commodity == "WTI_USD"
        assert price.value == 70.25
        assert price.unit == "barrel"

    def test_historical_price_date_parsing(self):
        """Test date parsing from string."""
        price = HistoricalPrice(
            created_at="2024-01-15T10:00:00Z",
            commodity_name="TEST",
            price=100.0,
            unit_of_measure="barrel",
        )
        assert isinstance(price.date, datetime)
        assert price.date.year == 2024


class TestPaginationMeta:
    """Test PaginationMeta model."""

    def test_pagination_meta_creation(self):
        """Test creating pagination metadata."""
        meta = PaginationMeta(
            page=2,
            per_page=100,
            total=500,
            total_pages=5,
            has_next=True,
            has_prev=True,
        )

        assert meta.page == 2
        assert meta.per_page == 100
        assert meta.total == 500
        assert meta.total_pages == 5
        assert meta.has_next is True
        assert meta.has_prev is True

    def test_pagination_first_page(self):
        """Test pagination metadata for first page."""
        meta = PaginationMeta(
            page=1,
            per_page=100,
            total=300,
            total_pages=3,
            has_next=True,
            has_prev=False,
        )

        assert meta.page == 1
        assert meta.has_prev is False
        assert meta.has_next is True

    def test_pagination_last_page(self):
        """Test pagination metadata for last page."""
        meta = PaginationMeta(
            page=5,
            per_page=100,
            total=500,
            total_pages=5,
            has_next=False,
            has_prev=True,
        )

        assert meta.page == 5
        assert meta.has_next is False
        assert meta.has_prev is True


class TestCommodityModel:
    """Test Commodity model."""

    def test_commodity_creation(self):
        """Test creating Commodity."""
        commodity = Commodity(
            code="BRENT_CRUDE_USD",
            name="Brent Crude Oil",
            category="oil",
            unit="barrel",
            currency="USD",
            description="North Sea Brent Crude",
        )

        assert commodity.code == "BRENT_CRUDE_USD"
        assert commodity.name == "Brent Crude Oil"
        assert commodity.category == "oil"
        assert commodity.unit == "barrel"
        assert commodity.currency == "USD"

    def test_commodity_without_description(self):
        """Test Commodity without optional description."""
        commodity = Commodity(
            code="WTI_USD",
            name="West Texas Intermediate",
            category="oil",
            unit="barrel",
            currency="USD",
        )

        assert commodity.description is None


class TestResponseModels:
    """Test response wrapper models."""

    def test_price_response(self, sample_price_data):
        """Test PriceResponse model."""
        price = Price(**sample_price_data)
        response = PriceResponse(
            data=price,
            timestamp=datetime.now(),
        )

        assert response.success is True
        assert isinstance(response.data, Price)
        assert isinstance(response.timestamp, datetime)

    def test_historical_response(self, sample_historical_price_data):
        """Test HistoricalResponse model."""
        price = HistoricalPrice(**sample_historical_price_data)
        meta = PaginationMeta(
            page=1,
            per_page=100,
            total=1,
            total_pages=1,
            has_next=False,
            has_prev=False,
        )

        response = HistoricalResponse(
            data=[price],
            meta=meta,
        )

        assert response.success is True
        assert len(response.data) == 1
        assert isinstance(response.data[0], HistoricalPrice)
        assert isinstance(response.meta, PaginationMeta)


class TestApiStatusModel:
    """Test ApiStatus model."""

    def test_api_status_creation(self):
        """Test creating ApiStatus."""
        status = ApiStatus(
            status="operational",
            version="1.0.0",
            timestamp=datetime.now(),
            uptime=99.9,
            response_time=125.5,
        )

        assert status.status == "operational"
        assert status.version == "1.0.0"
        assert status.uptime == 99.9
        assert status.response_time == 125.5


class TestUsageStatsModel:
    """Test UsageStats model."""

    def test_usage_stats_creation(self):
        """Test creating UsageStats."""
        stats = UsageStats(
            requests_today=450,
            requests_this_month=12500,
            limit_daily=1000,
            limit_monthly=50000,
            remaining_today=550,
            remaining_this_month=37500,
            reset_at=datetime.now(),
            plan="Professional",
        )

        assert stats.requests_today == 450
        assert stats.requests_this_month == 12500
        assert stats.limit_monthly == 50000
        assert stats.remaining_this_month == 37500
        assert stats.plan == "Professional"

    def test_usage_stats_without_daily_limit(self):
        """Test UsageStats without daily limit."""
        stats = UsageStats(
            requests_today=100,
            requests_this_month=1000,
            limit_monthly=10000,
            remaining_this_month=9000,
            reset_at=datetime.now(),
            plan="Hobby",
        )

        assert stats.limit_daily is None
        assert stats.remaining_today is None