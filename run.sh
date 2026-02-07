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
    echo "✓ Dependencies installed"
else
    echo "✓ Dependencies already installed"
fi

# Run quick demo
echo ""
echo "🔍 Running quick demo with sample data..."
python quick_demo.py

# Summary
echo ""
echo "=========================================="
echo "✅ Quick start complete!"
echo ""
echo "Output files:"
ls -lh artifacts/ 2>/dev/null || echo "  (No artifacts)"
echo ""
echo "Next steps:"
echo "  • View full system: python main.py --sample"
echo "  • Read docs: cat README.md"
echo "=========================================="
