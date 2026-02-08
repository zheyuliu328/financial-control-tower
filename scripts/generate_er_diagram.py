"""
生成 ER 关系图
使用 graphviz 或生成 Mermaid 格式的图表
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def generate_mermaid_er_diagram():
    """生成 Mermaid 格式的 ER 图"""

    mermaid_code = """
```mermaid
erDiagram
    %% Operations Database (db_operations.db)
    PRODUCTS ||--o{ SALES_ORDERS : "has"
    SALES_ORDERS ||--o{ SHIPPING_LOGS : "generates"

    PRODUCTS {
        string product_id PK
        string product_name
        string product_category
        decimal product_price
        decimal product_cost
        decimal product_margin
        timestamp created_at
    }

    SALES_ORDERS {
        string order_id PK
        date order_date
        string customer_id
        string customer_name
        string customer_segment
        string customer_country
        string customer_city
        string product_id FK
        string product_name
        string category_name
        int order_quantity
        decimal sales
        decimal discount
        decimal profit
        string order_status
        string order_priority
        int order_year
        int order_month
        int order_day
        int days_for_shipment_scheduled
        int days_for_shipment_real
        string delivery_status
        int late_delivery_risk
        timestamp created_at
    }

    SHIPPING_LOGS {
        int log_id PK
        string order_id FK
        string shipping_mode
        date shipping_date
        int days_for_shipment_scheduled
        int days_for_shipment_real
        string delivery_status
        int late_delivery_risk
        string customer_country
        string customer_city
        string market
        string region
        timestamp created_at
    }

    %% Finance Database (db_finance.db)
    GENERAL_LEDGER ||--o{ ACCOUNTS_RECEIVABLE : "references"
    SALES_ORDERS ||--o| ACCOUNTS_RECEIVABLE : "generates"

    GENERAL_LEDGER {
        int gl_id PK
        date transaction_date
        string related_order_id
        string account_code
        string account_name
        decimal debit_amount
        decimal credit_amount
        string description
        string reference_number
        timestamp created_at
    }

    ACCOUNTS_RECEIVABLE {
        int ar_id PK
        string order_id UK
        string customer_id
        string customer_name
        date invoice_date
        date due_date
        decimal invoice_amount
        decimal paid_amount
        decimal outstanding_amount
        string payment_status
        int days_past_due
        timestamp created_at
        timestamp updated_at
    }

    %% Audit Database (audit.db)
    AUDIT_LOGS {
        int log_id PK
        timestamp audit_date
        string audit_type
        string source_system
        string entity_type
        string entity_id
        string action
        string old_value
        string new_value
        string auditor_id
        string auditor_name
        string notes
        string risk_level
        string status
    }

    RISK_FLAGS {
        int flag_id PK
        timestamp flag_date
        string risk_type
        string severity
        string entity_type
        string entity_id
        string description
        string source_system
        string status
        string assigned_to
        string resolution_notes
        timestamp resolved_at
        timestamp created_at
    }

    %% Cross-database relationships (logical, not physical)
    SALES_ORDERS ||--o| ACCOUNTS_RECEIVABLE : "reconciles_with"
    SALES_ORDERS ||--o{ RISK_FLAGS : "flagged_by"
```
"""

    return mermaid_code


def generate_text_er_diagram():
    """生成文本格式的 ER 图说明"""

    text = """
# 数据库 ER 关系图

## Operations Database (db_operations.db)

### PRODUCTS (产品主数据)
- **PK**: product_id
- **关系**: 1:N → SALES_ORDERS

### SALES_ORDERS (销售订单)
- **PK**: order_id
- **FK**: product_id → PRODUCTS
- **关系**:
  - N:1 → PRODUCTS
  - 1:N → SHIPPING_LOGS
  - 1:1 → ACCOUNTS_RECEIVABLE (跨库逻辑关系)

### SHIPPING_LOGS (物流日志)
- **PK**: log_id
- **FK**: order_id → SALES_ORDERS
- **关系**: N:1 → SALES_ORDERS

---

## Finance Database (db_finance.db)

### GENERAL_LEDGER (总账)
- **PK**: gl_id
- **关系**: 引用 SALES_ORDERS (通过 related_order_id)

### ACCOUNTS_RECEIVABLE (应收账款)
- **PK**: ar_id
- **UK**: order_id (唯一约束，对应 SALES_ORDERS.order_id)
- **关系**: 1:1 → SALES_ORDERS (跨库逻辑关系)

---

## Audit Database (audit.db)

### AUDIT_LOGS (审计日志)
- **PK**: log_id
- **关系**: 记录所有系统的审计事件

### RISK_FLAGS (风险标记)
- **PK**: flag_id
- **关系**: 标记 SALES_ORDERS 等实体的风险

---

## 跨数据库关系（逻辑关系，非物理外键）

1. **SALES_ORDERS ↔ ACCOUNTS_RECEIVABLE**
   - 对账关系：Operations DB 的订单金额 vs Finance DB 的 AR 金额
   - 通过 order_id 关联

2. **SALES_ORDERS → RISK_FLAGS**
   - 审计关系：订单可能被标记为风险
   - 通过 entity_id (order_id) 关联

3. **GENERAL_LEDGER → SALES_ORDERS**
   - 财务关系：总账分录引用订单
   - 通过 related_order_id 关联
"""

    return text


def save_er_diagram():
    """保存 ER 图到文件"""
    output_dir = project_root / "docs"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存 Mermaid 格式
    mermaid_file = output_dir / "ER_DIAGRAM.md"
    with open(mermaid_file, 'w', encoding='utf-8') as f:
        f.write("# 数据库 ER 关系图\n\n")
        f.write(generate_mermaid_er_diagram())
        f.write("\n\n")
        f.write(generate_text_er_diagram())

    print(f"✅ ER 图已保存到: {mermaid_file}")

    return mermaid_file


if __name__ == "__main__":
    save_er_diagram()



