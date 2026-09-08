"""Invented, fixed fixtures. Existing repository CSVs and databases are never opened."""

import sqlite3
from contextlib import closing


def create_sample(data_dir):
    data_dir.mkdir(parents=True, exist_ok=False)
    with closing(sqlite3.connect(data_dir / "db_operations.db")) as conn, conn:
        conn.execute(
            "CREATE TABLE sales_orders (order_id TEXT, order_status TEXT, sales TEXT, profit TEXT, order_date TEXT, customer_country TEXT)"
        )
        conn.executemany(
            "INSERT INTO sales_orders VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("O01", "COMPLETE", "100", "20", "2024-01-10", "Example A"),
                ("O02", "COMPLETE", "100", "-10", "2024-01-10", "Example A"),
                ("O03", "SHIPPED", "30", "5", "2024-01-10", "Example B"),
                ("O04", "COMPLETE", "20", "3", "2024-01-10", "Example B"),
                ("O04", "COMPLETE", "21", "3", "2024-01-10", "Example B"),
                ("O05", "COMPLETE", None, None, "2024-01-10", "Example B"),
                ("O06", "PENDING", "60", "10", "2024-01-10", "Example B"),
                ("O07", "COMPLETE", "100", "0", "2024-01-10", "Example A"),
            ],
        )
        conn.execute("CREATE TABLE shipping_logs (order_id TEXT, shipping_date TEXT)")
        conn.executemany(
            "INSERT INTO shipping_logs VALUES (?, ?)",
            [
                ("O01", "2024-01-11"),
                ("O02", "2024-01-09"),
                ("O04", "2024-01-11"),
                ("O05", "not-a-date"),
                ("O07", "2024-01-10"),
            ],
        )
    with closing(sqlite3.connect(data_dir / "db_finance.db")) as conn, conn:
        conn.execute("CREATE TABLE accounts_receivable (order_id TEXT, invoice_amount TEXT, payment_status TEXT)")
        conn.executemany(
            "INSERT INTO accounts_receivable VALUES (?, ?, ?)",
            [
                ("O01", "100", "PAID"),
                ("O02", "105", "OPEN"),
                ("O04", "40", "OPEN"),
                ("O05", "25", "OPEN"),
                ("O07", "100.01", "PAID"),
                ("F08", "10", "OPEN"),
            ],
        )


def sample_labels():
    # Deliberately separate toy outcomes: neither anomaly rule defines these labels.
    # Their disagreement exercises TP/FP/TN/FN, not the accuracy of real fraud detection.
    return {
        "timing_fraud": {"O01": True, "O02": False, "O07": False},
        "negative_margin": {"O01": False, "O02": True, "O03": True, "O07": False},
    }
