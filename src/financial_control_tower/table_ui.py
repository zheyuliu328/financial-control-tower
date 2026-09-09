"""Loopback-only browser entry for explicit two-table comparison."""

import argparse
import hmac
import json
import re
import secrets
import sys
import threading
import time
import webbrowser
from collections import OrderedDict
from contextlib import suppress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import __version__
from .table_compare import MAX_BYTES
from .table_workspace import INPUT_ERRORS, build_comparison, example_request, inspect_file

MAX_REQUEST = 70 * 1024 * 1024
MAX_CACHE_BYTES = 128 * 1024 * 1024
MAX_CACHED_RUNS = 3
CACHE_SECONDS = 3600
ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/static/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/static/styles.css": ("styles.css", "text/css; charset=utf-8"),
}
DOWNLOADS = {
    "report": ("report.html", "text/html; charset=utf-8"),
    "zip": ("bundle.zip", "application/zip"),
    "comparison.json": ("comparison.json", "application/json"),
    "request.json": ("request.json", "application/json"),
    "manifest.json": ("manifest.json", "application/json"),
    "differences.csv": ("differences.csv", "text/csv; charset=utf-8"),
}


def _reject_number(value):
    raise ValueError(f"JSON 不接受 {value}。")


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("JSON 包含重复设置名称。")
        result[key] = value
    return result


def load_request(raw):
    try:
        payload = json.loads(raw, parse_constant=_reject_number, object_pairs_hook=_unique_keys)
    except (UnicodeError, RecursionError, json.JSONDecodeError) as exc:
        raise ValueError("请求必须是有效的 UTF-8 JSON 对象。") from exc
    if not isinstance(payload, dict):
        raise ValueError("请求必须是一个设置对象。")
    return payload


class FCTServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port=8767):
        self.csrf_token = secrets.token_hex(32)
        self.work_slots = threading.BoundedSemaphore(2)
        self.runs = OrderedDict()
        self.runs_lock = threading.Lock()
        super().__init__(("127.0.0.1", port), FCTHandler)

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server_port}"

    def _expire(self):
        now = time.monotonic()
        for run_id in list(self.runs):
            if now - self.runs[run_id][0] >= CACHE_SECONDS:
                del self.runs[run_id]

    def store_run(self, files):
        size = sum(map(len, files.values()))
        if size > MAX_CACHE_BYTES:
            raise ValueError("报告超过本地会话容量，请缩小输入范围。")
        with self.runs_lock:
            self._expire()
            while self.runs and (
                len(self.runs) >= MAX_CACHED_RUNS
                or size + sum(item[2] for item in self.runs.values()) > MAX_CACHE_BYTES
            ):
                self.runs.popitem(last=False)
            run_id = secrets.token_hex(16)
            self.runs[run_id] = (time.monotonic(), files, size)
        return run_id

    def read_run(self, run_id, name):
        with self.runs_lock:
            self._expire()
            return self.runs[run_id][1][name] if run_id in self.runs else None

    def server_close(self):
        super().server_close()
        with self.runs_lock:
            self.runs.clear()


class FCTHandler(BaseHTTPRequestHandler):
    server_version = f"FinancialControlTower/{__version__}"
    sys_version = ""

    def setup(self):
        super().setup()
        self.connection.settimeout(20)

    def log_message(self, format, *args):
        # Selected data, filenames, query strings and tokens are never logged.
        return

    def _send(self, status, content, mime="application/json; charset=utf-8", *, download=None):
        if not isinstance(content, bytes):
            content = json.dumps(content, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
        )
        if download:
            self.send_header("Content-Disposition", f'attachment; filename="{download}"')
        self.end_headers()
        if self.command != "HEAD":
            with suppress(BrokenPipeError, ConnectionResetError):
                self.wfile.write(content)

    def _local(self):
        authorities = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        hosts, origins = self.headers.get_all("Host", []), self.headers.get_all("Origin", [])
        if len(hosts) != 1 or hosts[0] not in authorities:
            self._send(403, {"error": "请使用启动时显示的本机地址打开工具。"})
            return False
        if (
            len(origins) > 1
            or (origins and origins[0] not in {f"http://{value}" for value in authorities})
            or self.headers.get("Sec-Fetch-Site") == "cross-site"
        ):
            self._send(403, {"error": "本机工具不接受外部网页的跨来源请求。"})
            return False
        return True

    def do_GET(self):
        if not self._local():
            return
        path = self.path.partition("?")[0]
        if path == "/api/config":
            self._send(
                200,
                {
                    "version": __version__,
                    "csrf_token": self.server.csrf_token,
                    "max_file_bytes": MAX_BYTES,
                    "cached_runs": MAX_CACHED_RUNS,
                    "cache_seconds": CACHE_SECONDS,
                },
            )
        elif path == "/api/example":
            self._send(200, example_request())
        elif path in ASSETS:
            name, mime = ASSETS[path]
            try:
                content = Path(__file__).with_name("static").joinpath(name).read_bytes()
            except OSError:
                self._send(500, {"error": "已安装界面不完整，请重新安装工具。"})
                return
            self._send(200, content, mime)
        elif match := re.fullmatch(r"/api/runs/([a-f0-9]{32})/([a-z.]+)", path):
            run_id, kind = match.groups()
            if kind not in DOWNLOADS:
                self._send(404, {"error": "没有这个报告文件。"})
                return
            name, mime = DOWNLOADS[kind]
            content = self.server.read_run(run_id, name)
            if content is None:
                self._send(410, {"error": "临时结果已过期，请重新比较，再下载保存。"})
                return
            self._send(200, content, mime, download=f"fct-comparison-{run_id[:12]}.zip" if kind == "zip" else None)
        elif path == "/favicon.ico":
            self._send(204, b"", "image/x-icon")
        else:
            self._send(404, {"error": "本机工具不提供该路径。"})

    def do_HEAD(self):
        self.do_GET()

    def do_OPTIONS(self):
        self._send(403, {"error": "不提供跨来源访问。"})

    def do_POST(self):
        if not self._local():
            return
        tokens = self.headers.get_all("X-FCT-Token", [])
        if len(tokens) != 1 or not hmac.compare_digest(tokens[0].encode(), self.server.csrf_token.encode()):
            self._send(403, {"error": "请刷新本机工具后重试。"})
            return
        lengths = self.headers.get_all("Content-Length", [])
        if self.headers.get("Transfer-Encoding") or len(lengths) != 1:
            self._send(400, {"error": "请求必须包含一个明确的内容长度。"})
            return
        try:
            length = int(lengths[0])
        except ValueError:
            length = -1
        if not 0 < length <= MAX_REQUEST:
            self._send(413, {"error": "请求超过 70 MiB；每份原文件最多 25 MiB。"})
            return
        if self.headers.get_content_type() != "application/json":
            self._send(415, {"error": "请从本机页面提交 JSON 设置。"})
            return
        path = self.path.partition("?")[0]
        if path not in {"/api/inspect", "/api/compare"}:
            self._send(404, {"error": "没有这个操作。"})
            return
        if not self.server.work_slots.acquire(blocking=False):
            self._send(429, {"error": "已有两个文件任务正在运行，请等待完成。"})
            return
        try:
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError("文件传输未完成，请重新选择文件。")
            payload = load_request(raw)
            if path == "/api/inspect":
                self._send(200, inspect_file(payload))
            else:
                result, files = build_comparison(payload)
                run_id = self.server.store_run(files)
                self._send(
                    200,
                    {
                        "run_id": run_id,
                        "result": result,
                        "downloads": {"report": f"/api/runs/{run_id}/report", "zip": f"/api/runs/{run_id}/zip"},
                    },
                )
        except INPUT_ERRORS as exc:
            self._send(400, {"error": str(exc)})
        except Exception:
            # Keep internal paths and input values out of an unexpected-error response.
            self._send(500, {"error": "本次检查未完成，也未发布结果。请检查输入或重新启动工具。"})
        finally:
            self.server.work_slots.release()


def main(argv=None):
    parser = argparse.ArgumentParser(description="在本机浏览器选择 CSV / Excel 并完成两表比较。")
    parser.add_argument("--port", type=int, default=8767, help="本机端口；测试时可用 0 自动选择")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error("端口必须在 0 至 65535 之间。")
    try:
        server = FCTServer(args.port)
    except OSError:
        print("本机端口无法使用，请关闭旧实例或用 --port 指定另一端口。", file=sys.stderr)
        return 2
    print(f"FCT_URL={server.url}", flush=True)
    print("文件仅在本机处理。关闭后清除临时会话；需要保留的结果请下载证据包。", flush=True)
    if not args.no_browser:
        webbrowser.open(server.url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
