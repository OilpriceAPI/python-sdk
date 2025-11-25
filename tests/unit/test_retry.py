"""Tests for retry strategy with exponential backoff and jitter."""

import pytest
from oilpriceapi.retry import RetryStrategy


class TestRetryStrategy:
    """Test retry strategy configuration and behavior."""

    def test_default_configuration(self):
        """Verify default retry configuration."""
        strategy = RetryStrategy()

        assert strategy.max_retries == 3
        assert strategy.retry_on == [500, 502, 503, 504]
        assert strategy.jitter is True

    def test_custom_configuration(self):
        """Verify custom retry configuration."""
        strategy = RetryStrategy(
            max_retries=5,
            retry_on=[429, 500],
            jitter=False
        )

        assert strategy.max_retries == 5
        assert strategy.retry_on == [429, 500]
        assert strategy.jitter is False

    def test_should_retry_on_retryable_status(self):
        """Verify retry on configured status codes."""
        strategy = RetryStrategy(max_retries=3, retry_on=[500, 502])

        # Should retry on first attempt for retryable status
        assert strategy.should_retry(attempt=0, status_code=500) is True
        assert strategy.should_retry(attempt=0, status_code=502) is True

        # Should retry on second attempt
        assert strategy.should_retry(attempt=1, status_code=500) is True

    def test_should_not_retry_on_non_retryable_status(self):
        """Verify no retry on non-configured status codes."""
        strategy = RetryStrategy(retry_on=[500, 502])

        # Should not retry on 404 (not in retry_on list)
        assert strategy.should_retry(attempt=0, status_code=404) is False
        assert strategy.should_retry(attempt=0, status_code=429) is False

    def test_should_not_retry_after_max_attempts(self):
        """Verify no retry after max attempts reached."""
        strategy = RetryStrategy(max_retries=3)

        # Last attempt (attempt 2) should not retry
        assert strategy.should_retry(attempt=2, status_code=500) is False

    def test_should_retry_on_exception(self):
        """Verify retry on exceptions."""
        strategy = RetryStrategy(max_retries=3)

        # Should retry on first attempts
        assert strategy.should_retry_on_exception(attempt=0) is True
        assert strategy.should_retry_on_exception(attempt=1) is True

        # Should not retry on last attempt
        assert strategy.should_retry_on_exception(attempt=2) is False

    def test_exponential_backoff_without_jitter(self):
        """Verify exponential backoff calculation without jitter."""
        strategy = RetryStrategy(jitter=False)

        # Should follow 2^n pattern
        assert strategy.calculate_wait_time(attempt=0) == 1.0
        assert strategy.calculate_wait_time(attempt=1) == 2.0
        assert strategy.calculate_wait_time(attempt=2) == 4.0
        assert strategy.calculate_wait_time(attempt=3) == 8.0
        assert strategy.calculate_wait_time(attempt=4) == 16.0
        assert strategy.calculate_wait_time(attempt=5) == 32.0

        # Should cap at 60 seconds
        assert strategy.calculate_wait_time(attempt=10) == 60.0

    def test_exponential_backoff_with_jitter(self):
        """Verify exponential backoff adds randomized jitter."""
        strategy = RetryStrategy(jitter=True)

        # Run multiple times to verify randomness
        wait_times_attempt_0 = [strategy.calculate_wait_time(0) for _ in range(100)]
        wait_times_attempt_1 = [strategy.calculate_wait_time(1) for _ in range(100)]
        wait_times_attempt_2 = [strategy.calculate_wait_time(2) for _ in range(100)]

        # Attempt 0: base 1s + jitter (0-0.3s) = 1.0-1.3s
        assert all(1.0 <= t <= 1.3 for t in wait_times_attempt_0)
        assert len(set(wait_times_attempt_0)) > 50  # Should have variance

        # Attempt 1: base 2s + jitter (0-0.6s) = 2.0-2.6s
        assert all(2.0 <= t <= 2.6 for t in wait_times_attempt_1)
        assert len(set(wait_times_attempt_1)) > 50

        # Attempt 2: base 4s + jitter (0-1.2s) = 4.0-5.2s
        assert all(4.0 <= t <= 5.2 for t in wait_times_attempt_2)
        assert len(set(wait_times_attempt_2)) > 50

    def test_jitter_prevents_synchronized_retries(self):
        """Verify jitter creates different wait times for concurrent clients."""
        strategy = RetryStrategy(jitter=True)

        # Simulate 10 concurrent clients all retrying at same time
        wait_times = [strategy.calculate_wait_time(attempt=1) for _ in range(10)]

        # All should be in valid range
        assert all(2.0 <= t <= 2.6 for t in wait_times)

        # Should have multiple unique values (not all the same)
        unique_times = set(wait_times)
        assert len(unique_times) >= 5  # At least 5 different wait times

    def test_jitter_maintains_cap_at_60_seconds(self):
        """Verify jitter still respects 60-second cap."""
        strategy = RetryStrategy(jitter=True)

        # Even with jitter, should cap at 60 + (30% of 60) = 78 seconds max
        wait_times = [strategy.calculate_wait_time(attempt=10) for _ in range(100)]

        # All should be capped properly
        assert all(60.0 <= t <= 78.0 for t in wait_times)

    def test_log_retry_formats_message(self, caplog):
        """Verify retry logging format."""
        strategy = RetryStrategy()

        with caplog.at_level("WARNING"):
            strategy.log_retry(
                attempt=1,
                reason="Server error 500",
                wait_time=2.5,
                is_async=False
            )

        assert "Server error 500" in caplog.text
        assert "2.5s" in caplog.text
        assert "attempt 2/3" in caplog.text
        assert "[Sync]" in caplog.text

    def test_log_retry_async_client(self, caplog):
        """Verify async client logging format."""
        strategy = RetryStrategy()

        with caplog.at_level("WARNING"):
            strategy.log_retry(
                attempt=0,
                reason="Request timeout",
                wait_time=1.0,
                is_async=True
            )

        assert "Request timeout" in caplog.text
        assert "[Async]" in caplog.text
