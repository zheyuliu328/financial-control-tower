"""Real transport, browser snapshots and export integrity; no proprietary fixtures."""

import base64
import copy
import hashlib
import http.client
import io
import json
import threading
from pathlib import Path
from zipfile import ZipFile

import pytest

from financial_control_tower import table_ui
from financial_control_tower.table_workspace import build_comparison, decode_file, example_request, inspect_file


def file_data(name, content):
    return {"name": name, "content_base64": base64.b64encode(content).decode()}


def test_portable_bundle_keeps_exact_bytes_and_manual_counts():
    request = example_request()
    before = copy.deepcopy(request)
    result, files = build_comparison(request)
    assert result["summary"] == {
        "field_checks": {
            "amount_mismatch": 1,
            "currency_mismatch": 2,
            "duplicate_key": 6,
            "left_only": 2,
            "matched": 1,
            "right_only": 2,
        },
        "input_rows": {"left": 5, "right": 4},
        "accounted_rows": {"left": 5, "right": 4},
        "all_matched": False,
    }
    assert request == before
    manifest = json.loads(files["manifest.json"])
    settings = json.loads(files["request.json"])
    assert set(manifest["sha256"]) == set(files) - {"manifest.json", "bundle.zip"}
    for name, digest in manifest["sha256"].items():
        assert hashlib.sha256(files[name]).hexdigest() == digest
    with ZipFile(io.BytesIO(files["bundle.zip"])) as archive:
        assert set(archive.namelist()) == set(files) - {"bundle.zip"}
        for name in archive.namelist():
            assert not Path(name).is_absolute() and ".." not in Path(name).parts
            assert archive.read(name) == files[name]
    for side in ("left", "right"):
        item = result["inputs"][side]
        assert item["path"] == f"sources/{side}.csv"
        assert item["original_filename"] == request[side]["file"]["name"]
        assert files[item["path"]] == base64.b64decode(request[side]["file"]["content_base64"])
        assert settings[side]["sha256"] == item["sha256"]
    for name in ("report.html", "comparison.json", "manifest.json"):
        assert b"fct-browser-" not in files[name]


def test_replay_portable_snapshot_produces_same_result():
    result, files = build_comparison(example_request())
    settings = json.loads(files["request.json"])
    replay = {key: settings[key] for key in ("absolute_tolerance", "relative_tolerance", "common_unit")}
    for side in ("left", "right"):
        item = settings[side]
        replay[side] = {key: item[key] for key in ("keys", "values", "currency", "sheet", "header_row")}
        replay[side]["file"] = file_data(item["original_filename"], files[item["file"]])
    rerun, _files = build_comparison(replay)
    assert rerun == result


def test_setting_and_input_changes_bind_new_fingerprint():
    request = example_request()
    baseline, _files = build_comparison(request)
    request["absolute_tolerance"] = "0.1"
    changed, _files = build_comparison(request)
    assert baseline["request_fingerprint"] != changed["request_fingerprint"]
    request["left"]["file"]["name"] = "different-source.csv"
    renamed, _files = build_comparison(request)
    assert changed["request_fingerprint"] != renamed["request_fingerprint"]


def test_preview_selects_real_sheet_header_and_preserves_text_ids():
    from openpyxl import Workbook

    workbook = Workbook()
    workbook.active.title = "Notes"
    workbook.active.append(["Choose Records explicitly"])
    sheet = workbook.create_sheet("Records")
    sheet.append(["Invented source"])
    sheet.append([])
    sheet.append(["key", "amount", "unselected"])
    sheet.append(["0007", 25, "=1+1"])
    sheet.append(["0008", 40, "plain"])
    stream = io.BytesIO()
    workbook.save(stream)
    file = file_data("invented.xlsx", stream.getvalue())
    pending = inspect_file({"file": file})
    assert pending["selection_required"] is True
    assert pending["headers"] == [] and pending["data_rows"] is None
    actual = inspect_file({"file": file, "sheet": "Records", "header_row": 3})
    assert actual["sheets"] == ["Notes", "Records"]
    assert actual["headers"] == ["key", "amount", "unselected"]
    assert actual["data_rows"] == 2
    assert actual["preview"][0] == {"row": 4, "values": ["0007", "25", "=1+1"], "kinds": ["text", "other", "formula"]}


@pytest.mark.parametrize(
    "patch",
    [
        {"path": "/etc/passwd"},
        {"name": "../source.csv"},
        {"name": "C:\\secret.csv"},
        {"name": "a\u0000.csv"},
        {"name": "macro.xlsm"},
        {"content_base64": "%%%"},
        {"content_base64": ""},
        {"content_base64": 42},
    ],
)
def test_untrusted_file_descriptors_rejected(patch):
    file = file_data("source.csv", b"id,value\nA,1\n")
    file.update(patch)
    with pytest.raises(ValueError):
        decode_file(file)


@pytest.mark.parametrize("header", [True, 0, -1, "1", 100001])
def test_header_row_requires_bounded_integer(header):
    with pytest.raises(ValueError):
        inspect_file({"file": example_request()["left"]["file"], "header_row": header})


@pytest.fixture
def live_server():
    server = table_ui.FCTServer(0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def send(server, method, path, body=None, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=10)
    supplied = {"Content-Type": "application/json", "X-FCT-Token": server.csrf_token}
    supplied.update(headers or {})
    conn.request(method, path, body=body, headers=supplied)
    response = conn.getresponse()
    result = response.status, dict(response.getheaders()), response.read()
    conn.close()
    return result


def test_http_compare_and_companion_files(live_server):
    status, headers, data = send(live_server, "POST", "/api/compare", json.dumps(example_request()))
    assert status == 200 and headers["Cache-Control"] == "no-store"
    response = json.loads(data)
    assert response["result"]["summary"]["field_checks"]["duplicate_key"] == 6
    status, headers, report = send(live_server, "GET", response["downloads"]["report"])
    assert status == 200 and b"Comparison completed with exceptions" in report
    assert headers["X-Frame-Options"] == "DENY"
    base = response["downloads"]["report"].rsplit("/", 1)[0]
    for name in ("comparison.json", "manifest.json", "differences.csv"):
        assert send(live_server, "GET", base + "/" + name)[0] == 200
    status, headers, zipped = send(live_server, "GET", response["downloads"]["zip"])
    assert status == 200 and "attachment;" in headers["Content-Disposition"]
    assert ZipFile(io.BytesIO(zipped)).read("report.html") == report


@pytest.mark.parametrize(
    "headers",
    [
        {"Host": "evil.example"},
        {"Origin": "https://evil.example"},
        {"Sec-Fetch-Site": "cross-site"},
        {"X-FCT-Token": "wrong"},
        {"X-FCT-Token": "é"},
    ],
)
def test_external_or_invalid_token_requests_fail_closed(live_server, headers):
    status, _headers, data = send(live_server, "POST", "/api/compare", "{}", headers)
    assert status == 403 and "error" in json.loads(data)
    assert not live_server.runs


@pytest.mark.parametrize("raw", ['{"x":1,"x":2}', '{"x":NaN}', "[]", '{"x":'])
def test_invalid_json_never_publishes(live_server, raw):
    assert send(live_server, "POST", "/api/compare", raw)[0] == 400
    assert not live_server.runs


def test_post_size_type_and_server_path_limits(live_server):
    assert send(live_server, "POST", "/api/inspect", "{}", {"Content-Type": "text/plain"})[0] == 415
    assert send(live_server, "POST", "/api/inspect", "{}", {"Content-Length": str(table_ui.MAX_REQUEST + 1)})[0] == 413
    assert send(live_server, "POST", "/api/inspect", '{"file":{"path":"/etc/passwd"}}')[0] == 400
    for path in ("/etc/passwd", "/static/../../pyproject.toml", "/api/runs/" + "a" * 32 + "/table_ui.py"):
        assert send(live_server, "GET", path)[0] == 404
    assert not live_server.runs


def test_two_work_slots_reject_third_without_publishing(live_server):
    assert live_server.work_slots.acquire(blocking=False)
    assert live_server.work_slots.acquire(blocking=False)
    try:
        assert send(live_server, "POST", "/api/compare", json.dumps(example_request()))[0] == 429
    finally:
        live_server.work_slots.release()
        live_server.work_slots.release()
    assert not live_server.runs


def test_run_cache_expiration_and_eviction_are_explicit(live_server, monkeypatch):
    first = live_server.store_run({"report.html": b"old"})
    for _index in range(3):
        live_server.store_run({"report.html": b"new"})
    assert send(live_server, "GET", f"/api/runs/{first}/report")[0] == 410
    last = live_server.store_run({"report.html": b"current"})
    now = table_ui.time.monotonic()
    monkeypatch.setattr(table_ui.time, "monotonic", lambda: now + table_ui.CACHE_SECONDS + 1)
    assert send(live_server, "GET", f"/api/runs/{last}/report")[0] == 410


def test_unexpected_error_does_not_expose_paths_or_publish(live_server, monkeypatch):
    def broken(_payload):
        raise RuntimeError("sensitive detail /private/source")

    monkeypatch.setattr(table_ui, "build_comparison", broken)
    status, _headers, data = send(live_server, "POST", "/api/compare", "{}")
    assert status == 500 and b"sensitive" not in data and b"/private" not in data
    assert not live_server.runs
