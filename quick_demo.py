#!/usr/bin/env python3
"""
FCT Quick Demo - Simplified version for quickstart
"""

import sqlite3
from pathlib import Path

import pandas as pd


def run_demo():
    print("=" * 70)
    print("   Financial Control Tower - Quick Demo")
    print("=" * 70)

    # Setup paths
    project_root = Path(__file__).parent
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)

    # Create sample databases
    print("\n[Step 1] Creating sample databases...")

    # Operations DB
    conn_ops = sqlite3.connect(data_dir / "db_operations.db")
    df_ops = pd.read_csv(project_root / "data" / "sample" / "operations_sample.csv")
    df_ops.to_sql("sales_orders", conn_ops, if_exists="replace", index=False)
    conn_ops.close()
    print("✓ Operations database created")

    # Finance DB
    conn_fin = sqlite3.connect(data_dir / "db_finance.db")
    df_fin = pd.read_csv(project_root / "data" / "sample" / "finance_sample.csv")
    df_fin.to_sql("order_revenue", conn_fin, if_exists="replace", index=False)
    conn_fin.close()
    print("✓ Finance database created")

    # Audit DB
    conn_audit = sqlite3.connect(data_dir / "audit.db")
    conn_audit.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            severity TEXT,
            description TEXT
        )
    """)

    # Run simple reconciliation
    print("\n[Step 2] Running reconciliation...")

    conn_ops = sqlite3.connect(data_dir / "db_operations.db")
    conn_fin = sqlite3.connect(data_dir / "db_finance.db")

    df_ops = pd.read_sql("SELECT * FROM sales_orders", conn_ops)
    df_fin = pd.read_sql("SELECT * FROM order_revenue", conn_fin)

    # Simple matching
    matched = 0
    mismatched = 0

    for _, fin_row in df_fin.iterrows():
        order_id = fin_row["order_id"]
        fin_amount = fin_row["amount"]

        ops_match = df_ops[df_ops["order_id"] == order_id]
        if not ops_match.empty:
            ops_amount = ops_match.iloc[0]["sales"]
            if abs(fin_amount - ops_amount) < 0.01:
                matched += 1
                status = "MATCHED"
            else:
                mismatched += 1
                status = "MISMATCH"

            conn_audit.execute(
                "INSERT INTO audit_logs (timestamp, severity, description) VALUES (datetime('now'), ?, ?)",
                (
                    "INFO" if status == "MATCHED" else "WARNING",
                    f"Order {order_id}: {status} (Ops: {ops_amount}, Fin: {fin_amount})",
                ),
            )

    conn_audit.commit()
    conn_ops.close()
    conn_fin.close()
    conn_audit.close()

    print(f"✓ Reconciliation complete: {matched} matched, {mismatched} mismatched")

    # Generate report
    print("\n[Step 3] Generating report...")

    artifacts_dir = project_root / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)

    report = {
        "mode": "DEMO",
        "timestamp": pd.Timestamp.now().isoformat(),
        "summary": {
            "total_orders": len(df_ops),
            "matched": matched,
            "mismatched": mismatched,
            "match_rate": f"{matched / len(df_ops) * 100:.1f}%",
        },
        "output_files": ["data/db_operations.db", "data/db_finance.db", "data/audit.db"],
    }

    import json

    with open(artifacts_dir / "quickstart_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print("✓ Report saved to: artifacts/quickstart_report.json")

    print("\n" + "=" * 70)
    print("✅ Demo complete!")
    print("=" * 70)

    return report


if __name__ == "__main__":
    run_demo()
