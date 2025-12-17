#!/bin/bash

# Pre-Release Validation Script for OilPriceAPI Python SDK
# This script would have caught the v1.4.1 historical timeout bug

set -e  # Exit on first error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
SKIPPED=0

# Options
VERBOSE=false
SKIP_SLOW=false
SKIP_INTEGRATION=false

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --verbose|-v) VERBOSE=true ;;
        --skip-slow) SKIP_SLOW=true ;;
        --skip-integration) SKIP_INTEGRATION=true ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --verbose, -v         Verbose output"
            echo "  --skip-slow           Skip slow tests"
            echo "  --skip-integration    Skip integration tests"
            echo "  --help, -h            Show this help message"
            exit 0
            ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Helper functions
print_header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_check() {
    echo -e "${YELLOW}► $1${NC}"
}

print_pass() {
    echo -e "${GREEN}✓ $1${NC}"
    ((PASSED++))
}

print_fail() {
    echo -e "${RED}✗ $1${NC}"
    ((FAILED++))
    return 1
}

print_skip() {
    echo -e "${YELLOW}⊘ $1${NC}"
    ((SKIPPED++))
}

run_command() {
    local description="$1"
    shift

    print_check "$description"

    if $VERBOSE; then
        if "$@"; then
            print_pass "$description"
        else
            print_fail "$description"
        fi
    else
        if "$@" > /dev/null 2>&1; then
            print_pass "$description"
        else
            print_fail "$description"
        fi
    fi
}

# Start validation
print_header "OilPriceAPI Python SDK - Pre-Release Validation"

echo "This script ensures SDK releases meet quality standards."
echo "It would have caught the v1.4.1 historical timeout bug."
echo ""

# Check we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: pyproject.toml not found. Run from SDK root directory.${NC}"
    exit 1
fi

# 1. VERSION MANAGEMENT
print_header "1. Version Management"

print_check "Checking version consistency"
VERSION_PYPROJECT=$(grep '^version =' pyproject.toml | cut -d'"' -f2)
VERSION_INIT=$(grep '__version__' oilpriceapi/__init__.py | cut -d'"' -f2)

if [ "$VERSION_PYPROJECT" = "$VERSION_INIT" ]; then
    print_pass "Version consistent: $VERSION_PYPROJECT"
else
    print_fail "Version mismatch: pyproject.toml ($VERSION_PYPROJECT) != __init__.py ($VERSION_INIT)"
fi

print_check "Checking CHANGELOG.md updated"
if grep -q "$VERSION_PYPROJECT" CHANGELOG.md; then
    print_pass "CHANGELOG.md includes version $VERSION_PYPROJECT"
else
    print_fail "CHANGELOG.md missing version $VERSION_PYPROJECT"
fi

print_check "Checking no UNRELEASED sections"
if ! grep -q "UNRELEASED" CHANGELOG.md; then
    print_pass "No UNRELEASED sections in CHANGELOG"
else
    print_fail "CHANGELOG contains UNRELEASED sections"
fi

# 2. CODE QUALITY
print_header "2. Code Quality"

# Unit tests
print_check "Running unit tests"
if pytest tests/unit -v --tb=short > /tmp/unit_tests.log 2>&1; then
    print_pass "All unit tests passed"
else
    print_fail "Unit tests failed (see /tmp/unit_tests.log)"
    if $VERBOSE; then
        tail -50 /tmp/unit_tests.log
    fi
fi

# Integration tests
if [ "$SKIP_INTEGRATION" = false ]; then
    print_check "Running integration tests"

    TEST_OPTS="-v --tb=short"
    if [ "$SKIP_SLOW" = true ]; then
        TEST_OPTS="$TEST_OPTS -m 'not slow'"
    fi

    if [ -f ".env" ] && grep -q "OILPRICEAPI_KEY" .env; then
        if pytest tests/integration $TEST_OPTS > /tmp/integration_tests.log 2>&1; then
            print_pass "All integration tests passed"
        else
            print_fail "Integration tests failed (see /tmp/integration_tests.log)"
            if $VERBOSE; then
                tail -50 /tmp/integration_tests.log
            fi
        fi
    else
        print_skip "Integration tests (no API key in .env)"
    fi
else
    print_skip "Integration tests (--skip-integration)"
fi

# Test coverage
print_check "Checking test coverage"
COVERAGE=$(pytest --cov=oilpriceapi --cov-report=term-missing --cov-fail-under=70 tests/unit 2>&1 | grep "^TOTAL" | awk '{print $4}' | sed 's/%//')
if [ ! -z "$COVERAGE" ] && [ "${COVERAGE%.*}" -ge 70 ]; then
    print_pass "Test coverage: $COVERAGE% (≥70%)"
else
    print_fail "Test coverage too low: $COVERAGE% (need ≥70%)"
fi

# Linting
print_check "Running ruff linter"
if command -v ruff &> /dev/null; then
    if ruff check . > /tmp/ruff.log 2>&1; then
        print_pass "No linting errors"
    else
        print_fail "Linting errors found (see /tmp/ruff.log)"
        if $VERBOSE; then
            cat /tmp/ruff.log
        fi
    fi
else
    print_skip "Ruff linter (not installed)"
fi

# Formatting
print_check "Checking code formatting"
if command -v black &> /dev/null; then
    if black --check . > /tmp/black.log 2>&1; then
        print_pass "Code properly formatted"
    else
        print_fail "Code formatting issues (run: black .)"
        if $VERBOSE; then
            cat /tmp/black.log
        fi
    fi
else
    print_skip "Black formatter (not installed)"
fi

# 3. CRITICAL TESTS (Would have caught v1.4.1 bug)
print_header "3. Critical Tests (Historical Timeout Prevention)"

if [ "$SKIP_INTEGRATION" = false ] && [ -f ".env" ]; then
    print_check "Testing 7-day historical query (would catch endpoint bug)"
    if pytest tests/integration/test_historical_endpoints.py::TestHistoricalEndpointSelection::test_7_day_query_uses_past_week_endpoint -v --tb=short > /tmp/7day_test.log 2>&1; then
        print_pass "7-day query test passed (endpoint optimization working)"
    else
        print_fail "7-day query test FAILED - THIS IS THE v1.4.1 BUG!"
        if $VERBOSE; then
            cat /tmp/7day_test.log
        fi
    fi

    print_check "Testing 1-year historical query (would catch timeout bug)"
    if pytest tests/integration/test_historical_endpoints.py::TestHistoricalEndpointSelection::test_365_day_query_uses_past_year_endpoint -v --tb=short > /tmp/1year_test.log 2>&1; then
        print_pass "1-year query test passed (timeout handling working)"
    else
        print_fail "1-year query test FAILED - THIS IS THE v1.4.1 BUG!"
        if $VERBOSE; then
            cat /tmp/1year_test.log
        fi
    fi

    if [ "$SKIP_SLOW" = false ]; then
        print_check "Running performance baseline tests"
        if pytest tests/integration/test_historical_endpoints.py::TestHistoricalPerformanceBaselines -v --tb=short > /tmp/perf_tests.log 2>&1; then
            print_pass "Performance baselines met"
        else
            print_fail "Performance regression detected!"
            if $VERBOSE; then
                cat /tmp/perf_tests.log
            fi
        fi
    else
        print_skip "Performance baseline tests (--skip-slow)"
    fi
else
    print_skip "Critical tests (no API key or integration tests skipped)"
fi

# 4. BUILD & PACKAGE
print_header "4. Build & Package"

print_check "Cleaning previous builds"
if rm -rf dist/ build/ *.egg-info > /dev/null 2>&1; then
    print_pass "Previous builds cleaned"
else
    print_skip "No previous builds to clean"
fi

print_check "Building package"
if python -m build > /tmp/build.log 2>&1; then
    print_pass "Package built successfully"
else
    print_fail "Package build failed (see /tmp/build.log)"
    if $VERBOSE; then
        cat /tmp/build.log
    fi
fi

print_check "Verifying wheel created"
if ls dist/*.whl > /dev/null 2>&1; then
    WHEEL_FILE=$(ls dist/*.whl)
    print_pass "Wheel created: $(basename $WHEEL_FILE)"
else
    print_fail "No wheel file found in dist/"
fi

print_check "Verifying source distribution created"
if ls dist/*.tar.gz > /dev/null 2>&1; then
    SDIST_FILE=$(ls dist/*.tar.gz)
    print_pass "Source dist created: $(basename $SDIST_FILE)"
else
    print_fail "No source distribution found in dist/"
fi

# 5. SECURITY
print_header "5. Security Checks"

print_check "Checking for hardcoded credentials"
if grep -r "sk_live_" oilpriceapi/ 2>/dev/null || grep -r "api_key.*=.*['\"]" oilpriceapi/ | grep -v "api_key: str" | grep -v "api_key=" > /dev/null 2>&1; then
    print_fail "Possible hardcoded credentials found!"
else
    print_pass "No hardcoded credentials detected"
fi

print_check "Scanning dependencies for vulnerabilities"
if command -v pip-audit &> /dev/null; then
    if pip-audit > /tmp/pip-audit.log 2>&1; then
        print_pass "No vulnerable dependencies"
    else
        print_fail "Vulnerable dependencies found (see /tmp/pip-audit.log)"
        if $VERBOSE; then
            cat /tmp/pip-audit.log
        fi
    fi
else
    print_skip "pip-audit (not installed - run: pip install pip-audit)"
fi

# 6. GIT STATUS
print_header "6. Git Status"

print_check "Checking for uncommitted changes"
if [ -z "$(git status --porcelain)" ]; then
    print_pass "No uncommitted changes"
else
    print_fail "Uncommitted changes detected (run: git status)"
    if $VERBOSE; then
        git status --short
    fi
fi

print_check "Checking if tag exists for version"
if git tag | grep -q "^v$VERSION_PYPROJECT$"; then
    print_pass "Git tag v$VERSION_PYPROJECT exists"
else
    print_fail "Git tag v$VERSION_PYPROJECT not found (run: git tag v$VERSION_PYPROJECT)"
fi

# SUMMARY
print_header "Validation Summary"

TOTAL=$((PASSED + FAILED + SKIPPED))

echo -e "${GREEN}✓ Passed:  $PASSED${NC}"
echo -e "${RED}✗ Failed:  $FAILED${NC}"
echo -e "${YELLOW}⊘ Skipped: $SKIPPED${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━"
echo "  Total:   $TOTAL"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅  ALL VALIDATIONS PASSED - READY TO RELEASE${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Review .github/PRE_RELEASE_CHECKLIST.md"
    echo "  2. Test upload to TestPyPI: twine upload --repository testpypi dist/*"
    echo "  3. Upload to PyPI: twine upload dist/*"
    echo "  4. Create GitHub release with CHANGELOG notes"
    echo ""
    exit 0
else
    echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}❌  VALIDATION FAILED - DO NOT RELEASE${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Fix the failed checks above before releasing."
    echo "Re-run this script after fixes: $0"
    echo ""
    echo "This validation would have prevented the v1.4.1 timeout bug."
    echo ""
    exit 1
fi
