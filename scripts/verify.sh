#!/bin/bash
# Unified Verification Script for OpenClaw Projects
# 统一验收脚本 - 必须在三仓都能运行

set -e

PROJECT_NAME=$(basename $(pwd))
echo "================================"
echo "🔍 Verifying: $PROJECT_NAME"
echo "================================"
echo ""

# Colors for output (disable for compatibility)
RED=''
GREEN=''
YELLOW=''
NC=''

# Counters
PASSED=0
FAILED=0

# Helper functions
pass() {
    echo "[PASS]: $1"
    PASSED=$((PASSED + 1))
}

fail() {
    echo "[FAIL]: $1"
    FAILED=$((FAILED + 1))
}

warn() {
    echo "[WARN]: $1"
}

# 1. Check project structure
echo "[1/8] Checking project structure..."
if [ -d "src" ] && [ -f "pyproject.toml" ] && [ -f "Makefile" ]; then
    pass "Project structure (src/ + pyproject.toml + Makefile)"
else
    fail "Project structure missing src/ or pyproject.toml or Makefile"
fi

# 2. Check configuration files
echo ""
echo "[2/8] Checking configuration files..."
if [ -f ".env.example" ]; then
    pass ".env.example exists"
else
    fail ".env.example missing"
fi

if [ -f "config/config.example.yaml" ] || [ -f "config.yaml.example" ]; then
    pass "Config example exists"
else
    warn "Config example missing (optional but recommended)"
fi

# 3. Check lint
echo ""
echo "[3/8] Running lint checks..."
if make lint > /dev/null 2>&1; then
    pass "Lint check"
else
    fail "Lint check"
fi

# 4. Check tests
echo ""
echo "[4/8] Running tests..."
if make test > /dev/null 2>&1; then
    pass "Unit tests"
else
    fail "Unit tests"
fi

# 5. Check quickstart
echo ""
echo "[5/8] Running quickstart..."
OUTPUT_DIR=""
if [ -d "artifacts" ]; then
    OUTPUT_DIR="artifacts"
elif [ -d "reports" ]; then
    OUTPUT_DIR="reports"
else
    OUTPUT_DIR="output"
    mkdir -p $OUTPUT_DIR
fi

# Clean previous output
rm -rf $OUTPUT_DIR/*

if make quickstart > /tmp/quickstart.log 2>&1; then
    pass "Quickstart execution"
    
    # Check output files exist
    if [ "$(ls -A $OUTPUT_DIR)" ]; then
        pass "Quickstart output files in $OUTPUT_DIR/"
        echo "      Output files:"
        ls -1 $OUTPUT_DIR/ | head -5 | sed 's/^/        - /'
    else
        fail "Quickstart output files missing"
    fi
else
    fail "Quickstart execution"
    echo "      See /tmp/quickstart.log for details"
fi

# 6. Check config validation
echo ""
echo "[6/8] Checking config validation..."
if make config-check > /dev/null 2>&1 || [ -f "config/validator.py" ]; then
    pass "Config validation mechanism"
else
    warn "Config validation not implemented"
fi

# 7. Check security
echo ""
echo "[7/8] Running security checks..."
if [ -f ".github/workflows/security.yml" ] && grep -q "gitleaks" .github/workflows/security.yml 2>/dev/null; then
    pass "Security scan in CI (gitleaks)"
else
    warn "Security scan not in CI"
fi

if [ -f ".gitleaks.toml" ]; then
    pass ".gitleaks.toml exists"
else
    warn ".gitleaks.toml missing"
fi

if [ -f ".pre-commit-config.yaml" ] && grep -q "gitleaks" .pre-commit-config.yaml 2>/dev/null; then
    pass "pre-commit gitleaks configured"
else
    warn "pre-commit gitleaks not configured"
fi

if grep -q ".env" .gitignore 2>/dev/null; then
    pass ".env in .gitignore"
else
    fail ".env not in .gitignore"
fi

# 8. Check documentation
echo ""
echo "[8/8] Checking documentation..."
if [ -f "README.md" ]; then
    pass "README.md exists"
else
    fail "README.md missing"
fi

if [ -f "docs/quickstart.md" ] || [ -f "QUICKSTART.md" ]; then
    pass "Quickstart documentation"
else
    warn "Quickstart documentation missing"
fi

if [ -f "LICENSE" ]; then
    pass "LICENSE exists"
else
    warn "LICENSE missing"
fi

# Summary
echo ""
echo "================================"
echo "Verification Summary"
echo "================================"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "[OK] All checks passed!"
    exit 0
else
    echo "[ERROR] Some checks failed."
    exit 1
fi
