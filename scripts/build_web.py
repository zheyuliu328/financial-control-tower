"""Build a deterministic static, self-hosted browser app; no runtime CDN or upload API."""

import hashlib
import io
import json
import shutil
import urllib.request
from pathlib import Path
from tempfile import gettempdir
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "out"
PACKAGE = ROOT / "src/financial_control_tower"
RUNTIME = ROOT / "node_modules/pyodide"
PYODIDE_VERSION = "314.0.6"
STATIC_FILES = ["app.js", "suggestions.js", "styles.css"]
PACKAGE_FILES = [
    "__init__.py",
    "engine.py",
    "rules.py",
    "sample.py",
    "cli.py",
    "table_cli.py",
    "table_compare.py",
    "table_workspace.py",
    "table_ui.py",
]
RUNTIME_FILES = ["pyodide.mjs", "pyodide.asm.mjs", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"]


def sha(content):
    return hashlib.sha256(content).hexdigest()


def build():
    if json.loads((RUNTIME / "package.json").read_text())["version"] != PYODIDE_VERSION:
        raise ValueError("Run npm ci to install the pinned browser runtime.")
    wheels = json.loads((ROOT / "web/wheels.lock.json").read_text())
    allowed = {
        "index.html",
        "browser.js",
        "worker.mjs",
        "engine.zip",
        "browser-build.json",
        "THIRD_PARTY_NOTICES.txt",
        "LICENSE",
    }
    allowed.update("static/" + name for name in STATIC_FILES)
    allowed.update("runtime/" + name for name in RUNTIME_FILES)
    allowed.update("runtime/" + wheel["filename"] for wheel in wheels)
    for path in OUTPUT.rglob("*"):
        if path.is_symlink() or (path.is_file() and str(path.relative_to(OUTPUT)) not in allowed):
            raise ValueError(f"Unexpected existing build output; refusing to package: {path}")
    OUTPUT.mkdir(exist_ok=True)
    (OUTPUT / "static").mkdir(exist_ok=True)
    (OUTPUT / "runtime").mkdir(exist_ok=True)
    # Copy an explicit allowlist; never package local inputs, reports, or environment files.
    for name in STATIC_FILES:
        shutil.copyfile(PACKAGE / "static" / name, OUTPUT / "static" / name)
    html = (PACKAGE / "static/index.html").read_text()
    html = html.replace(
        '<script src="/static/app.js"', '<script src="/browser.js" defer></script>\n  <script src="/static/app.js"'
    )
    html = html.replace("本机处理", "浏览器内处理").replace("正在连接本机工作区…", "正在准备工作区…")
    html = html.replace("文件只在浏览器内处理，原件保持不变。", "文件只在此浏览器中处理，不会上传到服务器。")
    html = html.replace(
        "结果最多临时保留 3 次、总计约 128 MiB、最长 60 分钟；服务重启即清空。",
        "只保留当前结果，刷新或关闭页面即清空。ZIP 包含所选原始文件的完整副本。",
    )
    html = html.replace("文件只在本机处理，原件保持不变。", "文件只在此浏览器中处理，不会上传到服务器。")
    html = html.replace('查看报告 <span aria-hidden="true">↗</span>', "下载报告（HTML）")
    html = html.replace(
        '<meta name="color-scheme" content="light">',
        "<meta name=\"color-scheme\" content=\"light\">\n  <meta name=\"description\" content=\"免费在线核对两份 CSV 或 Excel，查找数值差异、遗漏与重复记录。文件在浏览器中处理，无需注册或安装。\">\n  <meta name=\"referrer\" content=\"no-referrer\">\n  <meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self'; worker-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'self'; form-action 'none'\">",
    )
    html = html.replace(
        "</footer>", '<a href="/THIRD_PARTY_NOTICES.txt" target="_blank" rel="noopener">开源许可</a></footer>'
    )
    (OUTPUT / "index.html").write_text(html)
    shutil.copyfile(ROOT / "web/THIRD_PARTY_NOTICES.txt", OUTPUT / "THIRD_PARTY_NOTICES.txt")
    shutil.copyfile(ROOT / "LICENSE", OUTPUT / "LICENSE")
    for name in ("browser.js", "worker.mjs"):
        shutil.copyfile(ROOT / "web" / name, OUTPUT / name)
    for name in RUNTIME_FILES:
        shutil.copyfile(RUNTIME / name, OUTPUT / "runtime" / name)
    wheels = json.loads((ROOT / "web/wheels.lock.json").read_text())
    cache = Path(gettempdir()) / "fct-web-wheels"
    cache.mkdir(exist_ok=True)
    for wheel in wheels:
        cached = cache / wheel["filename"]
        if not cached.exists() or sha(cached.read_bytes()) != wheel["sha256"]:
            with urllib.request.urlopen(wheel["url"], timeout=60) as response:
                content = response.read()
            if sha(content) != wheel["sha256"]:
                raise ValueError(f"Wheel hash mismatch: {wheel['filename']}")
            cached.write_bytes(content)
        shutil.copyfile(cached, OUTPUT / "runtime" / wheel["filename"])
        wheel["path"] = "/runtime/" + wheel["filename"]
    engine = io.BytesIO()
    with ZipFile(engine, "w", compression=ZIP_DEFLATED) as archive:
        source = [(PACKAGE / name, "financial_control_tower/" + name) for name in PACKAGE_FILES]
        source += [
            (PACKAGE / "static" / name, "financial_control_tower/static/" + name)
            for name in ["index.html", *STATIC_FILES]
        ]
        source += [(ROOT / "web/browser-runtime.py", "browser_runtime.py")]
        for path, name in source:
            info = ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    (OUTPUT / "engine.zip").write_bytes(engine.getvalue())
    assets = {}
    for path in sorted(OUTPUT.rglob("*")):
        if path.is_file() and path.name != "browser-build.json":
            data = path.read_bytes()
            assets[str(path.relative_to(OUTPUT))] = {"sha256": sha(data), "bytes": len(data)}
    metadata = {
        "schema_version": 1,
        "pyodide_version": PYODIDE_VERSION,
        "file_processing": "browser-local Worker memory; no input upload endpoint",
        "wheels": wheels,
        "assets": assets,
    }
    (OUTPUT / "browser-build.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "directory": str(OUTPUT),
                "files": len(assets) + 1,
                "bytes": sum(a["bytes"] for a in assets.values()),
                "pyodide": PYODIDE_VERSION,
            }
        )
    )


if __name__ == "__main__":
    build()
