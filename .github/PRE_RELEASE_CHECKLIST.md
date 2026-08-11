# Pre-Release Validation Checklist

The authoritative release design is documented in
[`docs/RELEASE_PROCESS.md`](../docs/RELEASE_PROCESS.md). Complete every gate
below before publishing a non-prerelease GitHub Release.

## Automated Gate

Run from a clean checkout of the release commit:

```bash
python -m pip install --upgrade pip
python -m pip install -e '.[dev]' build pip-audit
ruff check oilpriceapi/
mypy oilpriceapi/ --ignore-missing-imports
pytest tests/ --ignore=tests/integration --ignore=tests/contract -m 'not slow'
python scripts/validate_storefront_claims.py
python scripts/generate_snippet_manifest.py --source-commit "$(git rev-parse HEAD)" --output artifacts/snippets/oilpriceapi-python-snippets-v1.json
python -m build
./scripts/clean-wheel-smoke.sh
pip-audit
```

The hosted Python 3.8-3.12 matrix, keyless and keyed live tests, canonical
production snippets, and `Scheduled SDK Synthetic` must all be green at the
same release commit. The repository test gate enforces at least 50% aggregate
coverage; increases to that threshold require a reviewed test-coverage change.

## Release Metadata

- `pyproject.toml` and `oilpriceapi/version.py` contain the same version.
- `CHANGELOG.md` has one release section for that version with customer-visible
  behavior and recovery guidance.
- The version is absent from PyPI and from existing GitHub releases.
- The release tag is exactly `v<package-version>`.
- The worktree is clean and the tag resolves to the reviewed main commit.

## Publication And Recovery

Publish through a non-prerelease GitHub Release only. The `Publish to PyPI`
workflow verifies the tag, repeats the tests and dependency audit, builds and
installs the wheel in a clean environment, attaches the snippet manifest, and
uses PyPI trusted publishing. Do not upload with Twine or a local API token.

PyPI artifacts are immutable. If a production defect appears, stop promotion,
yank the affected version, add a failing regression test, and publish a new
patch version through the same gate.
