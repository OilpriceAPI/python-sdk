"""POST-shaped READS must keep their retries; genuine writes must not (#118).

#115 keyed replay safety on the HTTP method, which is right, but no audit of
the SDK's own call sites was done. Four of them are POSTs that read: a query
with a body, or a diagnostic. They create nothing, and repeating one has the
same effect as doing it once, so removing their retries was a pure availability
regression with no safety benefit.

How a read-shaped POST is distinguished from a write, in one line: **the
endpoint creates or mutates no server-side resource, and the same request sent
twice returns the same answer.** `POST /v1/diesel-prices/stations` is a
lat/lng/radius query. The `/test` endpoints send a diagnostic through an
already-configured webhook and explicitly do not count against trigger limits.
Everything else -- `create()`, `rotate_credentials()` -- commits state, and
must stay non-replayable.

The distinction is declared at the call site with `idempotent=True`, which is
the mechanism #115 already built. `test_every_post_call_site_declares_intent`
below makes the next POST added to this SDK fail CI until someone decides
which kind it is.
"""

import ast
import asyncio
import pathlib
from unittest.mock import patch

import httpx
import pytest

import oilpriceapi
from oilpriceapi import AsyncOilPriceAPI, OilPriceAPI
from oilpriceapi.exceptions import OilPriceAPIError

# Not a credential: a fixture string, every request here hits a mock transport.
FIXTURE_KEY = "-".join(["fixture", "not", "a", "real", "key"])


class _Counter:
    def __init__(self, code=503):
        self.requests = []
        self._code = code

    def __call__(self, request):
        self.requests.append((request.method, str(request.url)))
        return httpx.Response(self._code, json={"error": "nope"})


def _sync_client(counter):
    client = OilPriceAPI(api_key=FIXTURE_KEY)
    client._client = httpx.Client(
        base_url=client.base_url,
        headers=client.headers,
        transport=httpx.MockTransport(counter),
    )
    return client


def _async_client(counter):
    client = AsyncOilPriceAPI(api_key=FIXTURE_KEY)
    client._client = httpx.AsyncClient(
        base_url=client.base_url,
        headers=client.headers,
        transport=httpx.MockTransport(counter),
    )
    return client


def _run_async(call):
    counter = _Counter()

    async def scenario():
        client = _async_client(counter)
        with pytest.raises(OilPriceAPIError):
            await call(client)
        await client._client.aclose()

    async def fake_sleep(seconds):
        return None

    with patch("asyncio.sleep", fake_sleep):
        asyncio.run(scenario())
    return counter


# ---------------------------------------------------------------------------
# (a) Read-shaped POSTs ride out a transient 5xx


READ_SHAPED_SYNC = [
    pytest.param(
        lambda c: c.diesel.get_stations(lat=37.7749, lng=-122.4194),
        id="diesel.get_stations",
    ),
    pytest.param(lambda c: c.webhooks.test("123"), id="webhooks.test"),
    pytest.param(lambda c: c.alerts.test("123"), id="alerts.test"),
]

READ_SHAPED_ASYNC = [
    pytest.param(
        lambda c: c.diesel.get_stations(lat=37.7749, lng=-122.4194),
        id="diesel.get_stations",
    ),
    pytest.param(lambda c: c.webhooks.test("123"), id="webhooks.test"),
    pytest.param(lambda c: c.alerts.test("123"), id="alerts.test"),
]


@pytest.mark.parametrize("call", READ_SHAPED_SYNC)
def test_sync_read_shaped_post_is_retried(call):
    counter = _Counter()
    client = _sync_client(counter)

    with patch("time.sleep"):
        with pytest.raises(OilPriceAPIError):
            call(client)

    methods = [m for m, _ in counter.requests]
    assert methods == ["POST", "POST", "POST"], (
        "a read-shaped POST lost its retries: a single bad gateway response "
        "now fails a call that creates nothing"
    )


@pytest.mark.parametrize("call", READ_SHAPED_ASYNC)
def test_async_read_shaped_post_is_retried(call):
    counter = _run_async(call)

    methods = [m for m, _ in counter.requests]
    assert methods == ["POST", "POST", "POST"]


def test_sync_and_async_agree_on_attempt_count():
    sync_counter = _Counter()
    with patch("time.sleep"):
        with pytest.raises(OilPriceAPIError):
            _sync_client(sync_counter).diesel.get_stations(lat=1.0, lng=2.0)

    async_counter = _run_async(lambda c: c.diesel.get_stations(lat=1.0, lng=2.0))

    assert [m for m, _ in sync_counter.requests] == [m for m, _ in async_counter.requests]


# ---------------------------------------------------------------------------
# (b) Genuine writes are still sent exactly once


WRITES_SYNC = [
    pytest.param(
        lambda c: c.subscriptions.create(codes=["BRENT_CRUDE_USD"], interval="1h"),
        id="subscriptions.create",
    ),
    pytest.param(
        lambda c: c.webhooks.create(url="https://fixture.invalid/hook", events=["price.updated"]),
        id="webhooks.create",
    ),
    pytest.param(
        lambda c: c.data_sources.rotate_credentials("123", {"api_key": "x"}),
        id="data_sources.rotate_credentials",
    ),
]


@pytest.mark.parametrize("call", WRITES_SYNC)
def test_sync_genuine_write_is_still_sent_once(call):
    counter = _Counter()
    client = _sync_client(counter)

    with patch("time.sleep"):
        with pytest.raises(OilPriceAPIError):
            call(client)

    methods = [m for m, _ in counter.requests]
    assert methods == ["POST"], "a genuine write must never be replayed"


# ---------------------------------------------------------------------------
# (c) The next POST added to this SDK must declare which kind it is


# POST call sites that are genuine writes: they commit server-side state, so
# they are deliberately NOT replay-safe and pass no `idempotent=`. Adding a
# line here is a decision, which is the point.
KNOWN_WRITES = {
    ("oilpriceapi/resources/subscriptions.py", "/v1/subscriptions"),
    ("oilpriceapi/resources/webhooks.py", "/v1/webhooks"),
    ("oilpriceapi/resources/alerts.py", "/v1/alerts"),
    ("oilpriceapi/resources/data_sources.py", "/v1/data-sources"),
    ("oilpriceapi/resources/data_sources.py", "/rotate_credentials"),
    # A data-source test triggers a fetch against the customer's configured
    # source and can write to its ingest log, so it is NOT classified as a
    # pure read. Left non-replayable deliberately.
    ("oilpriceapi/resources/data_sources.py", "/test"),
    ("oilpriceapi/async_resources.py", "/v1/subscriptions"),
    ("oilpriceapi/async_resources.py", "/v1/webhooks"),
    ("oilpriceapi/async_resources.py", "/v1/alerts"),
    ("oilpriceapi/async_resources.py", "/v1/data-sources"),
    ("oilpriceapi/async_resources.py", "/rotate_credentials"),
    ("oilpriceapi/async_resources.py", "/data-sources/{source_id}/test"),
}


def _package_root():
    return pathlib.Path(oilpriceapi.__file__).resolve().parent.parent


def _post_call_sites():
    """Every `.request(...)` call whose `method=` is "POST", as source text.

    Parsed with `ast`, so the whole argument list is examined however it is
    formatted: a long `json_data=` block cannot hide an `idempotent=` argument
    from this audit, and the next call site cannot bleed into this one.
    """
    root = _package_root()
    for path in sorted((root / "oilpriceapi").rglob("*.py")):
        source = path.read_text()
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.Call):
                continue
            method = next(
                (
                    kw.value.value
                    for kw in node.keywords
                    if kw.arg == "method" and isinstance(kw.value, ast.Constant)
                ),
                None,
            )
            if method != "POST":
                continue
            yield (
                str(path.relative_to(root)),
                node.lineno,
                ast.get_source_segment(source, node) or "",
            )


def test_every_post_call_site_declares_intent():
    """A new POST either says `idempotent=` or is listed as a known write."""
    undeclared = []
    for relative, line_number, window in _post_call_sites():
        if "idempotent=" in window:
            continue
        if any(
            relative == known_file and known_path in window
            for known_file, known_path in KNOWN_WRITES
        ):
            continue
        undeclared.append(f"{relative}:{line_number}")

    assert not undeclared, (
        "POST call sites that neither pass idempotent= nor appear in "
        "KNOWN_WRITES. A POST that is a query must pass idempotent=True so it "
        "keeps its retries; a POST that writes must be added to KNOWN_WRITES "
        f"with a reason: {undeclared}"
    )


def test_the_read_shaped_posts_actually_pass_idempotent():
    """Guards the guard: KNOWN_WRITES must not be used to smuggle a read past."""
    declared = {
        f"{relative}:{line_number}"
        for relative, line_number, window in _post_call_sites()
        if "idempotent=True" in window
    }
    assert len(declared) == 6, (
        f"expected 6 read-shaped POSTs (3 sync, 3 async), found {sorted(declared)}"
    )
