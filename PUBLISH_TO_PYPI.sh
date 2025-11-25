#!/bin/bash
# Script to publish oilpriceapi SDK v1.0.1 to PyPI

set -e  # Exit on error

echo "="
echo "Publishing oilpriceapi v1.0.1 to PyPI"
echo "="
echo ""

# Activate build environment
cd /home/kwaldman/code/sdks/python
source build-env/bin/activate

# Verify packages exist and are valid
echo "✓ Checking packages..."
twine check dist/oilpriceapi-1.0.1*
echo ""

# Show what we're about to upload
echo "📦 Packages to upload:"
ls -lh dist/oilpriceapi-1.0.1*
echo ""

# Upload to PyPI
echo "🚀 Uploading to PyPI..."
echo ""
echo "You'll be prompted for your PyPI credentials:"
echo "  Username: __token__"
echo "  Password: pypi-xxxxx (your API token)"
echo ""

twine upload dist/oilpriceapi-1.0.1*

echo ""
echo "="
echo "✅ PUBLISHED SUCCESSFULLY!"
echo "="
echo ""
echo "Next steps:"
echo "1. Wait 2-3 minutes for PyPI to process"
echo "2. Test: pip install --upgrade oilpriceapi"
echo "3. Verify version: python -c 'import oilpriceapi; print(oilpriceapi.__version__)'"
echo ""
