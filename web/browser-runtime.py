"""Browser-only transport; reuses the maintained exact-decimal comparison engine."""

import hashlib
import io
import json
import uuid
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from financial_control_tower.table_workspace import build_comparison, example_request, inspect_file

MAX_FILE_BYTES = 8 * 1024 * 1024
_run_id = None
_run_files = {}


def _file_limit(payload):
    file = payload.get("file", {}) if isinstance(payload, dict) else {}
    encoded = file.get("content_base64", "") if isinstance(file, dict) else ""
    if not isinstance(encoded, str) or len(encoded) > 4 * ((MAX_FILE_BYTES + 2) // 3):
        raise ValueError("网页版每份文件最多 8 MiB，请选择较小的数据摘录。")


def dispatch(action, payload_json):
    global _run_id, _run_files
    payload = json.loads(payload_json)
    if action == "/api/example":
        return json.dumps(example_request(), ensure_ascii=False)
    if action == "/api/inspect":
        _file_limit(payload)
        return json.dumps(inspect_file(payload), ensure_ascii=False)
    if action == "discard":
        _run_id, _run_files = None, {}
        return "{}"
    if action != "/api/compare":
        raise ValueError("未支持的操作，请刷新页面重试。")
    _run_id, _run_files = None, {}
    for side in ("left", "right"):
        _file_limit(payload.get(side))
    result, files = build_comparison(payload)
    runtime = Path("/app/browser-build.json").read_bytes()
    files["browser-build.json"] = runtime
    manifest = json.loads(files["manifest.json"])
    manifest["sha256"]["browser-build.json"] = hashlib.sha256(runtime).hexdigest()
    manifest["execution"] = "Browser-local Pyodide Worker. No input files sent to a server."
    files["manifest.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    archive_bytes = io.BytesIO()
    with ZipFile(archive_bytes, "w", compression=ZIP_DEFLATED) as archive:
        for name, content in files.items():
            if name != "bundle.zip":
                archive.writestr(name, content)
    files["bundle.zip"] = archive_bytes.getvalue()
    _run_id, _run_files = uuid.uuid4().hex, files
    return json.dumps(
        {
            "run_id": _run_id,
            "result": result,
            "downloads": {
                "report": f"/api/runs/{_run_id}/report",
                "zip": f"/api/runs/{_run_id}/zip",
                "differences.csv": f"/api/runs/{_run_id}/differences.csv",
            },
        },
        ensure_ascii=False,
        allow_nan=False,
    )


def download(run_id, kind):
    names = {"report": "report.html", "zip": "bundle.zip", "differences.csv": "differences.csv"}
    if run_id != _run_id or kind not in names:
        raise ValueError("本次结果已失效，请重新核对后下载。")
    return _run_files[names[kind]]
