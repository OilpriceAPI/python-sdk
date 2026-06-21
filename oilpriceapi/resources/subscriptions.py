"""
Subscriptions Resource

Agent "watch" subscriptions + event polling (#3245 Phase 2). Persistent watches
periodically evaluate commodity codes and emit events an agent can poll for.
"""

from typing import Any, Dict, List, Optional, Union, cast

from .._subscriptions_common import (
    build_attribution_headers,
    build_create_body,
    unwrap_data,
)
from ..models import Subscription, SubscriptionEvent


class SubscriptionEventsPage:
    """A single page of subscription events from the poll endpoint.

    Attributes:
        events: The events in this page.
        cursor: The latest sequence number seen; pass as ``since`` next poll.
        has_more: Whether more events are immediately available.
    """

    def __init__(self, events: List[SubscriptionEvent], cursor: Optional[int], has_more: bool) -> None:
        self.events = events
        self.cursor = cursor
        self.has_more = has_more

    def __iter__(self):
        return iter(self.events)

    def __len__(self) -> int:
        return len(self.events)

    def __repr__(self) -> str:
        return f"SubscriptionEventsPage(events={len(self.events)}, cursor={self.cursor}, has_more={self.has_more})"


class SubscriptionsResource:
    """Resource for agent-subscription CRUD and event polling."""

    def __init__(self, client: Any) -> None:
        """Initialize subscriptions resource.

        Args:
            client: OilPriceAPI client instance
        """
        self.client = client

    def list(self) -> List[Subscription]:
        """List all subscriptions for the authenticated user.

        Returns:
            List of Subscription models.

        Example:
            >>> for sub in client.subscriptions.list():
            ...     print(sub.name, sub.codes)
        """
        response = self.client.request(method="GET", path="/v1/subscriptions")
        data = unwrap_data(response)
        subs = data.get("subscriptions", [])
        return [Subscription(**s) for s in subs]

    def create(
        self,
        codes: List[str],
        interval: Union[str, int],
        name: Optional[str] = None,
        source: Optional[str] = None,
        tool: Optional[str] = None,
    ) -> Subscription:
        """Create a new subscription (watch).

        Args:
            codes: Commodity codes to watch (e.g. ["BRENT_CRUDE_USD"]).
            interval: Friendly interval ("5m", "1h", "daily") or seconds (int).
            name: Optional human-friendly name.
            source: Attribution source header (defaults to "sdk-python").
            tool: Optional attribution tool name header.

        Returns:
            The created Subscription model.

        Example:
            >>> sub = client.subscriptions.create(
            ...     ["BRENT_CRUDE_USD"], interval="5m", name="Brent watch"
            ... )
        """
        body = build_create_body(codes, interval, name=name)
        headers = build_attribution_headers(source=source, tool=tool)
        response = self.client.request(
            method="POST",
            path="/v1/subscriptions",
            json_data=body,
            headers=headers,
        )
        data = unwrap_data(response)
        sub = data.get("subscription", data)
        return Subscription(**sub)

    def delete(self, subscription_id: str) -> bool:
        """Delete a subscription.

        Args:
            subscription_id: The subscription id to delete.

        Returns:
            True on success.

        Example:
            >>> client.subscriptions.delete(sub.id)
        """
        self.client.request(
            method="DELETE",
            path=f"/v1/subscriptions/{subscription_id}",
        )
        return True

    def events(
        self,
        since: Optional[int] = None,
        limit: Optional[int] = None,
        watch_id: Optional[str] = None,
    ) -> SubscriptionEventsPage:
        """Poll for subscription events newer than a cursor.

        Args:
            since: Sequence cursor; only events with seq > since are returned.
            limit: Max events to return (server clamps to its own max).
            watch_id: Restrict to a single subscription.

        Returns:
            A SubscriptionEventsPage with events, cursor, and has_more.

        Example:
            >>> page = client.subscriptions.events(since=0)
            >>> for event in page:
            ...     print(event.type, event.code)
            >>> next_page = client.subscriptions.events(since=page.cursor)
        """
        params: Dict[str, Any] = {}
        if since is not None:
            params["since"] = since
        if limit is not None:
            params["limit"] = limit
        if watch_id is not None:
            params["watch_id"] = watch_id

        response = self.client.request(
            method="GET",
            path="/v1/subscriptions/events",
            params=params,
        )
        data = unwrap_data(response)
        events = [SubscriptionEvent(**e) for e in data.get("events", [])]
        cursor = cast(Optional[int], data.get("cursor"))
        has_more = bool(data.get("has_more", False))
        return SubscriptionEventsPage(events=events, cursor=cursor, has_more=has_more)
