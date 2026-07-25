from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, List


def _load_monitor() -> ModuleType:
    path = Path(__file__).parents[2] / "scripts" / "synthetic_monitor.py"
    spec = importlib.util.spec_from_file_location("synthetic_monitor", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


monitor = _load_monitor()


class FakeClient:
    def __init__(self, **_: Any) -> None:
        record = SimpleNamespace(
            commodity="BRENT_CRUDE_USD",
            value=96.25,
            currency="USD",
            unit="barrel",
            timestamp=datetime(2026, 7, 25, tzinfo=timezone.utc),
        )
        self.prices = SimpleNamespace(get=lambda _code: record)
        self.historical = SimpleNamespace(
            get=lambda **_kwargs: SimpleNamespace(data=[record, record])
        )

    def __enter__(self) -> "FakeClient":
        return self

    def __exit__(self, *_args: Any) -> None:
        return None


def _clock(values: List[float]):
    iterator = iter(values)
    return lambda: next(iterator)


def test_receipt_passes_for_valid_latest_and_history() -> None:
    receipt = monitor.run_synthetic_checks(
        "not-a-real-key",
        client_factory=FakeClient,
        monotonic=_clock([1.0, 1.2, 2.0, 2.4]),
    )

    assert receipt["status"] == "pass"
    assert [check["name"] for check in receipt["checks"]] == [
        "latest_price",
        "bounded_history",
    ]
    assert all(check["status"] == "pass" for check in receipt["checks"])
    assert receipt["checks"][1]["details"]["records_checked"] == 2


def test_failure_receipt_redacts_exception_message_and_key() -> None:
    secret = "secret-value-that-must-not-escape"

    class FailingClient(FakeClient):
        def __init__(self, **_: Any) -> None:
            raise RuntimeError(f"upstream echoed {secret}")

    receipt = monitor.run_synthetic_checks(secret, client_factory=FailingClient)
    rendered = json.dumps(receipt)

    assert receipt["status"] == "fail"
    assert receipt["checks"][0]["error_type"] == "RuntimeError"
    assert secret not in rendered
    assert "upstream echoed" not in rendered


def test_empty_history_fails_without_response_content() -> None:
    class EmptyHistoryClient(FakeClient):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self.historical = SimpleNamespace(get=lambda **_kwargs: SimpleNamespace(data=[]))

    receipt = monitor.run_synthetic_checks(
        "not-a-real-key",
        client_factory=EmptyHistoryClient,
        monotonic=_clock([1.0, 1.1, 2.0, 2.2]),
    )

    assert receipt["status"] == "fail"
    history = receipt["checks"][1]
    assert history["name"] == "bounded_history"
    assert history["error_type"] == "ValueError"
    assert "details" not in history


def test_time_budget_is_a_failure() -> None:
    receipt = monitor.run_synthetic_checks(
        "not-a-real-key",
        client_factory=FakeClient,
        monotonic=_clock([1.0, 32.0, 40.0, 40.1]),
    )

    assert receipt["status"] == "fail"
    assert receipt["checks"][0]["error_type"] == "TimeBudgetExceeded"
