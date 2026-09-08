# Financial Control Tower

An offline educational Python project for table comparison, SQLite reconciliation, exception reporting and explicitly labelled rule evaluation. It demonstrates controls on invented examples; it is not a live ERP integration, fraud detector or production audit system.

## Run the complete offline example

**Have two actual tables to review?** The separate [`fct-compare` command](docs/table-comparison.md) accepts explicitly mapped CSV or value-only Excel files and produces a local HTML report, row-level CSV, exact JSON and source/file hashes. Composite keys, currency checks and tolerances are explicit; duplicate keys and invalid inputs remain blocked. This is a narrow technical comparison, not accounting or model-validation approval.

Python 3.9+. The default SQLite and CSV runtime uses only the Python standard library. Excel input requires the optional `excel` extra. Installation/build tools may need the internet; the audit and table comparison make no network requests.

```bash
python -m pip install .
fct --sample --output /tmp/fct-example-new
```

Use a **new or empty** destination each time. The command creates fresh sample databases, `audit.db` and `audit_report.json` under that destination. It never replaces the repository's existing CSVs, databases or historical artifacts. A successful exit means execution completed; the report deliberately contains exceptions and blocked inputs.

From a checkout, `python main.py --sample --output /tmp/fct-example-new` uses the same engine. `quick_demo.py`, `fraud_rule_metrics.py` and `scripts/run_financial_audit.py` also route to the maintained CLI. Without `--output`, a unique directory under `artifacts/offline-*` is selected. See [quickstart](docs/quickstart.md).

## What is implemented

| Component | Current scope |
| --- | --- |
| Two-table comparison | `fct-compare` maps CSV/value-only Excel keys and numeric fields, blocks duplicate/invalid keys and currency disagreement, and publishes static HTML, CSV, exact JSON and a manifest |
| Reconciliation | Both-side missing records, exact-decimal amount comparison, duplicate-key groups, invalid inputs and status exclusions |
| Supply-chain rules | Shipping-before-order and negative-profit exceptions; missing/duplicate shipments and invalid dates remain visible |
| Operating summary | Eligible-order monthly and regional sales/profit aggregates; zero-revenue margin is undefined |
| Rule metrics | TP/FP/TN/FN and ratios only with explicit labels and source; unlabelled inputs report counts, with scores set to null |
| Packaging | Installable `financial_control_tower` wheel and `fct` entry point; CLI tests run outside the checkout |
| Evidence | Fresh JSON classifications, source-database hashes and ordinary mutable SQLite records |

The complete invented fixture has eight operations rows and six receivable rows. Its seven classified ID groups are: **2 matched, 1 amount mismatch, 1 operations-only, 1 finance-only, 1 duplicate key, 1 invalid input**. One pending operations row is explicitly excluded. Invalid rows and duplicate groups block any claim of complete valid-input coverage; they are not silently dropped or deduplicated.

## Input contract and interpretation

`fct --data-dir /path/to/inputs --output /path/to/new-output` reads the documented [SQLite schema and policies](docs/SCHEMA.md) in read-only mode. Supply stable checkpointed database copies: nonempty WAL/rollback journals and hardlinked inputs are rejected and before/after input fingerprints must agree. The tool never checkpoints live sources. Each order ID is expected once on each side. Amounts must be finite decimal values in a single agreed currency; no FX conversion or financial-statement recognition policy is inferred. The tolerance is explicitly inclusive at 0.01 currency units.

The synthetic rule labels are separately declared toy outcomes, including disagreement with the rule. They are not real fraud confirmations. Without supplied labels, precision/recall/confusion counts are null. Missing dates, records and invalid values remain data-quality gaps rather than evidence that a check passed.

## Verify

```bash
python -m pip install '.[dev,excel]'
python -m pytest
bash scripts/verify.sh
python -m build --wheel
```

The verification script propagates failures, uses a fresh temporary sample destination, does not install dependencies, and never deletes existing outputs. Its tools must already be installed. CI runs the `lint`, `test`, `e2e`, `verify` and `gitleaks` checks; a workflow definition or local test result is not proof of a successful remote run. [Current Actions results](https://github.com/zheyuliu328/financial-control-tower/actions) are the remote evidence.

## Retained boundaries

- Logs are ordinary, mutable SQLite records. No hash chain, signature, immutable store, RBAC or tested tamper prevention is implemented.
- SAP/Oracle connectivity and enterprise security documents remain proposals. They are not runtime capabilities.
- Two constructed ledgers are not independent evidence from two corporate systems. No real-world fraud accuracy, regulatory compliance or production suitability is established.
- Existing optional DataCo/Kaggle download scripts remain outside the offline runtime. Their different dataset handles, release versions and usage terms still require reconciliation before a reproducible external-data claim. The MIT code license does not establish third-party data rights.
- The historical single-CSV check is still available with `pip install '.[legacy]'`, then `python scripts/run_real.py data/sample_erp.csv --output /tmp/new-csv-example`. It is a single-file exception check, not two-system reconciliation.

[Status and repair evidence](docs/PORTFOLIO_STATUS.md) · [Input schema](docs/SCHEMA.md) · [Limitations](docs/limitations.md) · [Independent model-validation lab](https://github.com/zheyuliu328/model-risk-lab)

The current runtime and tests were revised with AI assistance. Older architecture/completion pages are retained as historical material; this README and the status record define current scope.
