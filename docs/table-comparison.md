# Compare two tables locally

`fct-compare` helps an analyst review two CSV or Excel extracts using explicit keys and numeric column mappings. It produces a static HTML report, row-level CSV, exact JSON and a source/file manifest. No upload, server, network call, model fitting or accounting interpretation is involved.

Prefer a graphical workflow? [`fct-ui`](table-ui.zh-CN.md) uses the same comparator behind a loopback-only browser application. Its ZIP adds the exact selected input snapshots and portable settings. The CLI described below remains server-free.

## Install

From this repository, with Python 3.9+:

```bash
python -m pip install .            # CSV uses only the standard library
python -m pip install '.[excel]'   # Optional: read .xlsx with openpyxl and defusedxml
```

Run from any directory after installation. Installation can access a package index; comparison itself stays offline.

## First useful comparison

Suppose `positions.csv` contains:

```csv
account_id,trade_id,ccy,pv
001,F01,USD,100.00
001,F02,HKD,250.00
002,F03,USD,30.00
```

And `review.csv` contains:

```csv
account,ticket,currency,market_value
001,F01,USD,100.01
001,F02,USD,250.00
003,F04,USD,45.00
```

Run:

```bash
fct-compare \
  --left positions.csv --right review.csv \
  --left-key account_id --left-key trade_id \
  --right-key account --right-key ticket \
  --left-value pv --right-value market_value \
  --left-currency ccy --right-currency currency \
  --absolute-tolerance 0.01 --relative-tolerance 0 \
  --output /tmp/positions-review-new
```

Open `/tmp/positions-review-new/report.html` in a browser. The first pair agrees at the inclusive one-cent tolerance. The second is blocked because HKD differs from USD; no amount difference is calculated. F03 and F04 remain visible as left-only and right-only rows. This example deliberately exits **1** because exceptions require review.

Repeat `--left-value` / `--right-value` to compare additional numeric fields. Repeated keys and values map **in the order supplied**, and both sides must have equal numbers of key/value columns. Tolerances apply to all mapped numeric fields, so choose fields with the same unit and tolerance policy.

## Excel sheets and header rows

```bash
fct-compare \
  --left positions.xlsx --left-sheet Positions --left-header-row 3 \
  --right review.xlsx --right-sheet Review --right-header-row 2 \
  --left-key trade_id --right-key ticket \
  --left-value pv --right-value market_value \
  --common-unit USD --absolute-tolerance 0.01 \
  --output /tmp/excel-review-new
```

Header rows are one-based. Select a sheet explicitly when a workbook has multiple sheets. CSV headers default to row 1 and also support a specified header record. CSV source row numbers count parsed records, including the header and blank records; a quoted multiline field is one record. Excel row numbers are worksheet rows.

Excel key cells must be **stored as text**. A numeric cell formatted as `0000` is blocked because converting its stored value to text would lose the displayed leading zeros. Text keys such as `0007` stay unchanged. Do not use this tool to infer the meaning of formatting. Numeric amount cells use their underlying values; percentage display formats do not multiply values by 100.

Selected Excel formula cells are blocked, including formulas with saved caches. A cache cannot prove that the value matches current inputs. Provide a separate values-only extract that you have independently checked. The tool never recalculates formulas, follows external links or saves the source workbook. Formulas in unmapped columns do not enter the comparison.

## Matching and counting rules

- Keys are exact, case-sensitive text tuples. Leading zeros, surrounding spaces and punctuation are preserved; no trimming, numeric conversion, fuzzy matching, grouping or deduplication occurs. Empty or whitespace-only keys are blocked.
- A key occurring more than once on either side blocks **every member of that group**, including a unique counterpart. Rows are not paired arbitrarily, summed or removed.
- Invalid selected values block the source row. Missing values, booleans, non-finite numbers, grouping separators and currency symbols are not treated as zero. Decimal/scientific notation is supported, within 50 significant digits and adjusted exponents from -100 through 100.
- Currency columns are optional but must be specified on both sides. Missing/nontext currency is blocked. Different currency text blocks subtraction; no FX conversion or normalization occurs. If no currency columns are supplied, `--common-unit` is a required **caller declaration** that all selected amounts share the stated unit; the tool cannot verify that assertion.
- Difference is `right − left`. A field matches when `abs(difference) <= max(absolute_tolerance, relative_tolerance * max(abs(left), abs(right)))`. Relative tolerance is a fraction: `0.01` means 1%. Both tolerances must be nonnegative; defaults are zero.
- Duplicate or empty headers, missing mapped columns, ragged CSV rows, absent sheets and empty data tables stop execution without publishing a report. Fully blank rows are excluded with their source row numbers recorded in the JSON; nonempty rows are all retained.
- Summary counts are **field checks**, not trades, monetary totals or unique entities. A valid unique pair creates one result per mapped numeric field. Each blocked duplicate/unpaired source row creates one result per field. Separate source-row accounting verifies that every nonempty left and right row appears.

## Output and exit codes

The destination must not exist, even as an empty directory or dangling symlink. Output is built in a temporary sibling directory and atomically published only when all files are complete and both source fingerprints still match. A concurrently created destination is preserved. Atomic publication supports macOS, Windows and Linux with `renameat2`; unsupported platforms fail instead of falling back to an overwrite-prone rename.

| File | Purpose |
| --- | --- |
| `report.html` | Human-readable summary and every field result, with original source row references; static, no scripts or remote assets |
| `differences.csv` | Machine-readable field results, including matched, blocked and unmatched entries |
| `comparison.json` | Exact original selected text, mappings, policy, detailed results, input row counts and ignored blank-row numbers |
| `manifest.json` | SHA-256 source snapshots, generated-file hashes, source-code hashes, mappings, summary and policy |

HTML text is escaped. Formula-like CSV text and control characters are prefixed with an apostrophe; the exact unmodified text remains in `comparison.json`. Generated numeric differences remain numeric decimal strings. CSV key tuples are represented as JSON arrays, preserving leading zeros; when importing individual source-text columns into a spreadsheet, select text types. Hashes detect changes, but do not establish source authenticity, separate origins, correct business meaning or tamper resistance.

| Exit | Meaning |
| --- | --- |
| `0` | Report published; all compared fields matched |
| `1` | Report published with differences, unmatched rows or blocked inputs |
| `2` | Configuration, input structure, file access or output publication failed; no new report published |

Use stable source copies, not files another process is actively saving. Inputs are opened read-only, fingerprinted before/after the run and never overwritten. Local reports contain the selected source values and absolute source paths: keep them within the same appropriate sharing boundary as the inputs.

## Scope and verification

This deliberately small workflow supports UTF-8 comma-separated CSV and `.xlsx`, at most 25 MiB per input, 100,000 data rows and 200 columns. For a readable local report, `(left data rows + right data rows) × mapped numeric fields` must also be at most 20,000 before pairing; reduce the extract or the selected fields for larger reviews. Excel archives are additionally limited to 2,048 ZIP members, 25 MiB per expanded member and 100 MiB expanded in total. It does not handle `.xls`, `.xlsm`, merged/multilevel headers, locale-specific number formats, row aggregation, partial invoices, unit conversion or formula freshness certification.

Run the new checks together with the existing audit tests:

```bash
python -m pip install '.[dev,excel]'
python -m pytest
```

The invented tests cover differently named/composite mappings, decimal tolerance boundaries, leading-zero identifiers, source-row coverage, duplicate/missing keys, invalid values, currency disagreement, Excel sheet/header selection, cached-formula rejection, file preservation, concurrent output creation, interrupted publication, HTML/CSV escaping and installed CLI execution. They test software behavior; they do not validate user data, accounting treatment or a financial model.
