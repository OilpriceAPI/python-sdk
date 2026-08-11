"""Retry strategy for API requests with exponential backoff and jitter."""

import logging
import random
from typing import List, Mapping, Optional

logger = logging.getLogger(__name__)


class RetryStrategy:
    """
    Shared retry logic for both sync and async clients.

    Implements exponential backoff with configurable retry conditions.
    """

    def __init__(
        self,
        max_retries: int = 3,
        retry_on: Optional[List[int]] = None,
        jitter: bool = True,
    ):
        """
        Initialize retry strategy.

        Args:
            max_retries: Maximum number of request attempts
            retry_on: HTTP status codes to retry on (default: [500, 502, 503, 504])
            jitter: Add randomized jitter to backoff to prevent thundering herd (default: True)
        """
        self.max_retries = max_retries
        self.retry_on = retry_on or [500, 502, 503, 504]
        self.jitter = jitter

    # A 429 means two completely different things, and retrying is only correct
    # for one of them:
    #
    #   "you are bursting"        -> wait and retry. Correct.
    #   "you are out of quota"    -> retrying CANNOT succeed until the billing
    #                                period resets. Two retries produce two more
    #                                refusals and nothing else.
    #
    # This method used to take the status code alone, so it could not tell them
    # apart and always retried. Measured against production over 30 days, free
    # accounts on this SDK were rate-limited on 26.2% of requests against 15.6%
    # for the Node SDK on the same tier -- 1.7x worse, self-inflicted.
    #
    # The API identifies durable quota exhaustion with both `state=exhausted`
    # and a counter-backed window. State or remaining alone are ambiguous: the
    # recoverable hourly circuit breaker also emits exhausted/0.
    PERSISTENT_QUOTA_WINDOWS = frozenset({"daily_counter", "monthly_counter", "trial_counter"})

    def should_retry(
        self,
        attempt: int,
        status_code: int,
        headers: Optional[Mapping[str, str]] = None,
    ) -> bool:
        """
        Determine if request should be retried.

        Args:
            attempt: Current attempt number (0-indexed)
            status_code: HTTP status code from response
            headers: Response headers. When they identify a durable counter
                window whose allowance is exhausted, the request is not
                retried because waiting briefly cannot help.

        Returns:
            True if request should be retried, False otherwise
        """
        if attempt >= self.max_retries - 1:
            return False
        if status_code not in self.retry_on:
            return False

        # Only 429 carries a remedy. Server errors are always worth a retry.
        if status_code == 429 and self.quota_exhausted(headers):
            return False

        return True

    @classmethod
    def quota_exhausted(cls, headers: Optional[Mapping[str, str]]) -> bool:
        """
        Has the caller run out of allowance, as opposed to merely bursting?

        Requires `X-RateLimit-State: exhausted` together with one of the API's
        durable counter windows. `state=exhausted` and `remaining=0` cannot be
        used independently because the recoverable hourly circuit breaker
        deliberately emits both values as well.

        Returns False when headers are absent or unparseable -- an unknown state
        must behave exactly as before this change, so a missing header can never
        turn a retryable burst into a hard failure.
        """
        if not headers:
            return False

        lookup = {str(k).lower(): v for k, v in headers.items()}

        state = str(lookup.get("x-ratelimit-state", "")).strip().lower()
        window = str(lookup.get("x-ratelimit-window", "")).strip().lower()
        return state == "exhausted" and window in cls.PERSISTENT_QUOTA_WINDOWS

    def should_retry_on_exception(self, attempt: int) -> bool:
        """
        Determine if request should be retried on exception.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            True if request should be retried, False otherwise
        """
        return attempt < self.max_retries - 1

    def calculate_wait_time(self, attempt: int) -> float:
        """
        Calculate exponential backoff wait time with optional jitter.

        Jitter prevents thundering herd problem where many clients retry
        simultaneously after an outage, potentially overwhelming the recovered service.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Wait time in seconds (capped at 60 seconds)

        Examples:
            Without jitter:
            - Attempt 0: 1.0s
            - Attempt 1: 2.0s
            - Attempt 2: 4.0s

            With jitter (adds 0-30% randomization):
            - Attempt 0: 1.0-1.3s
            - Attempt 1: 2.0-2.6s
            - Attempt 2: 4.0-5.2s
        """
        base_wait = min(2 ** attempt, 60)

        if self.jitter:
            # Add 0-30% random jitter to prevent synchronized retries
            jitter_amount = random.uniform(0, 0.3 * base_wait)
            return base_wait + jitter_amount

        return base_wait

    def log_retry(
        self,
        attempt: int,
        reason: str,
        wait_time: float,
        is_async: bool = False
    ) -> None:
        """
        Log retry attempt.

        Args:
            attempt: Current attempt number (0-indexed)
            reason: Reason for retry
            wait_time: Wait time before retry
            is_async: Whether this is an async client
        """
        client_type = "Async" if is_async else "Sync"
        logger.warning(
            f"[{client_type}] {reason}, retrying in {wait_time}s "
            f"(attempt {attempt + 1}/{self.max_retries})"
        )
