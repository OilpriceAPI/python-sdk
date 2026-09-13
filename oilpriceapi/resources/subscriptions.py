"""
Subscriptions Resource

Agent "watch" subscriptions + event polling (#3245 Phase 2). Persistent watches
periodically evaluate commodity codes and emit events an agent can poll for.
"""

from typing import Any, Dict, List, Optional, Union

from .._subscriptions_common import (
    build_attribution_headers,
    build_create_body,
    build_update_body,
    unwrap_events_page,
    unwrap_subscription,
    unwrap_subscription_list,
    validate_since,
    validate_subscription_id,
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
            List of Subscription models. Empty only when the API sent an empty
            list.

        Raises:
            OilPriceAPIError: ``code="MALFORMED_RESPONSE"`` when a success body
                has no ``data.subscriptions`` list or a record in it is invalid.

        Example:
            >>> for sub in client.subscriptions.list():
            ...     print(sub.name, sub.codes)
        """
        response = self.client.request(method="GET", path="/v1/subscriptions")
        return unwrap_subscription_list(response, subject="subscriptions.list")

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
        return unwrap_subscription(response, subject="subscriptions.create")

    def get(self, subscription_id: str) -> Subscription:
        """Fetch one subscription.

        Args:
            subscription_id: The id returned by ``list()`` or ``create()``.

        Returns:
            The Subscription, with the server's timestamps and nulls as sent.

        Raises:
            ValidationError: If the id is malformed (``field="subscription_id"``,
                ``status_code=None``). Nothing is sent.
            DataNotFoundError: If no subscription with that id belongs to you.
            OilPriceAPIError: ``code="MALFORMED_RESPONSE"`` on a malformed success.

        Example:
            >>> sub = client.subscriptions.get("f72ceac2-8b9a-406a-a57e-90c625785444")
            >>> sub.status
            'active'
        """
        subscription_id = validate_subscription_id(subscription_id)
        response = self.client.request(
            method="GET",
            path=f"/v1/subscriptions/{subscription_id}",
        )
        return unwrap_subscription(response, subject="subscriptions.get")

    def update(
        self,
        subscription_id: str,
        *,
        name: Optional[str] = None,
        codes: Optional[List[str]] = None,
        interval: Optional[Union[str, int]] = None,
        deliver_webhook: Optional[bool] = None,
        status: Optional[str] = None,
    ) -> Subscription:
        """Change a subscription. Only the arguments you pass are sent.

        Sent once: a PATCH is not replayed after a timeout or 5xx. If one of
        those is raised with ``ambiguous_write=True``, call ``get()`` to see
        whether the change landed.

        Args:
            subscription_id: The subscription to change.
            name: New name.
            codes: Replacement list of commodity codes.
            interval: Friendly interval ("5m", "1h", "daily") or seconds.
            deliver_webhook: Whether events are delivered by webhook.
            status: ``"active"`` or ``"paused"``.

        Returns:
            The updated Subscription as the server stored it.

        Raises:
            ValidationError: ``status_code=None``, ``field`` naming the argument,
                if the id or any field is invalid, or no field is given. Nothing
                is sent. (Distinct from the server's 422, which has a status.)
            DataNotFoundError: If the subscription does not exist.
            ValidationError: 422 when the server refuses the change, for example
                an interval below your plan minimum or webhook delivery your
                plan does not include.

        Example:
            >>> client.subscriptions.update(sub.id, name="Brent hourly", interval="1h")
        """
        subscription_id = validate_subscription_id(subscription_id)
        body = build_update_body(
            name=name,
            codes=codes,
            interval=interval,
            deliver_webhook=deliver_webhook,
            status=status,
        )
        response = self.client.request(
            method="PATCH",
            path=f"/v1/subscriptions/{subscription_id}",
            json_data=body,
        )
        return unwrap_subscription(response, subject="subscriptions.update")

    def pause(self, subscription_id: str) -> Subscription:
        """Pause a subscription so it stops being evaluated.

        Sent once, like every write in this SDK: after an ambiguous timeout or
        5xx, call ``get()`` to check the status rather than retrying blind.

        Returns:
            The Subscription, with ``status == "paused"``.

        Example:
            >>> client.subscriptions.pause(sub.id).status
            'paused'
        """
        subscription_id = validate_subscription_id(subscription_id)
        response = self.client.request(
            method="POST",
            path=f"/v1/subscriptions/{subscription_id}/pause",
        )
        return unwrap_subscription(response, subject="subscriptions.pause")

    def resume(self, subscription_id: str) -> Subscription:
        """Resume a paused subscription. The server schedules it to run now.

        Returns:
            The Subscription, with ``status == "active"`` and the new
            ``next_run_at``.

        Example:
            >>> client.subscriptions.resume(sub.id).status
            'active'
        """
        subscription_id = validate_subscription_id(subscription_id)
        response = self.client.request(
            method="POST",
            path=f"/v1/subscriptions/{subscription_id}/resume",
        )
        return unwrap_subscription(response, subject="subscriptions.resume")

    def delete(self, subscription_id: str) -> bool:
        """Delete a subscription.

        Args:
            subscription_id: The subscription id to delete.

        Returns:
            True on success.

        Raises:
            ValidationError: If the id is malformed (``field="subscription_id"``,
                ``status_code=None``). Nothing is sent.

        Example:
            >>> client.subscriptions.delete(sub.id)
        """
        subscription_id = validate_subscription_id(subscription_id)
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
            since: ``page.cursor`` from the previous call; only events with
                ``seq > since`` are returned. Omit it (or pass ``0``) only to
                start from the first event. Must be a non-negative ``int``: the
                API reads any other value as ``0`` and replays every event.
            limit: Max events to return (server clamps to its own max).
            watch_id: Restrict to a single subscription.

        Returns:
            A SubscriptionEventsPage with events, cursor, and has_more. The
            cursor is always an ``int``, so ``events(since=page.cursor)`` never
            restarts from the beginning.

        Raises:
            ValidationError: ``field="since"``, ``status_code=None``, if ``since``
                is not a non-negative int. Nothing is sent.
            OilPriceAPIError: ``code="MALFORMED_RESPONSE"`` when a success body
                lacks the ``events`` list, an integer ``cursor`` or a boolean
                ``has_more``, or its cursor would move polling backwards.

        Example:
            >>> page = client.subscriptions.events(since=0)
            >>> for event in page:
            ...     print(event.seq, event.watch_id)
            >>> next_page = client.subscriptions.events(since=page.cursor)
        """
        since = validate_since(since)
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
        return unwrap_events_page(response, since=since, subject="subscriptions.events")
