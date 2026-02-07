# 术语表 (Glossary)

## 通用术语

| 术语 | 英文 | 定义 |
|:-----|:-----|:-----|
| 信息系数 | Information Coefficient (IC) | 因子值与下期收益的相关系数，衡量预测能力 |
| 信息比率 | Information Ratio (IR) | IC 均值除以 IC 标准差，衡量因子稳定性 |
| t 统计量 | t-statistic | 检验均值显著性的统计量，\|t\|>2 通常认为显著 |
| p 值 | p-value | 显著性水平，<0.05 通常认为统计显著 |
| 人口稳定性指数 | Population Stability Index (PSI) | 衡量分布变化的指标，<0.1 稳定，>0.25 不稳定 |

## fct 专用术语

| 术语 | 英文 | 定义 |
|:-----|:-----|:-----|
| 孤儿记录 | Orphan Record | 在一个系统中存在但在另一系统中缺失的记录 |
| LEFT JOIN 完整性 | LEFT JOIN Integrity | 对账查询中确保无数据丢失的验证方法 |
| TP/FP/FN | True/False Positive/Negative | 真阳性/假阳性/假阴性，用于评估规则准确性 |
| 对账控制矩阵 | Reconciliation Control Matrix (RCM) | 系统间数据一致性校验框架 |
| 欺诈规则 | Fraud Rule | 基于业务逻辑定义的异常检测规则 |
| 审计追踪 | Audit Trail | 记录所有数据变更的不可篡改日志 |

## 参考

- [项目限制说明](limitations.md)
- [项目架构文档](../ARCHITECTURE.md)
