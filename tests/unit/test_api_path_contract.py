"""Every /v1 path the SDK can call must be routed by the API (#153).

Eight methods shipped calling paths the API never routed. Their mocked tests
stayed green because nothing compared the SDK's paths with the API's route
table. This test does, against tests/fixtures/api_paths.json.fixture (refresh with
scripts/refresh_api_paths.py).
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = json.loads((ROOT / "tests" / "fixtures" / "api_paths.json.fixture").read_text())
PATH_LITERAL = re.compile(r"""f?["'](/v1(?:/[^"'?\s]*)?)["']""")


def _template(path: str) -> tuple:
    path = re.sub(r"\{[^}]*\}", "{}", path).rstrip("/")
    return tuple(path.split("/"))


ROUTED = {_template(r.split(" ", 1)[1]) for r in SNAPSHOT["routes"]}


def _matches(route: tuple, segments: tuple) -> bool:
    # An SDK placeholder may stand for a route literal (``{slug}`` for
    # ``brent``) and a route parameter may take an SDK literal, but not both
    # in one match: that is how /v1/storage/{code}/history would otherwise
    # pass for /v1/storage/history/:code.
    if len(route) != len(segments):
        return False
    sdk_wild_on_literal = route_wild_on_literal = False
    for r, s in zip(route, segments):
        if r == s:
            continue
        if s == "{}" and r != "{}":
            sdk_wild_on_literal = True
        elif r == "{}":
            route_wild_on_literal = True
        else:
            return False
    return not (sdk_wild_on_literal and route_wild_on_literal)


def _is_routed(path: str) -> bool:
    segments = _template(path)
    return any(_matches(route, segments) for route in ROUTED)


def sdk_paths(source_root: Path = ROOT / "oilpriceapi") -> dict:
    found: dict = {}
    for py in sorted(source_root.rglob("*.py")):
        for lineno, line in enumerate(py.read_text().splitlines(), 1):
            if line.lstrip().startswith("#") or ">>>" in line:
                continue
            for match in PATH_LITERAL.finditer(line):
                found.setdefault(match.group(1), []).append(
                    f"{py.relative_to(source_root.parent)}:{lineno}"
                )
    return found


def test_snapshot_is_populated():
    assert len(SNAPSHOT["routes"]) > 400
    assert SNAPSHOT["source"]["commit"]


def test_collector_finds_sdk_paths():
    paths = sdk_paths()
    assert "/v1/prices/latest" in paths
    assert "/v1/storage/history/{storage_history_code(code)}" in paths


def test_matcher_rejects_known_dead_paths():
    for dead in (
        "/v1/futures/spreads",
        "/v1/drilling-intelligence/trends",
        "/v1/storage/{code}/history",
        "/v1/forecasts/accuracy",
        "/v1/bunker-fuels/spreads",
    ):
        assert not _is_routed(dead), dead


def test_every_sdk_path_is_routed():
    unrouted = {
        path: where for path, where in sdk_paths().items() if not _is_routed(path)
    }
    assert not unrouted, (
        "SDK calls /v1 paths the API does not route (refresh the snapshot if "
        "the API changed):\n"
        + "\n".join(f"  {p}  <- {', '.join(w)}" for p, w in sorted(unrouted.items()))
    )
