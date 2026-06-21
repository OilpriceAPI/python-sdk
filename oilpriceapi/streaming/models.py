"""
Pydantic models for WebSocket streaming payloads.

These mirror the broadcast shapes emitted by the OilPriceAPI ActionCable
``EnergyPricesChannel`` (see the API ``BroadcastEnergyPricesJob`` and channel
``send_initial_prices``). Three message types are streamed:

* ``welcome``           - initial snapshot sent on subscription
* ``price_update``      - debounced broadcast of the latest spot prices
* ``rig_count_update``  - drilling-intelligence rig count update
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _parse_ts(v: Any) -> Any:
    """Parse an ISO-8601 timestamp string into a ``datetime``."""
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            from dateutil import parser  # type: ignore[import-untyped]

            return parser.parse(v)
    return v


class NormalizedPrice(BaseModel):
    """A single normalized price entry inside a price block."""

    model_config = ConfigDict(populate_by_name=True)

    normalized_price: Optional[float] = Field(
        default=None, description="Price normalized to USD/MMBtu"
    )
    original_price: Optional[float] = Field(
        default=None, description="Price in its original unit/currency"
    )
    original_unit: Optional[str] = Field(default=None, description="Original unit of measure")
    original_currency: Optional[str] = Field(default=None, description="Original currency code")
    timestamp: Optional[datetime] = Field(default=None, description="Price timestamp")
    change_24h: Optional[float] = Field(default=None, description="Absolute 24h change")
    change_24h_percent: Optional[float] = Field(default=None, description="Percentage 24h change")

    @field_validator("timestamp", mode="before")
    @classmethod
    def _ts(cls, v: Any) -> Any:
        return _parse_ts(v)


class OilPrices(BaseModel):
    """Oil price block (Brent + WTI)."""

    model_config = ConfigDict(populate_by_name=True)

    brent: Optional[NormalizedPrice] = None
    wti: Optional[NormalizedPrice] = None


class NaturalGasPrices(BaseModel):
    """Natural gas price block (UK / US / EU)."""

    model_config = ConfigDict(populate_by_name=True)

    uk: Optional[NormalizedPrice] = None
    us: Optional[NormalizedPrice] = None
    eu: Optional[NormalizedPrice] = None


class PriceBlock(BaseModel):
    """Container of all normalized price groups in a broadcast."""

    model_config = ConfigDict(populate_by_name=True)

    oil: Optional[OilPrices] = None
    natural_gas: Optional[NaturalGasPrices] = None


class PriceUpdate(BaseModel):
    """A ``price_update`` (or ``welcome``) broadcast message.

    The ``welcome`` snapshot shares the same shape but carries ``type``
    ``"welcome"`` and an optional ``error`` field when initial data could not
    be assembled server-side.
    """

    model_config = ConfigDict(populate_by_name=True)

    type: str = Field(default="price_update", description="Message type")
    timestamp: Optional[datetime] = Field(default=None, description="Broadcast timestamp")
    base_currency: Optional[str] = Field(default=None, description="Normalization base currency")
    base_unit: Optional[str] = Field(default=None, description="Normalization base unit")
    prices: Optional[PriceBlock] = Field(default=None, description="Normalized price groups")
    error: Optional[str] = Field(default=None, description="Error message for degraded snapshots")

    @field_validator("timestamp", mode="before")
    @classmethod
    def _ts(cls, v: Any) -> Any:
        return _parse_ts(v)


class RigCount(BaseModel):
    """Rig count detail inside a ``rig_count_update`` message."""

    model_config = ConfigDict(populate_by_name=True)

    code: Optional[str] = Field(default=None, description="Drilling code, e.g. US_RIG_COUNT")
    region: Optional[str] = Field(default=None, description="Human-readable region name")
    count: Optional[float] = Field(default=None, description="Rig count value")
    source: Optional[str] = Field(default=None, description="Data source")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")

    @field_validator("updated_at", mode="before")
    @classmethod
    def _ts(cls, v: Any) -> Any:
        return _parse_ts(v)


class RigCountUpdate(BaseModel):
    """A ``rig_count_update`` broadcast message."""

    model_config = ConfigDict(populate_by_name=True)

    type: str = Field(default="rig_count_update", description="Message type")
    timestamp: Optional[datetime] = Field(default=None, description="Broadcast timestamp")
    rig_count: Optional[RigCount] = Field(default=None, description="Rig count detail")

    @field_validator("timestamp", mode="before")
    @classmethod
    def _ts(cls, v: Any) -> Any:
        return _parse_ts(v)


class StreamUpdate(BaseModel):
    """Wrapper yielded by the stream for any broadcast payload.

    ``raw`` always holds the decoded ``message`` dict. ``price_update`` /
    ``rig_count_update`` are populated when the payload matches a known type,
    so consumers can branch on ``update.type`` and read the typed model.
    """

    model_config = ConfigDict(populate_by_name=True)

    type: str = Field(description="Broadcast message type")
    raw: Dict[str, Any] = Field(description="Raw decoded message payload")
    price_update: Optional[PriceUpdate] = Field(default=None)
    rig_count_update: Optional[RigCountUpdate] = Field(default=None)

    @classmethod
    def from_message(cls, message: Dict[str, Any]) -> "StreamUpdate":
        """Build a typed update from a raw ActionCable ``message`` payload."""
        msg_type = str(message.get("type", "unknown"))
        price_update: Optional[PriceUpdate] = None
        rig_count_update: Optional[RigCountUpdate] = None

        if msg_type in ("price_update", "welcome"):
            price_update = PriceUpdate.model_validate(message)
        elif msg_type == "rig_count_update":
            rig_count_update = RigCountUpdate.model_validate(message)

        return cls(
            type=msg_type,
            raw=message,
            price_update=price_update,
            rig_count_update=rig_count_update,
        )
