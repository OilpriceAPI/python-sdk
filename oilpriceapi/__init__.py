"""
OilPriceAPI Python SDK

The official Python SDK for OilPriceAPI - Real-time and historical oil prices.
"""

from oilpriceapi.version import __version__

__author__ = "OilPriceAPI"
__email__ = "support@oilpriceapi.com"

from oilpriceapi.client import OilPriceAPI
from oilpriceapi.async_client import AsyncOilPriceAPI
from oilpriceapi.exceptions import (
    OilPriceAPIError,
    AuthenticationError,
    RateLimitError,
    DataNotFoundError,
    ServerError,
    ValidationError,
    TimeoutError,
    ConfigurationError,
)
from oilpriceapi.models import (
    DieselPrice,
    DieselStation,
    DieselStationsResponse,
    PriceAlert,
    WebhookTestResponse,
    DataConnectorPrice,
)

__all__ = [
    "OilPriceAPI",
    "AsyncOilPriceAPI",
    "OilPriceAPIError",
    "AuthenticationError",
    "RateLimitError",
    "DataNotFoundError",
    "ServerError",
    "ValidationError",
    "TimeoutError",
    "ConfigurationError",
    "DieselPrice",
    "DieselStation",
    "DieselStationsResponse",
    "PriceAlert",
    "WebhookTestResponse",
    "DataConnectorPrice",
]

from oilpriceapi.resources.webhooks import WebhooksResource

# Standalone webhook signature verification
verify_webhook_signature = WebhooksResource.verify_signature


# Convenience function for quick access
def get_current_price(commodity: str, api_key: str = None) -> float:
    """
    Quick helper to get current price without client initialization.

    Args:
        commodity: Commodity code (e.g., "BRENT_CRUDE_USD")
        api_key: Optional API key (uses environment variable if not provided)

    Returns:
        Current price as float

    Example:
        >>> import oilpriceapi as opa
        >>> price = opa.get_current_price("BRENT_CRUDE_USD")
        >>> print(f"Oil: ${price}")
    """
    with OilPriceAPI(api_key=api_key) as client:
        price = client.prices.get(commodity)
        return price.value