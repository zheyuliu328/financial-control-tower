"""Compatibility exports; scores require labels with an explicit source."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from financial_control_tower.cli import main
from financial_control_tower.rules import FraudRuleManager as FraudRuleManager
from financial_control_tower.rules import FraudRuleType as FraudRuleType
from financial_control_tower.rules import RulePerformanceMetrics as RulePerformanceMetrics
from financial_control_tower.rules import evaluate_flags as evaluate_flags

if __name__ == "__main__":
    raise SystemExit(main())
