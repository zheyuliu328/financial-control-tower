#!/bin/bash
set -e

echo "🏢 Financial Control Tower - Quick Start"
echo "=========================================="

# Check Python version
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Install dependencies if needed
if ! python -c "import pandas" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -q -r requirements.txt
fi
echo "✓ Dependencies installed"

# Setup project (download sample data or use fallback)
echo ""
echo "📊 Setting up project..."
if python scripts/setup_project.py 2>/dev/null; then
    echo "✓ Sample data ready"
else
    echo "⚠️  Using built-in sample data (Kaggle download skipped)"
fi

# Run audit
echo ""
echo "🔍 Running financial audit..."
python main.py

# Summary
echo ""
echo "=========================================="
echo "✅ Quick start complete!"
echo ""
echo "Output files:"
echo "  • data/audit.db - Audit trail database"
echo "  • data/reconciliation_report.xlsx - Reconciliation report"
echo ""
echo "Next steps:"
echo "  • View dashboard: streamlit run main.py"
echo "  • Read docs: cat README.md"
echo "=========================================="
