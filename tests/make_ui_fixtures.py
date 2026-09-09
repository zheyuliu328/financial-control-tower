"""Invent external-format inputs and verify GUI artifacts without importing FCT."""

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path
from zipfile import ZipFile

from openpyxl import Workbook

HTML_KEY = '<img src="x" onerror="alert(1)">'
LEFT_HEADERS = ["Account code", "Desk", "Book amount", "Fee amount", "CCY", "Comment"]
RIGHT_HEADERS = ["Ledger ID", "Region", "Posted total", "Charges", "Currency", "Memo"]
LEFT = [
    ["001", "A", "100", "5", "USD", "Small difference"],
    ["001", "B", "200", "2", "USD", "Same code, different desk"],
    ["002", "A", "1000", "7", "USD", "Relative allowance matters"],
    ["003", "A", "60", "1", "USD", "Check currency"],
    ["004", "A", "50", "4", "USD", "Only in this extract"],
    ["005", "A", "70", "1", "USD", "Duplicate member one"],
    ["005", "A", "71", "1", "USD", "Duplicate member two"],
    ["006", "A", "pending", "3", "USD", "Unusable amount; retain this row"],
    ["", "A", "90", "1", "USD", "Key was left blank"],
    [HTML_KEY, "A", "10", "0", "USD", "Literal text, not executable markup"],
    ["007", "A", "-20", "-1", "USD", "Negative values are still numbers"],
]
RIGHT = [
    ["007", "A", "-20.04", "-1", "USD", "Different source order"],
    ["001", "B", "200.30", "2.10", "USD", "Two differences"],
    ["002", "A", "1001", "7.04", "USD", "Within selected allowances"],
    ["003", "A", "60", "1", "HKD", "Equal numbers do not imply equal currency"],
    ["005", "A", "70", "1", "USD", "Do not pair with one arbitrary duplicate"],
    ["006", "A", "80", "3", "USD", "Opposite amount exists"],
    ["008", "A", "33", "2", "USD", "Only in the other extract"],
    [HTML_KEY, "A", "10", "0", "USD", "Literal text"],
    ["001", "A", "100.02", "5.00", "USD", "Small difference"],
    ["009", "A", "10", "=2+2", "USD", "A formula is not a verified frozen value"],
]
UNIT_LEFT_HEADERS = ["Batch", "Item", "Value A", "Value B"]
UNIT_RIGHT_HEADERS = ["Run", "Code", "Output A", "Output B"]
UNIT_LEFT = [["09", "AX", "10", "1"], ["09", "BX", "20", "2"]]
UNIT_RIGHT = [["09", "BX", "20.5", "2"], ["09", "AX", "10.01", "1"]]


def _hash(content):
    return hashlib.sha256(content).hexdigest()


def _write_csv(path, headers, rows):
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(headers)
        writer.writerows(rows)


def _write_excel(path):
    workbook = Workbook()
    cover = workbook.active
    cover.title = "Read me"
    cover.append(["Invented software acceptance/trial data. No client or real account data."])
    cover.append(["Select Posted entries; headers are on row 3."])
    sheet = workbook.create_sheet("Posted entries")
    sheet.append(["Independent monthly extract — retain the original file unchanged"])
    sheet.append([])
    sheet.append(RIGHT_HEADERS)
    for row in RIGHT:
        sheet.append(row)
    # Text such as 001 remains text. The deliberate Charges formula remains a formula.
    with path.open("xb") as stream:
        workbook.save(stream)
    workbook.close()


def _expectations(names):
    records = []

    def case(left_index, right_index, statuses, differences=(None, None), allowances=(None, None)):
        left = LEFT[left_index] if left_index is not None else None
        right = RIGHT[right_index] if right_index is not None else None
        for column in range(2):
            records.append(
                {
                    "key": (left or right)[:2],
                    "left_row": left_index + 2 if left is not None else None,
                    "right_row": right_index + 4 if right is not None else None,
                    "left_column": LEFT_HEADERS[column + 2],
                    "right_column": RIGHT_HEADERS[column + 2],
                    "left_value": left[column + 2] if left else None,
                    "right_value": right[column + 2] if right else None,
                    "left_currency": left[4] if left else None,
                    "right_currency": right[4] if right else None,
                    "status": statuses[column],
                    "difference_right_minus_left": differences[column],
                    "allowed_difference": allowances[column],
                }
            )

    # Independent row pairings and hand-calculated allowances. No engine joins or calls.
    case(0, 8, ["matched"] * 2, ["0.02", "0"], ["0.10002", "0.05"])
    case(1, 1, ["amount_mismatch"] * 2, ["0.30", "0.10"], ["0.20030", "0.05"])
    case(2, 2, ["matched"] * 2, ["1", "0.04"], ["1.001", "0.05"])
    case(3, 3, ["currency_mismatch"] * 2)
    case(4, None, ["left_only"] * 2)
    case(5, None, ["duplicate_key"] * 2)
    case(6, None, ["duplicate_key"] * 2)
    case(None, 4, ["duplicate_key"] * 2)
    case(7, 5, ["invalid_numeric"] * 2)
    case(8, None, ["missing_key"] * 2)
    case(9, 7, ["matched"] * 2, ["0", "0"], ["0.05", "0.05"])
    case(10, 0, ["matched"] * 2, ["-0.04", "0"], ["0.05", "0.05"])
    case(None, 6, ["right_only"] * 2)
    case(None, 9, ["formula_cell"] * 2)
    currency = {
        "left": {
            "name": names[0],
            "keys": LEFT_HEADERS[:2],
            "values": LEFT_HEADERS[2:4],
            "currency": "CCY",
            "sheet": None,
            "header_row": 1,
        },
        "right": {
            "name": names[1],
            "keys": RIGHT_HEADERS[:2],
            "values": RIGHT_HEADERS[2:4],
            "currency": "Currency",
            "sheet": "Posted entries",
            "header_row": 3,
        },
        "absolute_tolerance": "0.05",
        "relative_tolerance": "0.001",
        "common_unit": None,
        "input_rows": {"left": 11, "right": 10},
        "field_checks": {
            "matched": 8,
            "amount_mismatch": 2,
            "currency_mismatch": 2,
            "duplicate_key": 6,
            "invalid_numeric": 2,
            "missing_key": 2,
            "left_only": 2,
            "right_only": 2,
            "formula_cell": 2,
        },
        "source_filters": {"all": 28, "left": 22, "right": 20, "paired": 14, "unpaired": 14},
        "records": records,
    }
    unit_records = []
    for left_index, right_index, differences, statuses in [
        (0, 1, ["0.01", "0"], ["matched", "matched"]),
        (1, 0, ["0.5", "0"], ["amount_mismatch", "matched"]),
    ]:
        for column in range(2):
            unit_records.append(
                {
                    "key": UNIT_LEFT[left_index][:2],
                    "left_row": left_index + 2,
                    "right_row": right_index + 2,
                    "left_column": UNIT_LEFT_HEADERS[column + 2],
                    "right_column": UNIT_RIGHT_HEADERS[column + 2],
                    "left_value": UNIT_LEFT[left_index][column + 2],
                    "right_value": UNIT_RIGHT[right_index][column + 2],
                    "left_currency": "",
                    "right_currency": "",
                    "status": statuses[column],
                    "difference_right_minus_left": differences[column],
                    "allowed_difference": "0.05",
                }
            )
    unit = {
        "left": {
            "name": names[2],
            "keys": UNIT_LEFT_HEADERS[:2],
            "values": UNIT_LEFT_HEADERS[2:],
            "currency": None,
            "sheet": None,
            "header_row": 1,
        },
        "right": {
            "name": names[3],
            "keys": UNIT_RIGHT_HEADERS[:2],
            "values": UNIT_RIGHT_HEADERS[2:],
            "currency": None,
            "sheet": None,
            "header_row": 1,
        },
        "absolute_tolerance": "0.05",
        "relative_tolerance": "0",
        "common_unit": "synthetic points",
        "input_rows": {"left": 2, "right": 2},
        "field_checks": {"matched": 3, "amount_mismatch": 1},
        "source_filters": {"all": 4, "left": 4, "right": 4, "paired": 4, "unpaired": 0},
        "records": unit_records,
    }
    return {"currency": currency, "unit": unit, "files": names, "human_trial": "not performed"}


def make(destination, trial=False):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    prefix = "trial-" if trial else ""
    names = [
        prefix + "book-export.csv",
        prefix + "posted-review.xlsx",
        prefix + "unit-left.csv",
        prefix + "unit-right.csv",
    ]
    expectation_name = "facilitator-expectations.json" if trial else "fixture-expectations.json"
    generated = [*names, expectation_name] + (["PARTICIPANT_TASKS.zh-CN.md"] if trial else [])
    if any((destination / name).exists() or (destination / name).is_symlink() for name in generated):
        raise FileExistsError("Choose a fresh directory: this helper never replaces existing fixture files")
    _write_csv(destination / names[0], LEFT_HEADERS, LEFT)
    _write_excel(destination / names[1])
    _write_csv(destination / names[2], UNIT_LEFT_HEADERS, UNIT_LEFT)
    _write_csv(destination / names[3], UNIT_RIGHT_HEADERS, UNIT_RIGHT)
    expected = _expectations(names)
    expected["input_sha256"] = {name: _hash((destination / name).read_bytes()) for name in names}
    with (destination / expectation_name).open("x", encoding="utf-8") as stream:
        json.dump(expected, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    if trial:
        participant = f"""# 15 分钟试用任务卡（全部数据为新造样例）

请只使用本目录中的文件，无需上传自己的资料。主持人记录你的操作，不替你选择字段。
facilitator-expectations.json 是主持人的答案文件，请完成任务前不要打开。

1. 比较 {names[0]} 与 {names[1]}。Excel 取 Posted entries，表头第 3 行。
   左 Account code + Desk 对应右 Ledger ID + Region；Book amount / Fee amount 分别对应 Posted total / Charges。
   CCY 与 Currency 是币种。绝对容差 0.05，相对容差 0.001（小数比例）。
2. 找出两边都有、需要继续查看的金额差异，再找出一个由于数据问题不能直接相减的条目。
   记录编号、分组、字段和原因。不要把相同编号的不同分组并成一条。
3. 查看原始行位置，确认重复键的所有成员仍可追踪。下载完整包并打开报告。
4. 把绝对容差改为 0.10，再改回 0.05。在重新比较前尝试使用上一次下载入口，描述界面反馈。
5. 若还有时间：比较 {names[2]} 与 {names[3]}。Batch + Item 对 Run + Code；
   Value A / Value B 对 Output A / Output B；共同单位填 synthetic points，绝对容差 0.05，相对容差 0。

请说出你不确定的地方。完成与否、提示次数和错误都可以如实记录，不需要给产品好评。
"""
        with (destination / "PARTICIPANT_TASKS.zh-CN.md").open("x", encoding="utf-8") as stream:
            stream.write(participant)
    return {
        "directory": str(destination.resolve()),
        "expectations": expectation_name,
        "files": names,
        "human_trial": "not performed",
    }


def _identity(record):
    return tuple(record["key"]), record["left_row"], record["right_row"], record["left_column"], record["right_column"]


def verify_result(result, expected, scenario):
    wanted = expected[scenario]
    assert result["summary"]["input_rows"] == wanted["input_rows"]
    assert result["summary"]["accounted_rows"] == wanted["input_rows"]
    assert result["summary"]["field_checks"] == wanted["field_checks"]
    assert result["summary"]["all_matched"] is False
    assert Decimal(result["policy"]["absolute_tolerance"]) == Decimal(wanted["absolute_tolerance"])
    assert Decimal(result["policy"]["relative_tolerance"]) == Decimal(wanted["relative_tolerance"])
    if wanted["common_unit"]:
        assert wanted["common_unit"] in result["policy"]["unit"]
    actual = {_identity(record): record for record in result["records"]}
    assert len(actual) == len(result["records"]) == len(wanted["records"])
    assert set(actual) == {_identity(record) for record in wanted["records"]}
    assert dict(Counter(record["status"] for record in result["records"])) == wanted["field_checks"]
    for record in wanted["records"]:
        obtained = actual[_identity(record)]
        for key in ("status", "key", "left_value", "right_value", "left_currency", "right_currency"):
            assert obtained[key] == record[key], (key, record, obtained)
        for key in ("difference_right_minus_left", "allowed_difference"):
            if record[key] is None:
                assert obtained[key] is None
            else:
                assert Decimal(obtained[key]) == Decimal(record[key])
        if record["difference_right_minus_left"] is None:
            assert obtained["absolute_difference"] is None
        else:
            assert Decimal(obtained["absolute_difference"]) == abs(Decimal(record["difference_right_minus_left"]))
        assert bool(obtained["issues"]) == (record["status"] != "matched")
    for side in ("left", "right"):
        metadata = result["inputs"][side]
        assert metadata["sha256"] == expected["input_sha256"][wanted[side]["name"]]
        assert metadata["original_filename"] == wanted[side]["name"]
        assert metadata["keys"] == wanted[side]["keys"]
        assert metadata["values"] == wanted[side]["values"]
        assert metadata["header_row"] == wanted[side]["header_row"]
        assert metadata["sheet"] == wanted[side]["sheet"]
        assert not Path(metadata["path"]).is_absolute()
        assert ".." not in Path(metadata["path"]).parts
    return {
        "scenario": scenario,
        "field_records": len(actual),
        "source_rows": wanted["input_rows"],
        "field_checks": wanted["field_checks"],
        "exact_records": "pass",
    }


class _HtmlAudit(HTMLParser):
    def handle_starttag(self, tag, attrs):
        assert tag not in {"script", "iframe", "img", "object", "embed"}, f"Unexpected active/media tag: {tag}"
        for name, value in attrs:
            assert not name.lower().startswith("on"), "Unexpected event handler in report"
            if name in {"src", "href"} and value:
                assert not value.startswith(("http:", "https:", "//", "javascript:")), (
                    "Unexpected report network/executable URL"
                )


def verify_zip(path, expected, scenario, extract=None, source_root=None):
    with ZipFile(path) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names)), "ZIP has duplicate member names"
        contents = {name: archive.read(name) for name in names}
    wanted_sources = {
        side: f"sources/{side}{Path(expected[scenario][side]['name']).suffix}" for side in ("left", "right")
    }
    wanted_files = {
        "request.json",
        "comparison.json",
        "manifest.json",
        "differences.csv",
        "report.html",
        *wanted_sources.values(),
    }
    assert set(contents) == wanted_files
    manifest = json.loads(contents["manifest.json"])
    assert set(manifest["sha256"]) == wanted_files - {"manifest.json"}
    for name, digest in manifest["sha256"].items():
        assert _hash(contents[name]) == digest, f"Incorrect output digest: {name}"
    result = json.loads(contents["comparison.json"])
    request = json.loads(contents["request.json"])
    identity = {
        "request": request,
        "package_version": manifest["package_version"],
        "source_code_sha256": manifest["source_code_sha256"],
    }
    fingerprint = _hash(json.dumps(identity, ensure_ascii=False, sort_keys=True, allow_nan=False).encode())
    assert result["request_fingerprint"] == manifest["request_fingerprint"] == fingerprint
    if source_root:
        source_root = Path(source_root).resolve()
        assert manifest["source_code_sha256"], "No source code hashes in the manifest"
        installed_files = list(source_root.glob("*.py")) + list((source_root / "static").glob("*"))
        assert set(manifest["source_code_sha256"]) == {
            str(source.relative_to(source_root)) for source in installed_files if source.is_file()
        }, "Source hash inventory does not cover the installed application"
        for name, digest in manifest["source_code_sha256"].items():
            source_path = (source_root / name).resolve()
            assert source_root in source_path.parents, "Invalid source code hash path"
            assert _hash(source_path.read_bytes()) == digest, f"Installed source hash mismatch: {name}"
    checked = verify_result(result, expected, scenario)
    for side, name in wanted_sources.items():
        original = expected[scenario][side]["name"]
        assert _hash(contents[name]) == expected["input_sha256"][original]
        assert result["inputs"][side]["path"] == name
        assert manifest["inputs"][side]["sha256"] == expected["input_sha256"][original]
    exported = list(csv.DictReader(io.StringIO(contents["differences.csv"].decode("utf-8"))))
    assert len(exported) == len(result["records"])
    assert dict(Counter(row["status"] for row in exported)) == expected[scenario]["field_checks"]
    csv_records = {
        (
            tuple(json.loads(row["key"])),
            int(row["left_row"]) if row["left_row"] else None,
            int(row["right_row"]) if row["right_row"] else None,
            row["left_column"],
            row["right_column"],
        ): row
        for row in exported
    }
    for record in result["records"]:
        row = csv_records[_identity(record)]
        assert row["status"] == record["status"]
        for field in ("difference_right_minus_left", "absolute_difference", "allowed_difference"):
            assert Decimal(row[field]) == Decimal(record[field]) if record[field] is not None else row[field] == ""
        for field in ("left_value", "right_value"):
            raw = record[field]
            text = "" if raw is None else str(raw)
            # These invented sources only need the documented '=' / '-' protection.
            protected = "'" + text if text.startswith(("=", "-")) else text
            assert row[field] == protected
    report = contents["report.html"].decode("utf-8")
    _HtmlAudit().feed(report)
    if scenario == "currency":
        assert "&lt;img" in report
        assert HTML_KEY not in report
    if extract:
        extract = Path(extract)
        extract.mkdir(parents=True, exist_ok=False)
        for name, content in contents.items():
            target = extract / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(content)
    return {
        **checked,
        "zip_sha256": _hash(Path(path).read_bytes()),
        "all_member_hashes": "pass",
        "source_bytes": "unchanged",
        "html_active_content": "none",
        "source_code_hashes": "pass" if source_root else "not checked; provide --source-root",
        "extracted_to": str(extract) if extract else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", type=Path)
    parser.add_argument("--trial", action="store_true")
    verify = parser.add_mutually_exclusive_group()
    verify.add_argument("--verify-result", type=Path)
    verify.add_argument("--verify-zip", type=Path)
    verify.add_argument("--verify-sources", type=Path)
    parser.add_argument("--expectations", type=Path)
    parser.add_argument("--scenario", choices=["currency", "unit"], default="currency")
    parser.add_argument("--extract", type=Path)
    parser.add_argument("--source-root", type=Path)
    args = parser.parse_args()
    if args.verify_result or args.verify_zip or args.verify_sources:
        if not args.expectations:
            parser.error("--expectations is required for verification")
        expected = json.loads(args.expectations.read_text(encoding="utf-8"))
        if args.verify_sources:
            actual = {name: _hash((args.verify_sources / name).read_bytes()) for name in expected["files"]}
            assert actual == expected["input_sha256"], "Original source files changed"
            result = {"original_sources": "unchanged", "input_sha256": actual}
        elif args.verify_result:
            result = verify_result(json.loads(args.verify_result.read_text(encoding="utf-8")), expected, args.scenario)
        else:
            result = verify_zip(args.verify_zip, expected, args.scenario, args.extract, args.source_root)
    else:
        if args.output is None:
            parser.error("provide a new fixture output directory")
        result = make(args.output, trial=args.trial)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
