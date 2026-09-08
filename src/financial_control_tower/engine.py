"""Read-only input checks; classifications are exceptions, never proof of fraud."""

import re
import sqlite3
from collections import Counter, defaultdict
from contextlib import closing
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

ACTIVE = {"COMPLETE", "COMPLETED", "CLOSED", "SHIPPED"}
DEFERRED = {"PENDING", "PROCESSING", "PENDING_PAYMENT", "ON_HOLD"}
CANCELLED = {"CANCELED", "CANCELLED", "SUSPECTED_FRAUD"}
PAYMENTS = {"PAID", "UNPAID", "PENDING", "OPEN", "OVERDUE", "PARTIAL"}
TOLERANCE = Decimal("0.01")


def money(value):
    """Amounts are decimal currency units; negatives are permitted, NaN/inf are not."""
    if value is None or isinstance(value, bool):
        raise ValueError("amount must be a finite decimal")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("amount must be a finite decimal") from exc
    if not result.is_finite():
        raise ValueError("amount must be a finite decimal")
    return result


def order_key(value):
    if value is None or isinstance(value, bool) or not str(value).strip():
        raise ValueError("order_id must be nonblank")
    return str(value).strip()


def period(value):
    """The demonstrator accepts calendar dates in ISO YYYY-MM-DD form only."""
    if not isinstance(value, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
        raise ValueError("date must be YYYY-MM-DD")
    return date.fromisoformat(value)


def require_stable_database(path):
    """Immutable reads require standalone, checkpointed copies, never live journals."""
    target = path.resolve()
    if target.stat().st_nlink != 1:
        raise ValueError("hardlinked inputs are unsupported; provide a standalone checkpointed copy")
    for candidate in {path, target}:
        for suffix in ("-wal", "-journal"):
            sidecar = candidate.with_name(candidate.name + suffix)
            if sidecar.exists() and sidecar.stat().st_size:
                kind = "WAL" if suffix == "-wal" else "rollback journal"
                raise ValueError(
                    f"nonempty {kind} input is unsupported; provide a stable checkpointed copy without changing the source here"
                )


def _read(path, query, required):
    if not path.is_file():
        raise FileNotFoundError(f"Missing input database: {path.name}")
    require_stable_database(path)
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(query)
        columns = {column[0] for column in cursor.description}
        if not set(required) <= columns:
            raise ValueError(f"Missing columns: {sorted(set(required) - columns)}")
        return [dict(row) for row in cursor]


class FinancialControlTower:
    """Audit a documented SQLite input schema without modifying source databases."""

    def __init__(self, data_dir=None):
        self.data_dir = Path(data_dir) if data_dir is not None else Path("data")
        self.db_ops = self.data_dir / "db_operations.db"
        self.db_fin = self.data_dir / "db_finance.db"
        self.db_audit = self.data_dir / "audit.db"  # historical path; never written here

    def _orders(self):
        return _read(
            self.db_ops,
            "SELECT * FROM sales_orders",
            [
                "order_id",
                "order_status",
                "sales",
                "profit",
                "order_date",
                "customer_country",
            ],
        )

    def _finance(self):
        return _read(
            self.db_fin,
            "SELECT * FROM accounts_receivable",
            [
                "order_id",
                "invoice_amount",
                "payment_status",
            ],
        )

    def _shipping(self):
        return _read(self.db_ops, "SELECT * FROM shipping_logs", ["order_id", "shipping_date"])

    def reconcile_operations_finance(self):
        sources = {"operations": self._orders(), "finance": self._finance()}
        groups = {name: defaultdict(list) for name in sources}
        invalid, excluded = [], []
        blocked = set()
        for source, rows in sources.items():
            for row_number, row in enumerate(rows, 1):
                key = None
                try:
                    key = order_key(row["order_id"])
                    groups[source][key].append(row)
                    field = "sales" if source == "operations" else "invoice_amount"
                    money(row[field])
                    state = str(row["order_status"] if source == "operations" else row["payment_status"]).upper()
                    allowed = ACTIVE | DEFERRED | CANCELLED if source == "operations" else PAYMENTS | CANCELLED
                    if state not in allowed:
                        raise ValueError("unknown or missing status")
                except ValueError as exc:
                    invalid.append({"source": source, "row": row_number, "order_id": key, "reason": str(exc)})
                    if key is not None:
                        blocked.add(key)
        keys = set(groups["operations"]) | set(groups["finance"])
        classifications = []
        for key in sorted(keys):
            ops, fin = groups["operations"][key], groups["finance"][key]
            if len(ops) > 1 or len(fin) > 1:
                classifications.append(
                    {"order_id": key, "status": "duplicate_key", "operations_rows": len(ops), "finance_rows": len(fin)}
                )
                continue
            if key in blocked:
                classifications.append({"order_id": key, "status": "invalid_input"})
                continue
            if ops and str(ops[0]["order_status"]).upper() not in ACTIVE:
                excluded.append({"source": "operations", "order_id": key, "reason": "deferred_or_cancelled_status"})
                ops = []
            if fin and str(fin[0]["payment_status"]).upper() in CANCELLED:
                excluded.append({"source": "finance", "order_id": key, "reason": "cancelled_status"})
                fin = []
            if not ops and not fin:
                continue
            if not ops or not fin:
                classifications.append({"order_id": key, "status": "finance_only" if fin else "operations_only"})
                continue
            expected, booked = money(ops[0]["sales"]), money(fin[0]["invoice_amount"])
            difference = expected - booked
            classifications.append(
                {
                    "order_id": key,
                    "status": "matched" if abs(difference) <= TOLERANCE else "amount_mismatch",
                    "operations_amount": str(expected),
                    "finance_amount": str(booked),
                    "difference": str(difference),
                }
            )
        counts = dict.fromkeys(
            ["matched", "amount_mismatch", "operations_only", "finance_only", "duplicate_key", "invalid_input"], 0
        )
        counts.update(Counter(row["status"] for row in classifications))
        return {
            "input_rows": {name: len(rows) for name, rows in sources.items()},
            "count_unit": "classified nonblank order-id groups; invalid rows and exclusions reported separately",
            "tolerance_currency_units": str(TOLERANCE),
            "counts": counts,
            "classifications": classifications,
            "invalid_rows": invalid,
            "excluded_rows": excluded,
            "coverage_status": "blocked_inputs"
            if invalid or counts["duplicate_key"]
            else "complete_for_declared_status_policy"
            if classifications
            else "no_eligible_records",
        }

    def audit_supply_chain_risks(self):
        orders, shipping = self._orders(), self._shipping()
        shipments = defaultdict(list)
        issues, evaluations = [], []
        for row_number, row in enumerate(shipping, 1):
            try:
                shipments[order_key(row["order_id"])].append(row)
            except ValueError:
                issues.append({"order_id": None, "rule": "invalid_shipping_key", "row": row_number})
        keys = []
        for row in orders:
            try:
                keys.append(order_key(row["order_id"]))
            except ValueError:
                continue  # Invalid keys are reported per row below, never joined as strings.
        duplicates = {key for key, count in Counter(keys).items() if count > 1}
        excluded = 0
        for row in orders:
            key = row.get("order_id")
            try:
                key = order_key(key)
                if key in duplicates:
                    raise ValueError("duplicate_order")
                state = str(row["order_status"]).upper()
                if state in CANCELLED | DEFERRED:
                    excluded += 1
                    continue
                if state not in ACTIVE:
                    raise ValueError("unknown_status")
            except ValueError as exc:
                issues.append({"order_id": key, "rule": "invalid_order", "reason": str(exc)})
                continue
            try:
                profit = money(row["profit"])
                evaluations.append(
                    {
                        "order_id": key,
                        "order_date": row["order_date"],
                        "rule": "negative_margin",
                        "triggered": profit < 0,
                    }
                )
                if profit < 0:
                    issues.append({"order_id": key, "rule": "negative_margin", "profit": str(profit)})
            except ValueError:
                issues.append({"order_id": key, "rule": "invalid_profit"})
            candidates = shipments.get(key, [])
            if len(candidates) != 1:
                issues.append({"order_id": key, "rule": "missing_shipping" if not candidates else "duplicate_shipping"})
                continue
            try:
                delta = (period(candidates[0]["shipping_date"]) - period(row["order_date"])).days
            except (ValueError, TypeError):
                issues.append({"order_id": key, "rule": "invalid_date"})
                continue
            evaluations.append(
                {"order_id": key, "order_date": row["order_date"], "rule": "timing_fraud", "triggered": delta < 0}
            )
            if delta < 0:
                issues.append({"order_id": key, "rule": "shipping_before_order", "days": delta})
        for key in sorted(set(shipments) - set(keys)):
            issues.append({"order_id": key, "rule": "shipping_without_order"})
        return {
            "orders": len(orders),
            "excluded_status_rows": excluded,
            "issues": issues,
            "evaluations": evaluations,
            "counts": dict(Counter(row["rule"] for row in issues)),
            "interpretation": "rule exceptions and data-quality gaps; not confirmed fraud",
        }

    def generate_financial_statements(self):
        rows = self._orders()
        valid_keys = []
        for row in rows:
            try:
                valid_keys.append(order_key(row["order_id"]))
            except ValueError:
                continue
        counts = Counter(valid_keys)
        months = defaultdict(lambda: {"orders": 0, "sales": Decimal(0), "profit": Decimal(0)})
        regions = defaultdict(lambda: {"orders": 0, "sales": Decimal(0), "profit": Decimal(0)})
        excluded = []
        for row in rows:
            try:
                key = order_key(row["order_id"])
                if counts[key] != 1 or str(row["order_status"]).upper() not in ACTIVE:
                    raise ValueError("duplicate_or_ineligible_status")
                month = period(row["order_date"]).isoformat()[:7]
                sales, profit = money(row["sales"]), money(row["profit"])
            except (ValueError, TypeError) as exc:
                excluded.append({"order_id": row["order_id"], "reason": str(exc)})
                continue
            months[month]["orders"] += 1
            months[month]["sales"] += sales
            months[month]["profit"] += profit
            region = str(row["customer_country"] or "").strip() or None
            regions[region]["orders"] += 1
            regions[region]["sales"] += sales
            regions[region]["profit"] += profit
        result = []
        for month, amounts in sorted(months.items()):
            result.append(
                {
                    "month": month,
                    "orders": amounts["orders"],
                    "sales": str(amounts["sales"]),
                    "profit": str(amounts["profit"]),
                    "margin_percent": str(amounts["profit"] / amounts["sales"] * 100) if amounts["sales"] else None,
                }
            )
        regional = [
            {
                "region": region if region is not None else "Unknown / unassigned",
                "missing_dimension": region is None,
                "orders": totals["orders"],
                "sales": str(totals["sales"]),
                "profit": str(totals["profit"]),
            }
            for region, totals in sorted(regions.items(), key=lambda item: item[0] or "")
        ]
        return {
            "monthly": result,
            "regional": regional,
            "excluded_rows": excluded,
            "interpretation": "eligible-order sales/profit summary, not audited financial statements; zero-revenue margin is undefined",
        }

    def run_full_audit(self):
        return {
            "reconciliation": self.reconcile_operations_finance(),
            "supply_chain": self.audit_supply_chain_risks(),
            "financial_summary": self.generate_financial_statements(),
        }
