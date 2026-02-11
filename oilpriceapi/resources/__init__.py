"""
OilPriceAPI Resources

Resource modules for different API endpoints.
"""

from .prices import PricesResource
from .historical import HistoricalResource
from .diesel import DieselResource
from .alerts import AlertsResource
from .commodities import CommoditiesResource
from .futures import FuturesResource
from .storage import StorageResource
from .rig_counts import RigCountsResource
from .bunker_fuels import BunkerFuelsResource
from .analytics import AnalyticsResource
from .forecasts import ForecastsResource
from .data_quality import DataQualityResource

__all__ = [
    "PricesResource",
    "HistoricalResource",
    "DieselResource",
    "AlertsResource",
    "CommoditiesResource",
    "FuturesResource",
    "StorageResource",
    "RigCountsResource",
    "BunkerFuelsResource",
    "AnalyticsResource",
    "ForecastsResource",
    "DataQualityResource",
]
