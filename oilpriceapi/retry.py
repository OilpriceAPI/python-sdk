"""Retry strategy for API requests with exponential backoff and jitter."""

import logging
import random
from typing import List, Optional

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
            max_retries: Maximum number of retry attempts
            retry_on: HTTP status codes to retry on (default: [500, 502, 503, 504])
            jitter: Add randomized jitter to backoff to prevent thundering herd (default: True)
        """
        self.max_retries = max_retries
        self.retry_on = retry_on or [500, 502, 503, 504]
        self.jitter = jitter

    def should_retry(self, attempt: int, status_code: int) -> bool:
        """
        Determine if request should be retried.

        Args:
            attempt: Current attempt number (0-indexed)
            status_code: HTTP status code from response

        Returns:
            True if request should be retried, False otherwise
        """
        return (
            status_code in self.retry_on
            and attempt < self.max_retries - 1
        )

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
