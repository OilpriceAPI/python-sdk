"""Retry strategy for API requests with exponential backoff and jitter."""

import logging
import random
from typing import List, Mapping, Optional

logger = logging.getLogger(__name__)

AMBIGUOUS_WRITE_NOTE = (
    "This {method} was NOT retried: the server may have already processed it, "
    "and replaying it could create a duplicate. Check whether the write landed "
    "before sending it again. Pass idempotent=True to request() if repeating "
    "this call is safe."
)


def validated_max_retries(value: object) -> int:
    """Validate an explicit ``max_retries``.

    ``max_retries`` counts total ATTEMPTS, not retries after the first — that
    is what the clients have always documented and what the request loop does
    (``for attempt in range(self.max_retries)``). One attempt is the minimum;
    zero attempts would send nothing. This used to be swallowed by an ``or``
    default, which silently turned an explicit 0 into 3.
    """
    from .exceptions import ConfigurationError

    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(
            f"max_retries must be an int counting total attempts, got "
            f"{type(value).__name__}. Pass max_retries=1 for a single attempt "
            f"with no retries."
        )
    if value < 1:
        raise ConfigurationError(
            f"max_retries counts total attempts and must be at least 1, got {value}. "
            f"Pass max_retries=1 for a single attempt with no retries."
        )
    return value


def mark_ambiguous_write(error, method: Optional[str]):
    """Tell the caller the write was sent once and its outcome is unknown."""
    error.ambiguous_write = True
    note = AMBIGUOUS_WRITE_NOTE.format(method=str(method or "request").upper())
    error.message = f"{error.message} {note}"
    error.args = (error.message,)
    return error


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
        # None means "not configured"; an explicit [] means "retry on no status
        # code at all" and must survive (#104).
        self.retry_on = [500, 502, 503, 504] if retry_on is None else list(retry_on)
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

    # Replaying a request is only safe when repeating it has the same effect as
    # doing it once. RFC 9110 calls that idempotent. POST and PATCH are not:
    # a create the server committed just before the response was lost becomes
    # two creates on replay -- two subscriptions, two webhooks, two charges.
    #
    # A timeout or a transport error is AMBIGUOUS, not a failure: the SDK cannot
    # know whether the server processed the write. A 5xx is equally ambiguous,
    # because a gateway can return 502 after the origin already committed. Both
    # are therefore sent once for a non-idempotent method.
    #
    # 429 is the exception in the other direction: it is an outright refusal, so
    # the write definitively did not happen and replay is safe.
    IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE", "PUT", "DELETE"})

    # Bound on any wait, whether computed by backoff or handed to us by the
    # server in Retry-After. The keyless demo endpoint returns
    # `retry-after: 31612`, which unbounded would block a process for 8.8 hours.
    MAX_WAIT_SECONDS = 60.0

    @classmethod
    def is_replay_safe(
        cls,
        method: Optional[str] = None,
        idempotent: Optional[bool] = None,
    ) -> bool:
        """
        May this request be sent again after an ambiguous outcome?

        Args:
            method: HTTP method. ``None`` means the caller did not say, and is
                treated as safe so the public RetryStrategy contract is
                unchanged for existing callers. The SDK's own clients always
                pass it.
            idempotent: Caller's explicit assertion, which wins over the method.
                Pass True for a write you know is safe to repeat (your own
                server-side deduplication, a naturally idempotent endpoint).

        Returns:
            True if the request may be replayed.
        """
        if idempotent is not None:
            return bool(idempotent)
        if method is None:
            return True
        return str(method).upper() in cls.IDEMPOTENT_METHODS

    @classmethod
    def bounded_wait(cls, seconds: object, fallback: float) -> float:
        """
        Clamp a wait to [0, MAX_WAIT_SECONDS], falling back when unparseable.

        Both ends matter. Unbounded above, a server Retry-After can park a
        process for hours; below zero, ``time.sleep()`` raises ValueError.
        """
        try:
            value = float(seconds)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            value = float(fallback)
        if value != value:  # NaN
            value = float(fallback)
        return max(0.0, min(value, cls.MAX_WAIT_SECONDS))

    def should_retry(
        self,
        attempt: int,
        status_code: int,
        headers: Optional[Mapping[str, str]] = None,
        method: Optional[str] = None,
        idempotent: Optional[bool] = None,
    ) -> bool:
        """
        Determine if request should be retried.

        Args:
            attempt: Current attempt number (0-indexed)
            status_code: HTTP status code from response
            headers: Response headers. When they identify a durable counter
                window whose allowance is exhausted, the request is not
                retried because waiting briefly cannot help.
            method: HTTP method, so a non-idempotent write is never replayed
                after an ambiguous 5xx.
            idempotent: Caller's explicit override of the method check.

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

        # A 429 refused the request outright, so replaying a write is safe.
        # A 5xx may have committed it; do not replay.
        if status_code != 429 and not self.is_replay_safe(method, idempotent):
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

    def should_retry_on_exception(
        self,
        attempt: int,
        method: Optional[str] = None,
        idempotent: Optional[bool] = None,
    ) -> bool:
        """
        Determine if request should be retried on exception.

        A timeout or transport error is an ambiguous outcome, not a failure:
        the server may have processed the request before the response was lost.
        A non-idempotent write is therefore never replayed.

        Args:
            attempt: Current attempt number (0-indexed)
            method: HTTP method. Omitted means "unknown", treated as safe.
            idempotent: Caller's explicit override of the method check.

        Returns:
            True if request should be retried, False otherwise
        """
        if attempt >= self.max_retries - 1:
            return False
        return self.is_replay_safe(method, idempotent)

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
