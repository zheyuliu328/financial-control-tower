"""Confusion matrices require explicit labels; unlabelled rules only report counts."""

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .engine import FinancialControlTower, period


class FraudRuleType(Enum):
    TIMING_FRAUD = "timing_fraud"
    NEGATIVE_MARGIN = "negative_margin"


@dataclass
class RulePerformanceMetrics:
    rule_type: FraudRuleType
    evaluation_period: str
    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0
    observations: int = 0
    triggered: int = 0
    label_source: str = "unlabelled"

    def __post_init__(self):
        counts = (
            self.true_positives,
            self.false_positives,
            self.true_negatives,
            self.false_negatives,
            self.observations,
            self.triggered,
        )
        if any(type(value) is not int or value < 0 for value in counts):
            raise ValueError("counts must be nonnegative integers")
        if self.triggered > self.observations:
            raise ValueError("trigger count exceeds observations")
        if self.label_source != "unlabelled" and sum(counts[:4]) != self.observations:
            raise ValueError("confusion matrix must cover the declared observations")

    def _ratio(self, numerator, denominator):
        return numerator / denominator if denominator and self.label_source != "unlabelled" else None

    @property
    def precision(self):
        return self._ratio(self.true_positives, self.true_positives + self.false_positives)

    @property
    def recall(self):
        return self._ratio(self.true_positives, self.true_positives + self.false_negatives)

    @property
    def f1_score(self):
        return self._ratio(
            2 * self.true_positives, 2 * self.true_positives + self.false_positives + self.false_negatives
        )

    @property
    def false_positive_rate(self):
        return self._ratio(self.false_positives, self.false_positives + self.true_negatives)

    @property
    def false_negative_rate(self):
        return self._ratio(self.false_negatives, self.false_negatives + self.true_positives)

    @property
    def accuracy(self):
        return self._ratio(self.true_positives + self.true_negatives, self.observations)

    def to_dict(self):
        result = dict(vars(self), rule_type=self.rule_type.value)
        if self.label_source == "unlabelled":
            for name in ("true_positives", "false_positives", "true_negatives", "false_negatives"):
                result[name] = None
        for name in ("precision", "recall", "f1_score", "false_positive_rate", "false_negative_rate", "accuracy"):
            result[name] = getattr(self, name)
        result["interpretation"] = "agreement with declared labels only; no real fraud-performance claim"
        return result


def evaluate_flags(
    predicted, labels=None, *, rule_type=FraudRuleType.TIMING_FRAUD, label_source="unlabelled", evaluation_period="all"
):
    predicted = list(predicted)
    if any(type(value) is not bool for value in predicted):
        raise ValueError("predictions must be boolean")
    if labels is None:
        if label_source != "unlabelled":
            raise ValueError("a label source without labels is invalid")
        return RulePerformanceMetrics(
            rule_type, evaluation_period, observations=len(predicted), triggered=sum(predicted)
        )
    labels = list(labels)
    if len(labels) != len(predicted) or any(type(value) is not bool for value in labels):
        raise ValueError("labels must be matching booleans without missing values")
    if not label_source.strip() or label_source == "unlabelled":
        raise ValueError("explicit labels require their declared source")
    pairs = list(zip(predicted, labels))
    return RulePerformanceMetrics(
        rule_type,
        evaluation_period,
        sum(p and y for p, y in pairs),
        sum(p and not y for p, y in pairs),
        sum(not p and not y for p, y in pairs),
        sum(not p and y for p, y in pairs),
        len(predicted),
        sum(predicted),
        label_source,
    )


class FraudRuleManager:
    """Historical API name retained; rules identify exceptions, not confirmed fraud."""

    def __init__(self, data_dir=None):
        self.data_dir = Path(data_dir) if data_dir is not None else Path("data")

    def _evaluate(self, rule_type, start_date=None, end_date=None, labels=None, label_source="unlabelled"):
        if bool(start_date) != bool(end_date):
            raise ValueError("provide both start_date and end_date, or neither")
        if start_date and period(start_date) > period(end_date):
            raise ValueError("start_date is after end_date")
        evidence = FinancialControlTower(self.data_dir).audit_supply_chain_risks()
        rows = [row for row in evidence["evaluations"] if row["rule"] == rule_type.value]
        if start_date:
            # Invalid order dates cannot be silently put inside/outside an evaluation window.
            rows = [row for row in rows if period(start_date) <= period(row["order_date"]) <= period(end_date)]
        expected = None
        if labels is not None:
            if set(labels) != {row["order_id"] for row in rows}:
                raise ValueError("labels must cover exactly the evaluated order IDs")
            expected = [labels[row["order_id"]] for row in rows]
        return evaluate_flags(
            [row["triggered"] for row in rows],
            expected,
            rule_type=rule_type,
            label_source=label_source,
            evaluation_period=f"{start_date} to {end_date}" if start_date else "all",
        )

    def evaluate_timing_fraud_rule(self, start_date=None, end_date=None, **kwargs):
        return self._evaluate(FraudRuleType.TIMING_FRAUD, start_date, end_date, **kwargs)

    def evaluate_negative_margin_rule(self, start_date=None, end_date=None, **kwargs):
        return self._evaluate(FraudRuleType.NEGATIVE_MARGIN, start_date, end_date, **kwargs)

    def evaluate_all_rules(self, start_date=None, end_date=None, *, labels=None, label_source="unlabelled"):
        return [
            self._evaluate(
                rule,
                start_date,
                end_date,
                labels=labels[rule.value] if labels is not None else None,
                label_source=label_source,
            )
            for rule in FraudRuleType
        ]

    def generate_performance_report(self, metrics_list):
        return json.dumps([metrics.to_dict() for metrics in metrics_list], indent=2, allow_nan=False)

    def save_metrics_to_audit_db(self, metrics, output_path):
        """Explicit output only; never writes to an input ledger or legacy audit.db."""
        target = Path(output_path)
        protected = [self.data_dir / name for name in ("db_operations.db", "db_finance.db", "audit.db")]
        for source in protected:
            if target.resolve() == source.resolve() or (
                target.exists() and source.exists() and target.samefile(source)
            ):
                raise ValueError("metrics output must not refer to an input database or legacy audit.db")
        with closing(sqlite3.connect(target)) as conn, conn:
            conn.execute("CREATE TABLE IF NOT EXISTS rule_metrics (result_json TEXT NOT NULL)")
            conn.execute("INSERT INTO rule_metrics VALUES (?)", (json.dumps(metrics.to_dict(), allow_nan=False),))
