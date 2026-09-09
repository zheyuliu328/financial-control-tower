import {loadPyodide} from "/runtime/pyodide.mjs";

let runtime;
let queue = Promise.resolve();
const progress = message => self.postMessage({type: "progress", message});
async function checkedAsset(path, expected) {
  const response = await fetch(new URL(path, self.location.origin));
  if (!response.ok) throw new Error("工具文件未能下载，请检查网络后重试。");
  const bytes = new Uint8Array(await response.arrayBuffer());
  const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", bytes));
  const actual = Array.from(digest, byte => byte.toString(16).padStart(2, "0")).join("");
  if (actual !== expected) throw new Error("工具文件版本不一致，请刷新网页后重试。");
  return bytes;
}
async function initialize() {
  progress("首次使用正在下载计算组件（约 14 MB），文件仍留在此浏览器中…");
  const response = await fetch("/browser-build.json", {cache: "no-cache"});
  if (!response.ok) throw new Error("无法读取工具版本，请刷新后重试。");
  const build = await response.json();
  const py = await loadPyodide({indexURL: new URL("/runtime/", self.location.origin).href});
  const sitePackages = py.runPython("import site; site.getsitepackages()[0]");
  for (const wheel of build.wheels) {
    const bytes = await checkedAsset(wheel.path, wheel.sha256);
    py.unpackArchive(bytes, "zip", {extractDir: sitePackages});
  }
  const engine = await checkedAsset("/engine.zip", build.assets["engine.zip"].sha256);
  py.unpackArchive(engine, "zip", {extractDir: "/app"});
  py.FS.writeFile("/app/browser-build.json", JSON.stringify(build));
  py.runPython("import sys; sys.path.insert(0, '/app'); import browser_runtime");
  return py;
}
self.onmessage = event => {
  const {id, action, payload} = event.data;
  queue = queue.then(async () => {
    try {
      runtime ||= initialize().catch(error => { runtime = null; throw error; });
      const py = await runtime;
      progress(action === "/api/compare" ? "正在逐项核对…" : action === "download" ? "正在准备下载…" : "正在读取表格…");
      if (action === "download") {
        const proxy = py.globals.get("browser_runtime");
        let bytes;
        try { const value = proxy.download(payload.run_id, payload.kind); try { bytes = value.toJs(); } finally { value.destroy(); } }
        finally { proxy.destroy(); }
        self.postMessage({id, bytes}, [bytes.buffer]);
      } else {
        const proxy = py.globals.get("browser_runtime");
        let result;
        try { result = proxy.dispatch(action, JSON.stringify(payload ?? null)); } finally { proxy.destroy(); }
        self.postMessage({id, result: JSON.parse(result)});
      }
    } catch (error) {
      const lines = String(error.message || error).trim().split("\n");
      const detail = lines.at(-1).replace(/^(ValueError|OSError|RuntimeError|Error):\s*/, "");
      self.postMessage({id, error: detail || "无法完成本次操作，请尝试较小的文件。"});
    }
  });
};
