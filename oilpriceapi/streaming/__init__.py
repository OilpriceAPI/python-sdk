"""
Real-time WebSocket streaming for OilPriceAPI.

Exposes an async streaming client over the Rails ActionCable ``/cable``
endpoint (``EnergyPricesChannel``). Available via ``AsyncOilPriceAPI.stream``.

Requires the optional ``[stream]`` extra::

    pip install 'oilpriceapi[stream]'
"""
from __future__ import annotations

from .client import (
    CHANNEL_NAME,
    AsyncStreamNamespace,
    PriceStream,
    StreamingNotInstalledError,
)
from .models import (
    NaturalGasPrices,
    NormalizedPrice,
    OilPrices,
    PriceBlock,
    PriceUpdate,
    RigCount,
    RigCountUpdate,
    StreamUpdate,
)

__all__ = [
    "AsyncStreamNamespace",
    "PriceStream",
    "StreamingNotInstalledError",
    "CHANNEL_NAME",
    "StreamUpdate",
    "PriceUpdate",
    "RigCountUpdate",
    "PriceBlock",
    "OilPrices",
    "NaturalGasPrices",
    "NormalizedPrice",
    "RigCount",
]
