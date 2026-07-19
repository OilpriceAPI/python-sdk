import importlib.util
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import ModuleType
from typing import Any, Dict

from jsonschema import Draft202012Validator

from scripts.generate_snippet_manifest import build_manifest, write_manifest

ROOT = Path(__file__).resolve().parents[1]
SNIPPETS = ROOT / "examples/snippets"


class FixtureHandler(BaseHTTPRequestHandler):
    scenario = "success"

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def do_GET(self) -> None:
        if self.scenario == "timeout":
            time.sleep(0.2)
            return

        statuses = {"authentication": 401, "entitlement": 403, "rate_limit": 429}
        status = statuses.get(self.scenario, 200)
        if status != 200:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            if status == 429:
                self.send_header("Retry-After", "0")
                self.send_header("X-RateLimit-Limit", "1")
                self.send_header("X-RateLimit-Remaining", "0")
            self.end_headers()
            self.wfile.write(json.dumps({"error": self.scenario}).encode())
            return

        if "/v1/prices/latest" in self.path:
            data: Dict[str, Any] = {
                "status": "success",
                "data": {
                    "code": "BRENT_CRUDE_USD",
                    "price": 72.5,
                    "currency": "USD",
                    "unit": "barrel",
                    "created_at": "2026-01-15T12:00:00Z",
                },
            }
        else:
            data = {
                "status": "success",
                "data": {
                    "prices": [
                        {
                            "code": "BRENT_CRUDE_USD",
                            "price": 71.5,
                            "currency": "USD",
                            "unit": "barrel",
                            "type": "spot_price",
                            "created_at": "2026-01-14T12:00:00Z",
                        }
                    ]
                },
            }
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Total-Pages", "1")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


def load_snippet(name: str) -> ModuleType:
    path = SNIPPETS / f"{name}.py"
    sys.path.insert(0, str(SNIPPETS))
    try:
        spec = importlib.util.spec_from_file_location(f"snippet_{name}", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SNIPPETS))


def test_manifest_validates_and_checksum_matches(tmp_path: Path) -> None:
    commit = "a" * 40
    output = tmp_path / "oilpriceapi-python-snippets-v1.json"
    write_manifest(output, commit)
    manifest = json.loads(output.read_text())
    schema = json.loads((ROOT / "schemas/snippet-manifest.schema.json").read_text())
    Draft202012Validator(schema).validate(manifest)

    assert manifest == build_manifest(commit)
    assert manifest["package"]["minimum_runtime"] == "3.8"
    assert {
        example["http_status"]
        for example in manifest["examples"]
        if "http_status" in example
    } == {401, 403, 429}
    assert output.with_suffix(".json.sha256").read_text().endswith(
        "  oilpriceapi-python-snippets-v1.json\n"
    )


def test_exact_manifest_files_execute_against_fixtures(monkeypatch: Any) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("OILPRICEAPI_KEY", "fixture-key")
    monkeypatch.setenv("OILPRICEAPI_BASE_URL", f"http://127.0.0.1:{server.server_port}")

    try:
        cases = [
            ("latest_price", "success", {"commodity": "BRENT_CRUDE_USD", "value_type": "float"}),
            ("history", "success", {"commodity": "BRENT_CRUDE_USD", "count": 1}),
            ("authentication_error", "authentication", {"handled": True, "status_code": 401}),
            ("entitlement_error", "entitlement", {"handled": True, "status_code": 403}),
            ("rate_limit_error", "rate_limit", {"handled": True, "status_code": 429}),
            ("timeout_error", "timeout", {"handled": True, "error_type": "TimeoutError"}),
        ]
        for name, scenario, expected in cases:
            FixtureHandler.scenario = scenario
            result = load_snippet(name).run()
            assert result.items() >= expected.items()
    finally:
        server.shutdown()
        server.server_close()
