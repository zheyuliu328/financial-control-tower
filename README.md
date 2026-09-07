# Financial Control Tower

An educational Python/SQLite project for financial-data reconciliation and exception reporting. It demonstrates data-control techniques with small examples and optional public supply-chain data; it is not a live ERP integration or production audit system.

## What is implemented

| Component | Scope |
| --- | --- |
| [Offline quick demo](quick_demo.py) | Loads two bundled sample CSVs into SQLite, compares amounts for matching order IDs, and writes a JSON summary plus ordinary audit records. |
| [CSV checks](scripts/run_real.py) | Checks required columns and flags negative amounts or missing account codes in a single CSV. This is not a reconciliation between two independent systems. |
| [Core audit prototype](src/audit/financial_control_tower.py) | Operations-to-receivables left-join checks, amount differences, shipping-date/negative-profit rules and summary queries, using the fuller database schema. |
| [Integration/security designs](erp_integration_design.md) | Architecture proposals. SAP/Oracle connectors, access controls and tamper-resistant logging are not verified runtime capabilities. |

## Offline examples

Run from a fresh demo checkout with Python 3.9+ and pandas already installed. These examples make no network requests.

```bash
# Four toy transactions; produces a JSON exception report.
python scripts/run_real.py data/sample_erp.csv --output artifacts/csv_demo

# Eight toy orders; creates/replaces local demo tables and writes a summary.
python quick_demo.py
```

`quick_demo.py` writes to `data/db_operations.db`, `data/db_finance.db`, `data/audit.db` and `artifacts/quickstart_report.json`. Use a separate demo copy if those paths contain work you need to preserve.

In the 2026-09-07 isolated smoke test, CSV checks flagged two exceptions in four rows. The quick demo reported eight amount matches and zero mismatches. These small fixtures establish that those paths run; they do not establish detection accuracy, full reconciliation coverage or real-world audit effectiveness.

## Current limits

- Audit records are ordinary mutable SQLite rows. No runtime hash chain, signature, immutable store or tested update/delete prevention was found. SHA-256 and trigger examples in the security document are design material.
- The quick demo compares matched IDs. It does not report all unmatched records from both sides or validate duplicate-key/cardinality rules.
- `main.py --sample` does not currently create the schema required by the full engine. The audit observed a missing `accounts_receivable` table, followed by an error message with exit code 0.
- The separate rule-metrics module needs repair and uses heuristic labels, not independently confirmed fraud outcomes. TP/FP/FN claims are not established performance evidence.
- `scripts/setup_project.py` may install a package and download data. It is an optional online preparation path, not the offline quickstart.
- Packaging and automated acceptance checks require follow-up. See [Portfolio status](docs/PORTFOLIO_STATUS.md) for the evidence and next gates.

## Data sources

The bundled CSVs are small illustrative inputs. The optional full-data setup names the public DataCo supply-chain dataset on Kaggle. Two download scripts currently name different Kaggle dataset handles, so the chosen source and version must be reconciled before claiming a reproducible full-data run.

No external dataset was downloaded or verified in the offline smoke test. Document publisher, dataset version, retrieval date, transformations and usage terms separately; the repository's code license does not establish third-party data rights. The simulated finance records are not an independent company's accounting ledger.

## Next acceptance milestones

1. Make the offline sample schema compatible with the complete audit engine, with explicit nonzero failure exits.
2. Add fixtures with missing orders on both sides, duplicate IDs, amount differences and invalid values; assert expected classifications.
3. Repair the rule-metrics module and separate synthetic/heuristic labels from confirmed outcomes.
4. Test any future logging-integrity mechanism against a stated threat model before making security guarantees.

## Navigation

- [Portfolio status and audit evidence](docs/PORTFOLIO_STATUS.md)
- [Core source](src/audit/financial_control_tower.py)
- [CSV input format](docs/real-data.md)
- [Project limitations](docs/limitations.md)
- [Security design, not implemented guarantees](security_architecture.md)
- [ERP integration design](erp_integration_design.md)
- [MIT code license](LICENSE)
- [Separate fully synthetic model-validation lab](https://github.com/zheyuliu328/model-risk-lab)

Start with this page and the status record. Older quickstart and architecture pages may describe intended behavior that has not passed the current acceptance checks.
