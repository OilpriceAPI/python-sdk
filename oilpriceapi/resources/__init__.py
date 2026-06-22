"""
OilPriceAPI Resources

Resource modules for different API endpoints.
"""

from .alerts import AlertsResource
from .analysis import AnalysisResource
from .analytics import AnalyticsResource
from .bunker_fuels import BunkerFuelsResource
from .commodities import CommoditiesResource
from .data_quality import DataQualityResource
from .data_sources import DataSourcesResource
from .demo import DemoResource
from .diesel import DieselResource
from .drilling import DrillingIntelligenceResource
from .ei import EnergyIntelligenceResource
from .forecasts import ForecastsResource
from .futures import FuturesResource
from .historical import HistoricalResource
from .prices import PricesResource
from .rig_counts import RigCountsResource
from .storage import StorageResource
from .subscriptions import SubscriptionsResource
from .webhooks import WebhooksResource

__all__ = [
    "AnalysisResource",
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
    "DrillingIntelligenceResource",
    "EnergyIntelligenceResource",
    "WebhooksResource",
    "DataSourcesResource",
    "DemoResource",
    "SubscriptionsResource",
]
