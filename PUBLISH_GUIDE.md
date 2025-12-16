# Publishing Guide: Python SDK v1.4.0

## Pre-Publishing Checklist

✅ Version bumped to 1.4.0 in pyproject.toml
✅ Version bumped to 1.4.0 in __init__.py
✅ CHANGELOG.md updated with v1.4.0 release notes
✅ README.md updated with alerts examples
✅ All tests passing (22/22)
✅ Code committed and pushed to GitHub

## Publishing to PyPI

### Step 1: Install Build Tools

```bash
# Activate virtual environment
source .venv/bin/activate

# Install/upgrade build tools
pip install --upgrade build twine
```

### Step 2: Verify PyPI Authentication

```bash
# Check if you have PyPI credentials
ls -la ~/.pypirc

# If not, create ~/.pypirc:
cat > ~/.pypirc << 'EOF'
[pypi]
username = __token__
password = pypi-YOUR-API-TOKEN-HERE
EOF

chmod 600 ~/.pypirc
```

Get API token from: https://pypi.org/manage/account/token/

### Step 3: Run Final Checks

```bash
# Ensure clean working directory
git status

# Run tests one more time
pytest tests/unit/test_alerts_resource.py -v

# Check package metadata
python -c "import oilpriceapi; print(oilpriceapi.__version__)"
# Should output: 1.4.0
```

### Step 4: Build Distribution

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build source distribution and wheel
python -m build

# Verify build outputs
ls -lh dist/
# Should see:
# oilpriceapi-1.4.0.tar.gz
# oilpriceapi-1.4.0-py3-none-any.whl
```

### Step 5: Test Upload (Optional but Recommended)

```bash
# Upload to TestPyPI first
python -m twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ oilpriceapi==1.4.0

# Verify it works
python -c "from oilpriceapi import OilPriceAPI; print('Success!')"
```

### Step 6: Publish to PyPI

```bash
# Upload to production PyPI
python -m twine upload dist/*

# Expected output:
# Uploading distributions to https://upload.pypi.org/legacy/
# Uploading oilpriceapi-1.4.0-py3-none-any.whl
# Uploading oilpriceapi-1.4.0.tar.gz
# View at: https://pypi.org/project/oilpriceapi/1.4.0/
```

### Step 7: Verify Publication

```bash
# Wait 1-2 minutes for PyPI to index

# Check PyPI page
open https://pypi.org/project/oilpriceapi/

# Test installation in fresh environment
python -m venv /tmp/test-pypi
source /tmp/test-pypi/bin/activate
pip install oilpriceapi==1.4.0

# Verify version and alerts
python << 'EOF'
import oilpriceapi
print(f"Version: {oilpriceapi.__version__}")
print(f"Has alerts: {hasattr(oilpriceapi.OilPriceAPI, 'alerts')}")
EOF
```

### Step 8: Tag Release on GitHub

```bash
git tag -a v1.4.0 -m "Release v1.4.0: Price Alerts Support"
git push origin v1.4.0
```

### Step 9: Create GitHub Release

Go to: https://github.com/OilpriceAPI/python-sdk/releases/new

- Tag: v1.4.0
- Title: v1.4.0 - Price Alerts Support
- Description: Copy from CHANGELOG.md v1.4.0 section
- Attach: dist/oilpriceapi-1.4.0.tar.gz and .whl files

## Post-Publishing

### Update Documentation Website

```bash
# If you have a docs deployment script
python scripts/deploy_docs.py
```

### Announce Release

1. **Twitter/X**:
   ```
   🐍 OilPriceAPI Python SDK v1.4.0 is now live!

   New: Price Alerts 🔔
   • Automated price monitoring
   • Webhook notifications
   • DataFrame integration
   • 5 comparison operators

   pip install oilpriceapi==1.4.0

   Docs: https://docs.oilpriceapi.com/sdk/python
   ```

2. **Reddit** (r/Python, r/datascience, r/algotrading):
   - Title: "OilPriceAPI Python SDK v1.4.0: Price Alerts Feature"
   - Link to GitHub release and PyPI

3. **Email to Users**:
   - Subject: "New Feature: Price Alerts Now Available in Python SDK"
   - Highlight pandas integration and webhook automation

### Update Package Badges

Ensure README badges are up to date:
- PyPI version badge
- Downloads badge
- Coverage badge

## Troubleshooting

### "Invalid distribution"
```bash
# Check package metadata
python -m build --sdist
tar -tzf dist/oilpriceapi-1.4.0.tar.gz | head -20
```

### "File already exists"
- Version 1.4.0 already published to PyPI
- PyPI doesn't allow re-uploading same version
- Bump to 1.4.1: `python setup.py --version`

### "Invalid credentials"
- Check ~/.pypirc file permissions (should be 600)
- Verify API token is correct
- Generate new token if needed

### "Wheel build failed"
```bash
# Install wheel package
pip install wheel

# Rebuild
python -m build --wheel
```

## Quick Publish Command

```bash
# One-liner (use with caution)
source .venv/bin/activate && \
pytest tests/unit/test_alerts_resource.py && \
rm -rf dist/ && \
python -m build && \
python -m twine upload dist/* && \
git tag -a v1.4.0 -m "Release v1.4.0" && \
git push origin v1.4.0
```

## Rollback (If Needed)

```bash
# Yank version from PyPI (don't delete)
pip install --upgrade twine
twine upload --skip-existing dist/*

# Or use PyPI web interface to yank
# Go to: https://pypi.org/manage/project/oilpriceapi/releases/

# Publish fixed version
# Edit pyproject.toml: version = "1.4.1"
# Edit __init__.py: __version__ = "1.4.1"
python -m build
python -m twine upload dist/*
```

## Success Indicators

✅ Package appears on PyPI: https://pypi.org/project/oilpriceapi/
✅ Version 1.4.0 listed in release history
✅ `pip install oilpriceapi==1.4.0` works globally
✅ GitHub release created with wheels attached
✅ Git tag v1.4.0 pushed
✅ Download counter incrementing
✅ PyPI badges updated

## Verification Script

```bash
# Run this to verify everything
cat > verify_publish.sh << 'EOF'
#!/bin/bash
set -e

echo "🔍 Verifying PyPI publication..."

# Create test environment
python -m venv /tmp/verify-oilpriceapi
source /tmp/verify-oilpriceapi/bin/activate

# Install from PyPI
pip install oilpriceapi==1.4.0

# Test import and alerts
python << 'PYEOF'
from oilpriceapi import OilPriceAPI, PriceAlert, WebhookTestResponse
import oilpriceapi

print(f"✅ Version: {oilpriceapi.__version__}")
print(f"✅ PriceAlert model imported")
print(f"✅ WebhookTestResponse model imported")

# Check alerts resource exists
client = OilPriceAPI(api_key="test_key")
assert hasattr(client, 'alerts'), "Alerts resource missing!"
print(f"✅ Alerts resource available")

print("\n🎉 Publication verified successfully!")
PYEOF

# Cleanup
deactivate
rm -rf /tmp/verify-oilpriceapi

echo "✅ All checks passed!"
EOF

chmod +x verify_publish.sh
./verify_publish.sh
```

---

**Ready to publish!** 🚀

Run: `python -m build && python -m twine upload dist/*`
