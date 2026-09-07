# Portfolio status: Financial Control Tower

Audit baseline: 2026-09-07. This record separates runnable demonstrations, source-level functionality and proposed controls. It does not certify audit effectiveness, security or regulatory compliance.

## Scope and observed runs

The review read the public repository's code, tests and documentation. Sample runs used a separate temporary copy; the source checkout and its databases were not modified by those runs. No downloads, dependency installation, external ERP connection or destructive verification script was used.

| Entry point | Observed result | What it establishes |
| --- | --- | --- |
| `python quick_demo.py` | Exit 0; eight sample orders matched by amount, zero mismatches, SQLite records and JSON summary produced | A tiny matched-record demonstration runs. It does not establish comprehensive reconciliation or fraud detection. |
| `python scripts/run_real.py data/sample_erp.csv --output <new-directory>` | Exit 0; four rows and two exceptions | Required-column checks, a negative-amount flag and a missing-account-code flag work on the fixture. |
| `python main.py --sample` | Reports `no such table: accounts_receivable` but exits 0 | The sample initializer and the full engine have incompatible schemas; exit status also masks the failure. |
| SQLite log probe in the temporary demo | No triggers; one row could be updated inside a transaction, which was rolled back | The observed log is mutable. No immutability or tamper-evidence guarantee was demonstrated. |

The source audit and smoke tests do not establish correctness on a full external DataCo dataset or a real ERP export. The full dataset preparation path was not run.

## Functional boundaries and repair criteria

| Topic | Source evidence | Accurate interpretation / acceptance criterion |
| --- | --- | --- |
| Quick-demo matching | [`quick_demo.py`](../quick_demo.py) iterates finance rows and selects the first matching operations row | Basic amount comparison for matched IDs. Add missing-on-each-side and duplicate-key fixtures; verify counts, coverage and denominators before claiming complete reconciliation. |
| Full-engine reconciliation | [`financial_control_tower.py`](../src/audit/financial_control_tower.py) uses an operations-led left merge | Supports operations missing from receivables and matched-key amount differences. It is not a full outer join; finance-only records and join cardinality need explicit handling. The printed matched count includes key matches with amount differences. |
| Offline sample schema | [`main.py`](../main.py) creates `order_revenue`; the engine queries `accounts_receivable` and later needs shipping/order detail columns | Supply one documented schema for sample initialization and runtime. A full isolated sample run must finish and produce asserted findings. |
| Failure status | [`main.py`](../main.py) catches exceptions and prints them without failing the process | Return a nonzero exit code when the audit cannot execute. Tests must check both result artifacts and exit status. |
| Single-file checks | [`scripts/run_real.py`](../scripts/run_real.py) reads one CSV and checks negative amounts/missing account codes | Describe as CSV exception checks. A negative amount can be a valid refund, not proven fraud. |
| Rule metrics | [`fraud_rule_metrics.py`](../fraud_rule_metrics.py) applies Python `not` to pandas Series, has a malformed default negative-margin query, and derives labels from its own heuristics | Repair the boolean/SQL logic and test nonempty fixtures. Report heuristic-label agreement separately from performance against independently labelled fraud. |
| Runtime logs | [`quick_demo.py`](../quick_demo.py), [`create_audit_db`](../src/data_engineering/init_erp_databases.py) and the core log writer create/append ordinary SQLite rows | Describe exception records and traceability only. There is no implemented hash/signature field, hash chain or deployed update/delete trigger in these paths. |
| Security design | [`security_architecture.md`](../security_architecture.md) contains suggested triggers, hash calculations and role controls | These are design examples, not installed runtime controls. Even a future hash chain should be described according to a tested threat model, not as absolute immutability. |
| ERP integration | [`erp_integration_design.md`](../erp_integration_design.md) is architecture documentation; the depicted `src/integration` package is absent | Do not claim SAP/Oracle connectivity. Acceptance needs an implemented connector contract and reproducible integration tests. |
| Packaging | [`pyproject.toml`](../pyproject.toml) points its wheel and `fct` command at a missing `src/financial_control_tower` package | File-based examples are the current known entry points. Fix package layout and verify installation in a clean environment before documenting an installed CLI. |
| Test confidence | [`test_basic.py`](../tests/test_basic.py) only asserts true; [`test_e2e.py`](../tests/test_e2e.py) accepts an existing report; Makefile checks can hide failure | Use fresh temporary output directories and substantive expected-result assertions. Propagate failures. |

The audit did not run `scripts/verify.sh`: it deletes existing output-directory contents and treats some failures as optional. Its aggregate success message is not accepted as evidence for the claims above.

## Data provenance

| Route | Repository evidence | What still needs to be stated or verified |
| --- | --- | --- |
| Eight-order sample | [`operations_sample.csv`](../data/sample/operations_sample.csv) and [`finance_sample.csv`](../data/sample/finance_sample.csv) | Toy matching fixtures. Add deliberately anomalous records and expected findings; document the sample construction. |
| Four-transaction CSV | [`sample_erp.csv`](../data/sample_erp.csv) | Illustrates negative amounts and missing account codes; not a labelled fraud benchmark. |
| Full setup | [`setup_project.py`](../scripts/setup_project.py) names `shashwatwork/dataco-smart-supply-chain-for-big-data-analysis` on Kaggle | This may use a cached download or contact Kaggle, and may install `kagglehub`. External provenance and terms were not verified in the offline audit. |
| Alternative downloader | [`download_data.py`](../scripts/download_data.py) names `rohanrao/data-co-supply-chain-dataset` | Reconcile this different handle with the setup route. Record the chosen version and input-file checksum instead of assuming the two sources are interchangeable. |
| Simulated ledgers | [`init_erp_databases.py`](../src/data_engineering/init_erp_databases.py) derives operations and finance tables from the source data | Two generated databases are not independent evidence from two live corporate systems. |

Add the source URL, original publisher, dataset release/version, retrieval date, license/terms, transformations, field mapping and checksum to any future full-data reproduction. The code's MIT license does not establish rights to redistribute external datasets. No new conclusion about external data licensing was reached in this audit.

## Evidence needed before stronger claims

- A complete offline audit on a compatible sample schema, with current-run outputs and nonzero failure exits.
- Explicit tests for missing records in either direction, duplicate IDs, amount mismatches, rounding policy, cancelled/pending states and invalid input.
- Repaired rule metrics, with labels clearly distinguished from the rules being evaluated.
- Implemented and tested logging controls, including what an actor with database-file access can still change.
- Verified package installation and CLI behavior in a clean supported environment.
- A provenance manifest for each optional external dataset and a separate evaluation report for any real-data claim.

These are future acceptance criteria, not completed work. The separate [model-risk-lab](https://github.com/zheyuliu328/model-risk-lab) is a fully synthetic model-validation portfolio direction; it makes no claim about this audit system's maturity.
