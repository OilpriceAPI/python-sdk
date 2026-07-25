# Python SDK release process

Python package indexes do not support percentage-based staged rollouts. A
pre-release such as `1.12.0rc1` is visible only to users who explicitly request
pre-releases; it does not automatically reach a random 1–5% cohort. OilPriceAPI
therefore does not call pre-release publishing a canary rollout.

## Current release gate

Publishing is triggered only by a published, non-pre-release GitHub Release.
Pre-release GitHub Releases are intentionally skipped. The `Publish to PyPI`
workflow then:

1. verifies that the release tag exactly matches the package version;
2. installs the repository's development dependencies;
3. runs unit tests;
4. builds the package;
5. creates and attaches the executable snippet manifest;
6. publishes with PyPI trusted publishing.

Normal pushes, pull requests, tags, and documentation deployments do not
publish a package. The `pypi` GitHub environment is the final authorization
boundary.

Before publishing a GitHub Release, verify:

- the release tag and package version match;
- the changelog describes customer-visible changes and recovery guidance;
- Python 3.8–3.12 CI, live contract tests, and the scheduled SDK synthetic are
  green;
- a clean wheel installs and imports in an isolated environment;
- no release with that version already exists on PyPI.

## Recovery

PyPI artifacts are immutable. A bad release cannot be overwritten.

1. Stop promotion and mark the GitHub Release with a clear warning.
2. Yank the affected PyPI version so new unconstrained installs avoid it. Do
   not delete artifacts unless required for a security incident.
3. Tell affected users to pin the last known-good version while a fix is built.
4. Reproduce the defect, add a regression test, and publish a new patch version
   through the normal release gate.
5. Confirm the new version with the scheduled synthetic and production
   telemetry before closing the incident.

Yanking or publishing is a package-registry mutation and requires explicit
release authorization.

## Future release candidates

Release candidates may be useful after there is an identified adopter cohort
that has opted into `pip install --pre` and a written measurement window. Until
then, an RC would add another public artifact without providing statistically
meaningful staged-rollout evidence. The supported risk controls are the
pre-publish test gate, immutable-version recovery, live tests, and the hourly
SDK synthetic.
