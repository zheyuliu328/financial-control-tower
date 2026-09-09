/* End-to-end public-page acceptance: static host, real files, Worker, downloads and no upload requests. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const {spawn, execFileSync} = require("node:child_process");
const {chromium} = require("playwright");
(async () => {
  const root = path.resolve(__dirname, ".."), python = process.env.TEST_PYTHON || "python3";
  const output = process.env.WEB_TEST_OUTPUT ? path.resolve(process.env.WEB_TEST_OUTPUT) : fs.mkdtempSync(path.join(os.tmpdir(), "fct-public-ui-"));
  fs.mkdirSync(output, {recursive: true});
  const fixture = path.join(__dirname, "make_ui_fixtures.py");
  execFileSync(python, [fixture, output]);
  const expectedPath = path.join(output, "fixture-expectations.json");
  const expected = JSON.parse(fs.readFileSync(expectedPath, "utf8"));
  let server, browser, page;
  const requests = [], errors = [];
  try {
    server = spawn(python, ["-u", "-m", "http.server", "0", "--bind", "127.0.0.1", "--directory", path.join(root, "out")]);
    const base = await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("Static server did not start")), 15000);
      server.on("error", reject);
      server.stdout.on("data", chunk => { const match = String(chunk).match(/port (\d+)/); if (match) { clearTimeout(timer); resolve("http://127.0.0.1:" + match[1]); } });
    });
    browser = await chromium.launch();
    const context = await browser.newContext({viewport: {width: 1440, height: 1000}, acceptDownloads: true});
    context.on("request", request => requests.push({url: request.url(), method: request.method()}));
    page = await context.newPage(); page.setDefaultTimeout(30000);
    page.on("pageerror", error => errors.push(error.message));
    await page.goto(base);
    assert(await page.locator("#files-stage").isVisible());
    assert.equal(await page.locator("#mapping-stage").isVisible(), false);
    assert.equal(await page.locator("#left-sheet").count(), 0);
    await page.locator("#load-example").click();
    await page.locator("#comparison-results").waitFor({state: "visible"});
    assert.equal(await page.locator("#count-total").innerText(), "14");
    assert.equal(await page.locator("#status-filter").inputValue(), "attention");
    assert(await page.locator("#example-guide").isVisible());
    await page.locator("#use-own-files").click();
    assert(await page.locator("#files-stage").isVisible());
    assert.equal(await page.locator("#comparison-results").isVisible(), false);
    await page.locator("#left-file").setInputFiles(path.join(output, expected.currency.left.name));
    await page.locator("#left-details").waitFor({state: "visible"});
    await page.locator("#right-file").setInputFiles(path.join(output, expected.currency.right.name));
    await page.locator("#right-sheet").selectOption(expected.currency.right.sheet);
    await page.locator("#right-read-options[open]").waitFor({state: "visible"});
    await page.locator("#right-header-row").fill("3");
    await page.locator("#right-header-row").press("Tab");
    await page.waitForFunction(() => !document.querySelector("#files-next").disabled);
    await page.locator("#files-next").click();
    await page.locator("#add-key").click(); await page.locator("#add-value").click();
    for (const side of ["left", "right"]) {
      for (let index = 0; index < 2; index++) {
        await page.locator(`#key-${side}-${index}`).selectOption(expected.currency[side].keys[index]);
        await page.locator(`#value-${side}-${index}`).selectOption(expected.currency[side].values[index]);
      }
      await page.locator(`#${side}-currency`).selectOption(expected.currency[side].currency);
    }
    await page.locator("#tolerance-options > summary").click();
    await page.locator("#absolute-tolerance").fill("0.05");
    await page.locator("#relative-tolerance").fill("0.001");
    await page.locator("#run-compare").click();
    await page.locator("#comparison-results").waitFor({state: "visible"});
    assert.equal(await page.locator("#count-total").innerText(), "28");
    assert.equal(await page.locator("#count-different").innerText(), "2");
    const downloaded = {};
    for (const [id, name] of [["download-csv", "differences.csv"], ["download-report", "report.html"], ["download-zip", "result.zip"]]) {
      const waiting = page.waitForEvent("download");
      await page.locator("#" + id).click();
      const download = await waiting;
      await download.saveAs(path.join(output, name));
      assert.equal(await download.failure(), null); downloaded[name] = true;
    }
    execFileSync(python, ["-c", `
import hashlib,json,sys,zipfile
from pathlib import Path
p=Path(sys.argv[1])
with zipfile.ZipFile(p/'result.zip') as z:
 m=json.loads(z.read('manifest.json'))
 assert len(z.namelist())==8
 assert all(hashlib.sha256(z.read(k)).hexdigest()==v for k,v in m['sha256'].items())
 for name in ['differences.csv','report.html']:
  assert z.read(name)==(p/name).read_bytes()
 for side,name in [('left','book-export.csv'),('right','posted-review.xlsx')]:
  assert z.read('sources/'+side+Path(name).suffix)==(p/name).read_bytes()
 (p/'result.json').write_bytes(z.read('comparison.json'))
`, output]);
    execFileSync(python, [fixture, "--verify-result", path.join(output, "result.json"), "--expectations", expectedPath, "--scenario", "currency"]);
    await page.locator("#step-results").click();
    await page.screenshot({path: path.join(output, "public-results-desktop.png"), fullPage: true});
    await page.setViewportSize({width: 390, height: 844});
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), "Mobile document overflows");
    await page.screenshot({path: path.join(output, "public-results-mobile.png"), fullPage: true});
    await page.locator("#edit-comparison").click();
    await page.locator("#absolute-tolerance").fill("0");
    assert(await page.locator("#download-zip").isDisabled());
    await page.reload();
    assert(await page.locator("#files-stage").isVisible());
    await page.screenshot({path: path.join(output, "public-start-mobile.png"), fullPage: true});
    assert(requests.filter(request => !request.url.startsWith("blob:")).every(request => request.method === "GET" && request.url.startsWith(base + "/") && !request.url.includes("/api/")), JSON.stringify(requests));
    assert.deepEqual(errors, []);
    fs.writeFileSync(path.join(output, "public-ui-result.json"), JSON.stringify({status: "pass", downloaded, records: 28, inputUploads: 0, externalRequests: 0, requests, errors, mobileOverflow: false, humanTrial: "not performed"}, null, 2));
    console.log("PUBLIC_UI_PASS " + output);
  } catch (error) {
    if (page) await page.screenshot({path: path.join(output, "failure.png"), fullPage: true}).catch(() => {});
    fs.writeFileSync(path.join(output, "failure.json"), JSON.stringify({message: error.message, requests, errors}, null, 2)); throw error;
  } finally { if (browser) await browser.close(); if (server) server.kill("SIGTERM"); }
})().catch(error => { console.error(error); process.exitCode = 1; });
