# Quickstart Guide - 10 分钟跑通

> 本指南帮助你在 10 分钟内完整运行 FCT 系统并验证输出。

---

## 前置要求

- Python 3.8+
- 2GB 可用磁盘空间
- 网络连接（用于下载数据集）

---

## 步骤 1: 环境准备 (2 分钟)

```bash
# 克隆项目
git clone <repo-url> fct
cd fct

# 安装依赖
pip install -r requirements.txt
```

**依赖清单**:
- pandas>=2.0.0
- numpy>=1.24.0
- kagglehub>=0.2.0
- matplotlib>=3.7.0

---

## 步骤 2: 项目初始化 (3 分钟)

```bash
python scripts/setup_project.py
```

**这一步会做什么**:
- ✅ 自动下载 DataCo 数据集（约 18 万条订单）
- ✅ 创建三个 ERP 数据库（Operations、Finance、Audit）
- ✅ 导入并分类数据到不同表

**预期输出**:
```
======================================================================
🚀 开始项目初始化设置...
======================================================================
✅ 数据文件已存在: data/raw/DataCoSupplyChainDataset.csv

======================================================================
🏭 正在初始化 ERP 数据库架构...
======================================================================
✓ Operations DB 初始化完成
✓ Finance DB 初始化完成
✓ Audit DB 初始化完成

🎉 项目初始化完成！
```

**如果下载失败**: 见 [FAQ - 数据下载失败](./faq.md#数据下载失败)

---

## 步骤 3: 运行审计 (3 分钟)

```bash
python main.py
```

**预期输出**:
```
================================================================================
🗼 Financial Control Tower - Production Audit
📅 Audit Date: 2026-02-07 14:30:15
================================================================================

🔍 [Process 1] Reconciliation: Ops vs Finance
   → Operations orders: 123,456
   → Finance invoices: 123,400
   → Match rate: 99.95%
   
   ⚠️  Orphan Records Detected:
      - ORPHAN_OPS_ONLY: 45 orders (Revenue Leakage Risk)
      - ORPHAN_FIN_ONLY: 11 invoices (Ghost Invoice Risk)
      - AMOUNT_MISMATCH: 8 records
   
   ✅ LEFT JOIN Integrity: PASSED

🛡️ [Process 2] Fraud Detection with Metrics
   Rule: Timing Fraud
   → Precision: 94.2% | Recall: 89.5% | F1: 0.918
   
   Rule: Negative Margin
   → Precision: 87.3% | Recall: 92.1% | F1: 0.896

📊 [Process 3] P&L Report
   Month       Revenue         Profit      Margin
   2026-01     $1,274,500     $254,900     20.0%

✅ Audit complete. All metrics saved to audit.db
```

---

## 步骤 4: 验证输出 (2 分钟)

### 验证 1: 检查数据库文件

```bash
ls -lh data/
```

**预期看到**:
```
db_operations.db  (约 50MB)
db_finance.db     (约 30MB)
audit.db          (约 5MB)
```

### 验证 2: 查询审计日志

```bash
sqlite3 data/audit.db "SELECT * FROM audit_logs ORDER BY audit_date DESC LIMIT 5;"
```

**预期看到**: 至少包含以下字段的审计记录
- audit_date
- entity_id (订单ID)
- action (风险类型)
- risk_level

### 验证 3: 检查对账结果

```bash
sqlite3 data/audit.db "SELECT risk_level, COUNT(*) as count FROM audit_logs GROUP BY risk_level;"
```

**预期看到**: 不同风险等级的统计分布

---

## 下一步

- [配置真实 ERP 接入](./configuration.md) - 30 分钟接入生产环境
- [查看 FAQ 常见问题](./faq.md) - 故障排查

---

## 故障速查

| 现象 | 可能原因 | 解决方案 |
|:-----|:---------|:---------|
| `ModuleNotFoundError` | 依赖未安装 | `pip install -r requirements.txt` |
| 数据库文件不存在 | 初始化未运行 | 重新运行 `python scripts/setup_project.py` |
| Kaggle 下载超时 | 网络问题 | 手动下载数据，见 FAQ |
| 审计输出为空 | 数据库损坏 | 删除 `data/*.db` 重新初始化 |

---

*最后更新: 2026-02-08*
