"""Browser-selected file snapshots and portable evidence for the existing comparator."""

import base64
import binascii
import csv
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

from . import __version__
from .table_compare import (
    MAX_BYTES,
    MAX_COLUMNS,
    MAX_ROWS,
    TableSpec,
    _raw_rows,
    _read_table,
    _write_html,
    run_comparison,
)

SIDES = ("left", "right")
MAX_BUNDLE_BYTES = 100 * 1024 * 1024


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def decode_file(file):
    if not isinstance(file, dict) or set(file) != {"name", "content_base64"}:
        raise ValueError("请选择本机文件；接口只接受文件名和内容，不接受服务器路径。")
    name, encoded = file["name"], file["content_base64"]
    if (
        not isinstance(name, str)
        or not name
        or len(name) > 200
        or any(char in name for char in "/\\")
        or any(ord(char) < 32 or ord(char) == 127 for char in name)
        or Path(name).suffix.lower() not in {".csv", ".xlsx"}
    ):
        raise ValueError("文件名必须是 CSV 或 XLSX 文件名，不包含目录。")
    if not isinstance(encoded, str) or len(encoded) > 4 * ((MAX_BYTES + 2) // 3):
        raise ValueError("每份文件最多 25 MiB；请选择较小的导出文件。")
    try:
        content = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("文件内容编码无效，请重新选择原文件。") from exc
    if not content or len(content) > MAX_BYTES:
        raise ValueError("请选择非空且不超过 25 MiB 的文件。")
    return name, content


def _selection(sheet, header_row):
    if type(header_row) is not int or not 1 <= header_row <= MAX_ROWS:
        raise ValueError("表头行必须是 1 至 100000 的整数。")
    if sheet is not None and (not isinstance(sheet, str) or not sheet or len(sheet) > 200):
        raise ValueError("请选择一个有效的工作表名称。")


def _sheet_names(content):
    try:
        from defusedxml.common import DefusedXmlException
        from defusedxml.ElementTree import ParseError, fromstring
    except ImportError as exc:
        raise ValueError("Excel 支持尚未安装，请安装 financial-control-tower[excel]。") from exc
    with ZipFile(io.BytesIO(content)) as archive:
        members = archive.infolist()
        if (
            len(members) > 2048
            or len({member.filename for member in members}) != len(members)
            or sum(member.file_size for member in members) > 100 * 1024 * 1024
            or any(member.file_size > MAX_BYTES for member in members)
        ):
            raise ValueError("Excel 压缩包包含重复文件或超过展开大小限制。")
        try:
            tree = fromstring(archive.read("xl/workbook.xml"))
            names = [node.get("name") for node in tree.findall("{*}sheets/{*}sheet")]
        except (KeyError, ParseError, DefusedXmlException) as exc:
            raise ValueError("无法读取 Excel 工作表目录；请使用有效的 XLSX 文件。") from exc
    if not names or any(not isinstance(name, str) or not name for name in names) or len(names) != len(set(names)):
        raise ValueError("Excel 工作表目录为空或包含重复名称。")
    return names


def inspect_file(payload):
    if not isinstance(payload, dict) or set(payload) - {"file", "sheet", "header_row"}:
        raise ValueError("文件预览请求包含未支持的设置。")
    name, content = decode_file(payload.get("file"))
    sheet, header_row = payload.get("sheet"), payload.get("header_row", 1)
    _selection(sheet, header_row)
    suffix = Path(name).suffix.lower()
    names = _sheet_names(content) if suffix == ".xlsx" else []
    result = {
        "filename": name,
        "sha256": hashlib.sha256(content).hexdigest(),
        "format": suffix[1:],
        "sheets": names,
        "selection_required": False,
        "sheet": sheet,
        "header_row": header_row,
        "headers": [],
        "preview": [],
        "data_rows": None,
        "blank_rows_ignored": [],
    }
    if sheet is None and len(names) > 1:
        result["selection_required"] = True
        return result
    if sheet is None and names:
        sheet = names[0]
    spec = TableSpec(Path(name), (), (), sheet, header_row)
    _rows, metadata = _read_table(spec, content)
    result.update(metadata)
    result["sheet"] = metadata.get("sheet")
    raw = _raw_rows(spec, content, {})
    try:
        for number, cells in enumerate(raw, 1):
            if number <= header_row or not any(value is not None and value != "" for value, _kind in cells):
                continue
            width = len(metadata["headers"])
            cells = cells[:width] + [(None, "other")] * max(0, width - len(cells))
            result["preview"].append(
                {
                    "row": number,
                    "values": ["" if value is None else str(value) for value, _kind in cells],
                    "kinds": [kind for _value, kind in cells],
                }
            )
            if len(result["preview"]) == 5:
                break
    finally:
        raw.close()
    return result


def _side_request(side, value, source_dir):
    allowed = {"file", "sheet", "header_row", "keys", "values", "currency"}
    if not isinstance(value, dict) or set(value) - allowed:
        raise ValueError(f"{side} 文件设置无效；不接受本机路径。")
    name, content = decode_file(value.get("file"))
    sheet, header_row = value.get("sheet"), value.get("header_row", 1)
    _selection(sheet, header_row)
    for field in ("keys", "values"):
        names = value.get(field)
        if (
            not isinstance(names, list)
            or not 1 <= len(names) <= MAX_COLUMNS
            or any(not isinstance(name, str) or not name.strip() for name in names)
        ):
            raise ValueError(f"{side} 的 {field} 必须包含至少一个明确的列名。")
    currency = value.get("currency")
    if currency is not None and (not isinstance(currency, str) or not currency.strip()):
        raise ValueError("币种列必须是有效列名或空值。")
    suffix = Path(name).suffix.lower()
    if suffix == ".xlsx":
        _sheet_names(content)
    path = source_dir / f"{side}{suffix}"
    path.write_bytes(content)
    spec = TableSpec(path, tuple(value["keys"]), tuple(value["values"]), sheet, header_row, currency)
    request = {
        "file": f"sources/{path.name}",
        "original_filename": name,
        "sha256": hashlib.sha256(content).hexdigest(),
        "sheet": sheet,
        "header_row": header_row,
        "keys": list(spec.keys),
        "values": list(spec.values),
        "currency": currency,
    }
    return spec, request, content


def build_comparison(payload):
    """Use the maintained exact-decimal engine, then make its evidence portable."""
    allowed = {*SIDES, "absolute_tolerance", "relative_tolerance", "common_unit"}
    if not isinstance(payload, dict) or set(payload) - allowed:
        raise ValueError("对账请求包含未支持的设置。")
    options = {
        "absolute_tolerance": payload.get("absolute_tolerance", "0"),
        "relative_tolerance": payload.get("relative_tolerance", "0"),
        "common_unit": payload.get("common_unit"),
    }
    if any(not isinstance(options[key], str) for key in ("absolute_tolerance", "relative_tolerance")):
        raise ValueError("请以十进制文本输入容差，避免 JSON 浮点精度损失。")
    if options["common_unit"] is not None and not isinstance(options["common_unit"], str):
        raise ValueError("共同单位必须是文本或空值。")
    with TemporaryDirectory(prefix="fct-browser-") as temporary:
        root = Path(temporary)
        source_dir = root / "sources"
        source_dir.mkdir()
        specs, request, files = [], {"schema_version": 1, "kind": "fct-table-comparison", **options}, {}
        for side in SIDES:
            spec, item, content = _side_request(side, payload.get(side), source_dir)
            specs.append(spec)
            request[side] = item
            files[item["file"]] = content
        output = root / "result"
        result = run_comparison(*specs, output, **options)
        for side in SIDES:
            item = request[side]
            result["inputs"][side]["path"] = item["file"]
            result["inputs"][side]["original_filename"] = item["original_filename"]
            item["sheet"] = result["inputs"][side]["sheet"]
        source_hashes = {}
        package = Path(__file__).parent
        for path in sorted(package.glob("*.py")) + sorted((package / "static").glob("*")):
            if path.is_file():
                source_hashes[str(path.relative_to(package))] = hashlib.sha256(path.read_bytes()).hexdigest()
        identity = {"request": request, "package_version": __version__, "source_code_sha256": source_hashes}
        fingerprint = hashlib.sha256(
            json.dumps(identity, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()
        ).hexdigest()
        result["request_fingerprint"] = fingerprint
        _write_html(output / "report.html", result)
        files.update(
            {
                "comparison.json": _json_bytes(result),
                "request.json": _json_bytes(request),
                "differences.csv": (output / "differences.csv").read_bytes(),
                "report.html": (output / "report.html").read_bytes(),
            }
        )
        files["manifest.json"] = _json_bytes(
            {
                "schema_version": 2,
                "package_version": __version__,
                "request_fingerprint": fingerprint,
                "inputs": result["inputs"],
                "policy": result["policy"],
                "summary": result["summary"],
                "source_code_sha256": source_hashes,
                "sha256": {name: hashlib.sha256(content).hexdigest() for name, content in sorted(files.items())},
                "scope": "Snapshots are browser-selected bytes. Original device paths are not collected. SHA-256 is not authentication or approval.",
            }
        )
        if sum(map(len, files.values())) > MAX_BUNDLE_BYTES:
            raise ValueError("导出证据超过 100 MiB，请缩小输入范围。")
        zipped = io.BytesIO()
        with ZipFile(zipped, "w", compression=ZIP_DEFLATED) as archive:
            for name, content in files.items():
                archive.writestr(name, content)
        files["bundle.zip"] = zipped.getvalue()
    return result, files


def example_request():
    rows = {
        "left": "account,record,currency,balance,accrual\n001,A,USD,100.00,2.00\n001,B,HKD,20.00,1.00\n002,C,USD,30.00,0.00\n003,D,USD,40.00,1.00\n003,D,USD,41.00,2.00\n",
        "right": "entity,ticket,ccy,amount,interest\n001,A,USD,100.01,2.03\n001,B,USD,20.00,1.00\n004,E,USD,50.00,0.00\n003,D,USD,40.00,1.00\n",
    }
    return {
        side: {
            "file": {"name": f"example-{side}.csv", "content_base64": base64.b64encode(rows[side].encode()).decode()},
            "sheet": None,
            "header_row": 1,
            "keys": ["account", "record"] if side == "left" else ["entity", "ticket"],
            "values": ["balance", "accrual"] if side == "left" else ["amount", "interest"],
            "currency": "currency" if side == "left" else "ccy",
        }
        for side in SIDES
    } | {"absolute_tolerance": "0.01", "relative_tolerance": "0", "common_unit": None}


INPUT_ERRORS = (ValueError, OSError, UnicodeError, csv.Error, BadZipFile)
