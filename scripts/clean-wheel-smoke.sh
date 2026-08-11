#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
wheel="$(find "$root_dir/dist" -maxdepth 1 -name '*.whl' -print -quit)"
expected_version="$(
  cd "$root_dir"
  python -c 'from oilpriceapi.version import SDK_VERSION; print(SDK_VERSION)'
)"

if [[ -z "$wheel" ]]; then
  echo "no wheel found under dist/" >&2
  exit 1
fi

smoke_dir="$(mktemp -d)"
trap 'rm -rf "$smoke_dir"' EXIT

python -m venv "$smoke_dir/venv"
"$smoke_dir/venv/bin/python" -m pip install --quiet "$wheel"
"$smoke_dir/venv/bin/python" -m pip check
"$smoke_dir/venv/bin/python" -c '
import sys
from oilpriceapi import OilPriceAPI, __version__
from oilpriceapi.resources.demo import DemoResource

expected = sys.argv[1]
assert __version__ == expected, (__version__, expected)
assert OilPriceAPI(api_key="artifact-smoke").prices is not None
demo = DemoResource()
assert demo.base_url.startswith("https://")
prices = demo.prices()["prices"]
brent = next((price for price in prices if price.get("code") == "BRENT_CRUDE_USD"), None)
assert brent is not None
assert isinstance(brent.get("price"), (int, float))
assert brent.get("updated_at")
' "$expected_version"

echo "clean wheel install and production demo smoke passed for oilpriceapi $expected_version"
