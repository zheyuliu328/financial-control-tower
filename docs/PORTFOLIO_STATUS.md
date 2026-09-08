# Portfolio status: Financial Control Tower

Updated 2026-09-08. The current scope is a complete offline educational audit workflow on explicit synthetic fixtures and a documented SQLite schema. This is not production, regulatory or real-fraud certification.

## Implemented repair

| Prior observed defect | Current implementation and verification requirement |
| --- | --- |
| Wheel/CLI referenced a missing package | Maintained `src/financial_control_tower` package; build a wheel, install it normally, and run the CLI outside the checkout |
| `main --sample` created incompatible tables and swallowed errors | One fixture generator supplies the complete schema; all entries use the CLI; missing-input and overwrite attempts must exit nonzero |
| Left join hid finance-only records and inflated matches | Explicit union of both sides; independent expected group classifications; duplicates and malformed input remain blocked |
| Inner shipping join could hide negative profits | Profit evaluation is independent; missing/duplicate shipment and invalid-date issues remain visible |
| Metrics used Series `not`, malformed SQL and circular heuristic labels | Boolean confusion matrices on explicit labels with source; unlabelled scores and undefined ratios are null; synthetic tests contain TP/FP/TN/FN |
| Tests only asserted true or accepted stale reports | Fresh isolated fixtures, exact classifications, read-only input hashes, installed CLI and failure-path assertions |
| Make/verify could mask failures or delete output | Failure propagation and unique temporary output; no deletion, automatic installation or network request in the local verification script |
| New Ruff formatted historical Markdown examples; required context names differed | Pinned Ruff checks all maintained Python paths; jobs use actual `lint`, `test`, `e2e`, `verify`, `gitleaks` names without changing branch protection |

## Evidence and current-run gates

The repair uses a temporary build/test environment and retains source CSVs, databases and existing artifacts unchanged. Unit tests compare the toy classifications with explicit expectations; a normal wheel installation and isolated `fct` execution check packaging. Current-run outputs must be generated into fresh directories.

Remote CI is a separate gate: see [Actions](https://github.com/zheyuliu328/financial-control-tower/actions). Do not infer it passed from this document or a local command. Required contexts include lint, substantive tests, installed-wheel e2e, security verification and Gitleaks. The historical main run at `d1030a33` failed formatting and skipped downstream tests; it does not describe the repaired implementation's eventual CI result.

The earlier SQLite audit-workflow revalidation on 2026-09-08 completed **37 tests**, Ruff/format, Bandit, dependency consistency,
normal wheel installation and a complete installed CLI run outside the checkout. An independent
review added **11 counterexample checks**, including missing-region reconciliation, null/valid ID
separation, strict dates, WAL/journal and linked-file input protection, and 341 label-matrix cases.
The source files are unchanged on those failure paths. The main review repeated the full local
verifier in a separate Python 3.12 environment; the 10 original tracked data/artifact files remained
byte-identical. These local results are separate from the revision-specific remote gates above.

## New table-comparison entry point — 2026-09-08

The separate `fct-compare` CLI accepts two CSV or value-only `.xlsx` tables with explicit composite-key and numeric-column mappings, Excel sheet/header selection, currency columns or a declared common unit, and absolute/relative tolerances. It retains every nonempty source row, blocks duplicate/missing keys, invalid values, formulas and currency disagreement, and publishes a static HTML report, CSV, exact JSON and source/file manifest into a new directory. This is a technical comparison, not accounting approval or financial-model validation. The existing SQLite engine and rule semantics are unchanged. See the [table-comparison guide](table-comparison.md).

The completed local verification now comprises **97 tests: the earlier 37 plus 60 table-comparison tests, with zero skips**, on macOS/Python 3.12.14. Ruff, format checks, Bandit, dependency consistency and the existing installed audit CLI also passed. A normal wheel installation exercised `fct-compare` outside the checkout. Eight damaged-Excel cases confirm exit 2, no published directory and unchanged input hashes, including missing OOXML parts, malformed XML, invalid shared-string references and invalid workbook field types. CI test, compatibility and verification jobs explicitly install `.[dev,excel]`; the separate wheel CSV smoke remains available without Excel dependencies. These are local checks and workflow requirements, not evidence of a future remote run.

The delivered interaction is a CLI. GUI field selection is not implemented, and an observed trial by a second analyst has not yet been performed. The static report has been designed for direct file opening; those remaining usability questions must not be inferred from test counts.

## Boundaries retained

- Ordinary SQLite logs are mutable; the test demonstrates this rather than claiming immutability.
- No SAP/Oracle connector, RBAC, hash chain, signature, encrypted storage or regulatory certification is implemented.
- Label agreement on invented fixtures is not measured real-world fraud detection. Caller-provided labels retain their declared/unverified origin.
- The data model assumes one order and one receivable per ID, one currency, prescribed statuses and ISO dates. Partial invoices, FX conversion, general-ledger accounting policies and production-scale controls require separate design.
- Historical DataCo/Kaggle preparation scripts remain optional. Their source-handle discrepancy, source/version/terms and independent-source limitations are unresolved and outside the offline demo.
- Existing `data/` and historical `artifacts/` files are not acceptance evidence for the new run and are not regenerated by the new sample.

See [schema and counting units](SCHEMA.md), [current quickstart](quickstart.md) and [limitations](limitations.md). Older completion, integration and security pages are historical design notes, not additional implemented capabilities.
