# FCT (Financial Control Tower) 安全改造清单

## 文件修改清单

### 1. src/utils/guardrails.py (新增)
- **路径**: `fct/src/utils/guardrails.py`
- **操作**: 复制根目录 guardrails.py
- **说明**: 危险操作保护、审计日志

### 2. src/utils/secrets.py (新增)
- **路径**: `fct/src/utils/secrets.py`
- **操作**: 复制根目录 secrets.py
- **说明**: Secrets 统一管理

### 3. src/utils/data_boundary.py (新增)
- **路径**: `fct/src/utils/data_boundary.py`
- **操作**: 复制根目录 data_boundary.py
- **说明**: 输入数据校验

### 4. src/data_engineering/db_connector.py (修改)
- **路径**: `fct/src/data_engineering/db_connector.py`
- **修改内容**:
  1. 添加路径校验
  2. 添加审计日志
  3. SQL 注入防护

```python
# 在 ERPDatabaseConnector 类中添加:
from ..utils.guardrails import PathValidator, AuditLogger, require_confirm
from ..utils.data_boundary import DataBoundaryValidator, FieldSchema, FieldType

class ERPDatabaseConnector:
    def __init__(self, data_dir: Path = None):
        # ... 原有代码 ...
        
        # 添加路径校验
        self.path_validator = PathValidator([str(self.data_dir)])
        self.audit = AuditLogger(str(self.project_root / "logs"))
    
    def execute_query(self, db_name: str, query: str, params: Tuple = None) -> List[Dict]:
        """执行查询 - 添加审计日志"""
        self.audit.log("DB_QUERY", {
            "db_name": db_name,
            "query": query[:200],  # 截断避免日志过大
            "has_params": params is not None
        })
        # ... 原有代码 ...
    
    @require_confirm("database.drop_table")
    def drop_table(self, db_name: str, table_name: str, confirm: bool = False):
        """删除表 - 危险操作需确认"""
        # 实现删除表逻辑
        pass
```

### 5. main.py (修改)
- **路径**: `fct/main.py`
- **修改内容**:
  1. 添加 --confirm 参数支持
  2. 数据库删除前确认
  3. 添加审计日志

```python
# 修改 main() 函数:
def main():
    parser = argparse.ArgumentParser(description='Financial Control Tower')
    parser.add_argument('--sample', action='store_true', help='Use sample data (demo mode)')
    parser.add_argument('--confirm', action='store_true', help='Confirm dangerous operations')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (no actual changes)')
    args = parser.parse_args()
    
    # 设置环境变量
    if args.dry_run:
        os.environ['GUARDRAILS_DRY_RUN'] = 'true'
    if args.confirm:
        os.environ['GUARDRAILS_CONFIRM'] = 'true'
    
    # ... 原有代码 ...
```

### 6. pyproject.toml (修改)
- **路径**: `fct/pyproject.toml`
- **修改内容**:
  1. 添加 pre-commit 依赖
  2. 添加 gitleaks 配置引用

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "black>=22.0.0",
    "ruff>=0.0.200",
    "pre-commit>=2.20.0",
    "bandit>=1.7.0",
]

[tool.bandit]
exclude_dirs = ["tests"]
skips = ["B101"]  # 跳过 assert 检查
```

### 7. .pre-commit-config.yaml (新增)
- **路径**: `fct/.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
  
  - repo: https://github.com/psf/black
    rev: 23.12.0
    hooks:
      - id: black
        language_version: python3.11
  
  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.8
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
  
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.6
    hooks:
      - id: bandit
        args: ["-c", "pyproject.toml"]
        additional_dependencies: ["bandit[toml]"]
```

### 8. .gitleaks.toml (新增)
- **路径**: `fct/.gitleaks.toml`
- **操作**: 复制根目录 .gitleaks.toml

### 9. docs/SECURITY.md (新增)
- **路径**: `fct/docs/SECURITY.md`

```markdown
# FCT 安全指南

## Secrets 管理
- 所有 API Key 通过环境变量读取
- 禁止在代码中硬编码凭证

## 危险操作
- 删除数据库需要 --confirm 参数
- 使用 --dry-run 预览操作

## 审计日志
- 所有数据库操作记录在 logs/audit_YYYYMMDD.log
- 保留 30 天
```

### 10. scripts/backup.sh (新增)
- **路径**: `fct/scripts/backup.sh`

```bash
#!/bin/bash
# 数据库自动备份脚本
set -euo pipefail

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# 备份所有数据库
for db in data/*.db; do
    if [ -f "$db" ]; then
        backup_name="${BACKUP_DIR}/$(basename "$db" .db)_${TIMESTAMP}.db"
        echo "Backing up $db -> $backup_name"
        cp "$db" "$backup_name"
    fi
done

# 清理旧备份（保留最近10个）
ls -t "$BACKUP_DIR"/*.db 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true

echo "Backup completed: $BACKUP_DIR"
```

## 实施步骤

1. **创建工具模块**
   ```bash
   mkdir -p fct/src/utils
   cp src/utils/guardrails.py fct/src/utils/
   cp src/utils/secrets.py fct/src/utils/
   cp src/utils/data_boundary.py fct/src/utils/
   ```

2. **修改数据库连接器**
   ```bash
   # 编辑 fct/src/data_engineering/db_connector.py
   # 添加路径校验和审计日志
   ```

3. **配置安全扫描**
   ```bash
   cd fct
   cp ../.gitleaks.toml .
   cp ../scripts/pre-commit.sh .git/hooks/pre-commit
   chmod +x .git/hooks/pre-commit
   pre-commit install
   ```

4. **验证**
   ```bash
   # 测试危险操作确认
   python main.py --sample --dry-run
   
   # 测试审计日志
   ls logs/audit_*.log
   
   # 测试 gitleaks
   gitleaks detect --source . --verbose
   ```
