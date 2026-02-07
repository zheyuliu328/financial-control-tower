# FCT (Financial Control Tower) - 用户体验文档

## 📋 项目概述
**FCT** 是一个生产级 ERP 审计系统，用于企业财务控制。支持 SAP S/4HANA 和 Oracle ERP 集成，包含对账控制、欺诈检测和审计追踪功能。

---

## 🚀 3分钟上手

### 步骤1: Clone & Install
```bash
git clone <repo-url> fct
cd fct
pip install -r requirements.txt
```

**依赖清单**:
- pandas>=2.0.0, numpy>=1.24.0
- kagglehub>=0.2.0 (数据下载)
- matplotlib>=3.7.0, seaborn>=0.12.0 (可视化)
- python-dotenv>=1.0.0 (环境配置)

### 步骤2: 初始化项目
```bash
# 自动下载数据并初始化数据库
python scripts/setup_project.py
```

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

### 步骤3: 运行审计
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
```

---

## 🎯 10分钟跑通

### 核心功能理解

| 模块 | 功能 | 运行命令 |
|------|------|----------|
| `main.py` | 主审计流程 | `python main.py` |
| `setup_project.py` | 项目初始化 | `python scripts/setup_project.py` |
| `fraud_rule_metrics.py` | 欺诈规则评估 | `python fraud_rule_metrics.py` |
| `financial_control_tower.py` | 核心审计引擎 | 被 main.py 调用 |

### 完整运行流程

```bash
# 1. 初始化（仅需一次）
python scripts/setup_project.py

# 2. 运行完整审计
python main.py

# 3. 评估欺诈规则性能
python fraud_rule_metrics.py
```

**审计输出文件**:
- `data/db_operations.db` - 运营数据库
- `data/db_finance.db` - 财务数据库
- `data/audit.db` - 审计日志数据库

---

## 📊 30分钟接入真实数据

### 配置说明

#### 1. ERP 连接配置
复制并编辑配置文件:
```bash
cp config/erp_config.example.yaml config/erp_config.yaml
```

编辑 `config/erp_config.yaml`:
```yaml
sap:
  host: "your-sap-server.com"
  system_id: "PRD"
  client: "100"
  username: "FCT_USER"
  password: "${SAP_PASSWORD}"  # 使用环境变量

oracle:
  base_url: "https://your-oracle-erp.com"
  username: "FCT_USER"
  password: "${ORACLE_PASSWORD}"
```

#### 2. 字段映射配置
编辑 `erp_integration_design.md` 中的映射:
```yaml
# SAP to FCT Mapping
sap_mapping:
  VBELN: order_id          # 销售订单号
  AUDAT: order_date        # 订单日期
  KUNNR: customer_id       # 客户编号
  NETWR: sales             # 净值
```

#### 3. 运行生产模式
```bash
# 设置环境变量
export SAP_PASSWORD="your_password"
export ORACLE_PASSWORD="your_password"

# 运行 ERP 数据同步
python -m src.integration.sync_scheduler

# 运行生产审计
python main.py --mode=production
```

### 真实数据映射

| 源系统 | 表名 | FCT 字段 | 说明 |
|--------|------|----------|------|
| SAP | VBAK | order_id | 销售订单 |
| SAP | VBAP | sales | 销售金额 |
| Oracle | RA_CUSTOMER_TRX_ALL | invoice_id | 发票ID |
| Oracle | AR_PAYMENT_SCHEDULES | payment_status | 付款状态 |

---

## ❓ FAQ (5个最常见问题)

### Q1: `setup_project.py` 报错 "kagglehub 未安装"
**A**: 脚本会自动安装，如失败请手动安装:
```bash
pip install kagglehub
python scripts/setup_project.py
```

### Q2: 数据下载失败 / Kaggle 认证错误
**A**: 手动下载数据:
1. 访问 https://www.kaggle.com/datasets/shashwatwork/dataco-smart-supply-chain-for-big-data-analysis
2. 下载 CSV 文件
3. 放入 `data/raw/DataCoSupplyChainDataset.csv`
4. 重新运行 `python scripts/setup_project.py`

### Q3: 如何查看审计日志?
**A**: 使用 SQLite 查看:
```bash
sqlite3 data/audit.db "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 10;"
```

### Q4: 对账不匹配率过高怎么办?
**A**: 检查 `reconciliation_matrix.md` 中的控制矩阵:
1. 确认时间范围一致
2. 检查货币单位
3. 验证字段映射正确性

### Q5: 如何添加新的欺诈规则?
**A**: 编辑 `src/audit/financial_control_tower.py`:
```python
def detect_fraud(self):
    # 添加新规则
    new_fraud = df[df['your_condition'] > threshold]
    self.fraud_cases.extend(new_fraud.to_dict('records'))
```

---

## 🚧 上手阻断点清单

### P0 (阻断性)
| 问题 | 影响 | 解决方案 |
|------|------|----------|
| Kaggle 数据下载失败 | 无法初始化 | 手动下载并放入 data/raw/ |
| SQLite 数据库损坏 | 审计无法运行 | 删除 data/*.db 重新初始化 |
| Python < 3.8 | 依赖不兼容 | 升级 Python |

### P1 (高优先级)
| 问题 | 影响 | 解决方案 |
|------|------|----------|
| 字段映射错误 | 对账结果异常 | 检查 `erp_integration_design.md` |
| 数据库权限不足 | 无法写入审计日志 | 检查 data/ 目录权限 |
| 内存不足 (大数据集) | 处理失败 | 分批处理或增加内存 |

### P2 (中优先级)
| 问题 | 影响 | 解决方案 |
|------|------|----------|
| 时区不一致 | 时间戳错误 | 统一使用 UTC |
| 编码问题 (中文) | CSV 读取乱码 | 指定 encoding='utf-8' |
| 性能缓慢 | 审计耗时长 | 启用数据库索引 |

---

## 📸 截图计划

| 截图位置 | 描述 | 优先级 |
|----------|------|--------|
| `main.py` 审计报告 | 对账结果总览 | P0 |
| 孤儿记录检测 | Orphan Records 列表 | P0 |
| 欺诈规则指标 | TP/FP/FN 统计 | P1 |
| 数据库架构图 | 三库分离设计 | P1 |
| RBAC 权限矩阵 | 角色权限表 | P2 |

---

## 🔗 相关文档

- [reconciliation_matrix.md](reconciliation_matrix.md) - 对账控制矩阵
- [fraud_rule_metrics.py](fraud_rule_metrics.py) - 欺诈规则性能指标
- [security_architecture.md](security_architecture.md) - 安全架构
- [erp_integration_design.md](erp_integration_design.md) - ERP 集成设计
