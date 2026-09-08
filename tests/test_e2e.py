"""Run the installed wheel from outside the checkout, using fresh output paths."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e


def test_installed_cli_outside_checkout(tmp_path):
    result = subprocess.run(
        [sys.executable, "-I", "-m", "financial_control_tower.cli", "--sample", "--output", str(tmp_path / "run")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads((tmp_path / "run/audit_report.json").read_text())
    assert report["reconciliation"]["counts"]["finance_only"] == 1
    assert report["reconciliation"]["counts"]["duplicate_key"] == 1
    assert report["rule_metrics"][0]["false_negatives"] == 1
    assert report["rule_metrics"][0]["false_positives"] == 1


def test_console_script_and_failure_exit(tmp_path):
    executable = Path(sys.executable).parent / ("fct.exe" if os.name == "nt" else "fct")
    good = subprocess.run(
        [str(executable), "--sample", "--output", str(tmp_path / "ok")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert good.returncode == 0, good.stderr
    failure = subprocess.run(
        [str(executable), "--data-dir", str(tmp_path / "absent"), "--output", str(tmp_path / "bad")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert failure.returncode != 0
    assert not (tmp_path / "bad/audit_report.json").exists()
    refused = subprocess.run(
        [str(executable), "--sample", "--output", str(tmp_path / "ok")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert refused.returncode != 0 and "never replaced" in refused.stderr


@pytest.mark.parametrize(
    "entry", ["main.py", "quick_demo.py", "fraud_rule_metrics.py", "scripts/run_financial_audit.py"]
)
def test_compatible_source_entry(tmp_path, entry):
    script = Path(__file__).resolve().parents[1] / entry
    result = subprocess.run(
        [sys.executable, str(script), "--sample", "--output", str(tmp_path / "compat")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
    )
    assert result.returncode == 0, result.stderr
    assert (
        json.loads((tmp_path / "compat/audit_report.json").read_text())["provenance"]["data_kind"] == "invented_fixture"
    )


@pytest.mark.parametrize("defect", ["missing_table", "missing_column"])
def test_schema_failure_is_nonzero(tmp_path, defect):
    import sqlite3

    from financial_control_tower.sample import create_sample

    inputs = tmp_path / "inputs"
    create_sample(inputs)
    with sqlite3.connect(inputs / "db_finance.db") as conn:
        if defect == "missing_table":
            conn.execute("ALTER TABLE accounts_receivable RENAME TO incompatible_table")
        else:
            conn.execute("ALTER TABLE accounts_receivable RENAME COLUMN invoice_amount TO incompatible_column")
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-m",
            "financial_control_tower.cli",
            "--data-dir",
            str(inputs),
            "--output",
            str(tmp_path / "output"),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "Audit could not execute" in result.stderr
    assert not (tmp_path / "output/audit_report.json").exists()
