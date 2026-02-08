#!/bin/bash
# FCT - Verification Script
# 验收脚本：验证项目可运行性和输出完整性

set -e

RUN_ID="${RUN_ID:-$(date -u +"%Y%m%d-%H%M%S")}"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
VERSION="${VERSION:-v1.0.0}"
REPORT_DIR="${REPORT_DIR:-./artifacts/verify_reports}"

mkdir -p "$REPORT_DIR"

echo "=============================================="
echo "🔍 FCT Verification Script"
echo "Run ID: $RUN_ID"
echo "Timestamp: $TIMESTAMP"
echo "Version: $VERSION"
echo "=============================================="

# 初始化报告
REPORT_FILE="$REPORT_DIR/verify_report_${RUN_ID}.json"
echo '{"run_id": "'$RUN_ID'", "timestamp": "'$TIMESTAMP'", "version": "'$VERSION'", "commands": [], "status": "running"}' > "$REPORT_FILE"

COMMANDS_PASSED=0
COMMANDS_FAILED=0

# 辅助函数
run_check() {
    local name="$1"
    local cmd="$2"
    
    echo ""
    echo "[$name] Running: $cmd"
    
    if eval "$cmd" > /dev/null 2>&1; then
        echo "✅ PASS: $name"
        COMMANDS_PASSED=$((COMMANDS_PASSED + 1))
        return 0
    else
        echo "❌ FAIL: $name"
        COMMANDS_FAILED=$((COMMANDS_FAILED + 1))
        return 1
    fi
}

# ========== 1. 环境检查 ==========
echo ""
echo "📋 Step 1: Environment Check"
echo "------------------------------"

run_check "Python 3.8+" "python --version | grep -E 'Python 3\.(8|9|[0-9])'" || true
run_check "pip available" "pip --version" || true

# ========== 2. 依赖检查 ==========
echo ""
echo "📦 Step 2: Dependencies Check"
echo "------------------------------"

run_check "pandas" "python -c 'import pandas'" || true
run_check "numpy" "python -c 'import numpy'" || true
run_check "matplotlib" "python -c 'import matplotlib'" || true

# ========== 3. 文件结构检查 ==========
echo ""
echo "📁 Step 3: File Structure Check"
echo "------------------------------"

run_check "README.md exists" "test -f README.md" || true
run_check "requirements.txt exists" "test -f requirements.txt" || true
run_check ".env.example exists" "test -f .env.example" || true
run_check "run.sh exists" "test -f run.sh" || true
run_check "Makefile exists" "test -f Makefile" || true
run_check "main.py exists" "test -f main.py" || true

# ========== 4. Quickstart 运行 ==========
echo ""
echo "🚀 Step 4: Quickstart Execution"
echo "------------------------------"

# 安装依赖
if ! python -c "import pandas" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -q -r requirements.txt
fi
run_check "Dependencies installed" "python -c 'import pandas, numpy'" || true

# 运行 quickstart
if [ -f "quick_demo.py" ]; then
    run_check "Quick demo" "python quick_demo.py" || true
elif [ -f "main.py" ]; then
    run_check "Main demo" "python main.py --sample" || true
fi

# ========== 5. 输出检查 ==========
echo ""
echo "📊 Step 5: Output Verification"
echo "------------------------------"

run_check "artifacts directory" "test -d artifacts" || true
run_check "data directory" "test -d data" || true
run_check "docs directory" "test -d docs" || true

# 检查数据库文件
if [ -f "data/audit.db" ]; then
    run_check "audit.db exists" "test -s data/audit.db" || true
fi

# ========== 6. 生成报告 ==========
echo ""
echo "📝 Generating Report"
echo "------------------------------"

FINAL_STATUS="passed"
if [ $COMMANDS_FAILED -gt 0 ]; then
    FINAL_STATUS="partial"
fi
if [ $COMMANDS_PASSED -eq 0 ]; then
    FINAL_STATUS="failed"
fi

# 生成 JSON 报告
cat > "$REPORT_FILE" << EOF
{
  "run_id": "$RUN_ID",
  "timestamp": "$TIMESTAMP",
  "version": "$VERSION",
  "project": "fct",
  "commands_passed": $COMMANDS_PASSED,
  "commands_failed": $COMMANDS_FAILED,
  "final_status": "$FINAL_STATUS",
  "checks": {
    "environment": "checked",
    "dependencies": "checked",
    "file_structure": "checked",
    "quickstart": "checked",
    "outputs": "checked"
  }
}
EOF

echo ""
echo "=============================================="
echo "✅ Verification Complete"
echo "Status: $FINAL_STATUS"
echo "Passed: $COMMANDS_PASSED"
echo "Failed: $COMMANDS_FAILED"
echo "Report: $REPORT_FILE"
echo "=============================================="

# 输出验证结果
if [ "$FINAL_STATUS" = "passed" ]; then
    exit 0
else
    exit 1
fi
