# 🏗️ 企业级 ERP 架构设计

## 架构概述

本项目采用**分离式数据库架构**，模拟真实企业 ERP 环境。数据从单一 CSV 文件被拆分到三个独立的数据库系统中，实现**物理隔离**和**职责分离**。

## 数据库架构

### 1. Operations Database (`db_operations.db`)

**职责**：运营数据的源系统（Source of Truth for Operations）

**表结构**：
- `products` - 产品主数据
- `sales_orders` - 销售订单
- `shipping_logs` - 物流日志

**数据来源**：从 CSV 中的订单、产品、物流相关字段提取

### 2. Finance Database (`db_finance.db`)

**职责**：财务数据的源系统（Source of Truth for Finance）

**表结构**：
- `general_ledger` - 总账（从订单数据生成借贷分录）
- `accounts_receivable` - 应收账款

**数据来源**：从 CSV 中的销售金额、利润等字段生成财务记录

### 3. Audit Database (`audit.db`)

**职责**：审计和风险管理系统

**表结构**：
- `audit_logs` - 审计日志（初始为空，由审计流程填充）
- `risk_flags` - 风险标记（初始为空，由风险检测流程填充）

## 数据流架构

```
原始 CSV 文件
    ↓
[ETL 脚本: init_erp_databases.py]
    ↓
    ├─→ Operations DB (运营数据)
    ├─→ Finance DB (财务数据)
    └─→ Audit DB (审计结构，空表)
    ↓
[审计系统: main.py]
    ↓
跨系统 SQL 查询 + ETL
    ↓
审计报告
```

## 为什么这样设计？

### 1. 模拟真实环境

在真实企业中：
- **运营系统**（如 SAP MM/SD）管理订单和物流
- **财务系统**（如 SAP FI/CO）管理总账和应收应付
- **审计系统**（如 GRC）独立运行，定期从各系统抽取数据

### 2. 支持跨系统对账

面试官问："如何处理跨系统的财务对账？"

**我们的答案**：
> "我模拟了业务库和财务库的物理隔离。通过 SQL ETL 定期从 Operations DB 抽取发货记录，与 Finance DB 的应收账款进行核对。这确保了数据一致性，并支持自动化对账流程。"

### 3. 职责分离

- **Operations DB**：业务运营的单一数据源
- **Finance DB**：财务核算的单一数据源
- **Audit DB**：独立的审计追踪系统

## 技术实现

### 数据库连接器 (`db_connector.py`)

提供统一的接口访问三个数据库：

```python
from src.data_engineering.db_connector import ERPDatabaseConnector

connector = ERPDatabaseConnector()

# 单数据库查询
df = connector.execute_query_df('operations', "SELECT * FROM sales_orders LIMIT 10")

# 跨数据库查询（模拟 ETL）
results = connector.cross_db_query(
    query_operations="SELECT order_id, sales FROM sales_orders",
    query_finance="SELECT order_id, invoice_amount FROM accounts_receivable"
)
```

### 跨系统对账示例

```python
# 1. 从 Operations DB 获取订单金额
df_orders = connector.execute_query_df('operations', 
    "SELECT order_id, sales FROM sales_orders")

# 2. 从 Finance DB 获取应收账款金额
df_ar = connector.execute_query_df('finance',
    "SELECT order_id, invoice_amount FROM accounts_receivable")

# 3. 在内存中合并（模拟 ETL 工具）
merged = df_orders.merge(df_ar, on='order_id', how='left')
mismatches = merged[abs(merged['sales'] - merged['invoice_amount']) > 0.01]

# 4. 将不匹配记录写入 Audit DB
# (实现审计日志记录)
```

## 扩展方向

### 1. 实现真正的 ETL 流程
- 使用 Apache Airflow 调度定期数据同步
- 实现增量更新而非全量重建

### 2. 添加数据验证层
- 在 ETL 过程中进行数据质量检查
- 自动标记异常数据到 Audit DB

### 3. 实现审计规则引擎
- 在 Audit DB 中定义审计规则
- 自动执行规则并生成风险标记

### 4. 支持更多数据库类型
- PostgreSQL（生产环境）
- MySQL（备选方案）
- 通过 SQLAlchemy 实现数据库抽象

## 面试要点

当被问到"你如何处理跨系统数据整合"时：

1. **展示架构理解**：说明分离式数据库的设计理念
2. **展示技术能力**：演示 SQL 查询和 ETL 流程
3. **展示业务理解**：解释为什么需要跨系统对账
4. **展示工程能力**：展示代码的模块化和可扩展性

---

**这就是从"数据分析项目"到"企业级 ERP 架构"的升级！** 🚀



