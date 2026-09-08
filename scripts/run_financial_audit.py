"""Run the documented audit CLI; unsupported legacy monthly-close flags fail clearly."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from financial_control_tower.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
