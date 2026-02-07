# FAQ - 常见问题

---

## 安装问题

### Q: `setup_project.py` 报错 "kagglehub 未安装"

**A**: 脚本会自动安装，如失败请手动安装:
```bash
pip install kagglehub
python scripts/setup_project.py
```

### Q: 数据下载失败 / Kaggle 认证错误

**A**: 手动下载数据:
1. 访问 https://www.kaggle.com/datasets/shashwatwork/dataco-smart-supply-chain-for-big-data-analysis
2. 下载 CSV 文件
3. 放入 `data/raw/DataCoSupplyChainDataset.csv`
4. 重新运行 `python scripts/setup_project.py`

### Q: Python 版本要求

**A**: 需要 Python 3.8+。检查版本:
```bash
python --version
```

---

## 运行问题

### Q: 如何查看审计日志?

**A**: 使用 SQLite 查看:
```bash
# 命令行方式
sqlite3 data/audit.db "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 10;"

# 或使用 Python
import sqlite3
import pandas as pd
conn = sqlite3.connect('data/audit.db')
df = pd.read_sql("SELECT * FROM audit_logs ORDER BY audit_date DESC LIMIT 20", conn)
print(df)
```

### Q: 对账不匹配率过高怎么办?

**A**: 检查以下项目:
1. 确认时间范围一致（检查日期字段）
2. 检查货币单位（是否统一为同一币种）
3. 验证字段映射正确性（见 [configuration.md](./configuration.md)）
4. 检查是否有取消订单被错误计入

### Q: 数据库文件损坏如何恢复?

**A**: 
```bash
# 1. 备份损坏的数据库（如有需要）
cp data/audit.db data/audit.db.bak

# 2. 删除损坏的数据库
rm data/*.db

# 3. 重新初始化
python scripts/setup_project.py
```

### Q: 如何添加新的欺诈规则?

**A**: 编辑 `src/audit/financial_control_tower.py`:
```python
def detect_fraud(self):
    # 在现有规则后添加
    new_fraud = df[df['your_condition'] > threshold]
    self.fraud_cases.extend(new_fraud.to_dict('records'))
```

---

## 配置问题

### Q: SAP 连接超时

**A**: 
1. 检查网络连通性: `ping your-sap-server.com`
2. 确认 SAP 网关端口（默认 3300）开放
3. 增加超时设置:
```yaml
sap:
  rfc:
    timeout: 60  # 增加超时时间
```

### Q: 字段映射后数据类型错误

**A**: SAP 金额字段通常需要除以 100:
```python
# 在字段映射中添加转换
"sales": {
    "source_field": "NETWR",
    "transform": lambda x: float(x) / 100
}
```

### Q: 中文显示乱码

**A**: 确保使用 UTF-8 编码:
```python
# 读取 CSV 时指定编码
df = pd.read_csv('file.csv', encoding='utf-8')

# 写入数据库时确保连接使用 UTF-8
conn = sqlite3.connect('db.db')
conn.execute("PRAGMA encoding='UTF-8'")
```

---

## 性能问题

### Q: 审计运行太慢

**A**: 
1. 启用数据库索引:
```sql
CREATE INDEX idx_order_id ON sales_orders(order_id);
CREATE INDEX idx_invoice_id ON accounts_receivable(invoice_id);
```

2. 分批处理大数据集:
```python
# 修改 main.py 中的批处理大小
BATCH_SIZE = 10000
```

### Q: 内存不足

**A**: 
1. 减少批处理大小
2. 使用数据库游标而非一次性加载
3. 关闭不必要的日志输出

---

## 其他问题

### Q: 如何导出审计报告?

**A**: 
```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('data/audit.db')
df = pd.read_sql("SELECT * FROM audit_logs", conn)
df.to_csv('audit_report.csv', index=False)
df.to_excel('audit_report.xlsx', index=False)
```

### Q: 如何清空审计日志?

**A**: 
```bash
sqlite3 data/audit.db "DELETE FROM audit_logs;"
```

**注意**: 审计日志通常不应删除，如需归档请先备份。

### Q: 项目是否支持其他数据库?

**A**: 支持。修改 `src/data_engineering/db_connector.py`:
```python
# PostgreSQL 示例
import psycopg2
conn = psycopg2.connect(
    host="localhost",
    database="fct",
    user="user",
    password="password"
)
```

---

*最后更新: 2026-02-08*
