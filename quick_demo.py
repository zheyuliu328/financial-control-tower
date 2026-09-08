"""Compatibility entry point; outputs now use a fresh directory."""

import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from financial_control_tower.cli import main, run


def run_demo(output=None):
    return run(output or Path("artifacts") / f"demo-{uuid4().hex[:12]}")


if __name__ == "__main__":
    raise SystemExit(main())
