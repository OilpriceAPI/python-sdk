#!/usr/bin/env python3
"""Refresh tests/fixtures/api_paths.json.fixture from an oilpriceapi-api checkout.

The contract test (tests/unit/test_api_path_contract.py) fails when the SDK
calls a /v1 path the API does not route (#153). It reads this snapshot rather
than the live API so CI stays hermetic. Refresh it when the API adds or
removes routes:

    git -C ../oilpriceapi-api fetch origin
    git -C ../oilpriceapi-api worktree add --detach /tmp/opa-api-routes origin/main
    (cd /tmp/opa-api-routes && RAILS_ENV=test SECRET_KEY_BASE=x \\
        bundle exec rails routes > /tmp/routes.txt)
    python scripts/refresh_api_paths.py \\
        --routes /tmp/routes.txt \\
        --swagger /tmp/opa-api-routes/swagger/v1/swagger.json \\
        --commit "$(git -C /tmp/opa-api-routes rev-parse HEAD)"
    git -C ../oilpriceapi-api worktree remove /tmp/opa-api-routes

The swagger file is the documented public contract. It is recorded alongside
the full route table but is not sufficient on its own: the SDK also wraps
routed compatibility and preview endpoints that swagger omits, and
config/openapi_route_policy.yml excludes those by prefix, which would also
admit unrouted paths under the same prefix.
"""

import argparse
import json
import re
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "api_paths.json.fixture"
ROUTE_LINE = re.compile(r"\s(GET|POST|PUT|PATCH|DELETE)\s+(/v1/\S*)")


def normalize(path: str) -> str:
    path = path.replace("(.:format)", "")
    path = re.sub(r"\([^)]*\)", "", path)  # optional segments
    path = re.sub(r":[A-Za-z_]+", "{}", path)
    path = re.sub(r"\*[A-Za-z_]+", "{}", path)
    return path.rstrip("/") or "/"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--routes", required=True, help="output of `rails routes`")
    parser.add_argument("--swagger", required=True, help="swagger/v1/swagger.json")
    parser.add_argument("--commit", required=True, help="oilpriceapi-api commit")
    args = parser.parse_args()

    routes = set()
    for line in Path(args.routes).read_text().splitlines():
        match = ROUTE_LINE.search(line)
        if match:
            routes.add(f"{match.group(1)} {normalize(match.group(2))}")

    swagger = json.loads(Path(args.swagger).read_text())
    openapi = sorted(
        normalize(re.sub(r"\{[^}]+\}", ":p", p)) for p in swagger["paths"]
    )

    OUT.write_text(
        json.dumps(
            {
                "source": {"repo": "OilpriceAPI/oilpriceapi-api", "commit": args.commit},
                "routes": sorted(routes),
                "openapi": openapi,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"wrote {OUT} ({len(routes)} routes, {len(openapi)} openapi paths)")


if __name__ == "__main__":
    main()
