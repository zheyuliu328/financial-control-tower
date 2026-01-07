# 快速启动指南 (Quick Start Guide)

> 📌 **目标**: 3 分钟内运行完整的财务控制塔系统

---

## 🚀 三步启动

### 步骤 1: 安装依赖
```bash
# 克隆项目后，进入项目目录
cd "Global Supply Chain & Finance Audit"

# 安装 Python 依赖
pip install -r requirements.txt
```

### 步骤 2: 初始化项目（一键完成）
```bash
python scripts/setup_project.py
```

**这一步会做什么**：
- ✅ 自动下载 DataCo 数据集（通过 kagglehub）
- ✅ 创建三个 ERP 数据库（Operations、Finance、Audit）
- ✅ 导入约 18 万条订单数据
- ✅ 分类到不同的表（订单、物流、财务）

**预计耗时**: 2-3 分钟（取决于网络速度）

**如果下载失败**：
```bash
# 手动下载数据集
# 1. 访问: https://www.kaggle.com/datasets/shashwatwork/dataco-smart-supply-chain-for-big-data-analysis
# 2. 下载 CSV 文件
# 3. 放入 data/raw/ 目录
# 4. 重新运行: python scripts/setup_project.py
```

### 步骤 3: 运行财务控制塔
```bash
python main.py
```

**输出示例**：
```
======================================================================
   DataCo Global Supply Chain & Finance Audit System
======================================================================

[Step 1] 检查环境...
✓ 数据库文件已就绪

[Step 2] 启动财务控制塔...
======================================================================

======================================================================
🗼 启动财务控制塔 (Financial Control Tower)
📅 审计日期: 2026-01-07 10:30:15
======================================================================

======================================================================
🔍 [Process 1] 业财对账 (Reconciliation: Ops vs Finance)
======================================================================

📊 对账结果：
   -> 业务侧订单数: 123,456
   -> 财务侧入账数: 123,450
   -> 完全匹配数量: 123,400

   ⚠️ 发现 6 笔订单未入财务账 (Revenue Leakage)!
   ...

======================================================================
🛡️ [Process 2] 供应链合规审计 (Compliance Audit)
======================================================================

   ⚠️ 检测到 127 笔'时间倒流'交易 (Timing Fraud)
   ...

======================================================================
📊 [Process 3] 生成经营分析报表 (Business Analysis)
======================================================================

📈 月度损益概览 (P&L - Last 6 Months)
...

✅ 所有审计流程执行完毕
```

---

## 📊 查看审计结果

### 方法 1: 使用 SQLite 命令行
```bash
sqlite3 data/audit.db

# 查看审计日志
sqlite> SELECT * FROM audit_logs ORDER BY audit_date DESC LIMIT 10;

# 统计各类风险
sqlite> SELECT risk_level, COUNT(*) as count 
        FROM audit_logs 
        GROUP BY risk_level;

# 退出
sqlite> .exit
```

### 方法 2: 使用 Python
```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('data/audit.db')

# 查看最新的审计日志
df = pd.read_sql("""
    SELECT 
        audit_date,
        entity_id as order_id,
        action as risk_type,
        risk_level,
        notes
    FROM audit_logs
    ORDER BY audit_date DESC
    LIMIT 20
""", conn)

print(df)
conn.close()
```

### 方法 3: 使用 GUI 工具
推荐使用 **DB Browser for SQLite**：
1. 下载: https://sqlitebrowser.org/
2. 打开 `data/audit.db`
3. 浏览 `audit_logs` 表

---

## 🔍 探索数据库

### Operations DB (业务数据)
```bash
sqlite3 data/db_operations.db

# 查看表结构
.tables

# 查看最近的订单
SELECT * FROM sales_orders ORDER BY order_date DESC LIMIT 10;

# 查看物流日志
SELECT * FROM shipping_logs LIMIT 10;
```

### Finance DB (财务数据)
```bash
sqlite3 data/db_finance.db

# 查看应收账款
SELECT * FROM accounts_receivable LIMIT 10;

# 查看总账
SELECT * FROM general_ledger LIMIT 10;
```

---

## 🎯 常见使用场景

### 场景 1: 查找收入漏记的订单
```python
import sqlite3
import pandas as pd

# 连接两个数据库
conn_ops = sqlite3.connect('data/db_operations.db')
conn_fin = sqlite3.connect('data/db_finance.db')

# 业务数据
df_ops = pd.read_sql("""
    SELECT order_id, sales 
    FROM sales_orders 
    WHERE order_status NOT IN ('CANCELED')
""", conn_ops)

# 财务数据
df_fin = pd.read_sql("""
    SELECT order_id, invoice_amount 
    FROM accounts_receivable
""", conn_fin)

# 对账
merged = df_ops.merge(df_fin, on='order_id', how='left', indicator=True)
missing = merged[merged['_merge'] == 'left_only']

print(f"发现 {len(missing)} 笔订单未入财务账")
print(missing.head())
```

### 场景 2: 查找负毛利订单
```sql
-- 在 Operations DB 中执行
SELECT 
    order_id,
    sales,
    profit,
    (profit / sales * 100) as margin_pct
FROM sales_orders
WHERE profit < 0 
    AND order_status NOT IN ('CANCELED')
ORDER BY profit ASC
LIMIT 20;
```

### 场景 3: 分析地区盈利能力
```sql
SELECT 
    customer_country,
    COUNT(*) as order_count,
    SUM(sales) as total_revenue,
    SUM(profit) as total_profit,
    (SUM(profit) / SUM(sales) * 100) as margin_pct
FROM sales_orders
WHERE order_status NOT IN ('CANCELED')
GROUP BY customer_country
ORDER BY total_profit DESC
LIMIT 10;
```

---

## 🛠️ 故障排除

### 问题 1: `ModuleNotFoundError: No module named 'kagglehub'`
**解决**:
```bash
pip install kagglehub
```

### 问题 2: 数据库文件不存在
**解决**:
```bash
# 重新运行初始化脚本
python scripts/setup_project.py
```

### 问题 3: 数据下载超时
**解决**:
1. 检查网络连接
2. 或者手动下载数据集（见步骤 2）

### 问题 4: "Permission denied" 错误
**解决**:
```bash
# 确保你在项目根目录
pwd

# 检查文件权限
chmod +x scripts/*.py
```

---

## 📚 下一步

完成快速启动后，你可以：

1. **阅读核心文档**:
   - [SQL_RECONCILIATION.md](docs/SQL_RECONCILIATION.md) - SQL 对账逻辑详解
   - [ARCHITECTURE.md](ARCHITECTURE.md) - 系统架构说明

2. **扩展功能**:
   - 修改 `src/audit/financial_control_tower.py` 添加新的审计规则
   - 创建自定义报表

3. **可视化**:
   - 使用 Plotly/Streamlit 创建仪表板
   - 生成 PDF 审计报告

4. **集成到简历**:
   - 截图系统运行结果
   - 准备面试时的演示

---

## 💡 面试时的演示建议

### 演示流程（5 分钟）

1. **展示项目启动** (1 分钟):
   ```bash
   python main.py
   ```
   边运行边解释："这是我构建的财务控制塔，它会自动执行业财对账、合规审计和报表生成。"

2. **展示对账逻辑** (2 分钟):
   - 打开 `SQL_RECONCILIATION.md`
   - 解释核心 SQL 逻辑
   - 说明："我使用 LEFT JOIN 找出业务数据和财务数据的差异。"

3. **展示审计结果** (1 分钟):
   ```bash
   sqlite3 data/audit.db
   SELECT * FROM audit_logs LIMIT 5;
   ```
   说明："系统自动发现了这些风险，并记录到审计日志中。"

4. **展示数据库架构** (1 分钟):
   - 打开 `ER_DIAGRAM.md`
   - 说明："我设计了三库分离的架构，模拟真实 ERP 环境。"

---

**准备好了吗？开始你的财务控制塔之旅！** 🚀

---

*最后更新: 2026-01-07*  
*作者: Zheyu Liu*
