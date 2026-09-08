"""Compare mapped CSV/XLSX tables locally; publish HTML, CSV, exact JSON and a manifest."""

import argparse
import csv
import json
import sys
from pathlib import Path
from zipfile import BadZipFile

from .table_compare import TableSpec, run_comparison


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for side in ("left", "right"):
        parser.add_argument(f"--{side}", type=Path, required=True, help="UTF-8 comma-separated CSV or .xlsx file")
        parser.add_argument(
            f"--{side}-key", action="append", required=True, help="Repeat for a composite key; order maps across sides"
        )
        parser.add_argument(
            f"--{side}-value", action="append", required=True, help="Repeat for numeric fields; order maps across sides"
        )
        parser.add_argument(f"--{side}-sheet", help="Required for multi-sheet Excel; exact worksheet name")
        parser.add_argument(f"--{side}-header-row", type=int, default=1, help="One-based header row (default 1)")
        parser.add_argument(f"--{side}-currency", help="Explicit currency column; must be supplied on both sides")
    parser.add_argument(
        "--absolute-tolerance", "--abs-tol", default="0", help="Nonnegative amount tolerance; inclusive"
    )
    parser.add_argument("--relative-tolerance", "--rel-tol", default="0", help="Nonnegative fraction, e.g. 0.01 = 1%%")
    parser.add_argument("--common-unit", help="Required declaration if no currency columns, e.g. USD or decimal rate")
    parser.add_argument(
        "--output", type=Path, required=True, help="New directory only; existing directories are never replaced"
    )
    args = parser.parse_args(argv)
    specs = []
    for side in ("left", "right"):
        specs.append(
            TableSpec(
                getattr(args, side),
                tuple(getattr(args, f"{side}_key")),
                tuple(getattr(args, f"{side}_value")),
                getattr(args, f"{side}_sheet"),
                getattr(args, f"{side}_header_row"),
                getattr(args, f"{side}_currency"),
            )
        )
    try:
        result = run_comparison(
            *specs,
            args.output,
            absolute_tolerance=args.absolute_tolerance,
            relative_tolerance=args.relative_tolerance,
            common_unit=args.common_unit,
        )
    except (OSError, ValueError, csv.Error, BadZipFile) as exc:
        print(f"Comparison could not execute: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "output": str(args.output.absolute()),
                "execution": "completed",
                **result["summary"],
                "meaning": "technical comparison only; exceptions and blocked inputs require review",
            },
            indent=2,
        )
    )
    return 0 if result["summary"]["all_matched"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
