/* Independent real-file acceptance of the normally installed, offline FCT UI. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const crypto = require("node:crypto");
const {pathToFileURL} = require("node:url");
const {spawn, execFileSync} = require("node:child_process");
const {chromium} = require("playwright");

(async () => {
  const requested = process.env.BROWSER_TEST_OUTPUT && path.resolve(process.env.BROWSER_TEST_OUTPUT);
  let output;
  if (!requested) output = fs.mkdtempSync(path.join(os.tmpdir(), "fct-browser-ui-"));
  else if (fs.existsSync(requested) && fs.readdirSync(requested).length) output = fs.mkdtempSync(requested + "-");
  else { output = requested; fs.mkdirSync(output, {recursive: true}); }
  const python = process.env.TEST_PYTHON || "python3";
  const fixtureScript = path.join(__dirname, "make_ui_fixtures.py");
  execFileSync(python, [fixtureScript, output], {encoding: "utf8"});
  const expectationPath = path.join(output, "fixture-expectations.json");
  const expected = JSON.parse(fs.readFileSync(expectationPath, "utf8"));
  const hash = file => crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
  const inputHashes = Object.fromEntries(expected.files.map(name => [name, hash(path.join(output, name))]));
  assert.deepEqual(inputHashes, expected.input_sha256);
  const runtime = {...process.env, PYTHONUNBUFFERED: "1"};
  delete runtime.PYTHONPATH; delete runtime.PYTHONHOME;
  const packageOrigin = execFileSync(python, ["-c", "import importlib.util; spec = importlib.util.find_spec('financial_control_tower'); assert spec and spec.origin, 'Install the normal FCT wheel in TEST_PYTHON'; print(spec.origin)"], {cwd: output, env: runtime, encoding: "utf8"}).trim();
  const installedPackageRoot = fs.realpathSync(path.dirname(packageOrigin));
  assert(/(?:site|dist)-packages/.test(installedPackageRoot), "TEST_PYTHON must import a normal installation, not an editable checkout");
  const binary = process.env.FCT_UI_BIN || "fct-ui";
  let server, browser, page, routeGate, releaseGate;
  let serverText = "", serverErrors = "";
  const externalRequests = [], pageErrors = [], apiFailures = [], apiRequests = [], inspectionCorrections = [];
  const downloads = [], screenshots = [];
  try {
    // The installed entry point is launched outside the checkout, with no source-path injection.
    server = spawn(binary, ["--port", "0", "--no-browser"], {cwd: output, env: runtime});
    server.stderr.on("data", data => { serverErrors += data.toString(); });
    const base = await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("Installed fct-ui did not announce a loopback URL")), 20000);
      server.once("error", error => { clearTimeout(timer); reject(error); });
      server.stdout.on("data", data => {
        serverText += data.toString();
        const match = serverText.match(/FCT_URL=(http:\/\/127\.0\.0\.1:\d+)/);
        if (match) { clearTimeout(timer); resolve(match[1]); }
      });
      server.once("exit", code => { clearTimeout(timer); reject(new Error(`Installed fct-ui exited (${code}): ${serverErrors}`)); });
    });
    assert.equal(new URL(base).hostname, "127.0.0.1");
    browser = await chromium.launch({headless: true, ...(process.env.TEST_CHROME_PATH ? {executablePath: process.env.TEST_CHROME_PATH} : {})});
    const context = await browser.newContext({viewport: {width: 1440, height: 1000}, acceptDownloads: true});
    await context.route("**/*", async route => {
      const url = route.request().url();
      if (!url.startsWith(base + "/") && !url.startsWith("blob:")) {
        externalRequests.push(url); return route.abort();
      }
      if (routeGate && new URL(url).pathname === routeGate.endpoint) await routeGate.promise;
      return route.continue();
    });
    context.on("page", opened => opened.on("pageerror", error => pageErrors.push(error.message)));
    context.on("request", request => {
      if (request.url().startsWith(base + "/api/")) apiRequests.push({method: request.method(), path: new URL(request.url()).pathname});
    });
    context.on("response", response => {
      if (response.url().startsWith(base + "/api/") && response.status() >= 400) apiFailures.push({path: new URL(response.url()).pathname, status: response.status()});
    });
    page = await context.newPage();
    page.setDefaultTimeout(20000);
    const configResponse = page.waitForResponse(response => response.url() === base + "/api/config");
    await page.goto(base + "/");
    const config = await (await configResponse).json();
    assert(config.version && config.csrf_token && config.max_file_bytes > 0);

    async function ready(selector) {
      await page.waitForFunction(selector => {
        const element = document.querySelector(selector);
        return element && !element.disabled && !element.closest("fieldset:disabled");
      }, selector);
    }
    async function post(endpoint, action, permitHeaderCorrection = false) {
      const waiting = page.waitForResponse(response => response.url() === base + endpoint && response.request().method() === "POST");
      await action();
      const response = await waiting;
      const data = await response.json();
      if (permitHeaderCorrection && response.status() === 400) {
        inspectionCorrections.push({endpoint, error: data.error});
      } else assert.equal(response.status(), 200, JSON.stringify(data));
      return data;
    }
    async function upload(side, definition) {
      let inspected = await post("/api/inspect", () => page.locator(`#${side}-file`).setInputFiles(path.join(output, definition.name)), true);
      if (definition.sheet) {
        await ready(`#${side}-sheet`);
        inspected = await post("/api/inspect", () => page.locator(`#${side}-sheet`).selectOption(definition.sheet), true);
      }
      await ready(`#${side}-header-row`);
      if (await page.locator(`#${side}-header-row`).inputValue() !== String(definition.header_row)) {
        await page.locator(`#${side}-header-row`).fill(String(definition.header_row));
        inspected = await post("/api/inspect", () => page.locator(`#${side}-header-row`).press("Tab"));
      }
      await ready(`#${side}-header-row`);
      assert.equal(inspected.sha256, expected.input_sha256[definition.name]);
      assert.equal(inspected.header_row, definition.header_row);
      assert.equal(inspected.sheet, definition.sheet);
      for (const column of [...definition.keys, ...definition.values]) assert(inspected.headers.includes(column));
    }
    async function mappings(scenario) {
      const wanted = expected[scenario];
      while (await page.locator('[id^="key-left-"]').count() < 2) await page.locator("#add-key").click();
      while (await page.locator('[id^="value-left-"]').count() < 2) await page.locator("#add-value").click();
      for (const side of ["left", "right"]) {
        for (let index = 0; index < 2; index += 1) {
          await ready(`#key-${side}-${index}`);
          await page.locator(`#key-${side}-${index}`).selectOption(wanted[side].keys[index]);
          await page.locator(`#value-${side}-${index}`).selectOption(wanted[side].values[index]);
        }
      }
      if (wanted.common_unit) {
        await page.locator("#unit-mode-common").check();
        await page.locator("#common-unit").fill(wanted.common_unit);
      } else {
        await page.locator("#unit-mode-currency").check();
        await page.locator("#left-currency").selectOption(wanted.left.currency);
        await page.locator("#right-currency").selectOption(wanted.right.currency);
      }
      await page.locator("#absolute-tolerance").fill(wanted.absolute_tolerance);
      await page.locator("#relative-tolerance").fill(wanted.relative_tolerance);
    }
    async function capture(target, name, mobile = false) {
      const size = mobile ? {width: 390, height: 844} : {width: 1440, height: 1000};
      await target.setViewportSize(size);
      await target.waitForTimeout(120);
      assert(await target.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), `${name}: document-level horizontal overflow`);
      await target.screenshot({path: path.join(output, name + ".png"), fullPage: true});
      screenshots.push({name: name + ".png", viewport: size, documentOverflow: false});
    }
    function verifyResult(result, scenario, suffix = "") {
      const filename = path.join(output, scenario + suffix + "-result.json");
      fs.writeFileSync(filename, JSON.stringify(result, null, 2) + "\n");
      return JSON.parse(execFileSync(python, [fixtureScript, "--verify-result", filename, "--expectations", expectationPath, "--scenario", scenario], {encoding: "utf8"}));
    }
    async function compare(scenario, suffix = "") {
      const response = await post("/api/compare", () => page.locator("#run-compare").click());
      assert(response.run_id && response.result && response.downloads.report && response.downloads.zip);
      verifyResult(response.result, scenario, suffix);
      await page.locator("#comparison-results").waitFor({state: "visible"});
      await ready("#download-zip"); await ready("#download-report");
      return response;
    }
    async function visibleRows(count) {
      await page.waitForFunction(count => document.querySelectorAll("#results-table tbody tr").length === count, count);
    }
    async function retired() {
      await page.locator("#stale-results").waitFor({state: "visible"});
      assert(await page.locator("#download-report").isDisabled());
      assert(await page.locator("#download-zip").isDisabled());
    }
    async function exportRun(response, scenario) {
      const reportURL = new URL(response.downloads.report, base).href;
      const reportResponse = context.waitForEvent("response", {predicate: reply => reply.url() === reportURL && reply.request().isNavigationRequest()});
      const popupWaiting = page.waitForEvent("popup");
      await page.locator("#download-report").click();
      const popup = await popupWaiting;
      await popup.waitForURL(reportURL);
      const rawReport = await (await reportResponse).body();
      await popup.waitForLoadState("domcontentloaded");
      fs.writeFileSync(path.join(output, scenario + "-viewed-report.html"), rawReport);
      assert((await popup.locator("body").innerText()).includes("Row coverage"));
      await capture(popup, scenario + "-report-desktop");
      await capture(popup, scenario + "-report-mobile", true);
      await popup.close();
      const waiting = page.waitForEvent("download");
      await page.locator("#download-zip").click();
      const item = await waiting;
      const zip = path.join(output, scenario + "-evidence.zip");
      await item.saveAs(zip);
      assert.equal(await item.failure(), null);
      const extract = path.join(output, scenario + "-offline");
      const proof = JSON.parse(execFileSync(python, [fixtureScript, "--verify-zip", zip, "--expectations", expectationPath, "--scenario", scenario, "--extract", extract, "--source-root", installedPackageRoot], {encoding: "utf8"}));
      assert(rawReport.equals(fs.readFileSync(path.join(extract, "report.html"))), "Viewed report must be the same report included in the ZIP");
      downloads.push(proof);
      return extract;
    }

    await upload("left", expected.currency.left);
    await upload("right", expected.currency.right);
    await mappings("currency");
    await capture(page, "currency-inputs-desktop");
    await capture(page, "currency-inputs-mobile", true);
    await page.setViewportSize({width: 1440, height: 1000});
    const currency = await compare("currency");
    // Re-inspecting unchanged inputs keeps the result but temporarily disables exports.
    routeGate = {endpoint: "/api/inspect", promise: new Promise(resolve => { releaseGate = resolve; })};
    const rereadResponse = page.waitForResponse(response => response.url() === base + "/api/inspect");
    await page.locator("#left-read-header").click();
    assert(await page.locator("#download-report").isDisabled());
    assert(await page.locator("#download-zip").isDisabled());
    assert(await page.locator("#comparison-results").isVisible());
    assert.equal(await page.locator("#stale-results").isVisible(), false);
    releaseGate(); releaseGate = null; routeGate = null;
    assert.equal((await rereadResponse).status(), 200);
    await ready("#download-report"); await ready("#download-zip");
    await page.locator("#page-size").selectOption("100");
    await visibleRows(28);
    assert.equal(await page.locator("#results-table img").count(), 0, "Literal key became executable markup");
    for (const [status, count] of Object.entries(expected.currency.field_checks)) {
      await page.locator("#status-filter").selectOption(status);
      await visibleRows(count);
    }
    assert((await page.locator("#results-table tbody").innerText()).includes("=2+2"), "Formula source value is hidden");
    await page.locator("#status-filter").selectOption("all");
    for (const [source, count] of Object.entries(expected.currency.source_filters)) {
      await page.locator("#source-filter").selectOption(source);
      await visibleRows(count);
    }
    await page.locator("#source-filter").selectOption("all");
    await page.locator("#result-search").fill('"001"');
    await visibleRows(4);
    await page.locator("#status-filter").selectOption("amount_mismatch");
    await visibleRows(2);
    const differenceText = await page.locator("#results-table tbody").innerText();
    assert(differenceText.includes("200.30") && differenceText.includes("2.10"));
    await page.locator("#comparison-results").screenshot({path: path.join(output, "currency-differences-panel.png")});
    screenshots.push({name: "currency-differences-panel.png", viewport: page.viewportSize(), selector: "#comparison-results", filtered: true, documentOverflow: false});
    await page.locator("#result-search").fill("");
    await page.locator("#status-filter").selectOption("all");
    await page.locator("#page-size").selectOption("25");
    await visibleRows(25);
    await page.locator("#next-page").click(); await visibleRows(3);
    await page.locator("#prev-page").click(); await visibleRows(25);
    await capture(page, "currency-results-desktop");
    await capture(page, "currency-results-mobile", true);
    const currencyOffline = await exportRun(currency, "currency");

    // An edit followed by restoring the same value still retires the previous run.
    await page.locator("#absolute-tolerance").fill("0.10"); await retired();
    await page.locator("#absolute-tolerance").fill("0.05"); await retired();
    await compare("currency", "-explicit-rerun");

    // Observe retirement while a new file's inspection is deliberately still pending.
    routeGate = {endpoint: "/api/inspect", promise: new Promise(resolve => { releaseGate = resolve; })};
    const replacedResponse = page.waitForResponse(response => response.url() === base + "/api/inspect");
    await page.locator("#right-file").setInputFiles(path.join(output, expected.unit.right.name));
    await retired();
    assert(await page.locator("#right-sheet").isDisabled());
    assert(await page.locator("#right-header-row").isDisabled());
    assert(await page.locator("#key-left-0").isDisabled());
    releaseGate(); releaseGate = null; routeGate = null;
    const replacement = await replacedResponse;
    if (replacement.status() === 400) {
      inspectionCorrections.push({endpoint: "/api/inspect", error: (await replacement.json()).error});
    } else assert.equal(replacement.status(), 200);
    await upload("right", expected.unit.right);
    await upload("left", expected.unit.left);
    await mappings("unit");
    await capture(page, "unit-inputs-mobile", true);
    const unit = await compare("unit");
    await capture(page, "unit-results-desktop");
    await capture(page, "unit-results-mobile", true);
    const unitOffline = await exportRun(unit, "unit");

    // The report remains usable after the local server is stopped, with networking disabled.
    server.kill("SIGTERM");
    await new Promise(resolve => { if (server.exitCode !== null) resolve(); else server.once("exit", resolve); });
    server = null;
    const offline = await browser.newContext({offline: true, viewport: {width: 1440, height: 1000}});
    await offline.route("**/*", route => {
      if (!route.request().url().startsWith("file:")) { externalRequests.push(route.request().url()); return route.abort(); }
      return route.continue();
    });
    const offlinePage = await offline.newPage();
    offlinePage.on("pageerror", error => pageErrors.push(error.message));
    for (const [scenario, directory] of [["currency", currencyOffline], ["unit", unitOffline]]) {
      await offlinePage.goto(pathToFileURL(path.join(directory, "report.html")).href);
      assert((await offlinePage.locator("body").innerText()).includes("Row coverage"));
      await capture(offlinePage, scenario + "-offline-desktop");
      await capture(offlinePage, scenario + "-offline-mobile", true);
    }
    assert.deepEqual(Object.fromEntries(expected.files.map(name => [name, hash(path.join(output, name))])), inputHashes, "Original source bytes changed");
    assert.deepEqual(externalRequests, [], "Unexpected non-local network use");
    assert.deepEqual(pageErrors, [], "Uncaught browser errors");
    assert(apiFailures.every(failure => failure.path === "/api/inspect" && failure.status === 400), JSON.stringify(apiFailures));
    assert.equal(apiFailures.length, inspectionCorrections.length, "Unaccounted API failure");
    const evidence = {
      status: "pass", installedEntryPoint: binary, installedPackageRoot, version: config.version, browser: browser.version(),
      launchedOutsideCheckout: true, sourcePathInjection: false, inputHashes, downloads, screenshots,
      exactCurrencyRecords: 28, compositeKeyRetained: true, multipleValues: true, currencySubtractionBlocked: true,
      commonUnitCase: {records: 4, matched: 3, amountMismatch: 1}, filtersAndPagination: "pass",
      unchangedHeaderRereadTemporarilyLocksDownloads: true,
      restoredSettingsRetireDownloads: true, fileChangeRetiresDownloadsBeforeInspectionCompletes: true,
      offlineReportAfterServerExit: true, originalSourcesUnchanged: true,
      externalRequests, pageErrors, inspectionCorrections, humanUsabilityTrial: "not performed",
    };
    fs.writeFileSync(path.join(output, "browser-ui-result.json"), JSON.stringify(evidence, null, 2) + "\n");
    console.log("BROWSER_UI_PASS " + path.join(output, "browser-ui-result.json"));
  } catch (error) {
    if (page && !page.isClosed()) await page.screenshot({path: path.join(output, "failure.png"), fullPage: true}).catch(() => {});
    fs.writeFileSync(path.join(output, "failure.json"), JSON.stringify({message: error.message, stack: error.stack, serverText, serverErrors, externalRequests, pageErrors, apiFailures, apiRequests}, null, 2) + "\n");
    throw error;
  } finally {
    if (releaseGate) releaseGate();
    if (browser) await browser.close();
    if (server) server.kill("SIGTERM");
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
