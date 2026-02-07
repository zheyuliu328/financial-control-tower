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
