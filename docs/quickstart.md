# Current quickstart

```bash
python -m pip install '.[dev]'
fct --sample --output /tmp/fct-example-new
python -m pytest
bash scripts/verify.sh
```

Use a new or empty output destination. The installed CLI works outside the checkout. The audit runtime is offline and requires no third-party Python packages; optional legacy CSV/download scripts have separate extras.

Open `audit_report.json` in the chosen output directory. The sample deliberately includes differences and invalid data: 2 matched groups, one each of amount mismatch, operations-only, finance-only, duplicate key and invalid input. Do not read an execution exit code of zero as a clean audit opinion.

For caller-supplied input use `fct --data-dir <input-directory> --output <new-directory>` and follow [the schema](SCHEMA.md). Missing tables/columns and inaccessible input files return nonzero. Existing output is refused, not erased. Inputs are never rewritten.

`main.py`, `quick_demo.py`, `fraud_rule_metrics.py` and `scripts/run_financial_audit.py` retain command-line entry points to this same implementation. The formerly advertised monthly-close flags had no implementation and are rejected explicitly; monthly/regional aggregates appear in the complete report.
