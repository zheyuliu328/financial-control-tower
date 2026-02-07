<p align="center">
  <img src="https://img.icons8.com/fluency/96/control-tower.png" alt="Control Tower" width="80"/>
</p>

<h1 align="center">Financial Control Tower</h1>

<p align="center">
  <strong>面向企业财务审计与风控研究的 ERP 数据对账工具</strong>
</p>

<p align="center">
  <a href="https://github.com/zheyuliu328/financial-control-tower/stargazers"><img src="https://img.shields.io/github/stars/zheyuliu328/financial-control-tower?style=for-the-badge&logo=github&labelColor=000000&color=0500ff" alt="Stars"/></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.8+-blue?style=for-the-badge&logo=python&labelColor=000000&logoColor=white" alt="Python"/></a>
  <a href="#"><img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge&labelColor=000000" alt="License"/></a>
</p>

<p align="center">
  <a href="#核心能力">核心能力</a> •
  <a href="#快速开始">快速开始</a> •
  <a href="#项目结构">项目结构</a> •
  <a href="#项目定位与限制">限制说明</a>
</p>

---

## 一句话定位

面向企业财务审计与风控研究的 ERP 数据对账工具，演示多系统数据一致性校验与异常检测方法。

---

## 核心能力

1. **多源数据对账**: 模拟 SAP/Oracle ERP 系统间数据一致性校验，识别孤儿记录与金额差异
2. **异常检测规则**: 实现欺诈检测规则（时序异常、负毛利等）并追踪 TP/FP/FN 指标
3. **审计可追溯性**: 生成不可篡改的审计日志，支持 LEFT JOIN 完整性验证

---

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化演示数据库
python scripts/setup_project.py

# 3. 运行审计流程
python main.py
```

### 输出工件

运行后生成：
- `data/db_operations.db` - 运营系统模拟数据
- `data/db_finance.db` - 财务系统模拟数据  
- `data/audit.db` - 审计日志与异常记录
- 控制台输出对账报告与欺诈检测结果

---

## 项目结构

```
financial-control-tower/
├── 📁 config/                      # 配置文件
│   └── erp_config.yaml            # ERP 连接配置（演示架构）
│
├── 📁 src/
│   ├── 📁 audit/
│   │   └── financial_control_tower.py    # 核心审计引擎
│   ├── 📁 integration/
│   │   ├── sap_connector.py       # SAP 连接器架构
│   │   ├── oracle_connector.py    # Oracle 连接器架构
│   │   └── sync_scheduler.py      # 数据同步编排
│   └── 📁 data_engineering/
│       ├── init_erp_databases.py  # 演示数据生成
│       └── db_connector.py        # 数据库连接管理
│
├── 📁 scripts/
│   └── setup_project.py           # 演示数据初始化
│
├── 📁 data/                       # 数据库文件（gitignored）
│   ├── db_operations.db
│   ├── db_finance.db
│   └── audit.db
│
├── 📁 docs/
│   ├── glossary.md                # 术语表
│   └── limitations.md             # 项目限制说明
│
├── 📄 reconciliation_matrix.md    # 对账控制矩阵
├── 📄 fraud_rule_metrics.py       # 欺诈规则指标实现
├── 📄 security_architecture.md    # 安全架构设计文档
├── 📄 erp_integration_design.md   # ERP 集成设计文档
├── 📄 main.py                     # 主入口
└── 📄 README.md                   # 本文件
```

---

## 文档索引

| 文档 | 说明 |
|:-----|:-----|
| [docs/glossary.md](docs/glossary.md) | 术语表（IC、PSI、孤儿记录等） |
| [docs/limitations.md](docs/limitations.md) | 项目限制与使用边界 |
| [reconciliation_matrix.md](reconciliation_matrix.md) | 对账控制矩阵 (RCM) |
| [fraud_rule_metrics.py](fraud_rule_metrics.py) | TP/FP/FN 指标实现 |
| [security_architecture.md](security_architecture.md) | RBAC 与审计安全设计 |
| [erp_integration_design.md](erp_integration_design.md) | SAP/Oracle 集成架构设计 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 系统架构概览 |
| [QUICKSTART.md](QUICKSTART.md) | 详细使用指南 |

---

## 项目定位与限制

### 项目性质

**本项目是面向财务审计与风控研究的教育演示工具**，用于展示数据对账流程与风控规则设计思路。

### 明确限制

| 限制项 | 说明 |
|:-------|:-----|
| ❌ 非合规系统 | 未获得任何监管合规认证（非 Basel/IFRS/SOX 合规系统） |
| ❌ 模拟数据 | 不包含真实 ERP 系统连接器（仅演示架构设计） |
| ❌ 示例规则 | 欺诈规则为示例性质，需根据实际业务调整 |
| ❌ 概念安全 | 安全架构为概念设计，生产部署需专业安全审计 |

### 适用场景

- ✅ 数据工程/审计岗位面试项目演示
- ✅ 财务对账流程学习与研究
- ✅ 风控规则设计思路参考

### 生产使用需补充

- 真实 ERP API 集成开发
- 企业级安全加固（加密、RBAC 实施）
- 合规审查与法律评估

---

## 技术栈

| 组件 | 技术 | 用途 |
|:-----|:-----|:-----|
| 语言 | Python 3.8+ | 核心实现 |
| 数据库 | SQLite | 多数据库 ERP 模拟 |
| 数据处理 | Pandas, NumPy | ETL 与分析 |
| 安全 | SHA-256 | 审计日志完整性 |

---

## 作者

**Zheyu Liu**

面向风险建模与审计研究的教育项目。

---

<p align="center">
  <sub>面向审计研究 • 演示级实现 • 非生产系统</sub>
</p>
