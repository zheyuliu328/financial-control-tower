"""E2E tests for run-real path"""

import glob
import subprocess


def test_run_real():
    """Test run-real path"""
    result = subprocess.run(
        ["python", "scripts/run_real.py", "data/sample_erp.csv", "--output", "artifacts"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"run-real failed: {result.stderr}"

    # Check output files exist
    report_files = glob.glob("artifacts/reconciliation_report_*.json")
    assert len(report_files) > 0, "No report file generated"
