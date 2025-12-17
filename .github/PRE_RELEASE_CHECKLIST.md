# Pre-Release Validation Checklist

This checklist ensures SDK releases meet quality standards. **Complete ALL items before publishing to PyPI.**

## Automated Checks (Run Script)

```bash
./scripts/pre-release-validation.sh
```

This script runs all automated validations and reports pass/fail status.

## Manual Checklist

### 1. Version Management ✅
- [ ] Version bumped in `pyproject.toml`
- [ ] Version bumped in `oilpriceapi/__init__.py`
- [ ] Version updated in `CHANGELOG.md`
- [ ] CHANGELOG has comprehensive release notes
- [ ] No `UNRELEASED` sections in CHANGELOG

### 2. Code Quality ✅
- [ ] All unit tests pass (`pytest tests/unit -v`)
- [ ] All integration tests pass (`pytest tests/integration -v`)
- [ ] Test coverage ≥ 80% (`pytest --cov`)
- [ ] No linting errors (`ruff check .`)
- [ ] No type errors (`mypy oilpriceapi`)
- [ ] Code formatted (`black --check .`)

### 3. Integration Validation ✅
- [ ] Historical endpoint tests pass (catches timeout bug)
- [ ] Performance baselines met:
  - 1-week queries: <30s
  - 1-month queries: <60s
  - 1-year queries: <120s
- [ ] All commodities tested
- [ ] Error handling verified

### 4. Documentation ✅
- [ ] README.md updated with new features
- [ ] API documentation current
- [ ] Code examples work
- [ ] Migration guide included (if breaking changes)
- [ ] Docstrings updated for new/changed functions

### 5. Build & Package ✅
- [ ] Clean build: `rm -rf dist/ build/ *.egg-info`
- [ ] Build succeeds: `python -m build`
- [ ] Wheel created: `ls dist/*.whl`
- [ ] Source distribution created: `ls dist/*.tar.gz`
- [ ] Package installs locally: `pip install dist/*.whl`
- [ ] Imports work: `python -c "import oilpriceapi; print(oilpriceapi.__version__)"`

### 6. Backwards Compatibility ✅
- [ ] No breaking changes (or documented in CHANGELOG)
- [ ] Existing code samples still work
- [ ] Deprecations properly warned
- [ ] Migration guide provided (if needed)

### 7. Security ✅
- [ ] No hardcoded credentials
- [ ] No secrets in code or tests
- [ ] Dependencies scanned: `pip-audit`
- [ ] SECURITY.md reviewed and current

### 8. Git & GitHub ✅
- [ ] All changes committed
- [ ] Commit message follows convention
- [ ] Git tag created: `git tag v1.X.Y`
- [ ] Tag pushed: `git push --tags`
- [ ] No uncommitted changes

### 9. PyPI Publishing ✅
- [ ] Test PyPI upload works: `twine upload --repository testpypi dist/*`
- [ ] Test installation from TestPyPI
- [ ] Production PyPI upload: `twine upload dist/*`
- [ ] Verify on PyPI: https://pypi.org/project/oilpriceapi/
- [ ] Installation works: `pip install --upgrade oilpriceapi`

### 10. Post-Release ✅
- [ ] GitHub release created with notes
- [ ] Documentation site updated
- [ ] Announcement prepared (if major release)
- [ ] Monitor error tracking for 24 hours
- [ ] Check PyPI download stats

## What Would Have Caught the v1.4.1 Bug?

The historical timeout bug (reported by idan@comity.ai) would have been caught by:

1. ✅ **Integration Tests** (`tests/integration/test_historical_endpoints.py`)
   - `test_7_day_query_uses_past_week_endpoint` - Would fail (67s timeout)
   - `test_365_day_query_uses_past_year_endpoint` - Would fail (30s timeout)

2. ✅ **Performance Baselines** (`TestHistoricalPerformanceBaselines`)
   - All tests would fail with timeouts

3. ✅ **Pre-Release Script** (`scripts/pre-release-validation.sh`)
   - Integration tests would fail
   - Script would prevent release

## Automation Script

The `pre-release-validation.sh` script automates items 1-7:

```bash
# Run full validation
./scripts/pre-release-validation.sh

# Run with verbose output
./scripts/pre-release-validation.sh --verbose

# Skip slow tests (for quick checks)
./scripts/pre-release-validation.sh --skip-slow
```

**Exit Codes:**
- `0` - All checks passed, ready to release
- `1` - One or more checks failed, DO NOT release

## Emergency Release Procedure

If critical bug requires immediate release:

1. Run minimum validation:
   ```bash
   pytest tests/unit -v --tb=short
   pytest tests/integration/test_historical_endpoints.py -v
   ```

2. Verify the specific fix works

3. Document in CHANGELOG as emergency release

4. **Still run full validation after emergency release**

## Failed Validation - What to Do

### Tests Failed
1. Fix failing tests
2. Re-run full validation
3. Update CHANGELOG if fixes required code changes

### Performance Regression
1. Investigate using profiling
2. Fix performance issue
3. Re-establish baseline

### Documentation Missing
1. Update documentation
2. Add code examples
3. Test examples actually work

### Build Failed
1. Check `pyproject.toml` for errors
2. Verify all files included in manifest
3. Test clean build: `rm -rf dist/ && python -m build`

## Version History

| Version | Date | Validator | Result | Notes |
|---------|------|-----------|--------|-------|
| v1.4.2 | 2025-12-16 | Manual | ✅ Pass | Fixed historical timeout bug |
| v1.4.1 | 2025-12-15 | None | ❌ Fail | Historical timeout bug shipped |

*Note: v1.4.1 did not use this checklist, which is why the bug reached production.*

## Integration with CI/CD

### GitHub Actions (Recommended)

```yaml
name: Pre-Release Validation

on:
  push:
    tags:
      - 'v*'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
          pip install twine pip-audit

      - name: Run pre-release validation
        env:
          OILPRICEAPI_KEY: ${{ secrets.OILPRICEAPI_KEY }}
        run: ./scripts/pre-release-validation.sh

      - name: Build package
        if: success()
        run: python -m build

      - name: Publish to PyPI
        if: success()
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
        run: twine upload dist/*
```

## Contact

Questions about the validation process:
- GitHub Issues: https://github.com/OilpriceAPI/python-sdk/issues
- Email: support@oilpriceapi.com

## Related Issues

- [#20](https://github.com/OilpriceAPI/python-sdk/issues/20) - Integration tests
- [#21](https://github.com/OilpriceAPI/python-sdk/issues/21) - Performance baselines
- [#22](https://github.com/OilpriceAPI/python-sdk/issues/22) - Pre-release validation (this document)
