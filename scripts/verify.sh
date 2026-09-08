#!/usr/bin/env bash
# Required checks fail the script. No installation, network request, deletion or output reuse.
set -euo pipefail
FCT_PYTHON="${FCT_PYTHON:-python}"
FCT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
FCT_VERIFY_OUTPUT="$(mktemp -d "${TMPDIR:-/tmp}/fct-verify.XXXXXX")"
cd "$FCT_ROOT"
"$FCT_PYTHON" -m ruff check --no-cache src scripts tests main.py quick_demo.py fraud_rule_metrics.py
"$FCT_PYTHON" -m ruff format --check --no-cache src scripts tests main.py quick_demo.py fraud_rule_metrics.py
PYTHONDONTWRITEBYTECODE=1 "$FCT_PYTHON" -m pytest -p no:cacheprovider
"$FCT_PYTHON" -m bandit -r src -q
"$FCT_PYTHON" -m pip check
"$FCT_PYTHON" -I -m financial_control_tower.cli --sample --output "$FCT_VERIFY_OUTPUT/sample"
echo "Verification completed; retained outputs: $FCT_VERIFY_OUTPUT"
