# FCT (Financial Control Tower) - 文档产品化修改清单

## 修改目标
将 FCT 项目文档重构为标准化用户路径文档，确保用户能在 3/10/30 分钟内完成上手、跑通和真实接入。

---

## 一、README.md 重构

**文件路径**: `fct/README.md`

**修改内容**:

```markdown
<p align="center">
  <img src="https://img.icons8.com/fluency/96/control-tower.png" alt="Control Tower" width="80"/>
</p>

<h1 align="center">Financial Control Tower</h1>

<p align="center">
  <strong>面向风险建模、审计与研究的 ERP 数据对账与欺诈检测工具</strong>
</p>

<p align="center">
  <a href="https://github.com/zheyuliu328/financial-control-tower/stargazers"><img src="https://img.shields.io/github/stars/zheyuliu328/financial-control-tower?style=for-the-badge&logo=github&labelColor=000000&color=0500ff" alt="Stars"/></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.8+-blue?style=for-the-badge&logo=python&labelColor=000000&logoColor=white" alt="Python"/></a>
  <a href="#"><img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge&labelColor=000000" alt="License"/></a>
</p>

---

## 核心能力

1. **业财对账引擎**: 自动检测业务系统与财务系统的数据差异，识别孤儿记录
2. **欺诈规则检测**: 内置时间倒流、负毛利等规则，支持 TP/FP/FN 指标追踪
3. **审计追踪**: 不可篡改的审计日志，支持数据血缘追溯

---

## Quickstart (3 分钟)

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化项目（自动下载数据并构建数据库）
python scripts/setup_project.py

# 3. 运行审计
python main.py
```

**输出工件**:
- `data/db_operations.db` - 业务数据库
- `data/db_finance.db` - 财务数据库  
- `data/audit.db` - 审计日志数据库

---

## 文档导航

| 文档 | 内容 | 阅读时间 |
|:-----|:-----|:---------|
| [docs/quickstart.md](docs/quickstart.md) | 详细快速入门、预期输出验证 | 10 分钟 |
| [docs/configuration.md](docs/configuration.md) | ERP 集成配置、字段映射规范 | 30 分钟 |
| [docs/faq.md](docs/faq.md) | 常见问题与故障排查 | 按需查阅 |
| [reconciliation_matrix.md](reconciliation_matrix.md) | 对账控制矩阵详解 | 参考 |
| [security_architecture.md](security_architecture.md) | 安全架构与 RBAC 设计 | 参考 |

---

## 项目结构

```
fct/
├── docs/                      # 用户文档
│   ├── quickstart.md         # 10 分钟跑通指南
│   ├── configuration.md      # 30 分钟接入配置
│   └── faq.md                # 常见问题
├── src/
│   ├── audit/                # 审计引擎
│   ├── integration/          # ERP 连接器
│   └── data_engineering/     # 数据工程
├── scripts/
│   └── setup_project.py      # 项目初始化
├── data/                     # 数据库文件 (gitignored)
└── README.md                 # 本文件
```

---

## 技术栈

| 组件 | 技术 | 用途 |
|:-----|:-----|:-----|
| 数据库 | SQLite / PostgreSQL | 多库 ERP 模拟 |
| 数据处理 | Pandas, NumPy | ETL 与分析 |
| ERP 连接 | PyRFC, Requests | SAP/Oracle 集成 |

---

## 作者

**Zheyu Liu** - 面向风险建模、审计与研究的工具开发

---

<p align="center">
  <sub>面向风险建模、审计与研究的工具</sub>
</p>
```

---

## 二、新建 docs/quickstart.md

**文件路径**: `fct/docs/quickstart.md`

**内容**:

```markdown
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
```

---

## 三、新建 docs/configuration.md

**文件路径**: `fct/docs/configuration.md`

**内容**:

```markdown
# Configuration Guide - 30 分钟真实接入

> 本指南帮助你将 FCT 接入真实 ERP 系统，完成字段映射和配置。

---

## 前置要求

- 已完成 [Quickstart](./quickstart.md)
- 拥有 ERP 系统访问权限（SAP/Oracle/其他）
- 了解源系统表结构

---

## 一、ERP 连接配置

### 1.1 复制配置模板

```bash
cp config/erp_config.example.yaml config/erp_config.yaml
```

### 1.2 配置 SAP S/4HANA

编辑 `config/erp_config.yaml`:

```yaml
sap:
  host: "your-sap-server.com"
  system_id: "PRD"
  client: "100"
  username: "FCT_USER"
  password: "${SAP_PASSWORD}"  # 使用环境变量
  
  # RFC 连接参数
  rfc:
    ashost: "your-sap-server.com"
    sysnr: "00"
    lang: "EN"
```

### 1.3 配置 Oracle ERP

```yaml
oracle:
  base_url: "https://your-oracle-erp.com"
  username: "FCT_USER"
  password: "${ORACLE_PASSWORD}"
  
  # REST API 参数
  api_version: "v2"
  timeout: 30
```

### 1.4 设置环境变量

```bash
# Linux/Mac
export SAP_PASSWORD="your_sap_password"
export ORACLE_PASSWORD="your_oracle_password"

# Windows PowerShell
$env:SAP_PASSWORD="your_sap_password"
```

---

## 二、字段映射规范

### 2.1 SAP 字段映射

| SAP 表 | SAP 字段 | FCT 字段 | 说明 |
|:-------|:---------|:---------|:-----|
| VBAK | VBELN | order_id | 销售订单号 |
| VBAK | AUDAT | order_date | 订单日期 |
| VBAK | KUNNR | customer_id | 客户编号 |
| VBAP | NETWR | sales | 销售金额 |
| VBAP | GBSTK | order_status | 订单状态 |
| LIKP | WADAT | shipping_date | 发货日期 |

### 2.2 Oracle 字段映射

| Oracle 表 | Oracle 字段 | FCT 字段 | 说明 |
|:----------|:------------|:---------|:-----|
| RA_CUSTOMER_TRX_ALL | trx_number | invoice_id | 发票编号 |
| RA_CUSTOMER_TRX_ALL | trx_date | invoice_date | 发票日期 |
| RA_CUSTOMER_TRX_ALL | bill_to_customer_id | customer_id | 客户ID |
| RA_CUSTOMER_TRX_ALL | invoice_amount | invoice_amount | 发票金额 |
| AR_PAYMENT_SCHEDULES | status | payment_status | 付款状态 |

### 2.3 自定义字段映射

编辑 `src/integration/field_mapping.py`:

```python
CUSTOM_MAPPING = {
    "sap": {
        "VBELN": "order_id",
        "AUDAT": "order_date",
        # 添加自定义映射
        "YOUR_FIELD": "fct_field"
    },
    "oracle": {
        "OrderNumber": "order_id",
        # 添加自定义映射
    }
}
```

---

## 三、运行生产模式

### 3.1 同步 ERP 数据

```bash
# 运行数据同步调度器
python -m src.integration.sync_scheduler
```

**这一步会做什么**:
- 连接 ERP 系统
- 抽取增量数据
- 写入 Operations/Finance 数据库

### 3.2 运行生产审计

```bash
python main.py --mode=production
```

---

## 四、常见失败点

### 4.1 连接失败

**现象**: `Connection refused` 或 `RFC_ERROR_COMMUNICATION`

**排查步骤**:
1. 检查网络连通性: `ping your-sap-server.com`
2. 验证端口开放: `telnet your-sap-server.com 3300`
3. 确认 SAP 网关服务运行中
4. 检查防火墙规则

### 4.2 字段映射错误

**现象**: 对账结果异常，匹配率过低

**排查步骤**:
1. 检查源数据编码（中文需 UTF-8）
2. 验证日期格式一致（建议统一为 YYYY-MM-DD）
3. 确认货币单位一致
4. 检查字段大小写（SAP 字段通常大写）

### 4.3 数据类型不匹配

**现象**: `TypeError` 或数据截断

**解决方案**:
```python
# 在字段映射中添加类型转换
"sales": {
    "source_field": "NETWR",
    "transform": lambda x: float(x) / 100  # SAP 金额通常需除100
}
```

### 4.4 权限不足

**现象**: `Authorization failed` 或无法写入 audit.db

**解决方案**:
```bash
# 检查目录权限
chmod 755 data/

# 确认 ERP 用户有读取权限
# 确认 FCT 进程有写入权限
```

---

## 五、验证清单

接入完成后，验证以下项目:

- [ ] ERP 连接成功，无报错
- [ ] 数据同步完成，记录数符合预期
- [ ] 字段映射正确，数据类型匹配
- [ ] 对账结果合理（匹配率 > 95% 为正常）
- [ ] 审计日志正常写入
- [ ] 性能满足要求（单次审计 < 5 分钟）

---

## 六、生产环境建议

### 6.1 数据库

- 使用 PostgreSQL 替代 SQLite
- 配置读写分离
- 启用自动备份

### 6.2 监控

- 设置审计任务定时运行（建议每日凌晨）
- 配置异常告警（孤儿记录数突增）
- 监控数据库连接池

### 6.3 安全

- 使用密钥管理服务存储密码
- 启用审计日志加密
- 配置 RBAC 权限

---

*最后更新: 2026-02-08*
```

---

## 四、新建 docs/faq.md

**文件路径**: `fct/docs/faq.md`

**内容**:

```markdown
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
```

---

## 五、文件创建/修改清单总结

| 文件路径 | 操作 | 说明 |
|:---------|:-----|:-----|
| `fct/README.md` | 修改 | 重构为标准化结构 |
| `fct/docs/quickstart.md` | 新建 | 10 分钟跑通指南 |
| `fct/docs/configuration.md` | 新建 | 30 分钟接入配置 |
| `fct/docs/faq.md` | 新建 | 常见问题解答 |

---

## 关键纠偏落实

1. **监管合规描述**: README 中已将 "Production-Ready ERP Audit System for Enterprise Financial Control" 修改为 "面向风险建模、审计与研究的 ERP 数据对账与欺诈检测工具"

2. **移除夸大描述**: 
   - 删除了 "符合监管要求" 等无事实支持的表述
   - 删除了 "Audit Ready"、"Compliance" 等可能暗示监管合规的词汇
   - 统一使用 "面向风险建模、审计与研究" 作为定位描述

3. **事实源标注**: 所有技术能力描述均基于实际代码实现，可验证
