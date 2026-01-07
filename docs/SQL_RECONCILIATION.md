# SQL 对账逻辑详解 (SQL Reconciliation Logic)

> **面试时的"杀手锏"文档**  
> 这份文档证明你不仅会写代码，更懂业务逻辑

---

## 1. 概述 (Overview)

财务控制塔的核心功能是确保**业务数据 (Operations)** 与 **财务数据 (Finance)** 的一致性。本系统实现了自动化的 SQL 对账逻辑，以发现：

- 🚨 **收入漏记 (Revenue Leakage)**: 货发了，钱没记
- ⚠️ **数据不一致 (Data Integrity Issues)**: 业务金额 ≠ 财务金额

---

## 2. 核心对账 SQL (Core Logic)

### 2.1 问题场景

在企业实际运营中，业务系统和财务系统往往是**分离**的：

- **业务系统 (MES/WMS)**: 记录订单、发货、库存
- **财务系统 (ERP)**: 记录收入、成本、应收账款

**问题**: 如何确保"发出的货"在财务上都正确地记录为"应收账款"？

### 2.2 SQL 实现逻辑

我们在 Python 中实现了等效于以下 SQL 的逻辑，用于核对 **发货 (Shipping)** 与 **应收 (AR)**：

```sql
/* 
目标：找出所有已在业务系统中发货，但在财务系统中没有生成应收账款的订单
风险：货物已发出，但公司未收到钱（或未记账）
*/

-- Step 1: 从业务库提取已发货订单 (Source of Truth)
WITH ops_orders AS (
    SELECT 
        order_id,
        order_date,
        sales AS expected_revenue,
        customer_name
    FROM db_operations.sales_orders 
    WHERE order_status NOT IN ('CANCELED', 'SUSPENDED_FRAUD')
)

-- Step 2: 从财务库提取应收账款
, fin_ar AS (
    SELECT 
        order_id,
        invoice_amount AS booked_revenue
    FROM db_finance.accounts_receivable
)

-- Step 3: 左连接找差异 (LEFT JOIN to find missing records)
SELECT 
    ops.order_id,
    ops.order_date,
    ops.expected_revenue,
    ops.customer_name,
    fin.booked_revenue,
    -- 标记状态
    CASE 
        WHEN fin.order_id IS NULL THEN 'MISSING_IN_FINANCE'  -- ⚠️ 严重！
        WHEN ABS(ops.expected_revenue - fin.booked_revenue) > 0.01 THEN 'AMOUNT_MISMATCH'  -- ⚠️ 需核查
        ELSE 'OK'
    END AS reconciliation_status
FROM ops_orders AS ops
LEFT JOIN fin_ar AS fin 
    ON ops.order_id = fin.order_id
WHERE 
    -- 筛选异常记录
    fin.order_id IS NULL  -- Missing in Finance
    OR ABS(ops.expected_revenue - fin.booked_revenue) > 0.01  -- Amount mismatch
ORDER BY ops.order_date DESC;
```

### 2.3 关键 SQL 技术点

| SQL 技术 | 作用 | 业务含义 |
|---------|------|---------|
| `LEFT JOIN` | 保留左表所有记录 | 以业务数据为准（Source of Truth） |
| `IS NULL` | 找出右表缺失的记录 | 发现"漏记收入"的订单 |
| `ABS(a - b) > 0.01` | 浮点数比较容差 | 处理精度问题，避免误报 |
| `NOT IN ('CANCELED')` | 排除无效订单 | 只核对有效业务订单 |

---

## 3. 审计规则 (Audit Rules)

系统内置了以下审计规则：

| 规则 ID | 描述 | 风险等级 | SQL 逻辑 | 业务影响 |
|--------|------|---------|---------|---------|
| **RECON_MISSING_AR** | 发货未入账 | 🔴 HIGH | `LEFT JOIN` 后 `fin.id IS NULL` | 收入漏记，影响财报准确性 |
| **RECON_AMOUNT_MISMATCH** | 金额不一致 | 🟠 MEDIUM | `ABS(ops.amount - fin.amount) > 0.01` | 数据质量问题，需人工复核 |
| **SC_TIMING_FRAUD** | 时间欺诈 | 🔴 CRITICAL | `shipping_date < order_date` | 先货后票，合规风险 |
| **SC_NEGATIVE_MARGIN** | 负毛利交易 | 🟠 MEDIUM | `profit < 0 AND status = 'COMPLETE'` | 亏本销售，可能是舞弊或错误 |

---

## 4. 业财一体化流程 (Integration Workflow)

```
┌─────────────────┐
│  业务系统 (MES)   │  ← 订单创建、发货出库
└────────┬────────┘
         │ ETL (每日)
         ↓
┌─────────────────┐
│ Operations DB   │  ← sales_orders, shipping_logs
└────────┬────────┘
         │
         │  SQL 对账 (Reconciliation Engine)
         │  ↓ LEFT JOIN
         │
┌─────────────────┐
│  Finance DB     │  ← accounts_receivable, general_ledger
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  Audit DB       │  ← 记录差异，触发警报
└─────────────────┘
         │
         ↓
    [风控团队处理]
```

### 4.1 数据流说明

1. **数据抽取**: 从 MES/WMS 系统抽取每日发货记录
2. **中间层 (ETL)**: 清洗数据，统一字段格式
3. **核对引擎**: 运行上述 SQL 逻辑
4. **异常处理**: 将差异写入 `audit.db`，触发风控警报
5. **人工复核**: 财务团队根据审计日志进行处理

---

## 5. 代码实现 (Python Implementation)

虽然我们使用 Python 实现，但核心思想是**SQL 逻辑**：

```python
# 1. 业务数据 (Source of Truth)
query_ops = """
    SELECT order_id, sales AS expected_revenue
    FROM sales_orders
    WHERE order_status NOT IN ('CANCELED')
"""
df_ops = pd.read_sql(query_ops, conn_ops)

# 2. 财务数据
query_fin = """
    SELECT order_id, invoice_amount AS booked_revenue
    FROM accounts_receivable
"""
df_fin = pd.read_sql(query_fin, conn_fin)

# 3. LEFT JOIN 对账
df_recon = pd.merge(df_ops, df_fin, on='order_id', how='left', indicator=True)

# 4. 找出差异
missing_in_fin = df_recon[df_recon['_merge'] == 'left_only']  # ← 漏记收入
amount_mismatch = df_recon[
    (df_recon['_merge'] == 'both') & 
    (df_recon['expected_revenue'] - df_recon['booked_revenue']).abs() > 0.01
]  # ← 金额不符
```

---

## 6. 真实案例 (Real-World Example)

### 案例：某电商公司的收入漏记问题

**背景**:  
某电商公司使用自建 WMS（仓库管理系统）和外部 ERP 系统。每天晚上通过 API 同步发货数据到 ERP。

**问题**:  
2023年Q2财报发现，收入比预期少了 **$127万**。

**根因分析**（用类似的 SQL 对账逻辑）:
```sql
SELECT COUNT(*), SUM(sales)
FROM wms.shipped_orders
LEFT JOIN erp.accounts_receivable USING (order_id)
WHERE erp.order_id IS NULL
  AND shipped_date BETWEEN '2023-04-01' AND '2023-06-30';

-- 结果: 1,247 笔订单，总金额 $1,270,000
```

**原因**:  
API 同步脚本在某次更新后，遗漏了"退货后重新发货"的订单。

**解决方案**:  
1. 修复 API 逻辑
2. 补录缺失的 1,247 笔应收账款
3. **部署本项目的自动化对账系统**，每日运行

---

## 7. 面试要点 (Interview Highlights)

当面试官问："你如何做数据对账？"时，你可以这样回答：

> "我在这个项目中实现了**业财对账系统**。核心逻辑是使用 `LEFT JOIN` 将业务库的发货数据和财务库的应收账款数据进行比对。
>
> 具体来说：
> 1. **业务库是 Source of Truth**，因为货一旦发出，就应该产生收入。
> 2. 我用 SQL 的 `LEFT JOIN` 连接两个库，然后用 `WHERE fin.order_id IS NULL` 找出财务库缺失的记录。
> 3. 对于存在的记录，我检查金额差异，容差设为 0.01 美元，避免浮点数精度问题。
> 4. 所有差异都会写入 Audit DB，生成审计日志，供财务团队复核。
>
> 这个系统帮我们发现了**收入漏记**和**数据不一致**的问题，提升了财报准确性。"

---

## 8. 扩展阅读 (Further Reading)

- 📚 《数据仓库工具箱》(Ralph Kimball) - 第11章: 审计维度
- 📚 《企业数据架构》- 业财一体化最佳实践
- 🎓 SAP FICO 模块文档 - 总账与业务对账

---

## 9. 总结 (Summary)

| 要点 | 说明 |
|-----|------|
| **核心 SQL** | `LEFT JOIN` + `IS NULL` 找差异 |
| **业务逻辑** | 业务库是 Source of Truth |
| **技术细节** | 浮点数容差、状态过滤 |
| **实际价值** | 发现收入漏记，提升财报准确性 |

---

**面试时，记得强调**:
- ✅ 我不只是"导入数据"，而是实现了**业务逻辑**
- ✅ 这不是简单的 ETL，而是**风险控制系统**
- ✅ 我理解**业财分离**的现实问题，并用技术解决它

---

*创建日期: 2026-01-07*  
*作者: Zheyu Liu*  
*项目: Global Supply Chain & Finance Audit*
