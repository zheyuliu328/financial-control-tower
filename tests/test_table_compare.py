"""Invented analyst inputs exercise mappings, blocked rows and published evidence."""

import csv
import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from financial_control_tower import table_compare as comparison
from financial_control_tower.table_cli import main
from financial_control_tower.table_compare import TableSpec, run_comparison

pytestmark = pytest.mark.unit


def csv_input(tmp_path, name, rows):
    path = tmp_path / name
    with path.open("w", newline="", encoding="utf-8") as stream:
        csv.writer(stream).writerows(rows)
    return path


def simple_inputs(tmp_path, left="100", right="100"):
    a = csv_input(tmp_path, "left.csv", [["id", "amount"], ["001", left]])
    b = csv_input(tmp_path, "right.csv", [["id", "amount"], ["001", right]])
    return TableSpec(a, ("id",), ("amount",)), TableSpec(b, ("id",), ("amount",))


def test_composite_mapping_multiple_fields_and_leading_zeros(tmp_path):
    a = csv_input(
        tmp_path, "a.csv", [["acct", "trade", "pv", "fee"], ["001", "01", "10", "2"], ["001", "1", "20", "3"]]
    )
    b = csv_input(
        tmp_path,
        "b.csv",
        [["cost", "ticket", "value", "customer"], ["3", "1", "20", "001"], ["2", "01", "10.01", "001"]],
    )
    result = run_comparison(
        TableSpec(a, ("acct", "trade"), ("pv", "fee")),
        TableSpec(b, ("customer", "ticket"), ("value", "cost")),
        tmp_path / "report",
        common_unit="USD",
    )
    assert result["summary"]["field_checks"] == {"amount_mismatch": 1, "matched": 3}
    assert result["summary"]["accounted_rows"] == {"left": 2, "right": 2}
    assert result["records"][0]["key"] == ["001", "01"]
    assert result["records"][0]["right_row"] == 3
    assert result["records"][0]["difference_right_minus_left"] == "0.01"


@pytest.mark.parametrize(
    "left,right,absolute,relative,status",
    [
        ("100", "100.01", "0.01", "0", "matched"),
        ("100", "100.0101", "0.01", "0", "amount_mismatch"),
        ("100", "101", "0", "0.01", "matched"),
        ("-100", "-101.02", "0", "0.01", "amount_mismatch"),
        ("0", "0", "0", "0", "matched"),
    ],
)
def test_tolerance_rule_and_boundary(tmp_path, left, right, absolute, relative, status):
    a, b = simple_inputs(tmp_path, left, right)
    result = run_comparison(
        a, b, tmp_path / "out", absolute_tolerance=absolute, relative_tolerance=relative, common_unit="USD"
    )
    assert result["records"][0]["status"] == status


def test_exact_long_decimal_difference_is_not_rounded_by_default_context(tmp_path):
    a, b = simple_inputs(tmp_path, "0", "-0.123456789012345678901234567890123456789")
    row = run_comparison(a, b, tmp_path / "out", common_unit="unit")["records"][0]
    assert row["absolute_difference"] == "0.123456789012345678901234567890123456789"
    assert row["difference_right_minus_left"] == "-0.123456789012345678901234567890123456789"


def test_duplicates_invalid_numbers_and_missing_keys_retain_every_row(tmp_path):
    a = csv_input(tmp_path, "a.csv", [["id", "amount"], ["D", "2"], ["D", "3"], ["", "4"], ["N", "nan"], ["L", "5"]])
    b = csv_input(tmp_path, "b.csv", [["id", "amount"], ["D", "5"], ["N", "6"], ["R", "7"]])
    result = run_comparison(
        TableSpec(a, ("id",), ("amount",)), TableSpec(b, ("id",), ("amount",)), tmp_path / "out", common_unit="USD"
    )
    assert result["summary"]["field_checks"] == {
        "duplicate_key": 3,
        "missing_key": 1,
        "invalid_numeric": 1,
        "left_only": 1,
        "right_only": 1,
    }
    assert result["summary"]["input_rows"] == result["summary"]["accounted_rows"] == {"left": 5, "right": 3}
    assert all(row["difference_right_minus_left"] is None for row in result["records"])
    duplicates = [row for row in result["records"] if row["status"] == "duplicate_key"]
    assert [row["left_value"] for row in duplicates] == ["2", "3", None]
    assert duplicates[-1]["right_value"] == "5"


@pytest.mark.parametrize("bad", ["", "nan", "Infinity", "1,000", "1_000", "12 USD", "True", "1e9999999999999999999999"])
def test_invalid_numeric_is_blocked_instead_of_zero_or_success(tmp_path, bad):
    a, b = simple_inputs(tmp_path, bad, "0")
    result = run_comparison(a, b, tmp_path / "out", common_unit="USD")
    assert result["records"][0]["status"] == "invalid_numeric"
    assert result["records"][0]["difference_right_minus_left"] is None


@pytest.mark.parametrize("bad", ["-1", "NaN", "1e9999999999999999999999"])
def test_invalid_tolerance_does_not_publish(tmp_path, bad):
    a, b = simple_inputs(tmp_path)
    with pytest.raises(ValueError):
        run_comparison(a, b, tmp_path / "out", common_unit="USD", absolute_tolerance=bad)
    assert not (tmp_path / "out").exists()


def test_currency_mismatch_blocks_subtraction_and_currency_is_not_implicitly_a_key(tmp_path):
    a = csv_input(
        tmp_path, "a.csv", [["id", "ccy", "amount"], ["A", "USD", "100"], ["D", "USD", "1"], ["D", "HKD", "2"]]
    )
    b = csv_input(tmp_path, "b.csv", [["id", "currency", "amount"], ["A", "HKD", "100"], ["D", "USD", "1"]])
    result = run_comparison(
        TableSpec(a, ("id",), ("amount",), currency="ccy"),
        TableSpec(b, ("id",), ("amount",), currency="currency"),
        tmp_path / "out",
    )
    assert result["summary"]["field_checks"] == {"currency_mismatch": 1, "duplicate_key": 3}
    assert all(row["difference_right_minus_left"] is None for row in result["records"])


def test_unit_declaration_is_required_and_asymmetric_currency_rejected(tmp_path):
    a, b = simple_inputs(tmp_path)
    with pytest.raises(ValueError, match="common-unit"):
        run_comparison(a, b, tmp_path / "out")
    with pytest.raises(ValueError, match="both sides"):
        run_comparison(TableSpec(a.path, a.keys, a.values, currency="id"), b, tmp_path / "out")
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "rows,error",
    [
        ([["id", "amount", "amount"], ["A", "1", "2"]], "duplicate column"),
        ([["id", ""], ["A", "1"]], "header cells"),
        ([["id", "amount"], ["A", "1", "2"]], "different width"),
        ([["id", "amount"]], "no nonempty data"),
        ([["id", "renamed"], ["A", "1"]], "mapped columns absent"),
    ],
)
def test_ambiguous_table_shape_fails_without_report(tmp_path, rows, error):
    a, b = simple_inputs(tmp_path)
    csv_input(tmp_path, a.path.name, rows)
    with pytest.raises(ValueError, match=error):
        run_comparison(a, b, tmp_path / "out", common_unit="USD")
    assert not (tmp_path / "out").exists()


def test_csv_header_row_and_blank_rows_are_recorded_without_trimming_keys(tmp_path):
    a = csv_input(tmp_path, "a.csv", [["notes"], ["id", "amount"], [], [" 001", "1"], ["001", "2"]])
    b = csv_input(tmp_path, "b.csv", [["id", "amount"], ["001", "2"]])
    result = run_comparison(
        TableSpec(a, ("id",), ("amount",), header_row=2),
        TableSpec(b, ("id",), ("amount",)),
        tmp_path / "out",
        common_unit="USD",
    )
    assert result["inputs"]["left"]["blank_rows_ignored"] == [3]
    assert result["summary"]["field_checks"] == {"left_only": 1, "matched": 1}


def test_read_only_inputs_hashes_and_complete_manifest(tmp_path):
    a, b = simple_inputs(tmp_path)
    before = {spec.path: spec.path.read_bytes() for spec in (a, b)}
    for path in before:
        path.chmod(0o444)
    run_comparison(a, b, tmp_path / "out", common_unit="USD")
    assert before == {path: path.read_bytes() for path in before}
    manifest = json.loads((tmp_path / "out/manifest.json").read_text())
    assert set((tmp_path / "out").iterdir()) == {
        tmp_path / "out" / name for name in ("manifest.json", "comparison.json", "report.html", "differences.csv")
    }
    for name, digest in manifest["sha256"].items():
        assert hashlib.sha256((tmp_path / "out" / name).read_bytes()).hexdigest() == digest
    for side, spec in (("left", a), ("right", b)):
        assert manifest["inputs"][side]["sha256"] == hashlib.sha256(before[spec.path]).hexdigest()


@pytest.mark.parametrize("kind", ["empty_directory", "nonempty_directory", "file", "dangling_symlink"])
def test_existing_destination_is_preserved(tmp_path, kind):
    a, b = simple_inputs(tmp_path)
    output = tmp_path / "out"
    if kind.endswith("directory"):
        output.mkdir()
        if kind == "nonempty_directory":
            (output / "keep.txt").write_text("keep")
    elif kind == "file":
        output.write_text("keep")
    else:
        output.symlink_to(tmp_path / "absent", target_is_directory=True)
    with pytest.raises(FileExistsError):
        run_comparison(a, b, output, common_unit="USD")
    if kind == "nonempty_directory":
        assert (output / "keep.txt").read_text() == "keep"
    elif kind == "file":
        assert output.read_text() == "keep"
    elif kind == "dangling_symlink":
        assert output.is_symlink()
    else:
        assert output.is_dir() and not list(output.iterdir())


def test_competing_empty_output_is_not_replaced_at_publication(tmp_path, monkeypatch):
    a, b = simple_inputs(tmp_path)
    original = comparison._write_html

    def competing(path, result):
        original(path, result)
        (tmp_path / "out").mkdir()

    monkeypatch.setattr(comparison, "_write_html", competing)
    with pytest.raises(FileExistsError):
        run_comparison(a, b, tmp_path / "out", common_unit="USD")
    assert not list((tmp_path / "out").iterdir())
    assert not list(tmp_path.glob(".out-*"))


def test_failed_report_generation_publishes_nothing(tmp_path, monkeypatch):
    a, b = simple_inputs(tmp_path)

    def interrupted(path, result):
        path.write_text("partial")
        raise OSError("simulated disk failure")

    monkeypatch.setattr(comparison, "_write_html", interrupted)
    with pytest.raises(OSError, match="disk failure"):
        run_comparison(a, b, tmp_path / "out", common_unit="USD")
    assert not (tmp_path / "out").exists()
    assert not list(tmp_path.glob(".out-*"))


def test_source_change_during_generation_prevents_publication(tmp_path, monkeypatch):
    a, b = simple_inputs(tmp_path)
    original = comparison._write_html

    def changing(path, result):
        original(path, result)
        a.path.write_text("id,amount\n001,999\n")

    monkeypatch.setattr(comparison, "_write_html", changing)
    with pytest.raises(ValueError, match="input changed"):
        run_comparison(a, b, tmp_path / "out", common_unit="USD")
    assert not (tmp_path / "out").exists()


def test_html_escaping_and_csv_formula_text_protection(tmp_path):
    attack = '<script>alert("x")</script>'
    formula = '=HYPERLINK("https://example.invalid","click")'
    a = csv_input(tmp_path, "a.csv", [["id", "=amount"], [attack, formula]])
    b = csv_input(tmp_path, "b.csv", [["id", "amount"], [attack, "1"]])
    result = run_comparison(
        TableSpec(a, ("id",), ("=amount",)), TableSpec(b, ("id",), ("amount",)), tmp_path / "out", common_unit="<USD>"
    )
    rendered = (tmp_path / "out/report.html").read_text()
    assert "<script>" not in rendered and "&lt;script&gt;" in rendered
    assert "&lt;USD&gt;" in rendered and "default-src 'none'" in rendered
    with (tmp_path / "out/differences.csv").open(newline="") as stream:
        row = next(csv.DictReader(stream))
    assert row["left_column"] == "'=amount" and row["left_value"] == "'" + formula
    exact = json.loads((tmp_path / "out/comparison.json").read_text())
    assert exact["records"][0]["left_value"] == formula
    assert result["records"][0]["status"] == "invalid_numeric"


@pytest.mark.parametrize(
    "text", ["=1+1", " +1+1", "-1+1", "@SUM(1)", "\ufeff=1+1", "\x00=1+1", "\tvalue", "line\nnext"]
)
def test_csv_text_escape_covers_dangerous_prefixes_and_control_characters(text):
    assert comparison._csv_text(text) == "'" + text


def make_xlsx(tmp_path, name, *, formula=False, numeric_key=False, extra_sheet=False):
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Positions"
    sheet.append(["Synthetic values only"])
    sheet.append(["trade", "ccy", "pv"])
    sheet.append([7 if numeric_key else "0007", "USD", "=5+5" if formula else 10])
    if numeric_key:
        sheet["A3"].number_format = "0000"
    if extra_sheet:
        workbook.create_sheet("Other")
    path = tmp_path / name
    workbook.save(path)
    workbook.close()
    return path


def test_excel_sheet_header_mapping_and_leading_zero_text(tmp_path):
    a = make_xlsx(tmp_path, "a.xlsx", extra_sheet=True)
    b = csv_input(tmp_path, "b.csv", [["id", "currency", "amount"], ["0007", "USD", "10"]])
    result = run_comparison(
        TableSpec(a, ("trade",), ("pv",), "Positions", 2, "ccy"),
        TableSpec(b, ("id",), ("amount",), currency="currency"),
        tmp_path / "out",
    )
    assert result["summary"]["all_matched"]
    assert result["records"][0]["key"] == ["0007"] and result["records"][0]["left_row"] == 3
    assert result["inputs"]["left"]["sheet"] == "Positions"


def test_excel_formula_with_cache_still_blocks_arithmetic(tmp_path):
    a = make_xlsx(tmp_path, "a.xlsx", formula=True)
    raw = a.read_bytes()
    with ZipFile(io.BytesIO(raw)) as source, ZipFile(a, "w", ZIP_DEFLATED) as target:
        for member in source.infolist():
            value = source.read(member.filename)
            if member.filename == "xl/worksheets/sheet1.xml":
                value = value.replace(b"<f>5+5</f><v></v>", b"<f>5+5</f><v>10</v>")
                value = value.replace(b"<f>5+5</f><v />", b"<f>5+5</f><v>10</v>")
                assert b"<f>5+5</f><v>10</v>" in value
            target.writestr(member, value)
    b = csv_input(tmp_path, "b.csv", [["id", "amount"], ["0007", "10"]])
    result = run_comparison(
        TableSpec(a, ("trade",), ("pv",), header_row=2),
        TableSpec(b, ("id",), ("amount",)),
        tmp_path / "out",
        common_unit="USD",
    )
    assert result["records"][0]["status"] == "formula_cell"
    assert result["records"][0]["difference_right_minus_left"] is None


def test_excel_numeric_zero_padded_keys_are_not_silently_coerced(tmp_path):
    a = make_xlsx(tmp_path, "a.xlsx", numeric_key=True)
    b = csv_input(tmp_path, "b.csv", [["id", "amount"], ["7", "10"]])
    result = run_comparison(
        TableSpec(a, ("trade",), ("pv",), header_row=2),
        TableSpec(b, ("id",), ("amount",)),
        tmp_path / "out",
        common_unit="USD",
    )
    assert result["summary"]["field_checks"] == {"invalid_key": 1, "right_only": 1}
    assert "leading zeros" in " ".join(result["records"][0]["issues"])


def test_excel_multiple_sheets_require_selection(tmp_path):
    a = make_xlsx(tmp_path, "a.xlsx", extra_sheet=True)
    _unused, b = simple_inputs(tmp_path)
    with pytest.raises(ValueError, match="explicit sheet"):
        run_comparison(TableSpec(a, ("trade",), ("pv",), header_row=2), b, tmp_path / "out", common_unit="USD")


@pytest.mark.parametrize(
    "defect",
    [
        "missing_content_types",
        "missing_workbook",
        "missing_workbook_relationships",
        "malformed_content_types",
        "malformed_workbook",
        "malformed_worksheet",
        "invalid_shared_string_index",
        "invalid_sheet_id",
    ],
)
def test_installed_cli_reports_broken_excel_as_input_error_without_mutation(tmp_path, defect):
    path = make_xlsx(tmp_path, "broken.xlsx")
    raw = path.read_bytes()
    missing = {
        "missing_content_types": "[Content_Types].xml",
        "missing_workbook": "xl/workbook.xml",
        "missing_workbook_relationships": "xl/_rels/workbook.xml.rels",
    }
    malformed = {
        "malformed_content_types": "[Content_Types].xml",
        "malformed_workbook": "xl/workbook.xml",
        "malformed_worksheet": "xl/worksheets/sheet1.xml",
    }
    with ZipFile(io.BytesIO(raw)) as source, ZipFile(path, "w", ZIP_DEFLATED) as target:
        for member in source.infolist():
            if member.filename == missing.get(defect):
                continue
            value = source.read(member.filename)
            if member.filename == malformed.get(defect):
                value = b"<broken><not-closed>"
            elif defect == "invalid_shared_string_index" and member.filename == "xl/worksheets/sheet1.xml":
                value = value.replace(b't="n"', b't="s"')
            elif defect == "invalid_sheet_id" and member.filename == "xl/workbook.xml":
                value = value.replace(b'sheetId="1"', b'sheetId="not-an-integer"')
            target.writestr(member, value)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    right = csv_input(tmp_path, "right.csv", [["id", "amount"], ["0007", "10"]])
    right_before = hashlib.sha256(right.read_bytes()).hexdigest()
    executable = Path(sys.executable).parent / ("fct-compare.exe" if sys.platform == "win32" else "fct-compare")
    process = subprocess.run(
        [
            str(executable),
            "--left",
            str(path),
            "--left-sheet",
            "Positions",
            "--left-header-row",
            "2",
            "--right",
            str(right),
            "--left-key",
            "trade",
            "--right-key",
            "id",
            "--left-value",
            "pv",
            "--right-value",
            "amount",
            "--common-unit",
            "USD",
            "--output",
            str(tmp_path / "out"),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert process.returncode == 2, process.stderr
    assert "invalid Excel workbook structure" in process.stderr
    assert "Traceback" not in process.stderr
    assert not process.stdout
    assert not (tmp_path / "out").exists() and not list(tmp_path.glob(".out-*"))
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    assert hashlib.sha256(right.read_bytes()).hexdigest() == right_before


def test_expanded_excel_archive_limit_precedes_workbook_loading(tmp_path):
    a = tmp_path / "oversized.xlsx"
    with ZipFile(a, "w", ZIP_DEFLATED) as archive:
        archive.writestr("oversized.xml", b"x" * (25 * 1024 * 1024 + 1))
    _unused, b = simple_inputs(tmp_path)
    with pytest.raises(ValueError, match="Excel archive exceeds"):
        run_comparison(TableSpec(a, ("id",), ("amount",)), b, tmp_path / "out", common_unit="USD")


def test_potential_output_limit_precedes_record_construction(tmp_path, monkeypatch):
    a, b = simple_inputs(tmp_path)
    monkeypatch.setattr(comparison, "MAX_FIELD_CHECKS", 1)
    with pytest.raises(ValueError, match="potential row-field"):
        run_comparison(a, b, tmp_path / "out", common_unit="USD")
    assert not (tmp_path / "out").exists()


def test_cli_exit_codes_distinguish_agreement_exceptions_and_configuration_error(tmp_path, capsys):
    a, b = simple_inputs(tmp_path)
    args = [
        "--left",
        str(a.path),
        "--right",
        str(b.path),
        "--left-key",
        "id",
        "--right-key",
        "id",
        "--left-value",
        "amount",
        "--right-value",
        "amount",
        "--common-unit",
        "USD",
        "--output",
        str(tmp_path / "out"),
    ]
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)["all_matched"]
    assert main(args) == 2
    assert "already exists" in capsys.readouterr().err
    b.path.write_text("id,amount\n001,101\n")
    assert main(args[:-1] + [str(tmp_path / "different")]) == 1
    assert (tmp_path / "different/report.html").is_file()


@pytest.mark.e2e
def test_installed_table_cli_runs_outside_checkout(tmp_path):
    a, b = simple_inputs(tmp_path)
    executable = Path(sys.executable).parent / ("fct-compare.exe" if sys.platform == "win32" else "fct-compare")
    command = [
        str(executable),
        "--left",
        str(a.path),
        "--right",
        str(b.path),
        "--left-key",
        "id",
        "--right-key",
        "id",
        "--left-value",
        "amount",
        "--right-value",
        "amount",
        "--common-unit",
        "USD",
        "--output",
        str(tmp_path / "out"),
    ]
    process = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, check=False)
    assert process.returncode == 0, process.stderr
    assert json.loads((tmp_path / "out/comparison.json").read_text())["summary"]["all_matched"]
