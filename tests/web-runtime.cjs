/* Executes the shipped engine ZIP in the pinned WebAssembly runtime, without networking. */
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const {execFileSync} = require("node:child_process");
const {loadPyodide} = require("pyodide");
(async () => {
  const root = path.resolve(__dirname, ".."), dist = path.join(root, "out");
  const output = fs.mkdtempSync(path.join(os.tmpdir(), "fct-web-runtime-"));
  const python = process.env.TEST_PYTHON || "python3";
  const fixture = path.join(__dirname, "make_ui_fixtures.py");
  execFileSync(python, [fixture, output]);
  const expected = JSON.parse(fs.readFileSync(path.join(output, "fixture-expectations.json"), "utf8"));
  const build = JSON.parse(fs.readFileSync(path.join(dist, "browser-build.json"), "utf8"));
  const bytes = name => new Uint8Array(fs.readFileSync(path.join(dist, name)));
  for (const [name, item] of Object.entries(build.assets)) assert.equal(crypto.createHash("sha256").update(bytes(name)).digest("hex"), item.sha256);
  const py = await loadPyodide({indexURL: path.join(root, "node_modules/pyodide/")});
  const site = py.runPython("import site; site.getsitepackages()[0]");
  for (const wheel of build.wheels) py.unpackArchive(bytes(wheel.path.slice(1)), "zip", {extractDir: site});
  py.unpackArchive(bytes("engine.zip"), "zip", {extractDir: "/app"});
  py.FS.writeFile("/app/browser-build.json", JSON.stringify(build));
  py.runPython("import sys; sys.path.insert(0, '/app'); import browser_runtime");
  let networkAttempts = 0;
  globalThis.fetch = () => { networkAttempts++; throw new Error("Networking forbidden while processing inputs"); };
  const proxy = py.globals.get("browser_runtime");
  let prior;
  for (const scenario of ["currency", "unit"]) {
    const wanted = expected[scenario];
    const payload = {absolute_tolerance: wanted.absolute_tolerance, relative_tolerance: wanted.relative_tolerance, common_unit: wanted.common_unit};
    for (const side of ["left", "right"]) {
      const {name, ...definition} = wanted[side];
      const file = {name, content_base64: fs.readFileSync(path.join(output, name)).toString("base64")};
      const meta = JSON.parse(proxy.dispatch("/api/inspect", JSON.stringify({file, sheet: definition.sheet, header_row: definition.header_row})));
      assert.equal(meta.sha256, expected.input_sha256[name]);
      payload[side] = {file, ...definition};
    }
    const result = JSON.parse(proxy.dispatch("/api/compare", JSON.stringify(payload)));
    const resultPath = path.join(output, scenario + "-result.json");
    fs.writeFileSync(resultPath, JSON.stringify(result.result));
    execFileSync(python, [fixture, "--verify-result", resultPath, "--expectations", path.join(output, "fixture-expectations.json"), "--scenario", scenario]);
    if (prior) assert.throws(() => proxy.download(prior, "zip"), /失效/);
    prior = result.run_id;
    for (const kind of ["zip", "report", "differences.csv"]) {
      const content = proxy.download(result.run_id, kind);
      try { fs.writeFileSync(path.join(output, scenario + "-" + kind), content.toJs()); } finally { content.destroy(); }
    }
    py.globals.set("active_id", result.run_id);
    py.runPython(`
import hashlib, io, json
from zipfile import ZipFile
with ZipFile(io.BytesIO(browser_runtime.download(active_id, 'zip'))) as z:
    assert len(z.namelist()) == 8
    manifest = json.loads(z.read('manifest.json'))
    assert 'browser-build.json' in manifest['sha256']
    assert all(hashlib.sha256(z.read(k)).hexdigest() == v for k, v in manifest['sha256'].items())
    assert z.read('report.html') == browser_runtime.download(active_id, 'report')
    assert z.read('differences.csv') == browser_runtime.download(active_id, 'differences.csv')
`);
  }
  proxy.dispatch("discard", "null");
  assert.throws(() => proxy.download(prior, "zip"), /失效/);
  assert.throws(() => proxy.dispatch("/api/inspect", JSON.stringify({file: {name: "large.csv", content_base64: "A".repeat(12 * 1024 * 1024)}})), /8 MiB/);
  py.runPython(`
from pathlib import Path
from financial_control_tower.table_compare import _publish_new
Path('/tmp/publish-stage').mkdir()
Path('/tmp/existing-destination').mkdir()
try:
    _publish_new(Path('/tmp/publish-stage'), Path('/tmp/existing-destination'))
except FileExistsError:
    pass
else:
    raise AssertionError('Existing destination overwritten')
assert Path('/tmp/publish-stage').exists()
`);
  proxy.destroy();
  assert.equal(networkAttempts, 0);
  console.log(JSON.stringify({status: "pass", runtime: py.version, exactCurrencyRecords: 28, exactUnitRecords: 4, zipMembers: 8, allHashesValid: true, retiredDownloadsRejected: true, oversizedFileRejected: true, noReplace: true, networkAttempts, output}));
})().catch(error => { console.error(error); process.exitCode = 1; });
