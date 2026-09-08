"""Run an offline sample or documented SQLite inputs into a new output directory."""

import argparse
import hashlib
import json
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from . import __version__
from .engine import FinancialControlTower, require_stable_database
from .rules import FraudRuleManager
from .sample import create_sample, sample_labels


def input_fingerprint(data_dir):
    evidence = {}
    for name in ("db_operations.db", "db_finance.db"):
        path = data_dir / name
        require_stable_database(path)
        before = path.stat()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        after = path.stat()
        fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        identity = tuple(getattr(after, field) for field in fields)
        if identity != tuple(getattr(before, field) for field in fields):
            raise ValueError("input changed while fingerprinting; use a stable copy")
        require_stable_database(path)
        evidence[name] = (digest, identity)
    return evidence


def run(output, data_dir=None):
    output = Path(output)
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("output must be a new or empty directory; existing contents are never replaced")
    output.mkdir(parents=True, exist_ok=True)
    synthetic = data_dir is None
    if synthetic:
        data_dir = output / "sample_inputs"
        create_sample(data_dir)
    data_dir = Path(data_dir)
    before = input_fingerprint(data_dir)
    result = FinancialControlTower(data_dir).run_full_audit()
    manager = FraudRuleManager(data_dir)
    result["rule_metrics"] = [
        row.to_dict()
        for row in manager.evaluate_all_rules(
            labels=sample_labels() if synthetic else None,
            label_source="synthetic_fixture_declared_outcomes" if synthetic else "unlabelled",
        )
    ]
    if before != input_fingerprint(data_dir):
        raise ValueError("input changed during the audit; no report is published, use a stable checkpointed copy")
    result["provenance"] = {
        "version": __version__,
        "data_kind": "invented_fixture" if synthetic else "caller_supplied_unverified",
        "input_sha256": {name: evidence[0] for name, evidence in before.items()},
        "input_policy": "stable checkpointed copies only; nonempty WAL/rollback journals and hardlinked inputs rejected; pre/post fingerprints must match",
        "runtime": "offline; no external ERP or market-data connection",
        "logging": "ordinary mutable SQLite records; no tamper-resistance guarantee",
    }
    with closing(sqlite3.connect(output / "audit.db")) as conn, conn:
        conn.execute("CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, section TEXT, record_json TEXT)")
        for section, records in [
            ("reconciliation", result["reconciliation"]["classifications"]),
            ("supply_chain", result["supply_chain"]["issues"]),
        ]:
            conn.executemany(
                "INSERT INTO audit_logs (section, record_json) VALUES (?, ?)",
                [(section, json.dumps(row, allow_nan=False)) for row in records],
            )
    (output / "audit_report.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--sample", action="store_true", help="Use invented fixtures (default)")
    mode.add_argument("--data-dir", type=Path, help="Read existing inputs using the documented schema")
    parser.add_argument("--output", type=Path, help="New/empty destination; never overwrite user output")
    args = parser.parse_args(argv)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = args.output or Path("artifacts") / f"offline-{stamp}-{uuid4().hex[:8]}"
    try:
        result = run(output, args.data_dir)
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(f"Audit could not execute: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "output": str(output),
                "execution": "completed",
                "data_kind": result["provenance"]["data_kind"],
                "reconciliation": result["reconciliation"]["counts"],
                "meaning": "successful execution can contain exceptions; this is not audit approval",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
