/* Independent examples and refusal cases for name-only, provisional hints. */
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");
const {suggest} = require("../src/financial_control_tower/static/suggestions.js");

function meta(headers, values, kinds, extra = {}) {
  return {
    format: "csv", selection_required: false, headers, data_rows: 1,
    preview: [{row: 2, values, kinds: kinds || headers.map(() => "text")}], ...extra
  };
}

function freeze(value) {
  if (value && typeof value === "object") { Object.values(value).forEach(freeze); Object.freeze(value); }
  return value;
}

test("one explicit English identifier, amount and currency pair needs no type guessing", () => {
  const left = meta(["ID", "Amount", "Currency"], ["0007", "25", "USD"]);
  const right = meta(["ID", "Amount", "Currency"], ["0007", "25.01", "USD"]);
  assert.deepEqual(suggest(left, right).keys, [{left: "ID", right: "ID"}]);
  assert.deepEqual(suggest(left, right).values, [{left: "Amount", right: "Amount"}]);
  assert.deepEqual(suggest(left, right).currencies, {left: "Currency", right: "Currency"});
});

test("Chinese column names and explicit bilingual aliases retain their original spelling", () => {
  const left = meta(["交易编号", "金额", "币种"], ["T-007", "25", "USD"]);
  const chinese = suggest(left, meta(["交易编号", "金额", "币种"], ["T-007", "26", "USD"]));
  assert.deepEqual(chinese.keys, [{left: "交易编号", right: "交易编号"}]);
  assert.deepEqual(chinese.values, [{left: "金额", right: "金额"}]);
  const aliases = suggest(left, meta(["Trade ID", "AMOUNT", "ccy"], ["T-007", "26", "USD"]));
  assert.deepEqual(aliases.keys, [{left: "交易编号", right: "Trade ID"}]);
  assert.deepEqual(aliases.values, [{left: "金额", right: "AMOUNT"}]);
  assert.deepEqual(aliases.currencies, {left: "币种", right: "ccy"});
});

test("normalization helps find an alias but does not alter submitted headers or source metadata", () => {
  const left = freeze(meta(["  Record_ID ", " Ａｍｏｕｎｔ ", "幣種"], ["001", "9", "HKD"]));
  const right = freeze(meta(["记录编号", "金额", "Ccy"], ["001", "9", "HKD"]));
  const before = JSON.stringify([left, right]);
  const result = suggest(left, right);
  assert.deepEqual(result.keys, [{left: "  Record_ID ", right: "记录编号"}]);
  assert.deepEqual(result.values, [{left: " Ａｍｏｕｎｔ ", right: "金额"}]);
  assert.equal(JSON.stringify([left, right]), before);
});

test("ID/id collision on either side refuses key suggestions instead of choosing a first match", () => {
  const duplicate = meta(["ID", "id", "amount", "currency"], ["A", "B", "9", "USD"]);
  const unique = meta(["id", "amount", "currency"], ["A", "9", "USD"]);
  for (const [left, right] of [[duplicate, unique], [unique, duplicate]]) {
    const result = suggest(left, right);
    assert.deepEqual(result.keys, []);
    assert(result.warnings.some(note => note.includes("「ID」、「id」") && note.includes("同名")));
    assert.deepEqual(result.values, [{left: "amount", right: "amount"}]);
  }
});

test("amount and currency normalization collisions also refuse the affected role", () => {
  const left = meta(["id", "Amount", " amount ", "Currency", "CURRENCY"], ["A", "9", "8", "USD", "EUR"]);
  const result = suggest(left, meta(["id", "amount", "currency"], ["A", "9", "USD"]));
  assert.deepEqual(result.keys, [{left: "id", right: "id"}]);
  assert.deepEqual(result.values, []);
  assert.deepEqual(result.currencies, {left: "", right: ""});
});

test("multiple plausible identifiers require a choice even if one has an exact counterpart", () => {
  const result = suggest(
    meta(["id", "trade_id", "amount"], ["A", "T1", "9"]),
    meta(["id", "amount"], ["A", "9"])
  );
  assert.deepEqual(result.keys, []);
  assert(result.notes.some(note => note.includes("多个可能的记录编号")));
});

test("multiple possible numeric fields are not all selected or ranked by position", () => {
  const result = suggest(
    meta(["id", "amount", "balance", "interest"], ["A", "9", "20", "1"]),
    meta(["id", "amount", "balance", "interest"], ["A", "9", "20", "1"])
  );
  assert.deepEqual(result.values, []);
  assert(result.notes.some(note => note.includes("多个可能的数值")));
});

test("balance and amount are different semantic groups even when every sample is numeric", () => {
  const result = suggest(meta(["id", "balance"], ["A", "9"]), meta(["id", "amount"], ["A", "9"]));
  assert.deepEqual(result.values, []);
  assert(result.notes.some(note => note.includes("balance") && note.includes("amount") && note.includes("用途可能不同")));
  assert.deepEqual(suggest(meta(["id", "balance"], ["A", "9"]), meta(["id", "余额"], ["A", "9"])).values,
    [{left: "balance", right: "余额"}]);
});

test("record identifiers and trade identifiers are not silently equated", () => {
  const result = suggest(meta(["id", "amount"], ["001", "9"]), meta(["trade_id", "amount"], ["001", "9"]));
  assert.deepEqual(result.keys, []);
});

test("a missing or ambiguous currency never supplies one side or invents a common currency", () => {
  const withCurrency = meta(["id", "amount", "currency"], ["001", "9", "USD"]);
  for (const right of [
    meta(["id", "amount"], ["001", "9"]),
    meta(["id", "amount", "currency", "ccy"], ["001", "9", "USD", "EUR"])
  ]) {
    const result = suggest(withCurrency, right);
    assert.deepEqual(result.currencies, {left: "", right: ""});
    assert(!Object.hasOwn(result, "common_unit"));
    assert(result.notes.some(note => note.includes("明确填写共同单位")));
  }
});

test("an Excel numeric ID does not get coerced to text or get display-format zeros restored", () => {
  const left = meta(["id", "amount"], ["7", "25"], ["other", "other"], {format: "xlsx"});
  const result = suggest(left, meta(["id", "amount"], ["0007", "25"]));
  assert.deepEqual(result.keys, []);
  assert(result.warnings.some(note => note.includes("非文本") && note.includes("前导零")));
  assert.deepEqual(result.values, [{left: "amount", right: "amount"}]);
  assert.equal(left.preview[0].values[0], "7");
});

test("formula samples in ID, amount or currency are not suggested or evaluated", () => {
  const right = meta(["id", "amount", "currency"], ["001", "9", "USD"]);
  for (const [index, role] of [[0, "keys"], [1, "values"], [2, "currencies"]]) {
    const kinds = ["text", "other", "text"], values = ["001", "9", "USD"];
    kinds[index] = "formula"; values[index] = "=1+1";
    const result = suggest(meta(["id", "amount", "currency"], values, kinds, {format: "xlsx"}), right);
    assert.deepEqual(result[role], role === "currencies" ? {left: "", right: ""} : []);
    assert(result.warnings.some(note => note.includes("公式") && note.includes("不会重算")));
    assert.equal(values[index], "=1+1");
  }
});

test("blank keys and non-text currency samples are left for explicit correction", () => {
  const result = suggest(
    meta(["id", "amount", "currency"], [" ", "9", "1"], ["text", "other", "other"], {format: "xlsx"}),
    meta(["id", "amount", "currency"], ["A", "9", "USD"])
  );
  assert.deepEqual(result.keys, []);
  assert.deepEqual(result.currencies, {left: "", right: ""});
  assert(result.warnings.some(note => note.includes("空白记录编号")));
  assert(result.warnings.some(note => note.includes("币种需要原始文本")));
});

test("numeric-looking CSV IDs stay text hints and no uniqueness claim is made", () => {
  const result = suggest(meta(["id", "amount"], ["0007", "9"]), meta(["id", "amount"], ["0007", "10"]));
  assert.deepEqual(result.keys, [{left: "id", right: "id"}]);
  assert(result.notes.some(note => note.includes("未验证全表唯一性")));
  assert(result.notes.some(note => note.includes("待确认")));
  assert.equal(JSON.stringify(result).includes("已验证唯一"), false);
});

test("a sixth source row can be invalid without changing or validating a five-row hint", () => {
  const clean = meta(["id", "amount"], ["001", "9"]);
  clean.preview = [1, 2, 3, 4, 5].map(number => ({row: number + 1, values: ["00" + number, "9"], kinds: ["text", "text"]}));
  clean.data_rows = 6;
  const unseenInvalid = {...clean, unseen_source_row: {id: "001", amount: "not a number"}};
  const result = suggest(unseenInvalid, clean);
  assert.deepEqual(result, suggest(clean, clean));
  assert(result.notes.some(note => note.includes("最多 5 行") && note.includes("完整问题在开始核对后报告")));
  assert.equal(Object.hasOwn(result, "all_matched"), false);
});

test("an unnamed numeric column, an account label and a currency-like value do not infer roles", () => {
  const input = meta(["account", "col2", "country"], ["001", "25", "USD"]);
  const result = suggest(input, input);
  assert.deepEqual(result.keys, []);
  assert.deepEqual(result.values, []);
  assert.deepEqual(result.currencies, {left: "", right: ""});
});

test("unconfirmed sheets and absent or malformed previews do not yield premature hints", () => {
  const valid = meta(["id", "amount"], ["001", "9"]);
  for (const input of [null, {...valid, selection_required: true}, {...valid, headers: []}]) {
    const result = suggest(input, valid);
    assert.deepEqual(result.keys, []);
    assert.deepEqual(result.values, []);
    assert(result.warnings.length > 0);
  }
  const noPreview = suggest({...valid, preview: []}, valid);
  assert.deepEqual(noPreview.keys, []);
  assert.deepEqual(noPreview.values, []);
  assert(noPreview.warnings.some(note => note.includes("没有可查看的样本")));
  assert.deepEqual(suggest({...valid, preview: [{values: ["001", "9"]}]}, valid).keys, []);
});

test("HTML-like and prototype-like headers remain inert input data, not semantic aliases", () => {
  const hostile = '<img src=x onerror="globalThis.__fct_injected = true">';
  const input = freeze(meta([hostile, "__proto__", "constructor", "amount"], ["001", "002", "003", "9"]));
  const before = JSON.stringify(input);
  const result = suggest(input, meta(["id", "amount"], ["001", "9"]));
  assert.deepEqual(result.keys, []);
  assert.deepEqual(result.values, [{left: "amount", right: "amount"}]);
  assert.equal(JSON.stringify(input), before);
  assert.equal(input.headers[0], hostile);
  assert.equal(globalThis.__fct_injected, undefined);
  assert.equal(Object.prototype.__fct_injected, undefined);
});

test("the same helper exports a browser global without DOM access, network or module support", () => {
  const code = fs.readFileSync(path.join(__dirname, "../src/financial_control_tower/static/suggestions.js"), "utf8");
  const context = vm.createContext({});
  vm.runInContext(code, context);
  assert.equal(typeof context.FctSuggestions.suggest, "function");
  const input = meta(["id", "amount"], ["001", "9"]);
  assert.deepEqual(JSON.parse(JSON.stringify(context.FctSuggestions.suggest(input, input))), suggest(input, input));
  assert.equal(context.document, undefined);
  assert.equal(context.fetch, undefined);
});
