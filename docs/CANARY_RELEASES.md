# Canary Release Process

A canary release gradually rolls out new SDK versions to catch issues before they affect all users.

---

## What is a Canary Release?

**Traditional Release:**
```
v1.4.1 → Release v1.4.2 → 100% of users immediately get v1.4.2
                        → Bug affects everyone
```

**Canary Release:**
```
v1.4.1 → Release v1.4.2-rc1 → 1% of users (early adopters)
                            → Monitor for 24h
                            → No issues detected
                            → Release v1.4.2 → 100% of users
```

---

## Why Canary Releases?

### The v1.4.1 Problem

**What Happened:**
1. Released v1.4.1 to PyPI
2. All users who upgraded got the bug
3. Customer (Idan) discovered 100% failure rate
4. Emergency hotfix required (v1.4.2)

**With Canary Release:**
1. Release v1.4.2-rc1 to PyPI (marked as pre-release)
2. 1% of users upgrade (early adopters)
3. Monitor telemetry for issues
4. Detect timeout bug within 24h
5. Fix bug in v1.4.2-rc2
6. Test again
7. Release v1.4.2 stable (bug-free)

---

## Canary Release Workflow

### Phase 1: Pre-Release (1-5% of users)

```bash
# 1. Create release candidate
git tag v1.4.2-rc1
git push --tags

# 2. Build package
python -m build

# 3. Upload to PyPI as pre-release
twine upload dist/*
```

**PyPI marks it as pre-release automatically** (version contains `-rc`, `-alpha`, `-beta`).

**Users who get it:**
- Those who explicitly install pre-releases
- Early adopters with `--pre` flag
- CI/CD systems testing latest versions

```bash
# Regular users don't get it
pip install oilpriceapi
# Installs: v1.4.1 (stable)

# Early adopters get it
pip install --pre oilpriceapi
# Installs: v1.4.2-rc1 (pre-release)
```

### Phase 2: Monitor (24-48 hours)

**Monitor telemetry for:**
- Error rates
- Timeout rates
- Performance regressions
- Download counts

**Alert triggers:**
```yaml
- Error rate >5% compared to stable version
- Timeout rate >10%
- Performance regression >2x
- Zero downloads after 24h (nobody adopting)
```

**If issues detected:**
```bash
# Fix the issue
git checkout -b fix/issue-xyz
# ... make fixes ...

# Release new RC
git tag v1.4.2-rc2
python -m build
twine upload dist/*

# Monitor again
```

### Phase 3: Promote to Stable (100% of users)

**If no issues after 48h:**

```bash
# Remove RC suffix
git tag v1.4.2
git push --tags

# Build final release
python -m build

# Upload to PyPI
twine upload dist/*

# Announce release
gh release create v1.4.2 \
  --title "v1.4.2: Historical Query Performance Fix" \
  --notes "$(cat CHANGELOG.md)"
```

**Now all users get it:**
```bash
pip install --upgrade oilpriceapi
# Installs: v1.4.2 (stable)
```

---

## Version Naming Convention

### Pre-Release Versions

| Version | Meaning | Stability | Adoption |
|---------|---------|-----------|----------|
| `1.4.2-alpha1` | Very early, major changes | Unstable | Developers only |
| `1.4.2-beta1` | Feature complete, testing | Moderately stable | Early adopters |
| `1.4.2-rc1` | Release candidate, ready | Nearly stable | 1-5% users |
| `1.4.2` | Final release | Stable | 100% users |

### Example Timeline

```
Day 0:  Release 1.4.2-alpha1 (developers test)
Day 3:  Release 1.4.2-beta1 (early adopters test)
Day 7:  Release 1.4.2-rc1 (canary to 1% users)
Day 9:  No issues → Release 1.4.2 (stable to all)
```

**If issues found:**
```
Day 7:  Release 1.4.2-rc1
Day 8:  Issue detected → Fix → Release 1.4.2-rc2
Day 10: No issues → Release 1.4.2
```

---

## PyPI Configuration

### Setup `.pypirc`

```ini
[pypi]
username = __token__
password = pypi-xxx-your-token-xxx

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-xxx-your-test-token-xxx
```

### Test on TestPyPI First

```bash
# 1. Upload to TestPyPI
twine upload --repository testpypi dist/*

# 2. Test installation
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple \
            oilpriceapi==1.4.2rc1

# 3. Verify it works
python -c "import oilpriceapi; print(oilpriceapi.__version__)"

# 4. If successful, upload to production PyPI
twine upload dist/*
```

---

## Automated Canary Deployment

### GitHub Actions Workflow

`.github/workflows/canary-release.yml`:

```yaml
name: Canary Release

on:
  push:
    tags:
      - 'v*-rc*'  # Trigger on release candidates

jobs:
  canary-release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install build twine
          pip install -e ".[dev]"

      - name: Run pre-release validation
        env:
          OILPRICEAPI_KEY: ${{ secrets.OILPRICEAPI_KEY }}
        run: ./scripts/pre-release-validation.sh

      - name: Build package
        run: python -m build

      - name: Upload to Test PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.TEST_PYPI_TOKEN }}
        run: twine upload --repository testpypi dist/*

      - name: Test installation from TestPyPI
        run: |
          pip install --index-url https://test.pypi.org/simple/ \
                      --extra-index-url https://pypi.org/simple \
                      oilpriceapi
          python -c "import oilpriceapi; print(oilpriceapi.__version__)"

      - name: Upload to PyPI (pre-release)
        if: success()
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
        run: twine upload dist/*

      - name: Create GitHub pre-release
        run: |
          gh release create ${{ github.ref_name }} \
            --title "${{ github.ref_name }}" \
            --notes "Release candidate - monitor for 48h before promoting to stable" \
            --prerelease

      - name: Notify team
        run: |
          curl -X POST ${{ secrets.SLACK_WEBHOOK }} \
            -H 'Content-Type: application/json' \
            -d '{
              "text": "Canary release ${{ github.ref_name }} deployed. Monitor for 48h.",
              "blocks": [{
                "type": "section",
                "text": {
                  "type": "mrkdwn",
                  "text": "*Canary Release Deployed*\n\nVersion: ${{ github.ref_name }}\nMonitor: https://grafana.oilpriceapi.com"
                }
              }]
            }'
```

### Promote to Stable Workflow

`.github/workflows/promote-to-stable.yml`:

```yaml
name: Promote to Stable

on:
  workflow_dispatch:
    inputs:
      rc_version:
        description: 'RC version to promote (e.g., v1.4.2-rc1)'
        required: true
      stable_version:
        description: 'Stable version (e.g., v1.4.2)'
        required: true

jobs:
  promote:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Create stable tag
        run: |
          git tag ${{ github.event.inputs.stable_version }}
          git push origin ${{ github.event.inputs.stable_version }}

      - name: Build and upload
        run: |
          python -m build
          twine upload dist/*

      - name: Create GitHub release (stable)
        run: |
          gh release create ${{ github.event.inputs.stable_version }} \
            --title "v${{ github.event.inputs.stable_version }}" \
            --notes-file CHANGELOG.md

      - name: Announce release
        run: |
          curl -X POST ${{ secrets.SLACK_WEBHOOK }} \
            -H 'Content-Type: application/json' \
            -d '{
              "text": "Stable release ${{ github.event.inputs.stable_version }} published to PyPI"
            }'
```

---

## Monitoring Canary Releases

### Metrics to Track

```yaml
# Grafana Dashboard Queries

# 1. Download Rate by Version
sum by (version) (rate(pypi_downloads_total[1h]))

# 2. Error Rate by Version
sum by (version) (rate(telemetry_errors_total[5m])) /
sum by (version) (rate(telemetry_requests_total[5m]))

# 3. Timeout Rate by Version
sum by (version) (rate(telemetry_errors{error_type="TimeoutError"}[5m]))

# 4. Performance by Version
histogram_quantile(0.95,
  sum by (version, le) (rate(telemetry_duration_bucket[5m]))
)
```

### Alert Rules

```yaml
groups:
  - name: canary_health
    rules:
      - alert: CanaryHighErrorRate
        expr: |
          (
            sum by (version) (rate(telemetry_errors_total{version=~".*-rc.*"}[5m])) /
            sum by (version) (rate(telemetry_requests_total{version=~".*-rc.*"}[5m]))
          ) > 0.05
        for: 30m
        labels:
          severity: critical
        annotations:
          summary: "Canary version has >5% error rate"
          description: "Version {{ $labels.version }} error rate: {{ $value }}"

      - alert: CanaryPerformanceRegression
        expr: |
          histogram_quantile(0.95,
            sum by (version, le) (rate(telemetry_duration_bucket{version=~".*-rc.*"}[5m]))
          ) >
          histogram_quantile(0.95,
            sum by (version, le) (rate(telemetry_duration_bucket{version!~".*-rc.*"}[5m]))
          ) * 2
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Canary version is 2x slower"

      - alert: CanaryZeroAdoption
        expr: |
          sum(rate(pypi_downloads_total{version=~".*-rc.*"}[24h])) == 0
        for: 24h
        labels:
          severity: warning
        annotations:
          summary: "No users adopting canary release"
          description: "Consider promoting manually to early adopters"
```

---

## Rollback Procedure

**If critical issue found in canary:**

### Option 1: Yank from PyPI (Recommended)

```bash
# Yank the problematic version
twine yank oilpriceapi==1.4.2-rc1 \
  -m "Critical bug: timeout on historical queries"

# Users can't install it anymore
pip install --pre oilpriceapi
# Error: No matching distribution found
```

### Option 2: Release Hotfix RC

```bash
# Fix the issue
git checkout -b hotfix/rc2

# Release new RC
git tag v1.4.2-rc2
python -m build
twine upload dist/*
```

### Option 3: Communicate to Users

```python
# In SDK code, detect problematic version
if __version__ == "1.4.2-rc1":
    warnings.warn(
        "This version has a known issue. "
        "Please upgrade: pip install --upgrade --pre oilpriceapi",
        DeprecationWarning
    )
```

---

## User Communication

### For RC Releases

**GitHub Release Notes:**
```markdown
## v1.4.2-rc1 (Release Candidate)

**⚠️ This is a pre-release version.**

### What's New
- Fixed historical query timeout bug (#20)
- Added endpoint selection optimization

### Should You Upgrade?
- ✅ Yes, if you want to help test
- ✅ Yes, if you're affected by historical timeouts
- ❌ No, if you need maximum stability

### How to Test
```bash
pip install --pre oilpriceapi
```

### Report Issues
If you encounter problems, please report at:
https://github.com/OilpriceAPI/python-sdk/issues

**This will be promoted to stable after 48h if no issues found.**
```

### For Stable Releases

**GitHub Release Notes:**
```markdown
## v1.4.2

**✅ This is a stable release.**

### What's New
- Fixed historical query timeout bug
- Performance improvements: 7x faster for 1-week queries

### How to Upgrade
```bash
pip install --upgrade oilpriceapi
```

### Breaking Changes
None - this is a backward-compatible bug fix.

### Tested By
- 50+ early adopters during RC phase
- 100% test coverage
- Zero critical issues in 48h monitoring
```

---

## Best Practices

### 1. Always Test on TestPyPI First

```bash
# ALWAYS do this before production PyPI
twine upload --repository testpypi dist/*
pip install --index-url https://test.pypi.org/simple/ oilpriceapi
```

### 2. Monitor for Full 48 Hours

Don't promote early, even if everything looks good at 24h.

### 3. Have Rollback Plan Ready

Before releasing RC:
- [ ] Can yank from PyPI if needed
- [ ] Have hotfix branch ready
- [ ] Team available to respond
- [ ] Monitoring alerts configured

### 4. Communicate Clearly

- Mark as pre-release on GitHub
- Update CHANGELOG with RC notes
- Post in community channels
- Set expectations (48h monitoring period)

### 5. Automate Everything

Manual steps lead to mistakes. Automate:
- Building
- Testing
- Uploading
- Monitoring
- Alerts
- Rollbacks

---

## Success Metrics

### Canary Release is Successful If:

- ✅ Error rate < 1% above baseline
- ✅ No timeout regressions
- ✅ Performance within baselines
- ✅ At least 10 unique users adopted RC
- ✅ No critical issues reported
- ✅ Monitoring data looks normal for 48h

### Failed Canary (Don't Promote):

- ❌ Error rate >5% above baseline
- ❌ Timeout rate increased
- ❌ Performance regression >2x
- ❌ Critical bugs reported
- ❌ Zero adoption after 24h

---

## Timeline Example

### Successful Canary

```
Monday 9am:    Release v1.4.2-rc1
Monday 10am:   First early adopter installs
Monday 2pm:    10 users on RC, metrics look good
Tuesday 9am:   25 users on RC, no issues reported
Tuesday 5pm:   48h monitoring complete, all green
Wednesday 9am: Promote to v1.4.2 stable
Wednesday 10am: Announce stable release
```

### Failed Canary

```
Monday 9am:    Release v1.4.2-rc1
Monday 10am:   First early adopter installs
Monday 11am:   Timeout errors detected in telemetry
Monday 12pm:   Yank v1.4.2-rc1 from PyPI
Monday 2pm:    Fix bug, release v1.4.2-rc2
Monday 3pm:    Monitor v1.4.2-rc2
Wednesday 9am: 48h clean, promote v1.4.2-rc2 to v1.4.2
```

---

## Related

- [Pre-Release Checklist](../.github/PRE_RELEASE_CHECKLIST.md)
- [Monitoring Guide](../.github/MONITORING_GUIDE.md)
- [Telemetry Documentation](./TELEMETRY.md)
- [GitHub Issue #27](https://github.com/OilpriceAPI/python-sdk/issues/27)

---

## Contact

Questions about canary releases?
- GitHub: https://github.com/OilpriceAPI/python-sdk/issues/27
- Email: support@oilpriceapi.com
