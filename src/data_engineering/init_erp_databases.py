"""
企业级 ERP 数据库初始化脚本
将 CSV 数据拆分到三个独立的 SQLite 数据库，模拟真实 ERP 环境：
- Operations DB: 运营数据（订单、物流、产品）
- Finance DB: 财务数据（总账、应收账款）
- Audit DB: 审计数据（审计日志、风险标记）
"""

import contextlib
import sqlite3
import sys
from pathlib import Path
from typing import List

import pandas as pd

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class ERPDatabaseInitializer:
    """ERP 数据库初始化器"""

    def __init__(self, data_dir: Path = None):
        self.project_root = project_root
        self.data_dir = data_dir or (project_root / "data")
        self.raw_data_dir = self.data_dir / "raw"
        self.db_dir = self.data_dir

        # 数据库文件路径
        self.ops_db_path = self.db_dir / "db_operations.db"
        self.finance_db_path = self.db_dir / "db_finance.db"
        self.audit_db_path = self.db_dir / "audit.db"

    def find_csv_file(self) -> Path:
        """查找原始 CSV 文件"""
        csv_files = list(self.raw_data_dir.glob("*.csv"))
        if not csv_files:
            raise FileNotFoundError("未找到 CSV 文件。请先运行: python scripts/download_data.py")
        return csv_files[0]

    def load_raw_data(self) -> pd.DataFrame:
        """加载原始 CSV 数据"""
        csv_file = self.find_csv_file()
        print(f"正在加载数据: {csv_file.name}")
        print(f"文件大小: {csv_file.stat().st_size / 1024 / 1024:.2f} MB")

        # 读取 CSV（使用低内存模式处理大文件）
        df = pd.read_csv(csv_file, low_memory=False)
        print(f"✓ 加载完成: {df.shape[0]:,} 行, {df.shape[1]} 列")

        # 显示列名
        print(f"\n数据列 ({len(df.columns)} 列):")
        for i, col in enumerate(df.columns, 1):
            print(f"  {i:2d}. {col}")

        return df

    def create_operations_db(self, df: pd.DataFrame):
        """创建运营数据库 (Operations DB)"""
        print("\n" + "=" * 60)
        print("创建 Operations 数据库 (db_operations.db)")
        print("=" * 60)

        conn = sqlite3.connect(self.ops_db_path)
        cursor = conn.cursor()

        # 1. 产品表 (products)
        print("\n创建 products 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id TEXT PRIMARY KEY,
                product_name TEXT,
                product_category TEXT,
                product_price REAL,
                product_cost REAL,
                product_margin REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. 销售订单表 (sales_orders)
        print("创建 sales_orders 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_orders (
                order_id TEXT PRIMARY KEY,
                order_date DATE,
                customer_id TEXT,
                customer_name TEXT,
                customer_segment TEXT,
                customer_country TEXT,
                customer_city TEXT,
                product_id TEXT,
                product_name TEXT,
                category_name TEXT,
                order_quantity INTEGER,
                sales REAL,
                discount REAL,
                profit REAL,
                order_status TEXT,
                order_priority TEXT,
                order_year INTEGER,
                order_month INTEGER,
                order_day INTEGER,
                days_for_shipment_scheduled INTEGER,
                days_for_shipment_real INTEGER,
                delivery_status TEXT,
                late_delivery_risk INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(product_id)
            )
        """)

        # 3. 物流日志表 (shipping_logs)
        print("创建 shipping_logs 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shipping_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT,
                shipping_mode TEXT,
                shipping_date DATE,
                days_for_shipment_scheduled INTEGER,
                days_for_shipment_real INTEGER,
                delivery_status TEXT,
                late_delivery_risk INTEGER,
                customer_country TEXT,
                customer_city TEXT,
                market TEXT,
                region TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES sales_orders(order_id)
            )
        """)

        conn.commit()
        print("✓ Operations 数据库表结构创建完成")

        # 插入数据
        self._insert_products_data(cursor, df)
        self._insert_sales_orders_data(cursor, df)
        self._insert_shipping_logs_data(cursor, df)

        conn.commit()
        conn.close()
        print(f"✓ Operations 数据库初始化完成: {self.ops_db_path}")

    def _insert_products_data(self, cursor: sqlite3.Cursor, df: pd.DataFrame):
        """插入产品数据"""
        print("\n插入 products 数据...")

        # 智能映射列名（处理不同的列名变体）
        product_cols = {
            "id": ["Product ID", "Product Card Id", "product_id", "ProductId"],
            "name": ["Product Name", "product_name", "ProductName"],
            "category": ["Category Name", "category_name", "Category", "category"],
            "price": ["Sales", "sales", "Product Price", "price"],
            "cost": ["Order Item Product Price", "Cost", "cost"],
            "margin": ["Order Profit Per Order", "Profit", "profit", "margin"],
        }

        # 查找实际存在的列
        product_id_col = self._find_column(df, product_cols["id"])
        product_name_col = self._find_column(df, product_cols["name"])
        category_col = self._find_column(df, product_cols["category"])

        if not product_id_col:
            print("⚠️  未找到产品ID列，跳过产品数据插入")
            return

        # 获取唯一产品
        if product_name_col:
            products_df = df[[product_id_col, product_name_col, category_col]].drop_duplicates(subset=[product_id_col])
        else:
            products_df = df[[product_id_col]].drop_duplicates()
            products_df[product_name_col] = None
            products_df[category_col] = None

        # 计算价格和成本（从订单数据聚合）
        sales_col = self._find_column(df, product_cols["price"])
        if sales_col:
            price_df = df.groupby(product_id_col)[sales_col].mean().reset_index()
            price_df.columns = [product_id_col, "avg_price"]
            products_df = products_df.merge(price_df, on=product_id_col, how="left")
        else:
            products_df["avg_price"] = None

        # 插入数据
        inserted = 0
        for _, row in products_df.iterrows():
            try:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO products
                    (product_id, product_name, product_category, product_price)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        str(row[product_id_col]),
                        str(row[product_name_col]) if product_name_col and pd.notna(row[product_name_col]) else None,
                        str(row[category_col]) if category_col and pd.notna(row[category_col]) else None,
                        float(row["avg_price"]) if "avg_price" in row and pd.notna(row["avg_price"]) else None,
                    ),
                )
                inserted += 1
            except Exception as e:
                print(f"⚠️  插入产品失败: {e}")

        print(f"✓ 插入 {inserted:,} 条产品记录")

    def _insert_sales_orders_data(self, cursor: sqlite3.Cursor, df: pd.DataFrame):
        """插入销售订单数据"""
        print("\n插入 sales_orders 数据...")

        # 智能列名映射
        col_mapping = {
            "order_id": ["Order ID", "order_id", "OrderId"],
            "order_date": ["order date (DateOrders)", "Order Date", "order_date"],
            "customer_id": ["Customer ID", "customer_id", "CustomerId"],
            "customer_name": ["Customer Name", "customer_name"],
            "customer_segment": ["Customer Segment", "customer_segment"],
            "customer_country": ["Customer Country", "customer_country", "Country"],
            "customer_city": ["Customer City", "customer_city", "City"],
            "product_id": ["Product ID", "Product Card Id", "product_id"],
            "product_name": ["Product Name", "product_name"],
            "category": ["Category Name", "category_name", "Category"],
            "quantity": ["Order Item Quantity", "Quantity", "quantity"],
            "sales": ["Sales", "sales"],
            "discount": ["Order Item Discount", "Discount", "discount"],
            "profit": ["Order Profit Per Order", "Profit", "profit"],
            "status": ["Order Status", "order_status", "OrderStatus"],
            "priority": ["Order Priority", "order_priority"],
            "shipment_scheduled": ["Days for shipment (scheduled)", "days_for_shipment_scheduled"],
            "shipment_real": ["Days for shipment (real)", "days_for_shipment_real"],
            "delivery_status": ["Delivery Status", "delivery_status"],
            "late_delivery_risk": ["Late_delivery_risk", "late_delivery_risk"],
        }

        # 构建实际列名映射
        actual_cols = {}
        for key, possible_names in col_mapping.items():
            found = self._find_column(df, possible_names)
            if found:
                actual_cols[key] = found

        if "order_id" not in actual_cols:
            print("⚠️  未找到订单ID列，跳过订单数据插入")
            return

        # 准备插入数据
        inserted = 0
        batch_size = 1000

        for i in range(0, len(df), batch_size):
            batch = df.iloc[i : i + batch_size]
            values_list = []

            for _, row in batch.iterrows():
                try:
                    # 提取日期信息
                    order_date = None
                    if "order_date" in actual_cols:
                        date_val = row[actual_cols["order_date"]]
                        if pd.notna(date_val):
                            with contextlib.suppress(BaseException):
                                order_date = pd.to_datetime(date_val).date()

                    # 提取年月日
                    order_year = order_date.year if order_date else None
                    order_month = order_date.month if order_date else None
                    order_day = order_date.day if order_date else None

                    values = (
                        str(row[actual_cols["order_id"]]),
                        order_date,
                        str(row[actual_cols.get("customer_id", "order_id")])
                        if "customer_id" in actual_cols
                        else str(row[actual_cols["order_id"]]),
                        str(row[actual_cols.get("customer_name", "")]) if "customer_name" in actual_cols else None,
                        str(row[actual_cols.get("customer_segment", "")])
                        if "customer_segment" in actual_cols
                        else None,
                        str(row[actual_cols.get("customer_country", "")])
                        if "customer_country" in actual_cols
                        else None,
                        str(row[actual_cols.get("customer_city", "")]) if "customer_city" in actual_cols else None,
                        str(row[actual_cols.get("product_id", "")]) if "product_id" in actual_cols else None,
                        str(row[actual_cols.get("product_name", "")]) if "product_name" in actual_cols else None,
                        str(row[actual_cols.get("category", "")]) if "category" in actual_cols else None,
                        int(row[actual_cols.get("quantity", 0)])
                        if "quantity" in actual_cols and pd.notna(row[actual_cols["quantity"]])
                        else 0,
                        float(row[actual_cols.get("sales", 0)])
                        if "sales" in actual_cols and pd.notna(row[actual_cols["sales"]])
                        else 0.0,
                        float(row[actual_cols.get("discount", 0)])
                        if "discount" in actual_cols and pd.notna(row[actual_cols["discount"]])
                        else 0.0,
                        float(row[actual_cols.get("profit", 0)])
                        if "profit" in actual_cols and pd.notna(row[actual_cols["profit"]])
                        else 0.0,
                        str(row[actual_cols.get("status", "")]) if "status" in actual_cols else None,
                        str(row[actual_cols.get("priority", "")]) if "priority" in actual_cols else None,
                        order_year,
                        order_month,
                        order_day,
                        int(row[actual_cols.get("shipment_scheduled", 0)])
                        if "shipment_scheduled" in actual_cols and pd.notna(row[actual_cols["shipment_scheduled"]])
                        else None,
                        int(row[actual_cols.get("shipment_real", 0)])
                        if "shipment_real" in actual_cols and pd.notna(row[actual_cols["shipment_real"]])
                        else None,
                        str(row[actual_cols.get("delivery_status", "")]) if "delivery_status" in actual_cols else None,
                        int(row[actual_cols.get("late_delivery_risk", 0)])
                        if "late_delivery_risk" in actual_cols and pd.notna(row[actual_cols["late_delivery_risk"]])
                        else 0,
                    )
                    values_list.append(values)
                except Exception:
                    continue

            # 批量插入
            if values_list:
                cursor.executemany(
                    """
                    INSERT OR REPLACE INTO sales_orders
                    (order_id, order_date, customer_id, customer_name, customer_segment,
                     customer_country, customer_city, product_id, product_name, category_name,
                     order_quantity, sales, discount, profit, order_status, order_priority,
                     order_year, order_month, order_day, days_for_shipment_scheduled,
                     days_for_shipment_real, delivery_status, late_delivery_risk)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    values_list,
                )
                inserted += len(values_list)
                print(f"  已插入 {inserted:,} / {len(df):,} 条订单记录...", end="\r")

        print(f"\n✓ 插入 {inserted:,} 条销售订单记录")

    def _insert_shipping_logs_data(self, cursor: sqlite3.Cursor, df: pd.DataFrame):
        """插入物流日志数据"""
        print("\n插入 shipping_logs 数据...")

        # 查找相关列
        order_id_col = self._find_column(df, ["Order ID", "order_id", "OrderId"])
        shipping_mode_col = self._find_column(df, ["Shipping Mode", "shipping_mode", "Type"])
        order_date_col = self._find_column(df, ["order date (DateOrders)", "Order Date", "order_date"])

        if not order_id_col:
            print("⚠️  未找到订单ID列，跳过物流日志插入")
            return

        # 准备数据
        inserted = 0
        batch_size = 1000

        for i in range(0, len(df), batch_size):
            batch = df.iloc[i : i + batch_size]
            values_list = []

            for _, row in batch.iterrows():
                try:
                    order_date = None
                    if order_date_col:
                        date_val = row[order_date_col]
                        if pd.notna(date_val):
                            with contextlib.suppress(BaseException):
                                order_date = pd.to_datetime(date_val).date()

                    values = (
                        str(row[order_id_col]),
                        str(row[shipping_mode_col]) if shipping_mode_col and pd.notna(row[shipping_mode_col]) else None,
                        order_date,
                        int(row.get("Days for shipment (scheduled)", 0))
                        if pd.notna(row.get("Days for shipment (scheduled)", 0))
                        else None,
                        int(row.get("Days for shipment (real)", 0))
                        if pd.notna(row.get("Days for shipment (real)", 0))
                        else None,
                        str(row.get("Delivery Status", "")) if pd.notna(row.get("Delivery Status", "")) else None,
                        int(row.get("Late_delivery_risk", 0)) if pd.notna(row.get("Late_delivery_risk", 0)) else 0,
                        str(row.get("Customer Country", "")) if pd.notna(row.get("Customer Country", "")) else None,
                        str(row.get("Customer City", "")) if pd.notna(row.get("Customer City", "")) else None,
                        str(row.get("Market", "")) if pd.notna(row.get("Market", "")) else None,
                        str(row.get("Region", "")) if pd.notna(row.get("Region", "")) else None,
                    )
                    values_list.append(values)
                except Exception:
                    continue

            if values_list:
                cursor.executemany(
                    """
                    INSERT INTO shipping_logs
                    (order_id, shipping_mode, shipping_date, days_for_shipment_scheduled,
                     days_for_shipment_real, delivery_status, late_delivery_risk,
                     customer_country, customer_city, market, region)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    values_list,
                )
                inserted += len(values_list)
                print(f"  已插入 {inserted:,} / {len(df):,} 条物流记录...", end="\r")

        print(f"\n✓ 插入 {inserted:,} 条物流日志记录")

    def create_finance_db(self, df: pd.DataFrame):
        """创建财务数据库 (Finance DB)"""
        print("\n" + "=" * 60)
        print("创建 Finance 数据库 (db_finance.db)")
        print("=" * 60)

        conn = sqlite3.connect(self.finance_db_path)
        cursor = conn.cursor()

        # 1. 总账表 (general_ledger)
        print("\n创建 general_ledger 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS general_ledger (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_date DATE,
                order_id TEXT,
                account_code TEXT,
                account_name TEXT,
                debit_amount REAL DEFAULT 0,
                credit_amount REAL DEFAULT 0,
                description TEXT,
                reference_number TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. 应收账款表 (accounts_receivable)
        print("创建 accounts_receivable 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts_receivable (
                ar_id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE,
                customer_id TEXT,
                customer_name TEXT,
                invoice_date DATE,
                due_date DATE,
                invoice_amount REAL,
                paid_amount REAL DEFAULT 0,
                outstanding_amount REAL,
                payment_status TEXT,
                days_past_due INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        print("✓ Finance 数据库表结构创建完成")

        # 插入数据
        self._insert_general_ledger_data(cursor, df)
        self._insert_accounts_receivable_data(cursor, df)

        conn.commit()
        conn.close()
        print(f"✓ Finance 数据库初始化完成: {self.finance_db_path}")

    def _insert_general_ledger_data(self, cursor: sqlite3.Cursor, df: pd.DataFrame):
        """插入总账数据（从订单数据生成）"""
        print("\n插入 general_ledger 数据...")

        order_id_col = self._find_column(df, ["Order ID", "order_id", "OrderId"])
        order_date_col = self._find_column(df, ["order date (DateOrders)", "Order Date", "order_date"])
        sales_col = self._find_column(df, ["Sales", "sales"])
        profit_col = self._find_column(df, ["Order Profit Per Order", "Profit", "profit"])

        if not order_id_col or not sales_col:
            print("⚠️  缺少必要列，跳过总账数据插入")
            return

        inserted = 0
        batch_size = 1000

        for i in range(0, len(df), batch_size):
            batch = df.iloc[i : i + batch_size]
            values_list = []

            for _, row in batch.iterrows():
                try:
                    transaction_date = None
                    if order_date_col:
                        date_val = row[order_date_col]
                        if pd.notna(date_val):
                            with contextlib.suppress(BaseException):
                                transaction_date = pd.to_datetime(date_val).date()

                    sales = float(row[sales_col]) if pd.notna(row[sales_col]) else 0.0
                    profit = float(row[profit_col]) if profit_col and pd.notna(row[profit_col]) else 0.0
                    cost = sales - profit

                    order_id = str(row[order_id_col])

                    # 创建两条总账记录：收入（贷方）和成本（借方）
                    # 收入记录
                    values_list.append(
                        (
                            transaction_date,
                            order_id,
                            "4000",  # 收入账户代码
                            "Sales Revenue",
                            0.0,  # 借方
                            sales,  # 贷方
                            f"Sales for Order {order_id}",
                            order_id,
                        )
                    )

                    # 成本记录
                    if cost > 0:
                        values_list.append(
                            (
                                transaction_date,
                                order_id,
                                "5000",  # 成本账户代码
                                "Cost of Goods Sold",
                                cost,  # 借方
                                0.0,  # 贷方
                                f"COGS for Order {order_id}",
                                order_id,
                            )
                        )

                except Exception:
                    continue

            if values_list:
                cursor.executemany(
                    """
                    INSERT INTO general_ledger
                    (transaction_date, order_id, account_code, account_name,
                     debit_amount, credit_amount, description, reference_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    values_list,
                )
                inserted += len(values_list)
                print(f"  已插入 {inserted:,} 条总账记录...", end="\r")

        print(f"\n✓ 插入 {inserted:,} 条总账记录")

    def _insert_accounts_receivable_data(self, cursor: sqlite3.Cursor, df: pd.DataFrame):
        """插入应收账款数据"""
        print("\n插入 accounts_receivable 数据...")

        order_id_col = self._find_column(df, ["Order ID", "order_id", "OrderId"])
        order_date_col = self._find_column(df, ["order date (DateOrders)", "Order Date", "order_date"])
        sales_col = self._find_column(df, ["Sales", "sales"])
        customer_id_col = self._find_column(df, ["Customer ID", "customer_id", "CustomerId"])
        customer_name_col = self._find_column(df, ["Customer Name", "customer_name"])
        order_status_col = self._find_column(df, ["Order Status", "order_status", "OrderStatus"])

        if not order_id_col or not sales_col:
            print("⚠️  缺少必要列，跳过应收账款数据插入")
            return

        inserted = 0
        batch_size = 1000

        for i in range(0, len(df), batch_size):
            batch = df.iloc[i : i + batch_size]
            values_list = []

            for _, row in batch.iterrows():
                try:
                    invoice_date = None
                    if order_date_col:
                        date_val = row[order_date_col]
                        if pd.notna(date_val):
                            with contextlib.suppress(BaseException):
                                invoice_date = pd.to_datetime(date_val).date()

                    # 假设账期为30天
                    due_date = None
                    if invoice_date:
                        from datetime import timedelta

                        due_date = invoice_date + timedelta(days=30)

                    invoice_amount = float(row[sales_col]) if pd.notna(row[sales_col]) else 0.0
                    order_status = (
                        str(row[order_status_col])
                        if order_status_col and pd.notna(row[order_status_col])
                        else "Unknown"
                    )

                    # 根据订单状态判断支付状态
                    if "Complete" in order_status or "Completed" in order_status:
                        paid_amount = invoice_amount
                        outstanding_amount = 0.0
                        payment_status = "Paid"
                    elif "Cancel" in order_status or "Cancelled" in order_status:
                        paid_amount = 0.0
                        outstanding_amount = 0.0
                        payment_status = "Cancelled"
                    else:
                        paid_amount = 0.0
                        outstanding_amount = invoice_amount
                        payment_status = "Outstanding"

                    values = (
                        str(row[order_id_col]),
                        str(row[customer_id_col]) if customer_id_col and pd.notna(row[customer_id_col]) else None,
                        str(row[customer_name_col]) if customer_name_col and pd.notna(row[customer_name_col]) else None,
                        invoice_date,
                        due_date,
                        invoice_amount,
                        paid_amount,
                        outstanding_amount,
                        payment_status,
                        0,  # days_past_due
                    )
                    values_list.append(values)
                except Exception:
                    continue

            if values_list:
                cursor.executemany(
                    """
                    INSERT OR REPLACE INTO accounts_receivable
                    (order_id, customer_id, customer_name, invoice_date, due_date,
                     invoice_amount, paid_amount, outstanding_amount, payment_status, days_past_due)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    values_list,
                )
                inserted += len(values_list)
                print(f"  已插入 {inserted:,} 条应收账款记录...", end="\r")

        print(f"\n✓ 插入 {inserted:,} 条应收账款记录")

    def create_audit_db(self):
        """创建审计数据库 (Audit DB) - 空表结构"""
        print("\n" + "=" * 60)
        print("创建 Audit 数据库 (audit.db)")
        print("=" * 60)

        conn = sqlite3.connect(self.audit_db_path)
        cursor = conn.cursor()

        # 1. 审计日志表 (audit_logs)
        print("\n创建 audit_logs 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                audit_type TEXT,
                source_system TEXT,
                entity_type TEXT,
                entity_id TEXT,
                action TEXT,
                old_value TEXT,
                new_value TEXT,
                auditor_id TEXT,
                auditor_name TEXT,
                notes TEXT,
                risk_level TEXT,
                status TEXT DEFAULT 'Pending'
            )
        """)

        # 2. 风险标记表 (risk_flags)
        print("创建 risk_flags 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS risk_flags (
                flag_id INTEGER PRIMARY KEY AUTOINCREMENT,
                flag_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                risk_type TEXT,
                severity TEXT,
                entity_type TEXT,
                entity_id TEXT,
                description TEXT,
                source_system TEXT,
                status TEXT DEFAULT 'Open',
                assigned_to TEXT,
                resolution_notes TEXT,
                resolved_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_entity ON audit_logs(entity_type, entity_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_date ON audit_logs(audit_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_risk_flags_entity ON risk_flags(entity_type, entity_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_risk_flags_status ON risk_flags(status)")

        conn.commit()
        conn.close()
        print("✓ Audit 数据库表结构创建完成（空表）")
        print(f"✓ Audit 数据库初始化完成: {self.audit_db_path}")

    def _find_column(self, df: pd.DataFrame, possible_names: List[str]) -> str:
        """智能查找列名（处理大小写和空格变化）"""
        df_cols_lower = {col.lower().strip(): col for col in df.columns}

        for name in possible_names:
            name_lower = name.lower().strip()
            if name_lower in df_cols_lower:
                return df_cols_lower[name_lower]

        return None

    def verify_databases(self):
        """验证数据库创建成功"""
        print("\n" + "=" * 60)
        print("验证数据库")
        print("=" * 60)

        databases = [(self.ops_db_path, "Operations"), (self.finance_db_path, "Finance"), (self.audit_db_path, "Audit")]

        for db_path, db_name in databases:
            if db_path.exists():
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # 获取所有表
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()

                print(f"\n{db_name} DB ({db_path.name}):")
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                    count = cursor.fetchone()[0]
                    print(f"  - {table[0]}: {count:,} 条记录")

                conn.close()
            else:
                print(f"\n❌ {db_name} DB 不存在: {db_path}")

    def initialize(self):
        """执行完整的初始化流程"""
        print("=" * 60)
        print("ERP 数据库初始化 - 企业级架构")
        print("=" * 60)
        print("\n这将创建三个独立的数据库，模拟真实 ERP 环境：")
        print("  1. db_operations.db  - 运营数据（订单、物流、产品）")
        print("  2. db_finance.db     - 财务数据（总账、应收账款）")
        print("  3. audit.db          - 审计数据（审计日志、风险标记）")
        print()

        # 加载原始数据
        df = self.load_raw_data()

        # 创建三个数据库
        self.create_operations_db(df)
        self.create_finance_db(df)
        self.create_audit_db()

        # 验证
        self.verify_databases()

        print("\n" + "=" * 60)
        print("✓ ERP 数据库初始化完成！")
        print("=" * 60)
        print("\n数据库文件位置：")
        print(f"  - Operations: {self.ops_db_path}")
        print(f"  - Finance: {self.finance_db_path}")
        print(f"  - Audit: {self.audit_db_path}")
        print("\n现在可以使用 SQL 查询跨数据库进行审计分析！")


def main():
    """主函数"""
    initializer = ERPDatabaseInitializer()
    initializer.initialize()


if __name__ == "__main__":
    main()
