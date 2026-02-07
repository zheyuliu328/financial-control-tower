# Real Data Guide

## 真实数据接入路径

### 支持的数据格式

ERP 导出 CSV，必须包含以下字段：

| 字段名 | 类型 | 说明 |
|:-------|:-----|:-----|
| transaction_id | string | 交易ID |
| amount | float | 金额 |
| date | string | 日期 |
| account_code | string | 账户代码 |
| description | string | 描述（可选） |

### 快速开始

```bash
# 运行对账
make run-real CSV=path/to/erp.csv

# 仅验证
python scripts/run_real.py path/to/erp.csv --validate-only
```

### 示例 CSV

```csv
transaction_id,amount,date,account_code,description
TXN001,1000.00,2024-01-15,1000,Sales Revenue
TXN002,-500.00,2024-01-16,2000,Refund
```

### 输出工件

- `artifacts/reconciliation_report_{run_id}.json` - 对账报告
