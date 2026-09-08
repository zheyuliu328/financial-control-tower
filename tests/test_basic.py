"""Independent fixtures assert classifications and coverage, not command completion."""

import hashlib
import json
import sqlite3
from decimal import Decimal

import pytest

from financial_control_tower.cli import run
from financial_control_tower.engine import FinancialControlTower, money
from financial_control_tower.rules import FraudRuleManager, evaluate_flags
from financial_control_tower.sample import create_sample

pytestmark = pytest.mark.unit


@pytest.fixture
def data_dir(tmp_path):
    path = tmp_path / "inputs"
    create_sample(path)
    return path


def test_full_sample_expected_classifications(tmp_path):
    result = run(tmp_path / "result")
    recon = result["reconciliation"]
    assert recon["input_rows"] == {"operations": 8, "finance": 6}
    assert recon["counts"] == {
        "matched": 2,
        "amount_mismatch": 1,
        "operations_only": 1,
        "finance_only": 1,
        "duplicate_key": 1,
        "invalid_input": 1,
    }
    assert {row["order_id"]: row["status"] for row in recon["classifications"]} == {
        "O01": "matched",
        "O02": "amount_mismatch",
        "O03": "operations_only",
        "O04": "duplicate_key",
        "O05": "invalid_input",
        "O07": "matched",
        "F08": "finance_only",
    }
    assert len(recon["invalid_rows"]) == 1
    assert recon["excluded_rows"] == [
        {"source": "operations", "order_id": "O06", "reason": "deferred_or_cancelled_status"}
    ]
    assert recon["coverage_status"] == "blocked_inputs"
    assert result["financial_summary"]["monthly"] == [
        {
            "month": "2024-01",
            "orders": 4,
            "sales": "330",
            "profit": "15",
            "margin_percent": str(Decimal(15) / Decimal(330) * 100),
        }
    ]
    assert json.loads((tmp_path / "result/audit_report.json").read_text()) == result


@pytest.mark.parametrize("value", [None, True, "nan", "Infinity", "oops", "-Infinity"])
def test_invalid_amounts_rejected(value):
    with pytest.raises(ValueError):
        money(value)


def test_cent_policy_and_duplicate_cardinality(data_dir):
    engine = FinancialControlTower(data_dir)
    assert engine.reconcile_operations_finance()["counts"]["matched"] == 2
    with sqlite3.connect(data_dir / "db_finance.db") as conn:
        conn.execute("UPDATE accounts_receivable SET invoice_amount='100.0101' WHERE order_id='O07'")
        conn.execute("INSERT INTO accounts_receivable VALUES ('O01', '100', 'OPEN')")
    recon = engine.reconcile_operations_finance()
    assert recon["counts"]["amount_mismatch"] == 2
    assert recon["counts"]["duplicate_key"] == 2
    assert recon["counts"]["matched"] == 0


def test_bad_keys_nulls_unknown_status(data_dir):
    with sqlite3.connect(data_dir / "db_finance.db") as conn:
        conn.execute("UPDATE accounts_receivable SET invoice_amount=NULL WHERE order_id='O01'")
        conn.execute("UPDATE accounts_receivable SET payment_status=NULL WHERE order_id='O02'")
        conn.execute("INSERT INTO accounts_receivable VALUES ('', '100', 'OPEN')")
    result = FinancialControlTower(data_dir).reconcile_operations_finance()
    assert len(result["invalid_rows"]) == 4
    assert result["counts"]["invalid_input"] == 3
    assert result["coverage_status"] == "blocked_inputs"


def test_shipping_gaps_do_not_hide_negative_profit(data_dir):
    with sqlite3.connect(data_dir / "db_operations.db") as conn:
        conn.execute("UPDATE sales_orders SET profit='-9' WHERE order_id='O03'")
        conn.execute("INSERT INTO shipping_logs VALUES ('O01', '2024-01-12')")
        conn.execute("INSERT INTO shipping_logs VALUES ('ORPHAN', '2024-01-12')")
    report = FinancialControlTower(data_dir).audit_supply_chain_risks()
    pairs = {(row["order_id"], row["rule"]) for row in report["issues"]}
    assert {
        ("O03", "negative_margin"),
        ("O03", "missing_shipping"),
        ("O01", "duplicate_shipping"),
        ("O05", "invalid_date"),
        ("O02", "shipping_before_order"),
        ("ORPHAN", "shipping_without_order"),
    } <= pairs
    assert not any(row["order_id"] == "O05" and row["rule"] == "timing_fraud" for row in report["evaluations"])


def test_zero_revenue_margin_undefined(data_dir):
    with sqlite3.connect(data_dir / "db_operations.db") as conn:
        conn.execute("UPDATE sales_orders SET sales='0' WHERE order_id IN ('O01','O02','O03','O07')")
    assert FinancialControlTower(data_dir).generate_financial_statements()["monthly"][0]["margin_percent"] is None


def test_label_matrix_and_undefined_denominators():
    metric = evaluate_flags(
        [True, True, False, False], [True, False, True, False], label_source="independent_toy_fixture"
    )
    assert (metric.true_positives, metric.false_positives, metric.false_negatives, metric.true_negatives) == (
        1,
        1,
        1,
        1,
    )
    assert metric.precision == metric.recall == metric.accuracy == metric.f1_score == 0.5
    empty = evaluate_flags([], [], label_source="empty_fixture").to_dict()
    assert empty["precision"] is None and empty["accuracy"] is None
    unlabelled = evaluate_flags([True, False]).to_dict()
    assert unlabelled["observations"] == 2 and unlabelled["triggered"] == 1
    assert unlabelled["true_positives"] is None and unlabelled["recall"] is None
    with pytest.raises(ValueError):
        evaluate_flags([True], [False])
    with pytest.raises(ValueError):
        evaluate_flags([True], [None], label_source="bad_fixture")


def test_default_and_filtered_metrics(data_dir):
    manager = FraudRuleManager(data_dir)
    metrics = manager.evaluate_all_rules()
    assert [metric.observations for metric in metrics] == [3, 4]
    assert all(metric.label_source == "unlabelled" and metric.accuracy is None for metric in metrics)
    assert manager.evaluate_negative_margin_rule("2024-01-01", "2024-01-31").observations == 4
    with pytest.raises(ValueError):
        manager.evaluate_timing_fraud_rule("2024-01-01")
    with pytest.raises(ValueError):
        manager.evaluate_negative_margin_rule("2024-02-01", "2024-01-01")


def test_read_only_input_and_no_overwrite(data_dir, tmp_path):
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in data_dir.iterdir()}
    destination = tmp_path / "output"
    result = run(destination, data_dir)
    assert all(row["label_source"] == "unlabelled" for row in result["rule_metrics"])
    assert before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in data_dir.iterdir()}
    with pytest.raises(ValueError, match="never replaced"):
        run(destination)
    assert (destination / "audit_report.json").exists()


def test_mutable_log_no_immutability_claim(tmp_path):
    run(tmp_path / "run")
    with sqlite3.connect(tmp_path / "run/audit.db") as conn:
        assert conn.execute("SELECT count(*) FROM audit_logs").fetchone()[0] > 0
        conn.execute("UPDATE audit_logs SET section='test' WHERE id=1")
        assert conn.execute("SELECT section FROM audit_logs WHERE id=1").fetchone()[0] == "test"
        conn.rollback()


@pytest.mark.parametrize("name", ["db_operations.db", "db_finance.db", "audit.db"])
def test_metrics_writer_refuses_input_and_symlink_alias(data_dir, tmp_path, name):
    source = data_dir / name
    if not source.exists():
        with sqlite3.connect(source) as conn:
            conn.execute("CREATE TABLE preserved (value TEXT)")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    metric = evaluate_flags([True])
    manager = FraudRuleManager(data_dir)
    alias = tmp_path / "alias.db"
    alias.symlink_to(source)
    for target in (source, alias):
        with pytest.raises(ValueError, match="input database"):
            manager.save_metrics_to_audit_db(metric, target)
        assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
    destination = tmp_path / "metrics.db"
    manager.save_metrics_to_audit_db(metric, destination)
    with sqlite3.connect(destination) as conn:
        saved = json.loads(conn.execute("SELECT result_json FROM rule_metrics").fetchone()[0])
    assert saved["label_source"] == "unlabelled" and saved["precision"] is None


def test_missing_region_retains_reconcilable_totals(data_dir):
    with sqlite3.connect(data_dir / "db_operations.db") as conn:
        conn.execute("UPDATE sales_orders SET customer_country=NULL WHERE order_id='O01'")
    result = FinancialControlTower(data_dir).generate_financial_statements()
    assert sum(Decimal(row["sales"]) for row in result["monthly"]) == sum(
        Decimal(row["sales"]) for row in result["regional"]
    )
    assert sum(row["orders"] for row in result["monthly"]) == sum(row["orders"] for row in result["regional"])
    missing = [row for row in result["regional"] if row["missing_dimension"]]
    assert missing == [
        {"region": "Unknown / unassigned", "missing_dimension": True, "orders": 1, "sales": "100", "profit": "20"}
    ]


def test_null_key_does_not_collide_with_literal_none(data_dir):
    with sqlite3.connect(data_dir / "db_operations.db") as conn:
        conn.executemany(
            "INSERT INTO sales_orders VALUES (?, 'COMPLETE', '80', '8', '2024-01-10', 'Example A')",
            [(None,), ("None",)],
        )
        conn.execute("INSERT INTO shipping_logs VALUES ('None', '2024-01-11')")
    with sqlite3.connect(data_dir / "db_finance.db") as conn:
        conn.execute("INSERT INTO accounts_receivable VALUES ('None', '80', 'PAID')")
    tower = FinancialControlTower(data_dir)
    report = tower.run_full_audit()
    assert {row["order_id"]: row["status"] for row in report["reconciliation"]["classifications"]}["None"] == "matched"
    assert any(row["order_id"] == "None" for row in report["supply_chain"]["evaluations"])
    assert report["financial_summary"]["monthly"][0]["sales"] == "410"


@pytest.mark.parametrize("value", ["2024-W01-1", "20240101", "2024-1-01", "2024-02-30"])
def test_date_contract_is_calendar_iso_only(value):
    from financial_control_tower.engine import period

    with pytest.raises(ValueError):
        period(value)


def test_active_wal_is_rejected_without_checkpointing(data_dir, tmp_path):
    with sqlite3.connect(data_dir / "db_operations.db") as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute("UPDATE sales_orders SET sales='101' WHERE order_id='O01'")
        writer.commit()
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in data_dir.iterdir()}
        with pytest.raises(ValueError, match="WAL"):
            run(tmp_path / "wal-output", data_dir)
        assert before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in data_dir.iterdir()}
        assert not (tmp_path / "wal-output/audit_report.json").exists()


def test_input_change_during_run_prevents_report(data_dir, tmp_path, monkeypatch):
    original = FinancialControlTower.run_full_audit

    def mutate_after_read(engine):
        result = original(engine)
        with sqlite3.connect(data_dir / "db_operations.db") as writer:
            writer.execute("UPDATE sales_orders SET sales='101' WHERE order_id='O01'")
        return result

    monkeypatch.setattr(FinancialControlTower, "run_full_audit", mutate_after_read)
    with pytest.raises(ValueError, match="input changed"):
        run(tmp_path / "changing-output", data_dir)
    assert not (tmp_path / "changing-output/audit_report.json").exists()


@pytest.mark.parametrize("sidecar", ["-wal", "-journal"])
def test_sidecars_at_symlink_target_are_rejected(data_dir, tmp_path, sidecar):
    from financial_control_tower.engine import require_stable_database

    target = data_dir / "db_operations.db"
    marker = target.with_name(target.name + sidecar)
    marker.write_bytes(b"nonempty sidecar fixture")
    alias = tmp_path / "alias.db"
    alias.symlink_to(target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="nonempty"):
        require_stable_database(alias)
    assert hashlib.sha256(target.read_bytes()).hexdigest() == digest
    assert marker.read_bytes() == b"nonempty sidecar fixture"


def test_hardlinked_source_is_rejected(data_dir, tmp_path):
    import os

    from financial_control_tower.engine import require_stable_database

    target = data_dir / "db_operations.db"
    alias = tmp_path / "alias.db"
    os.link(target, alias)
    with pytest.raises(ValueError, match="hardlinked"):
        require_stable_database(alias)
