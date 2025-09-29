# GitHub Issues for OilPriceAPI Python SDK

## Issue 1: Refactor Duplicate Retry Logic Between Sync and Async Clients

**Labels:** `enhancement`, `refactoring`, `technical-debt`

**Priority:** Low (Post-v1.0)

### Description

The retry logic is duplicated between the sync client (`client.py`) and async client (`async_client.py`), with over 170 lines of nearly identical code. This violates the DRY (Don't Repeat Yourself) principle and makes maintenance harder.

### Current State

**Sync Client (`client.py` lines 163-250):**
```python
# Retry logic
last_exception = None
for attempt in range(self.max_retries):
    try:
        response = self._client.request(...)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            raise AuthenticationError()
        elif response.status_code == 429:
            # Rate limit handling
            ...
        elif response.status_code >= 500:
            if response.status_code in self.retry_on and attempt < self.max_retries - 1:
                wait_time = min(2 ** attempt, 60)
                time.sleep(wait_time)
                continue
            raise ServerError(...)
    except httpx.TimeoutException:
        # Retry with exponential backoff
        ...
```

**Async Client (`async_client.py` lines 120-193):**
```python
# Nearly identical logic, just with `await` keywords
for attempt in range(self.max_retries):
    try:
        response = await self._client.request(...)
        # ... same error handling logic ...
        await asyncio.sleep(wait_time)
```

### Proposed Solution

Extract retry logic into a shared strategy class:

```python
class RetryStrategy:
    """Abstract retry logic for both sync and async clients."""

    def __init__(self, max_retries: int = 3, retry_on: List[int] = None):
        self.max_retries = max_retries
        self.retry_on = retry_on or [429, 500, 502, 503, 504]

    def should_retry(self, attempt: int, status_code: int) -> bool:
        """Determine if request should be retried."""
        return (
            status_code in self.retry_on
            and attempt < self.max_retries - 1
        )

    def wait_time(self, attempt: int) -> float:
        """Calculate exponential backoff wait time."""
        return min(2 ** attempt, 60)

    def handle_response(self, response: httpx.Response) -> Union[Dict, Exception]:
        """Parse response and return data or exception."""
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            return AuthenticationError(...)
        elif response.status_code == 404:
            return DataNotFoundError(...)
        # ... etc
```

Then clients would use:

```python
class OilPriceAPI:
    def __init__(self, ...):
        self.retry_strategy = RetryStrategy(max_retries, retry_on)

    def request(self, ...):
        for attempt in range(self.retry_strategy.max_retries):
            response = self._client.request(...)
            result = self.retry_strategy.handle_response(response)

            if isinstance(result, Exception):
                if self.retry_strategy.should_retry(attempt, response.status_code):
                    time.sleep(self.retry_strategy.wait_time(attempt))
                    continue
                raise result
            return result
```

### Benefits

1. **Single Source of Truth**: One place to update retry logic
2. **Easier Testing**: Test retry strategy independently
3. **Consistency**: Guaranteed identical behavior between sync/async
4. **Maintainability**: Changes only need to be made once

### Impact

- **Breaking Changes**: None (internal refactoring only)
- **Lines Saved**: ~150 lines of duplicated code
- **Risk**: Low - well-tested functionality

### Acceptance Criteria

- [ ] Create `RetryStrategy` class in new file `oilpriceapi/retry.py`
- [ ] Update `OilPriceAPI` to use strategy
- [ ] Update `AsyncOilPriceAPI` to use strategy
- [ ] All existing tests pass without modification
- [ ] Add unit tests for `RetryStrategy` class
- [ ] Update documentation if needed

### References

- Code review feedback from veteran Python programmer
- Related files:
  - `oilpriceapi/client.py`
  - `oilpriceapi/async_client.py`
  - Tests: `tests/unit/test_client.py`, `tests/unit/test_async_client.py`

### Notes

This is a **quality-of-life** improvement, not a bug fix. The current implementation works correctly, it's just not as maintainable as it could be. Recommended for v1.1 or v2.0 release.

---

## Future Issues Placeholder

Add additional issues as they are identified during production use.