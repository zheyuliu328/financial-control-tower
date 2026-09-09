/* Column-name hints only. The comparison engine remains the source of validation. */
"use strict";

(function (root) {
  const GROUPS = {
    keys: {
      record: ["id", "key", "recordid", "recordkey", "记录编号", "記錄編號", "记录id", "記錄id", "记录键", "記錄鍵"],
      trade: ["tradeid", "交易编号", "交易編號", "交易id"],
      transaction: ["transactionid", "txnid", "交易流水号", "交易流水號"],
      account: ["accountid", "accountnumber", "accountno", "账户编号", "賬戶編號", "账户号", "賬戶號", "账号", "賬號"],
      invoice: ["invoiceid", "invoicenumber", "invoiceno", "发票编号", "發票編號", "发票号", "發票號"],
      order: ["orderid", "ordernumber", "orderno", "订单编号", "訂單編號", "订单号", "訂單號"]
    },
    values: {
      amount: ["amount", "金额", "金額"],
      balance: ["balance", "余额", "餘額", "结余", "結餘"],
      value: ["value", "数值", "數值"],
      notional: ["notional", "notionalamount", "名义本金", "名義本金"],
      principal: ["principal", "principalamount", "本金"],
      interest: ["interest", "interestamount", "利息"],
      accrual: ["accrual", "accruedinterest", "应计利息", "應計利息"]
    },
    currencies: {currency: ["currency", "ccy", "币种", "幣種", "货币", "貨幣"]}
  };
  const LABELS = {keys: "记录编号", values: "数值", currencies: "币种"};

  // Normalization locates hints; returned mappings always use the original names.
  // Punctuation such as brackets, slashes and HTML is deliberately not removed.
  function normalized(name) { return name.normalize("NFKC").trim().toLowerCase().replace(/[\s_-]+/gu, ""); }

  function groupFor(role, name) {
    return Object.keys(GROUPS[role]).find(function (group) { return GROUPS[role][group].includes(name); });
  }

  function source(meta, side, warnings) {
    if (!meta || meta.selection_required || !Array.isArray(meta.headers) || !meta.headers.length) {
      warnings.push(side + "的表头尚未确认，请先选择工作表并完成读取。");
      return null;
    }
    if (meta.headers.length > 200 || meta.headers.some(function (name) { return typeof name !== "string" || !name.trim(); })) {
      warnings.push(side + "的列名不完整，无法提供字段建议，请重新确认表头。");
      return null;
    }
    const names = new Map();
    meta.headers.forEach(function (name) {
      const key = normalized(name);
      if (!names.has(key)) names.set(key, []);
      names.get(key).push(name);
    });
    names.forEach(function (originals, name) {
      if (originals.length > 1 && Object.keys(GROUPS).some(function (role) { return groupFor(role, name); })) {
        warnings.push(side + "的「" + originals.join("」、「") + "」看起来是同名列，已停止建议这些列，请按原始列名手动选择。");
      }
    });
    return {meta: meta, side: side, names: names};
  }

  function candidate(input, role, notes, warnings) {
    const matches = [];
    input.meta.headers.forEach(function (name, index) {
      const normalizedName = normalized(name), group = groupFor(role, normalizedName);
      if (group) matches.push({name: name, index: index, group: group, collision: input.names.get(normalizedName).length > 1});
    });
    if (matches.length > 1) {
      notes.push(input.side + "有多个可能的" + LABELS[role] + "列，请手动选择需要核对的列。");
      return null;
    }
    if (matches.length !== 1 || matches[0].collision) return null;
    const item = matches[0], preview = Array.isArray(input.meta.preview) ? input.meta.preview.slice(0, 5) : [];
    if (!preview.length) {
      warnings.push(input.side + "的「" + item.name + "」没有可查看的样本，暂不建议该列。");
      return null;
    }
    const cells = preview.map(function (row) {
      return {
        kind: row && Array.isArray(row.kinds) ? row.kinds[item.index] : undefined,
        value: row && Array.isArray(row.values) ? row.values[item.index] : undefined
      };
    });
    if (cells.some(function (cell) { return cell.kind === "formula"; })) {
      warnings.push(input.side + "的「" + item.name + "」预览含 Excel 公式，暂不建议该列；需要提供已另存并核验的数值版本，工具不会重算公式。");
      return null;
    }
    if (role === "keys" || role === "currencies") {
      if (cells.some(function (cell) { return cell.kind !== "text"; })) {
        warnings.push(input.side + "的「" + item.name + "」预览含非文本单元格，暂不建议作为" + LABELS[role] + "列。" + (role === "keys" ? "数字格式显示的前导零不能作为原始编号恢复。" : "币种需要原始文本。"));
        return null;
      }
      if (cells.some(function (cell) { return typeof cell.value !== "string" || !cell.value.trim(); })) {
        warnings.push(input.side + "的「" + item.name + "」预览含空白" + LABELS[role] + "，暂不建议该列，请确认数据。");
        return null;
      }
    }
    return item;
  }

  function suggest(leftMeta, rightMeta) {
    const result = {
      keys: [], values: [], currencies: {left: "", right: ""},
      notes: [
        "仅按列名提供待确认建议，请核对预览中的业务含义。",
        "预览最多 5 行；未验证全表唯一性或数值有效性，完整问题在开始核对后报告。"
      ],
      warnings: []
    };
    const left = source(leftMeta, "左表", result.warnings), right = source(rightMeta, "右表", result.warnings);
    if (!left || !right) return result;
    Object.keys(GROUPS).forEach(function (role) {
      const a = candidate(left, role, result.notes, result.warnings);
      const b = candidate(right, role, result.notes, result.warnings);
      if (a && b && a.group === b.group) {
        if (role === "currencies") result.currencies = {left: a.name, right: b.name};
        else result[role].push({left: a.name, right: b.name});
      } else if (a && b) {
        result.notes.push("两侧的「" + a.name + "」与「" + b.name + "」用途可能不同，未自动对应，请手动确认。");
      }
    });
    if (!result.keys.length) result.notes.push("尚未建议记录编号；请选择能对应同一条记录的列，需要时可以组合多个列。");
    if (!result.values.length) result.notes.push("尚未建议数值列；请选择业务含义与单位一致的两列。");
    if (!result.currencies.left) result.notes.push("尚未识别出两侧唯一的币种列；请确认币种列，或明确填写共同单位。");
    return result;
  }

  const api = Object.freeze({suggest: suggest});
  root.FctSuggestions = api;
  if (typeof module === "object" && module && module.exports) module.exports = api;
})(globalThis);
