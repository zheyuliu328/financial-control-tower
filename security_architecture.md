# Security Architecture - 权限分离架构

## 1. 概述

本文档定义了 FCT (Financial Control Tower) 系统的安全架构，重点解决 Audit Trail 权限存疑问题，实现职责分离 (Segregation of Duties, SoD) 和最小权限原则 (Principle of Least Privilege)。

## 2. 安全原则

### 2.1 职责分离 (Segregation of Duties)

| 角色 | 职责 | 禁止操作 |
|:-----|:-----|:---------|
| 系统管理员 | 系统配置、用户管理 | 查看业务数据、修改审计日志 |
| 审计员 | 查看审计报告、执行审计查询 | 修改业务数据、删除审计记录 |
| 财务分析师 | 查看财务数据、生成报表 | 修改原始数据、访问审计配置 |
| 业务操作员 | 录入业务数据 | 访问财务数据、审计数据 |
| 只读查询用户 | 执行只读查询 | 任何数据修改操作 |

### 2.2 最小权限原则

每个用户/服务只拥有完成其工作所必需的最小权限集合。

## 3. 用户角色与权限矩阵

### 3.1 角色定义

```sql
-- 角色定义表
CREATE TABLE user_roles (
    role_id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name TEXT UNIQUE NOT NULL,
    role_description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入标准角色
INSERT INTO user_roles (role_name, role_description) VALUES
('SYS_ADMIN', '系统管理员 - 负责系统配置和用户管理'),
('AUDITOR', '审计员 - 负责执行审计和查看审计报告'),
('FINANCE_ANALYST', '财务分析师 - 负责财务数据分析和报表生成'),
('BUSINESS_OPERATOR', '业务操作员 - 负责业务数据录入'),
('READONLY_USER', '只读用户 - 仅可执行查询操作'),
('API_SERVICE', 'API服务账户 - 用于系统间集成');
```

### 3.2 权限矩阵

| 权限\角色 | SYS_ADMIN | AUDITOR | FINANCE_ANALYST | BUSINESS_OPERATOR | READONLY_USER | API_SERVICE |
|:----------|:---------:|:-------:|:---------------:|:-----------------:|:-------------:|:-----------:|
| **Operations DB** |
| 读取 sales_orders | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| 修改 sales_orders | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| 读取 shipping_logs | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| 修改 shipping_logs | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **Finance DB** |
| 读取 accounts_receivable | ❌ | ✅ | ✅ | ❌ | ✅ | ✅ |
| 修改 accounts_receivable | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 读取 general_ledger | ❌ | ✅ | ✅ | ❌ | ✅ | ✅ |
| **Audit DB** |
| 读取 audit_logs | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |
| 写入 audit_logs | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ |
| 删除 audit_logs | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 读取 risk_flags | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |
| 修改 risk_flags | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ |
| **系统配置** |
| 用户管理 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 角色分配 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 审计配置 | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |

## 4. 只读副本设计

### 4.1 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                        生产环境 (Production)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ Operations   │  │   Finance    │  │    Audit     │           │
│  │    DB        │  │     DB       │  │     DB       │           │
│  │  (主写入)     │  │   (主写入)    │  │   (主写入)    │           │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │
│         │                  │                  │                  │
│         └──────────────────┼──────────────────┘                  │
│                            │                                     │
│                            ▼                                     │
│                   ┌─────────────────┐                            │
│                   │  实时复制流      │  (Streaming Replication)   │
│                   │  (CDC / ETL)    │                            │
│                   └────────┬────────┘                            │
└────────────────────────────┼────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      只读副本环境 (Read-Only Replica)              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              只读副本数据库 (Read Replica DB)               │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │   │
│  │  │   ops_ro     │  │   fin_ro     │  │  audit_ro    │    │   │
│  │  │  (只读视图)   │  │  (只读视图)   │  │  (只读视图)   │    │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   查询接口层 (Query Layer)                 │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │   │
│  │  │  审计查询API  │  │  报表查询API  │  │  数据分析API  │    │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘    │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 只读副本实现

```sql
-- 创建只读视图（在副本数据库中）
-- 这些视图限制可访问的列，实现数据脱敏

-- Operations DB 只读视图
CREATE VIEW ro_sales_orders AS
SELECT 
    order_id,
    order_date,
    customer_id,
    -- 脱敏客户姓名: 只显示首字母
    CASE 
        WHEN customer_name IS NOT NULL 
        THEN SUBSTR(customer_name, 1, 1) || '***'
        ELSE NULL 
    END AS customer_name_masked,
    customer_segment,
    customer_country,
    product_id,
    category_name,
    order_quantity,
    sales,
    profit,
    order_status,
    order_priority
FROM sales_orders;

-- Finance DB 只读视图
CREATE VIEW ro_accounts_receivable AS
SELECT 
    ar_id,
    order_id,
    customer_id,
    -- 脱敏客户姓名
    CASE 
        WHEN customer_name IS NOT NULL 
        THEN SUBSTR(customer_name, 1, 1) || '***'
        ELSE NULL 
    END AS customer_name_masked,
    invoice_date,
    due_date,
    invoice_amount,
    paid_amount,
    outstanding_amount,
    payment_status,
    days_past_due
FROM accounts_receivable;

-- Audit DB 只读视图（完整访问，因为审计数据本身就是日志）
CREATE VIEW ro_audit_logs AS
SELECT *
FROM audit_logs;

-- 创建只读用户并授权
CREATE USER 'readonly_user'@'%' IDENTIFIED BY 'strong_password';
GRANT SELECT ON ro_sales_orders TO 'readonly_user'@'%';
GRANT SELECT ON ro_accounts_receivable TO 'readonly_user'@'%';
GRANT SELECT ON ro_audit_logs TO 'readonly_user'@'%';
-- 明确禁止写入权限
REVOKE INSERT, UPDATE, DELETE ON *.* FROM 'readonly_user'@'%';
```

### 4.3 数据同步策略

| 同步方式 | 延迟 | 适用场景 | 实现技术 |
|:---------|:-----|:---------|:---------|
| 实时同步 | < 1秒 | 审计查询 | CDC (Change Data Capture) |
| 准实时 | 1-5分钟 | 报表查询 | 定时 ETL 任务 |
| 批量同步 | 每小时 | 数据分析 | 批量数据导出 |

## 5. 审计日志安全

### 5.1 审计日志不可变性

```sql
-- 启用审计日志表的不可变性
-- 通过触发器禁止修改和删除

CREATE TRIGGER prevent_audit_logs_update
BEFORE UPDATE ON audit_logs
BEGIN
    SELECT RAISE(ABORT, '审计日志不可修改');
END;

CREATE TRIGGER prevent_audit_logs_delete
BEFORE DELETE ON audit_logs
BEGIN
    SELECT RAISE(ABORT, '审计日志不可删除');
END;

-- 只允许插入新记录
-- 如果需要"修改"，只能添加新的修正记录
```

### 5.2 审计日志完整性验证

```python
# 审计日志完整性校验
import hashlib
import json

def calculate_audit_log_hash(log_entry: dict) -> str:
    """计算审计日志条目的哈希值，用于完整性验证"""
    # 按字母顺序排序键值对，确保一致性
    sorted_entry = dict(sorted(log_entry.items()))
    entry_string = json.dumps(sorted_entry, sort_keys=True)
    return hashlib.sha256(entry_string.encode()).hexdigest()

def verify_audit_log_integrity(log_id: int, expected_hash: str) -> bool:
    """验证单条审计日志的完整性"""
    # 从数据库读取日志
    log_entry = fetch_audit_log_by_id(log_id)
    calculated_hash = calculate_audit_log_hash(log_entry)
    return calculated_hash == expected_hash
```

## 6. API 访问控制

### 6.1 认证与授权

```python
# API 访问控制示例
from functools import wraps
from flask import request, jsonify

def require_role(required_roles):
    """装饰器：要求特定角色才能访问"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = request.headers.get('Authorization')
            if not token:
                return jsonify({'error': 'Missing authentication token'}), 401
            
            user = verify_token(token)
            if not user:
                return jsonify({'error': 'Invalid token'}), 401
            
            if user.role not in required_roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# API 端点示例
@app.route('/api/audit/logs')
@require_role(['AUDITOR', 'SYS_ADMIN', 'READONLY_USER'])
def get_audit_logs():
    """只有审计员、系统管理员和只读用户可以访问审计日志"""
    pass

@app.route('/api/finance/reports')
@require_role(['FINANCE_ANALYST', 'AUDITOR', 'READONLY_USER'])
def get_finance_reports():
    """只有财务分析师、审计员和只读用户可以访问财务报告"""
    pass
```

### 6.2 API 权限矩阵

| API 端点 | GET | POST | PUT | DELETE |
|:---------|:---:|:----:|:---:|:------:|
| `/api/operations/orders` | BUSINESS_OPERATOR, FINANCE_ANALYST, READONLY_USER | BUSINESS_OPERATOR | - | - |
| `/api/finance/ar` | FINANCE_ANALYST, AUDITOR, READONLY_USER | API_SERVICE | - | - |
| `/api/audit/logs` | AUDITOR, SYS_ADMIN, READONLY_USER | AUDITOR, API_SERVICE | - | - |
| `/api/audit/risk-flags` | AUDITOR, SYS_ADMIN, READONLY_USER | AUDITOR | AUDITOR | - |
| `/api/admin/users` | SYS_ADMIN | SYS_ADMIN | SYS_ADMIN | SYS_ADMIN |
| `/api/admin/roles` | SYS_ADMIN | SYS_ADMIN | - | - |

## 7. 数据加密

### 7.1 传输加密

- 所有 API 通信必须使用 TLS 1.3
- 数据库连接必须使用 SSL/TLS
- 禁止明文传输敏感数据

### 7.2 静态数据加密

| 数据类型 | 加密方式 | 密钥管理 |
|:---------|:---------|:---------|
| 客户姓名 | AES-256 | KMS (Key Management Service) |
| 财务金额 | 透明数据加密 (TDE) | 数据库内置 |
| 审计日志 | 完整性哈希 (SHA-256) | 应用层管理 |
| 备份数据 | AES-256-GCM | 专用备份密钥 |

## 8. 监控与告警

### 8.1 安全事件监控

| 事件类型 | 监控方法 | 告警级别 |
|:---------|:---------|:---------|
| 未授权访问尝试 | 日志分析 | HIGH |
| 权限提升尝试 | 审计日志监控 | CRITICAL |
| 审计日志修改尝试 | 触发器 + 日志 | CRITICAL |
| 异常查询模式 | 行为分析 | MEDIUM |
| 大量数据导出 | 阈值监控 | HIGH |

### 8.2 审计日志查询

```sql
-- 查询权限变更历史
SELECT 
    audit_date,
    auditor_id,
    action,
    entity_type,
    entity_id,
    notes
FROM audit_logs
WHERE action LIKE '%PERMISSION%' OR action LIKE '%ROLE%'
ORDER BY audit_date DESC;

-- 查询异常访问模式
SELECT 
    auditor_id,
    COUNT(*) as access_count,
    COUNT(DISTINCT entity_type) as entity_types
FROM audit_logs
WHERE audit_date >= datetime('now', '-1 day')
GROUP BY auditor_id
HAVING access_count > 1000;  -- 单日访问超过1000次视为异常
```

## 9. 合规性检查清单

| 检查项 | 要求 | 验证方法 |
|:-------|:-----|:---------|
| 职责分离 | 关键操作需要多人审批 | 审查角色分配 |
| 最小权限 | 用户只有必要权限 | 权限审计报告 |
| 审计不可变 | 审计日志不可修改删除 | 触发器测试 |
| 数据加密 | 传输和静态数据加密 | 安全扫描 |
| 访问控制 | API 有适当的认证授权 | 渗透测试 |
| 监控告警 | 安全事件及时告警 | 告警测试 |

## 10. 附录

### 10.1 相关文档

- `reconciliation_matrix.md` - 对账控制矩阵
- `erp_integration_design.md` - ERP 集成设计
- `fraud_rule_metrics.py` - 欺诈规则性能指标

### 10.2 术语定义

| 术语 | 定义 |
|:-----|:-----|
| SoD | Segregation of Duties - 职责分离 |
| PoLP | Principle of Least Privilege - 最小权限原则 |
| CDC | Change Data Capture - 变更数据捕获 |
| KMS | Key Management Service - 密钥管理服务 |
| TDE | Transparent Data Encryption - 透明数据加密 |

---

**文档版本**: 1.0  
**最后更新**: 2026-02-07  
**维护者**: Financial Control Tower Security Team
