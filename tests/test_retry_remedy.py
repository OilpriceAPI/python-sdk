"""Retry must distinguish "you are bursting" from "you are out of quota".

Measured against production over 30 days: free accounts on this SDK were
rate-limited on 26.2% of requests against 15.6% for the Node SDK on the same
tier. `should_retry` took the status code alone, so a quota-exhausted 429 --
which cannot succeed until the billing period resets -- was tried three times,
turning one refusal into three.

The API distinguishes the two cases with the combination of
`X-RateLimit-State` and `X-RateLimit-Window` (oilpriceapi-api#5664). The state
alone is ambiguous: both a durable quota wall and the recoverable hourly
circuit breaker use `exhausted`.
"""

import pytest

from oilpriceapi.retry import RetryStrategy


@pytest.fixture
def strategy():
    return RetryStrategy(max_retries=3, retry_on=[429, 500, 502, 503, 504])


class TestQuotaExhaustedIsNotRetried:
    @pytest.mark.parametrize("window", ["daily_counter", "monthly_counter", "trial_counter"])
    def test_durable_quota_windows_stop_the_retry(self, strategy, window):
        headers = {
            "X-RateLimit-State": "exhausted",
            "X-RateLimit-Window": window,
            "X-RateLimit-Remaining": "0",
        }
        assert strategy.should_retry(0, 429, headers) is False

    def test_header_name_is_matched_case_insensitively(self, strategy):
        # HTTP header names are case-insensitive and clients normalise them
        # differently. Matching on exact case would silently disable this.
        headers = {
            "x-ratelimit-state": "EXHAUSTED",
            "x-ratelimit-window": "MONTHLY_COUNTER",
        }
        assert strategy.should_retry(0, 429, headers) is False


class TestBurstingIsStillRetried:
    def test_hourly_circuit_breaker_preserves_retry_behavior(self, strategy):
        # The API deliberately emits `state=exhausted` for this recoverable
        # safety limit. Looking at state or remaining alone would suppress the
        # existing bounded retry path even though this is not a durable quota.
        headers = {
            "X-RateLimit-State": "exhausted",
            "X-RateLimit-Window": "hourly_circuit_breaker",
            "X-RateLimit-Remaining": "0",
            "Retry-After": "1050",
        }
        assert strategy.should_retry(0, 429, headers) is True

    @pytest.mark.parametrize(
        "headers",
        [
            {"X-RateLimit-State": "exhausted"},
            {"X-RateLimit-Remaining": "0"},
            {
                "X-RateLimit-State": "unavailable",
                "X-RateLimit-Window": "enforcement_check",
            },
            {
                "X-RateLimit-State": "exhausted",
                "X-RateLimit-Window": "future_counter_contract",
            },
        ],
    )
    def test_ambiguous_or_recoverable_metadata_fails_open(self, strategy, headers):
        assert strategy.should_retry(0, 429, headers) is True

    def test_retries_when_headers_are_absent(self, strategy):
        # The critical safety property. An unknown state must behave exactly as
        # it did before this change, so a missing header can never convert a
        # retryable burst into a hard failure.
        assert strategy.should_retry(0, 429, None) is True
        assert strategy.should_retry(0, 429, {}) is True

    def test_server_errors_retry_regardless_of_rate_limit_headers(self, strategy):
        # A 500 carries no remedy. Exhausted allowance must not suppress it.
        headers = {"X-RateLimit-State": "exhausted"}
        for code in (500, 502, 503, 504):
            assert strategy.should_retry(0, code, headers) is True


class TestExistingBehaviourUnchanged:
    def test_attempt_budget_still_respected(self, strategy):
        assert strategy.should_retry(2, 429, None) is False

    def test_non_retryable_status_still_not_retried(self, strategy):
        # 402 must never be retried: it is a payment problem, not a timing one.
        assert strategy.should_retry(0, 402, None) is False
        assert strategy.should_retry(0, 404, None) is False

    def test_two_argument_calls_still_work(self, strategy):
        # `headers` is optional so third-party callers of this public method do
        # not break on upgrade.
        assert strategy.should_retry(0, 500) is True
        assert strategy.should_retry(0, 404) is False


class TestTheProductionScenario:
    def test_a_free_account_out_of_quota_makes_exactly_one_request(self, strategy):
        """The defect, stated as a test.

        A free account that has spent its 200 daily requests previously issued
        1 request + 2 retries = 3 refusals per call. It must now issue 1.
        """
        headers = {
            "X-RateLimit-Limit": "200",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-State": "exhausted",
            "X-RateLimit-Window": "daily_counter",
        }
        attempts = sum(
            1
            for attempt in range(strategy.max_retries)
            if strategy.should_retry(attempt, 429, headers)
        )
        assert attempts == 0, "a quota-exhausted 429 must not be retried at all"
