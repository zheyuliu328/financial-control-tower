# Reconciliation Control Matrix (RCM) - 对账控制矩阵

## 1. 概述

本文档定义了 FCT (Financial Control Tower) 系统的对账控制矩阵，用于确保 LEFT JOIN 完整性，检测孤儿记录，并建立完整的对账控制框架。

## 2. 控制目标

| 控制编号 | 控制目标 | 重要性 |
|:---------|:---------|:-------|
| RCM-001 | 确保所有业务订单在财务系统中有对应记录 | 高 |
| RCM-002 | 检测并处理孤儿记录（Orphan Records） | 高 |
| RCM-003 | 保证金额匹配的准确性 | 高 |
| RCM-004 | 建立完整的审计追踪 | 中 |

## 3. 对账控制矩阵

### 3.1 数据源映射

| 业务系统 (Operations) | 财务系统 (Finance) | 匹配键 | 匹配规则 |
|:----------------------|:-------------------|:-------|:---------|
| sales_orders.order_id | accounts_receivable.order_id | order_id | 精确匹配 |
| sales_orders.sales | accounts_receivable.invoice_amount | order_id | 金额差异 ≤ $0.01 |
| sales_orders.order_date | accounts_receivable.invoice_date | order_id | 日期差异 ≤ 1天 |

### 3.2 孤儿记录检测规则

```sql
-- 类型1: 业务有，财务无 (Revenue Leakage)
SELECT 
    o.order_id,
    o.sales AS expected_revenue,
    o.customer_name,
    'ORPHAN_OPS_ONLY' AS orphan_type
FROM operations.sales_orders o
LEFT JOIN finance.accounts_receivable f ON o.order_id = f.order_id
WHERE f.order_id IS NULL
  AND o.order_status NOT IN ('CANCELED', 'CANCELLED', 'SUSPECTED_FRAUD');

-- 类型2: 财务有，业务无 (Ghost Invoice)
SELECT 
    f.order_id,
    f.invoice_amount,
    f.customer_name,
    'ORPHAN_FIN_ONLY' AS orphan_type
FROM finance.accounts_receivable f
LEFT JOIN operations.sales_orders o ON f.order_id = o.order_id
WHERE o.order_id IS NULL;
```

### 3.3 完整性检查清单

| 检查项 | 检查方法 | 阈值 | 处理流程 |
|:-------|:---------|:-----|:---------|
| 孤儿记录率 | COUNT(orphan) / COUNT(total) | ≤ 0.1% | 自动告警 → 人工复核 |
| 金额差异率 | SUM(|diff|) / SUM(sales) | ≤ 0.01% | 自动标记 → 差异分析 |
| 时间差异率 | COUNT(date_diff > 1) / COUNT(total) | ≤ 1% | 自动标记 → 合规审查 |
| 重复记录 | COUNT(DISTINCT order_id) vs COUNT(*) | = 100% | 数据清洗 → 重新对账 |

## 4. 孤儿记录处理流程

### 4.1 检测流程

```
┌─────────────────┐
│  执行对账查询    │
└────────┬────────┘
         ▼
┌─────────────────┐
│  识别孤儿记录    │
└────────┬────────┘
         ▼
┌─────────────────┐     ┌─────────────────┐
│  分类孤儿类型    │────▶│ OPS_ONLY        │
└─────────────────┘     │ FIN_ONLY        │
                        │ AMOUNT_MISMATCH │
                        └─────────────────┘
```

### 4.2 处理策略

| 孤儿类型 | 可能原因 | 处理策略 | 责任方 |
|:---------|:---------|:---------|:-------|
| ORPHAN_OPS_ONLY | 订单未开票、数据同步延迟 | 自动创建应收账款记录 | 财务系统 |
| ORPHAN_FIN_ONLY | 幽灵发票、测试数据残留 | 标记为异常，人工审核 | 审计团队 |
| AMOUNT_MISMATCH | 折扣未同步、汇率差异 | 差异分析报告 | 财务分析师 |
| DATE_MISMATCH | 时区问题、批量处理延迟 | 允许1天容差 | 系统自动 |

## 5. 对账执行计划

### 5.1 执行频率

| 对账类型 | 频率 | 执行时间 | 负责人 |
|:---------|:-----|:---------|:-------|
| 实时对账 | 每笔交易 | 自动触发 | 系统 |
| 日终对账 | 每日 | 23:00 | 系统 |
| 月度对账 | 每月1日 | 02:00 | 系统 + 财务 |
| 年度审计 | 每年 | 财年结束后 | 审计团队 |

### 5.2 对账报告模板

```
================================================================================
对账控制报告 (Reconciliation Control Report)
报告日期: {date}
报告周期: {start_date} 至 {end_date}
================================================================================

1. 对账概况
   - 业务订单总数: {total_ops_orders}
   - 财务记录总数: {total_fin_records}
   - 匹配成功数: {matched_count}
   - 匹配成功率: {match_rate}%

2. 孤儿记录统计
   - 业务孤儿数 (ORPHAN_OPS_ONLY): {ops_orphan_count}
   - 财务孤儿数 (ORPHAN_FIN_ONLY): {fin_orphan_count}
   - 孤儿记录率: {orphan_rate}%

3. 差异分析
   - 金额差异数: {amount_mismatch_count}
   - 金额差异总额: ${amount_mismatch_total}
   - 日期差异数: {date_mismatch_count}

4. 处理状态
   - 已自动处理: {auto_resolved}
   - 待人工审核: {pending_review}
   - 已确认异常: {confirmed_anomaly}

5. 建议措施
   {recommendations}
================================================================================
```

## 6. 监控与告警

### 6.1 关键指标 (KPIs)

| 指标 | 计算公式 | 目标值 | 告警阈值 |
|:-----|:---------|:-------|:---------|
| 对账完成率 | 已匹配订单 / 总订单 | ≥ 99.9% | < 99.5% |
| 孤儿记录率 | 孤儿记录数 / 总记录数 | ≤ 0.1% | > 0.5% |
| 差异解决时效 | 平均解决时间 | ≤ 24小时 | > 48小时 |
| 自动处理率 | 自动处理 / 总异常 | ≥ 80% | < 60% |

### 6.2 告警级别

| 级别 | 触发条件 | 通知方式 | 响应时间 |
|:-----|:---------|:---------|:---------|
| INFO | 孤儿率 0.1% - 0.5% | 系统日志 | 无 |
| WARNING | 孤儿率 0.5% - 1% | 邮件通知 | 4小时 |
| CRITICAL | 孤儿率 > 1% | 邮件 + SMS | 1小时 |
| EMERGENCY | 系统无法对账 | 全员通知 | 立即 |

## 7. 审计追踪

所有对账操作必须记录到 audit_logs 表：

```sql
CREATE TABLE reconciliation_audit (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reconciliation_period TEXT,
    total_ops_records INTEGER,
    total_fin_records INTEGER,
    matched_records INTEGER,
    orphan_ops_count INTEGER,
    orphan_fin_count INTEGER,
    amount_mismatch_count INTEGER,
    executed_by TEXT,
    execution_status TEXT,
    notes TEXT
);
```

## 8. 附录

### 8.1 术语定义

| 术语 | 定义 |
|:-----|:-----|
| 孤儿记录 (Orphan Record) | 在一个系统中存在但在关联系统中找不到对应记录的数据 |
| LEFT JOIN 完整性 | 确保 LEFT JOIN 操作不会遗漏预期的匹配记录 |
| 对账控制矩阵 | 系统化的对账检查框架，定义检查项、方法和阈值 |
| 收入漏记 (Revenue Leakage) | 货物已发出但财务未记录收入的业务场景 |

### 8.2 相关文档

- `erp_integration_design.md` - ERP 集成设计
- `security_architecture.md` - 权限分离架构
- `fraud_rule_metrics.py` - 欺诈规则性能指标

---

**文档版本**: 1.0  
**最后更新**: 2026-02-07  
**维护者**: Financial Control Tower Team
