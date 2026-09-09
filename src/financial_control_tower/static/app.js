"use strict";

(function () {
  const $ = function (id) { return document.getElementById(id); };
  const LABELS = {
    matched: "容差内", amount_mismatch: "超出容差", left_only: "仅左表", right_only: "仅右表",
    missing_key: "缺少键", invalid_key: "键不明确", duplicate_key: "重复键", invalid_numeric: "无效数值",
    formula_cell: "Excel 公式", invalid_currency: "币种无效", currency_mismatch: "币种不同"
  };
  const EXPLANATIONS = {
    matched: "差异在所设容差内。",
    amount_mismatch: "绝对差额超过允许值。请检查原值、单位与字段对应关系；这里不推断差异原因。",
    left_only: "右表没有对应键。请检查文件覆盖范围与键列映射。",
    right_only: "左表没有对应键。请检查文件覆盖范围与键列映射。",
    missing_key: "键为空或只有空格，无法确定对应关系。",
    invalid_key: "键必须为原始文本。Excel 数值格式显示出的前导零不能作为文本键推断。",
    duplicate_key: "至少一侧存在重复键；所有相关源行均保留，不任意配对或加总。",
    invalid_numeric: "选中行包含无法比较的数值，未补零或转换。详细原因见原始说明。",
    formula_cell: "选中了 Excel 公式。请提供另存且已核验的数值版本；工具不会重算公式。",
    invalid_currency: "币种缺失或不是文本，因此不计算差额。",
    currency_mismatch: "两侧币种文本不一致，因此不相减，也不换算汇率。"
  };
  const BLOCKED = new Set(["missing_key", "invalid_key", "duplicate_key", "invalid_numeric", "formula_cell", "invalid_currency", "currency_mismatch"]);
  const state = {
    config: null, ready: false, busy: false, operation: "", revision: 0, run: null, stale: false,
    left: source("left"), right: source("right"),
    keys: [{left: "", right: ""}], values: [{left: "", right: ""}],
    unitMode: "currency", commonUnit: "", currencies: {left: "", right: ""},
    absolute: "0", relative: "0", status: "all", sourceFilter: "all", search: "", page: 0, pageSize: 25
  };
  function source(side) {
    return {side: side, file: null, sheet: null, header_row: 1, sheets: [], meta: null,
      loading: false, headerDirty: false, epoch: 0, error: "", size: null};
  }
  function append(parent, child) {
    if (Array.isArray(child)) child.forEach(function (value) { append(parent, value); });
    else if (child !== null && child !== undefined && child !== false) parent.appendChild(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    Object.entries(attrs || {}).forEach(function (pair) {
      const key = pair[0], value = pair[1];
      if (key === "value") return;
      if (key.startsWith("on") && typeof value === "function") node.addEventListener(key.slice(2), value);
      else if (key === "className") node.className = value;
      else if (value !== false && value !== undefined && value !== null) node.setAttribute(key, value === true ? "" : String(value));
    });
    append(node, children);
    if (Object.prototype.hasOwnProperty.call(attrs || {}, "value")) node.value = attrs.value === null ? "" : attrs.value;
    return node;
  }
  function button(label, action, attrs) { return el("button", Object.assign({type: "button", className: "button button-small", onclick: action}, attrs || {}), label); }
  function field(label, input, help) { return el("label", {className: "field"}, [label, input, help ? el("small", {}, help) : null]); }
  function select(options, value, action, attrs) {
    return el("select", Object.assign({value: value || "", onchange: action}, attrs || {}), options.map(function (option) {
      const item = typeof option === "string" ? {value: option, label: option} : option;
      return el("option", {value: item.value}, item.label);
    }));
  }
  function exact(value) { return value === null || value === undefined ? "—" : String(value); }
  function sideName(side) { return side === "left" ? "左表" : "右表"; }
  function activeHeaders(side) {
    const item = state[side];
    return item.loading || item.headerDirty || item.error || !item.meta ? [] : item.meta.headers || [];
  }
  function clearMessage() { $("error").classList.add("hidden"); $("app-status").classList.add("hidden"); }
  function message(value, error) {
    clearMessage(); const host = $(error ? "error" : "app-status");
    host.textContent = value; host.classList.remove("hidden");
    if (error) host.scrollIntoView({behavior: "smooth", block: "center"});
  }
  async function request(url, payload) {
    let response;
    try {
      response = await fetch(url, {
        method: payload === undefined ? "GET" : "POST", credentials: "same-origin",
        headers: payload === undefined ? {} : {"Content-Type": "application/json", "X-FCT-Token": state.config.csrf_token},
        body: payload === undefined ? undefined : JSON.stringify(payload)
      });
    } catch (_error) { throw new Error("无法连接本机服务。请保持工作区运行后重试。"); }
    let data;
    try { data = await response.json(); } catch (_error) { throw new Error("本机服务返回了无法读取的结果，请重新尝试。"); }
    if (!response.ok) throw new Error(data.error || "本次操作未能完成。");
    return data;
  }
  function invalidate() {
    state.revision += 1;
    state.stale = Boolean(state.run || state.stale);
    state.run = null;
    $("results-table").querySelector("tbody").replaceChildren();
    $("run-provenance").replaceChildren();
    clearMessage(); update();
  }
  function update() {
    const reading = state.left.loading || state.right.loading;
    $("input-fields").disabled = !state.ready || state.busy;
    $("load-example").disabled = !state.ready || state.busy || reading;
    $("run-compare").disabled = !state.ready || state.busy || reading || state.left.headerDirty || state.right.headerDirty;
    $("run-compare").textContent = state.busy && state.operation === "compare" ? "正在逐项核对…" : "开始核对 →";
    $("comparison-results").classList.toggle("hidden", !state.run);
    $("stale-results").classList.toggle("hidden", !state.stale || Boolean(state.run));
    $("download-report").disabled = state.busy || reading || !state.run;
    $("download-zip").disabled = state.busy || reading || !state.run;
    $("download-zip").textContent = state.busy && state.operation === "zip" ? "正在准备下载…" : "下载完整证据包 ↓";
    $("download-report").textContent = state.busy && state.operation === "report" ? "正在打开报告…" : "查看报告 ↗";
    $("add-key").disabled = state.keys.length >= 200 || reading;
    $("add-value").disabled = state.values.length >= 200 || reading;
    $("currency-fields").classList.toggle("hidden", state.unitMode !== "currency");
    $("common-unit-fields").classList.toggle("hidden", state.unitMode !== "common");
    $("currency-help").classList.toggle("hidden", state.unitMode !== "currency");
    ["left", "right"].forEach(function (side) {
      const item = state[side], details = $(side + "-details");
      if (details) details.classList.toggle("hidden", item.headerDirty || item.loading || !item.meta);
      ["key", "value"].forEach(function (kind) {
        const pairs = kind === "key" ? state.keys : state.values;
        pairs.forEach(function (_pair, index) {
          const control = $(kind + "-" + side + "-" + index);
          if (control) control.disabled = reading || !activeHeaders(side).length;
        });
      });
      $(side + "-currency").disabled = reading || !activeHeaders(side).length;
    });
  }
  function makeSourceCard(side) {
    const item = state[side], meta = item.meta;
    const label = item.loading ? "正在读取" : item.error ? "需要处理" : meta && meta.selection_required ? "请选择工作表" : meta ? meta.data_rows + " 行数据" : "待选择";
    const head = el("div", {className: "source-head"}, [
      el("div", {className: "source-title"}, [el("span", {className: "source-letter"}, side === "left" ? "L" : "R"), el("div", {}, [el("h3", {}, sideName(side)), el("small", {}, side === "left" ? "作为原值对照的一侧" : "与左表逐项对应的一侧")])]),
      el("span", {className: "tag" + (item.error || (meta && meta.selection_required) ? " warning" : meta && meta.headers.length ? " good" : "")}, label)
    ]);
    const fileControl = el("input", {id: side + "-file", type: "file", accept: ".csv,.xlsx", disabled: item.loading, onchange: function (event) { if (event.target.files[0]) readFile(side, event.target.files[0]); }});
    const body = el("div", {className: "source-body"}, [
      el("div", {className: "file-box"}, [
        el("span", {className: "file-icon", "aria-hidden": "true"}, "▤"),
        el("div", {className: "file-info"}, [el("span", {className: "file-name"}, item.file ? item.file.name : "选择 CSV 或 Excel 文件"), el("span", {className: "file-hint"}, "每份最多 " + Math.round((state.config ? state.config.max_file_bytes : 26214400) / 1048576) + " MiB · 原件保持不变")]),
        el("label", {className: "button file-picker", for: side + "-file"}, [item.file ? "更换文件" : "选择文件", fileControl])
      ])
    ]);
    const isCsv = item.file && /\.csv$/i.test(item.file.name);
    const sheetChoices = [{value: "", label: isCsv ? "CSV 无需工作表" : "选择一个工作表"}].concat(item.sheets);
    const sheet = select(sheetChoices, item.sheet, function (event) {
      item.sheet = event.target.value || null; invalidate(); inspect(side);
    }, {id: side + "-sheet", disabled: !item.file || Boolean(isCsv) || item.loading});
    const header = el("input", {id: side + "-header-row", type: "number", min: 1, step: 1, value: item.header_row, disabled: !item.file || item.loading,
      oninput: function (event) { item.header_row = Number(event.target.value); item.headerDirty = true; invalidate(); },
      onchange: function () { if (!item.loading) inspect(side); }});
    body.appendChild(el("div", {className: "file-selection"}, [field("工作表", sheet), field("表头行号", header)]));
    if (item.file) body.appendChild(el("div", {className: "source-inspect-actions"}, button("重新读取表头 ↻", function () { if (!item.loading) inspect(side); }, {id: side + "-read-header", className: "text-button", disabled: item.loading})));
    if (item.loading) body.appendChild(el("p", {className: "source-message", role: "status"}, "正在读取所选文件与表头…"));
    if (item.error) body.appendChild(el("p", {className: "source-message error", role: "status"}, item.error));
    if (meta && meta.selection_required) body.appendChild(el("p", {className: "source-message selection"}, "文件中有多个工作表。请明确选择需要比较的那一张。"));
    if (meta) {
      const details = el("details", {id: side + "-details", className: "source-details"}, [
        el("summary", {}, "查看预览、源行与文件哈希"),
        el("dl", {className: "source-metadata"}, [
          el("dt", {}, "原文件"), el("dd", {}, meta.filename || (item.file && item.file.name) || ""),
          el("dt", {}, "SHA-256"), el("dd", {}, el("code", {id: side + "-sha256"}, meta.sha256 || "—")),
          el("dt", {}, "读取范围"), el("dd", {}, (meta.sheet || "CSV") + " · 表头第 " + meta.header_row + " 行"),
          el("dt", {}, "空白行"), el("dd", {}, Array.isArray(meta.blank_rows_ignored) ? (meta.blank_rows_ignored.length ? meta.blank_rows_ignored.join("、") : "无") : exact(meta.blank_rows_ignored))
        ])
      ]);
      if (meta.headers && meta.headers.length) details.appendChild(el("div", {className: "table-wrap preview-table", tabindex: "0", "aria-label": sideName(side) + "原始表格预览"}, el("table", {id: side + "-preview"}, [
        el("thead", {}, el("tr", {}, [el("th", {}, "源行"), meta.headers.map(function (name) { return el("th", {}, name); })])),
        el("tbody", {}, (meta.preview || []).map(function (row) { return el("tr", {}, [el("td", {}, row.row), row.values.map(function (value, index) { return el("td", {title: "单元格类型：" + exact((row.kinds || [])[index])}, exact(value)); })]); }))
      ])));
      body.appendChild(details);
    }
    return el("article", {className: "source-card", "aria-label": sideName(side) + "文件选择"}, [head, body]);
  }
  function renderSource(side) { $(side + "-source").replaceChildren(makeSourceCard(side)); update(); }
  function renderMappings() {
    [["key", state.keys, "键"], ["value", state.values, "数值"]].forEach(function (kind) {
      $(kind[0] + "-pairs").replaceChildren.apply($(kind[0] + "-pairs"), kind[1].map(function (pair, index) {
        return el("div", {className: "pair-row"}, [
          ["left", "right"].map(function (side) {
            return select([{value: "", label: "选择" + sideName(side) + "列"}].concat(activeHeaders(side)), pair[side], function (event) { pair[side] = event.target.value; invalidate(); },
              {id: kind[0] + "-" + side + "-" + index, "aria-label": "第 " + (index + 1) + " 组" + kind[2] + "：" + sideName(side) + "列"});
          }),
          button("×", function () { kind[1].splice(index, 1); invalidate(); renderMappings(); }, {id: "remove-" + kind[0] + "-" + index, className: "icon-button", disabled: kind[1].length <= 1, "aria-label": "移除第 " + (index + 1) + " 组" + kind[2]})
        ]);
      }));
    });
    ["left", "right"].forEach(function (side) {
      const currency = $(side + "-currency");
      currency.replaceChildren.apply(currency, [{value: "", label: "选择币种列"}].concat(activeHeaders(side)).map(function (entry) { const option = typeof entry === "string" ? {value: entry, label: entry} : entry; return el("option", {value: option.value}, option.label); }));
      currency.value = state.currencies[side];
    });
    update();
  }
  async function readFile(side, file) {
    const item = state[side];
    item.epoch += 1; const epoch = item.epoch;
    item.file = null; item.sheet = null; item.header_row = 1; item.meta = null; item.sheets = []; item.error = ""; item.headerDirty = false; item.loading = false;
    state.keys.concat(state.values).forEach(function (pair) { pair[side] = ""; }); state.currencies[side] = "";
    invalidate();
    if (!/\.(csv|xlsx)$/i.test(file.name)) { item.error = "仅支持 UTF-8 CSV 和 .xlsx 文件。"; renderSource(side); renderMappings(); return; }
    if (file.size > state.config.max_file_bytes) { item.error = "文件超过 " + Math.round(state.config.max_file_bytes / 1048576) + " MiB，请使用较小的数据摘录。"; renderSource(side); renderMappings(); return; }
    item.loading = true; renderSource(side); renderMappings();
    try {
      const content = await new Promise(function (resolve, reject) {
        const reader = new FileReader();
        reader.onload = function () { resolve(String(reader.result).split(",")[1]); };
        reader.onerror = function () { reject(new Error("无法读取这份文件，请重新选择。")); };
        reader.readAsDataURL(file);
      });
      if (epoch !== item.epoch) return;
      item.file = {name: file.name, content_base64: content}; item.size = file.size;
      item.loading = false; await inspect(side);
    } catch (error) { if (epoch === item.epoch) { item.loading = false; item.error = error.message; renderSource(side); renderMappings(); } }
  }
  async function inspect(side) {
    const item = state[side];
    if (!item.file || item.loading) return;
    if (!Number.isInteger(item.header_row) || item.header_row < 1) { item.error = "表头行号需要是从 1 开始的整数。"; item.headerDirty = true; renderSource(side); return; }
    item.epoch += 1; const epoch = item.epoch;
    item.loading = true; item.error = ""; item.meta = null;
    renderSource(side); renderMappings();
    try {
      const meta = await request("/api/inspect", {file: item.file, sheet: item.sheet, header_row: item.header_row});
      if (epoch !== item.epoch) return;
      item.meta = meta; item.sheets = meta.sheets || []; item.sheet = meta.sheet || item.sheet; item.headerDirty = false;
      const headers = meta.headers || [];
      state.keys.concat(state.values).forEach(function (pair) { if (pair[side] && !headers.includes(pair[side])) pair[side] = ""; });
      if (state.currencies[side] && !headers.includes(state.currencies[side])) state.currencies[side] = "";
    } catch (error) { if (epoch === item.epoch) { item.error = error.message; item.meta = null; } }
    finally { if (epoch === item.epoch) { item.loading = false; renderSource(side); renderMappings(); } }
  }
  function validate() {
    if (!state.ready) throw new Error("本机工作区尚未连接。");
    ["left", "right"].forEach(function (side) {
      const item = state[side];
      if (!item.file) throw new Error("请先选择" + sideName(side) + "文件。");
      if (item.loading || item.headerDirty) throw new Error("请先完成" + sideName(side) + "表头读取。");
      if (item.error) throw new Error(sideName(side) + "：" + item.error);
      if (!item.meta || item.meta.selection_required || !activeHeaders(side).length) throw new Error("请选择" + sideName(side) + "的工作表和有效表头。");
    });
    [[state.keys, "记录键"], [state.values, "数值字段"]].forEach(function (group) {
      ["left", "right"].forEach(function (side) {
        const names = group[0].map(function (pair) { return pair[side]; });
        if (!names.length || names.some(function (value) { return !value; })) throw new Error("请完整对应每一组" + group[1] + "的左右两列。");
        if (new Set(names).size !== names.length) throw new Error(sideName(side) + "的" + group[1] + "不可重复选择同一列。");
      });
    });
    if (state.unitMode === "currency" && (!state.currencies.left || !state.currencies.right)) throw new Error("请同时选择两侧币种列，或改为明确声明共同单位。");
    if (state.unitMode === "common" && !state.commonUnit.trim()) throw new Error("请明确填写全部数值字段的共同单位。");
    [state.absolute, state.relative].forEach(function (value) {
      if (!/^[+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(value.trim())) throw new Error("容差需要是非负十进制数，不含千位分隔符或货币符号。相对容差填写比例。");
    });
    if ((state.left.meta.data_rows + state.right.meta.data_rows) * state.values.length > 20000) throw new Error("源数据行数与数值字段的组合超过 20,000 项。请减少数据范围或数值字段。");
  }
  function payload() {
    function input(side) {
      const item = state[side];
      return {file: item.file, sheet: item.sheet, header_row: item.header_row,
        keys: state.keys.map(function (pair) { return pair[side]; }), values: state.values.map(function (pair) { return pair[side]; }),
        currency: state.unitMode === "currency" ? state.currencies[side] : null};
    }
    return {left: input("left"), right: input("right"), absolute_tolerance: state.absolute.trim(), relative_tolerance: state.relative.trim(),
      common_unit: state.unitMode === "common" ? state.commonUnit.trim() : null};
  }
  async function compare() {
    if (state.busy) return;
    clearMessage();
    try { validate(); } catch (error) { message(error.message, true); return; }
    const data = payload(); invalidate(); const revision = state.revision;
    state.busy = true; state.operation = "compare"; update();
    try {
      const run = await request("/api/compare", data);
      if (state.revision !== revision) throw new Error("核对期间输入已改变，请使用当前输入重新核对。");
      if (!run.run_id || !run.result || !Array.isArray(run.result.records) || !run.downloads) throw new Error("本机服务返回的核对结果不完整，请重试。");
      state.run = run; state.stale = false; state.search = ""; state.status = "all"; state.sourceFilter = "all"; state.page = 0;
      renderResults();
      message(run.result.summary.all_matched ? "核对完成：所有字段检查均在容差内。原值和源行可在下方追溯。" : "核对完成：存在差异、无对应行或受阻字段，请查看下方明细。", false);
      $("comparison-results").scrollIntoView({behavior: "smooth", block: "start"});
    } catch (error) { message(error.message, true); }
    finally { state.busy = false; state.operation = ""; update(); }
  }
  function renderResults() {
    const result = state.run.result, summary = result.summary, counts = summary.field_checks;
    $("count-total").textContent = result.records.length;
    $("count-matched").textContent = counts.matched || 0;
    $("count-different").textContent = counts.amount_mismatch || 0;
    $("count-unpaired").textContent = (counts.left_only || 0) + (counts.right_only || 0);
    $("count-blocked").textContent = Object.entries(counts).reduce(function (total, pair) { return total + (BLOCKED.has(pair[0]) ? pair[1] : 0); }, 0);
    ["left", "right"].forEach(function (side) { $("coverage-" + side).textContent = sideName(side) + "源行覆盖：" + summary.accounted_rows[side] + " / " + summary.input_rows[side] + " 行"; });
    const name = function (side) { const item = result.inputs[side]; return item.original_filename || (state[side].file && state[side].file.name) || item.path; };
    $("result-context").textContent = name("left") + " ↔ " + name("right") + " · " + state.values.length + " 组数值字段";
    $("result-outcome").textContent = summary.all_matched ? "字段全部在容差内" : "有待查看的例外";
    $("result-outcome").className = "tag " + (summary.all_matched ? "good" : "warning");
    $("status-filter").replaceChildren(el("option", {value: "all"}, "全部状态（" + result.records.length + "）"));
    Object.keys(LABELS).forEach(function (status) { $("status-filter").appendChild(el("option", {value: status}, LABELS[status] + "（" + (counts[status] || 0) + "）")); });
    Object.keys(counts).filter(function (status) { return !LABELS[status]; }).forEach(function (status) { $("status-filter").appendChild(el("option", {value: status}, status + "（" + counts[status] + "）")); });
    $("result-search").value = ""; $("source-filter").value = "all"; $("status-filter").value = "all";
    renderRecords(); renderProvenance(); update();
  }
  function hasRow(record, side) { return record[side + "_row"] !== null && record[side + "_row"] !== undefined; }
  function renderRecords() {
    if (!state.run) return;
    const all = state.run.result.records, search = state.search.toLocaleLowerCase();
    const filtered = all.filter(function (record) {
      if (state.status !== "all" && state.status !== record.status) return false;
      const left = hasRow(record, "left"), right = hasRow(record, "right");
      if (state.sourceFilter === "left" && !left) return false;
      if (state.sourceFilter === "right" && !right) return false;
      if (state.sourceFilter === "paired" && !(left && right)) return false;
      if (state.sourceFilter === "unpaired" && left === right) return false;
      return !search || JSON.stringify(record).toLocaleLowerCase().includes(search) || (LABELS[record.status] || "").includes(search);
    });
    const pages = Math.max(1, Math.ceil(filtered.length / state.pageSize));
    state.page = Math.max(0, Math.min(state.page, pages - 1));
    const tbody = $("results-table").querySelector("tbody"); tbody.replaceChildren();
    filtered.slice(state.page * state.pageSize, (state.page + 1) * state.pageSize).forEach(function (record) {
      function amount(side) {
        const exists = hasRow(record, side), currency = record[side + "_currency"];
        return el("td", {className: "amount-cell"}, [
          el("div", {className: "amount-text"}, exists ? exact(record[side + "_value"]) : "无对应行"),
          el("span", {className: "row-ref"}, exists ? sideName(side) + "第 " + record[side + "_row"] + " 行" + (currency ? " · " + currency : "") : "—")
        ]);
      }
      function calculated(value) { return el("td", {}, el("div", {className: "exact-text"}, value === null || value === undefined ? "未计算" : value)); }
      const issue = el("td", {className: "issue-cell"}, el("p", {}, EXPLANATIONS[record.status] || "请检查本项记录。"));
      if ((record.issues || []).length) issue.appendChild(el("details", {}, [el("summary", {}, "展开原始说明（" + record.issues.length + "）"), el("ul", {}, record.issues.map(function (item) { return el("li", {}, item); }))]));
      tbody.appendChild(el("tr", {"data-status": record.status}, [
        el("td", {className: "status-cell"}, el("span", {className: "tag " + (record.status === "matched" ? "good" : record.status === "amount_mismatch" ? "difference" : "warning")}, LABELS[record.status] || record.status)),
        el("td", {className: "key-cell"}, el("code", {className: "exact-text"}, JSON.stringify(record.key))),
        el("td", {className: "field-cell"}, [el("span", {className: "column-name"}, "左：" + record.left_column), el("span", {className: "column-name"}, "右：" + record.right_column)]),
        amount("left"), amount("right"), calculated(record.difference_right_minus_left), calculated(record.absolute_difference), calculated(record.allowed_difference), issue
      ]));
    });
    if (!filtered.length) tbody.appendChild(el("tr", {}, el("td", {colspan: 9, className: "empty-row"}, "没有符合当前筛选条件的字段检查。")));
    $("visible-count").textContent = "筛选结果：" + filtered.length + " / " + all.length + " 项字段检查";
    $("page-label").textContent = "第 " + (state.page + 1) + " / " + pages + " 页";
    $("prev-page").disabled = state.page === 0; $("next-page").disabled = state.page >= pages - 1;
  }
  function renderProvenance() {
    const result = state.run.result, host = $("run-provenance"); host.replaceChildren();
    ["left", "right"].forEach(function (side) {
      const item = result.inputs[side], info = el("dl", {className: "source-metadata"});
      [["工作表", item.sheet || "CSV / 单一工作表"], ["表头行", item.header_row], ["记录键", JSON.stringify(item.keys)], ["数值字段", JSON.stringify(item.values)], ["币种列", item.currency || "未使用；采用共同单位声明"], ["SHA-256", item.sha256], ["忽略空白行", JSON.stringify(item.blank_rows_ignored || [])]].forEach(function (pair) {
        info.append(el("dt", {}, pair[0]), el("dd", {}, pair[0] === "SHA-256" ? el("code", {}, exact(pair[1])) : exact(pair[1])));
      });
      host.appendChild(el("section", {className: "run-source"}, [el("h4", {}, sideName(side) + " · " + (item.original_filename || state[side].file.name || item.path)), info]));
    });
    host.appendChild(el("p", {className: "policy-text"}, [
      "绝对容差：" + result.policy.absolute_tolerance + "；相对容差：" + result.policy.relative_tolerance + "（比例）。",
      el("br"), "允许差额 = max（绝对容差，相对容差 × max（|左值|，|右值|））。",
      el("br"), state.unitMode === "common" ? "共同单位声明：" + state.commonUnit : "币种来自两侧所选列；不同币种不相减。",
      el("br"), "精确文本键保留前导零、空格及大小写；不加总、不推断业务原因。"
    ]));
  }
  function runUrl(run, kind) {
    const route = run.downloads[kind], url = new URL(route, window.location.origin);
    const expected = "/api/runs/" + encodeURIComponent(run.run_id) + "/" + kind;
    if (url.origin !== window.location.origin || url.pathname !== expected || url.search || url.hash) throw new Error("结果下载地址与当前运行不一致，请重新核对。");
    return url.href;
  }
  async function download(kind) {
    if (!state.run || state.busy || state.left.loading || state.right.loading) return;
    const run = state.run, revision = state.revision; let reportWindow = null;
    clearMessage(); state.busy = true; state.operation = kind; update();
    try {
      const url = runUrl(run, kind);
      if (kind === "report") {
        reportWindow = window.open("about:blank", "_blank");
        if (!reportWindow) throw new Error("浏览器阻止了报告新标签页。请允许本机工作区打开新标签页后重试。");
        reportWindow.opener = null;
        reportWindow.document.title = "正在打开核对报告";
        reportWindow.document.body.textContent = "正在打开本次核对报告…";
      }
      let response;
      try { response = await fetch(url, {credentials: "same-origin"}); }
      catch (_error) { throw new Error("无法连接本机服务，请保持工作区运行后重新核对。"); }
      if (!response.ok) {
        if (response.status === 409 || response.status === 410 || response.status === 404) {
          state.run = null; state.stale = true;
          throw new Error("本次结果已过期，或本机服务已重启。请重新核对，再下载保存。");
        }
        let data = {};
        try { data = await response.json(); } catch (_error) { /* Use the local action message below. */ }
        throw new Error(data.error || "无法读取本次报告，请重试。");
      }
      if (revision !== state.revision || state.run !== run) throw new Error("输入已改变，先前下载已失效。请重新核对。");
      if (kind === "report") {
        await response.arrayBuffer();
        if (revision !== state.revision || state.run !== run) throw new Error("输入已改变，请重新核对后查看报告。");
        reportWindow.location.replace(url); reportWindow = null;
        message("报告已在新标签页打开。需要完整离线留存时，请下载证据包。", false);
      } else {
        const blob = await response.blob();
        if (revision !== state.revision || state.run !== run) throw new Error("输入已改变，请重新核对后下载。");
        const objectUrl = URL.createObjectURL(blob);
        const link = el("a", {href: objectUrl, download: "双表核对-完整证据包.zip", className: "hidden"}, "下载证据包");
        document.body.appendChild(link); link.click(); link.remove();
        window.setTimeout(function () { URL.revokeObjectURL(objectUrl); }, 60000);
        message("完整证据包已准备下载，包含本次全部字段结果、原始输入副本和文件清单。", false);
      }
    } catch (error) {
      if (reportWindow && !reportWindow.closed) reportWindow.close();
      message(error.message, true);
    } finally { state.busy = false; state.operation = ""; update(); }
  }
  async function loadExample() {
    if (state.busy || state.left.loading || state.right.loading) return;
    invalidate(); state.busy = true; state.operation = "example"; update();
    try {
      const data = await request("/api/example");
      state.keys = data.left.keys.map(function (name, index) { return {left: name, right: data.right.keys[index] || ""}; });
      state.values = data.left.values.map(function (name, index) { return {left: name, right: data.right.values[index] || ""}; });
      state.absolute = String(data.absolute_tolerance); state.relative = String(data.relative_tolerance);
      state.unitMode = data.left.currency && data.right.currency ? "currency" : "common";
      state.currencies = {left: data.left.currency || "", right: data.right.currency || ""};
      state.commonUnit = "";
      $("absolute-tolerance").value = state.absolute; $("relative-tolerance").value = state.relative;
      $("unit-mode-currency").checked = state.unitMode === "currency"; $("unit-mode-common").checked = state.unitMode === "common"; $("common-unit").value = "";
      for (const side of ["left", "right"]) {
        const incoming = data[side], item = source(side);
        item.file = incoming.file; item.sheet = incoming.sheet || null; item.header_row = incoming.header_row || 1;
        state[side] = item; renderSource(side); await inspect(side);
      }
      renderMappings();
      message("自造示例已载入，尚未比较。请确认字段与单位后点击“开始核对”。" + (state.unitMode === "common" ? "示例没有币种列，请自行确认并填写共同单位。" : ""), false);
    } catch (error) { message(error.message, true); }
    finally { state.busy = false; state.operation = ""; update(); }
  }
  function bind() {
    $("comparison-form").addEventListener("submit", function (event) { event.preventDefault(); compare(); });
    $("load-example").addEventListener("click", loadExample);
    [["add-key", "keys"], ["add-value", "values"]].forEach(function (pair) { $(pair[0]).addEventListener("click", function () { if (state[pair[1]].length < 200) { state[pair[1]].push({left: "", right: ""}); invalidate(); renderMappings(); } }); });
    ["left", "right"].forEach(function (side) { $(side + "-currency").addEventListener("change", function (event) { state.currencies[side] = event.target.value; invalidate(); }); });
    ["currency", "common"].forEach(function (mode) { $("unit-mode-" + mode).addEventListener("change", function (event) { if (event.target.checked) { state.unitMode = mode; invalidate(); } }); });
    $("common-unit").addEventListener("input", function (event) { state.commonUnit = event.target.value; invalidate(); });
    $("absolute-tolerance").addEventListener("input", function (event) { state.absolute = event.target.value; invalidate(); });
    $("relative-tolerance").addEventListener("input", function (event) { state.relative = event.target.value; invalidate(); });
    $("status-filter").addEventListener("change", function (event) { state.status = event.target.value; state.page = 0; renderRecords(); });
    $("source-filter").addEventListener("change", function (event) { state.sourceFilter = event.target.value; state.page = 0; renderRecords(); });
    $("result-search").addEventListener("input", function (event) { state.search = event.target.value; state.page = 0; renderRecords(); });
    $("page-size").addEventListener("change", function (event) { state.pageSize = Number(event.target.value); state.page = 0; renderRecords(); });
    $("prev-page").addEventListener("click", function () { state.page -= 1; renderRecords(); });
    $("next-page").addEventListener("click", function () { state.page += 1; renderRecords(); });
    $("download-report").addEventListener("click", function () { download("report"); });
    $("download-zip").addEventListener("click", function () { download("zip"); });
  }
  async function start() {
    bind(); renderSource("left"); renderSource("right"); renderMappings();
    try {
      const config = await request("/api/config");
      if (!config.csrf_token || !config.max_file_bytes) throw new Error("本机工作区配置不完整，请重新启动。");
      state.config = config; state.ready = true; $("app-version").textContent = config.version ? "· v" + config.version : "";
      renderSource("left"); renderSource("right"); update(); message("本机工作区已就绪。选择两份文件，或载入自造示例。", false);
    } catch (error) { message(error.message, true); }
  }
  start();
})();
