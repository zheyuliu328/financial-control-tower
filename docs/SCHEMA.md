# Offline input and result contract

The CLI reads `db_operations.db` and `db_finance.db` under `--data-dir`, using SQLite read-only immutable connections to stable checkpointed copies. Nonempty WAL and rollback-journal files are checked beside both the requested path and its resolved target and are rejected; multi-hardlink inputs are rejected because sidecar identity is ambiguous; the tool never checkpoints or modifies source databases. Input SHA-256 and file identity are checked before and after the audit; changes abort report publication. This requires an owner-provided stable snapshot, not a live database. It writes only into a new/empty `--output`. No input `audit.db` is required. A missing file/table/column is an execution error and produces a nonzero exit code.

| Database/table | Required columns |
| --- | --- |
| operations / `sales_orders` | `order_id`, `order_status`, `sales`, `profit`, `order_date`, `customer_country` |
| operations / `shipping_logs` | `order_id`, `shipping_date` |
| finance / `accounts_receivable` | `order_id`, `invoice_amount`, `payment_status` |

## Data rules

SQLite's immutable option skips file locking and change detection, so it cannot turn a live
database into a stable snapshot. The input restrictions above are part of this offline contract;
see the [SQLite URI documentation](https://www.sqlite.org/uri.html#uriimmutable).

- IDs are nonblank, converted to strings and stripped of outer whitespace. Multiple rows sharing an ID are flagged as duplicates; they are never silently reduced to the first row or multiplied through a join. This demonstrator assumes one order and one receivable per ID; multiple invoices require an explicit aggregation/key design before use.
- `sales`, `profit` and `invoice_amount` use finite decimal values. Null, NaN, infinity, booleans and malformed numbers are invalid. Negative amounts may represent credits; they are not automatically fraud. The inputs must already use one currency and consistent units.
- An amount matches when `abs(operations_amount - finance_amount) <= Decimal("0.01")`. Values are not rounded to conceal a difference. The tolerance is a documented demonstration choice, not an accounting standard.
- Eligible operations statuses: COMPLETE, COMPLETED, CLOSED, SHIPPED. PENDING, PROCESSING, PENDING_PAYMENT and ON_HOLD are deferred; CANCELED, CANCELLED and SUSPECTED_FRAUD are excluded. Receivable statuses PAID, UNPAID, PENDING, OPEN, OVERDUE and PARTIAL are eligible; cancelled/suspected states are excluded. Status comparison ignores case; unknown/null states are invalid. Exclusions are reported separately.
- Dates are ISO `YYYY-MM-DD` calendar dates. Invalid dates and missing/duplicate shipping records are explicit gaps. Negative profit is tested independently of shipping availability.
- Monthly/regional summaries use unique eligible orders with valid dates and amounts. They summarize supplied sales/profit fields, not audited net income. Zero-revenue margin is null. Missing region labels have an explicit Unknown / unassigned bucket with order counts, sales and profit, so regional totals reconcile to the monthly population.

## Counts and labels

The reconciliation summary counts **classified nonblank order-ID groups**, not source rows or fields. Raw operations/finance row counts, invalid source rows and status exclusions accompany the group classifications. A group can have a duplicate disposition and also have invalid-row details. These are different counting units and should not be added together as a single denominator.

Rule evaluation counts only evaluable orders for that rule; the supply-chain section retains the gaps that prevented other evaluations. Explicit labels must cover exactly those evaluated IDs and identify their source. No labels means no confusion matrix or performance ratios. A zero denominator is undefined (`null`), not a zero error rate. Declared toy labels are not independently confirmed real fraud.

The bundled example is generated from constants in `sample.py`; it does not read, anonymize or perturb existing repository datasets. `sample_labels()` declares toy outcomes separately from rule calculations and includes deliberate false positives and false negatives.

## Outputs

`audit_report.json` contains classifications, exception evidence, summaries, label provenance and source-file hashes. `audit.db` records the current run's ordinary mutable exception records. File hashes identify input bytes; they do not certify ownership, correct accounting or authenticity. Execution success and business approval are separate.
