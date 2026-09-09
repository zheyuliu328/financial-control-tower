"use strict";
(() => {
  let worker = null, serial = 0;
  const pending = new Map();
  const notify = (active, message = "") => window.dispatchEvent(new CustomEvent("fct-runtime-progress", {detail: {active, message}}));
  function cancel(message = "已取消。文件仍在页面上，可重新读取或开始核对。") {
    if (worker) worker.terminate();
    worker = null;
    for (const item of pending.values()) { clearTimeout(item.timer); item.reject(new Error(message)); }
    pending.clear(); notify(false);
    window.dispatchEvent(new CustomEvent("fct-runtime-reset"));
  }
  function ensureWorker() {
    if (worker) return;
    if (!window.Worker || !window.WebAssembly || !window.crypto?.subtle) throw new Error("此浏览器不支持本地计算，请使用较新的 Safari、Chrome、Edge 或 Firefox。");
    worker = new Worker("/worker.mjs", {type: "module", name: "table-check-local"});
    const current = worker;
    worker.onmessage = ({data}) => {
      if (worker !== current) return;
      if (data.type === "progress") { notify(true, data.message); return; }
      const item = pending.get(data.id);
      if (!item) return;
      pending.delete(data.id); clearTimeout(item.timer);
      if (!pending.size) notify(false);
      if (data.error) item.reject(new Error(data.error));
      else item.resolve(data.bytes ? {bytes: data.bytes} : data.result);
    };
    worker.onerror = () => { if (worker === current) cancel("计算组件未能运行。请刷新网页，或换用较小的文件重试。"); };
  }
  function call(action, payload) {
    return new Promise((resolve, reject) => {
      try { ensureWorker(); } catch (error) { reject(error); return; }
      const id = ++serial;
      const timer = setTimeout(() => cancel("本次处理超过 2 分钟，已停止。请缩小文件范围后重试。"), 120000);
      pending.set(id, {resolve, reject, timer});
      notify(true, "正在准备处理…"); worker.postMessage({id, action, payload});
    });
  }
  window.FctBrowser = {
    request(url, payload) {
      if (url === "/api/config") return Promise.resolve({max_file_bytes: 8 * 1024 * 1024, version: "2.3.0 · 网页版"});
      if (!["/api/example", "/api/inspect", "/api/compare"].includes(url)) return Promise.reject(new Error("未支持的操作。"));
      return call(url, payload);
    },
    async file(run_id, kind) {
      const formats = {report: ["表格对账-报告.html", "text/html;charset=utf-8"], zip: ["表格对账-结果与原表.zip", "application/zip"], "differences.csv": ["表格对账-差异表.csv", "text/csv;charset=utf-8"]};
      if (!formats[kind]) throw new Error("未支持的下载类型。");
      return {...await call("download", {run_id, kind}), name: formats[kind][0], mime: formats[kind][1]};
    },
    discard() { if (worker) call("discard", null).catch(() => {}); },
    cancel: () => cancel(),
  };
  window.addEventListener("pagehide", () => cancel("页面已关闭。"));
})();
