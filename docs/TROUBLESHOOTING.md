# Troubleshooting Guide - 常见故障与修复

> 10 条常见失败与一行修复方案

---

## 🔴 严重错误（阻止运行）

### 1. ModuleNotFoundError: No module named 'pandas'
**现象**: 运行 `python main.py` 时报错
```
ModuleNotFoundError: No module named 'pandas'
```
**修复**:
```bash
pip install -r requirements.txt
```

### 2. 数据库文件不存在
**现象**: 运行 `python main.py` 提示未检测到数据库
**修复**:
```bash
python scripts/setup_project.py  # 初始化数据库
# 或使用 demo 模式
python main.py --sample
```

### 3. Kaggle 数据集下载失败
**现象**: `scripts/setup_project.py` 下载超时或失败
**修复**:
```bash
# 手动下载数据
mkdir -p data/raw
curl -L -o data/raw/DataCoSupplyChainDataset.csv \
  "https://www.kaggle.com/datasets/shashwatwork/dataco-global-supply-chain/download"
# 然后重新运行初始化
python scripts/setup_project.py
```

---

## 🟡 警告错误（功能受限）

### 4. 审计输出为空
**现象**: 运行审计后没有输出结果
**修复**:
```bash
# 删除损坏的数据库并重新初始化
rm -f data/*.db
python scripts/setup_project.py
python main.py
```

### 5. SQLite 数据库被锁定
**现象**: 报错 "database is locked"
**修复**:
```bash
# 关闭所有访问数据库的程序，然后重试
lsof data/*.db  # 查看占用进程
# 或等待几秒后重试
```

### 6. 数据类型不匹配
**现象**: 对账时金额差异异常大
**修复**:
```bash
# 检查数据格式
sqlite3 data/db_operations.db "PRAGMA table_info(sales_orders);"
# 重新初始化数据
python scripts/setup_project.py --force
```

---

## 🟢 环境问题

### 7. Python 版本不兼容
**现象**: 运行时报语法错误
**修复**:
```bash
# 检查 Python 版本
python --version  # 需要 3.8+
# 使用 pyenv 切换版本
pyenv install 3.9.0
pyenv local 3.9.0
```

### 8. 磁盘空间不足
**现象**: 初始化时磁盘空间不足
**修复**:
```bash
# 清理临时文件
rm -rf data/raw/*.tmp
# 或手动下载精简数据集
```

### 9. 权限错误（Linux/Mac）
**现象**: Permission denied 错误
**修复**:
```bash
chmod +x run.sh
./run.sh
```

### 10. 网络代理问题
**现象**: Kaggle 下载被防火墙阻止
**修复**:
```bash
# 设置代理
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
python scripts/setup_project.py
```

---

## 快速诊断命令

```bash
# 检查环境
python -c "import pandas, numpy; print('OK')"

# 检查数据库
ls -lh data/*.db

# 检查表结构
sqlite3 data/audit.db ".tables"
sqlite3 data/audit.db "SELECT * FROM audit_logs LIMIT 5;"
```

---

*最后更新: 2026-02-08*
