"""
财务控制塔 (Financial Control Tower)
项目核心模块：自动化对账、合规审计、经营分析
"""

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd


class FinancialControlTower:
    """
    财务控制塔：企业级财务审计引擎

    核心功能：
    1. 业财对账 (Reconciliation): Operations vs Finance
    2. 供应链合规审计 (Compliance Audit)
    3. 财务报表生成 (Business Analysis)
    """

    def __init__(self):
        # 定义数据库路径
        base_dir = Path(__file__).parent.parent.parent / 'data'
        self.db_ops = base_dir / 'db_operations.db'
        self.db_fin = base_dir / 'db_finance.db'
        self.db_audit = base_dir / 'audit.db'

        # 验证数据库存在
        if not self.db_ops.exists():
            raise FileNotFoundError(
                f"Operations 数据库不存在: {self.db_ops}\n"
                "请先运行: python scripts/setup_project.py"
            )
        if not self.db_fin.exists():
            raise FileNotFoundError(
                f"Finance 数据库不存在: {self.db_fin}\n"
                "请先运行: python scripts/setup_project.py"
            )
        if not self.db_audit.exists():
            raise FileNotFoundError(
                f"Audit 数据库不存在: {self.db_audit}\n"
                "请先运行: python scripts/setup_project.py"
            )

    def _get_conn(self, db_path):
        """获取数据库连接"""
        return sqlite3.connect(str(db_path))

    def run_full_audit(self):
        """执行完整的审计流程"""
        print("\n" + "=" * 70)
        print("🗼 启动财务控制塔 (Financial Control Tower)")
        print(f"📅 审计日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        # 执行三大核心流程
        self.reconcile_operations_finance()
        self.audit_supply_chain_risks()
        self.generate_financial_statements()

        print("\n" + "=" * 70)
        print("✅ 所有审计流程执行完毕")
        print("=" * 70)

    def reconcile_operations_finance(self):
        """
        核心功能 1：业财对账 (SQL Reconciliation Logic)

        对比：业务库(发货) vs 财务库(应收)
        目标：找出收入漏记和金额不符

        面试要点：
        - 这是业财一体化的核心，展示你理解"数据对账"的业务逻辑
        - SQL: LEFT JOIN 找差异，WHERE NULL 找缺失
        """
        print("\n" + "=" * 70)
        print("🔍 [Process 1] 业财对账 (Reconciliation: Ops vs Finance)")
        print("=" * 70)

        conn_ops = self._get_conn(self.db_ops)
        conn_fin = self._get_conn(self.db_fin)

        # 1. 从业务库提取已发货订单 (Source of Truth for Revenue)
        # 排除已取消的订单
        query_ops = """
        SELECT
            order_id,
            order_status,
            sales as expected_revenue,
            customer_name
        FROM sales_orders
        WHERE order_status NOT IN ('CANCELED', 'SUSPECTED_FRAUD', 'CANCELLED')
        """
        df_ops = pd.read_sql(query_ops, conn_ops)

        # 2. 从财务库提取应收账款 (AR)
        query_fin = """
        SELECT
            order_id,
            invoice_amount as booked_revenue
        FROM accounts_receivable
        WHERE payment_status != 'Cancelled'
        """
        df_fin = pd.read_sql(query_fin, conn_fin)

        # 3. 对账逻辑 (Python Merge 模拟 SQL Full Outer Join)
        # 在真实 SQL 中可以是: SELECT ... FROM Ops LEFT JOIN Fin ON ... WHERE Fin.id IS NULL
        df_recon = pd.merge(df_ops, df_fin, on='order_id', how='left', indicator=True)

        # 4. 发现差异
        # Case A: 业务发货了，财务没记账 (漏记收入 - 严重风险)
        missing_in_fin = df_recon[df_recon['_merge'] == 'left_only']

        # Case B: 金额不一致 (处理浮点数精度问题)
        df_recon['diff'] = (df_recon['expected_revenue'] - df_recon['booked_revenue']).abs()
        amount_mismatch = df_recon[(df_recon['_merge'] == 'both') & (df_recon['diff'] > 0.01)]

        print("\n📊 对账结果：")
        print(f"   -> 业务侧订单数: {len(df_ops):,}")
        print(f"   -> 财务侧入账数: {len(df_fin):,}")
        print(f"   -> 完全匹配数量: {len(df_recon[df_recon['_merge'] == 'both']):,}")

        if not missing_in_fin.empty:
            print(f"\n   ⚠️  发现 {len(missing_in_fin)} 笔订单未入财务账 (Revenue Leakage)!")
            print("   风险级别: HIGH - 货物已发出但未记录收入")

            # 显示前5个案例
            print("\n   示例案例 (前5笔):")
            for _idx, row in missing_in_fin.head(5).iterrows():
                print(f"      - Order {row['order_id']}: ${row['expected_revenue']:.2f} | {row['customer_name']}")

            self._log_audit_issue(
                missing_in_fin['order_id'],
                'RECON_MISSING_AR',
                'HIGH',
                'Order shipped but not booked in AR'
            )
        else:
            print("\n   ✅ 收入确认完整性核对通过 (Completeness Check Passed)")

        if not amount_mismatch.empty:
            print(f"\n   ⚠️  发现 {len(amount_mismatch)} 笔订单金额不符!")
            print("   风险级别: MEDIUM - 业务金额与财务金额不一致")

            # 显示前5个案例
            print("\n   示例案例 (前5笔):")
            for _idx, row in amount_mismatch.head(5).iterrows():
                print(f"      - Order {row['order_id']}: 业务${row['expected_revenue']:.2f} vs 财务${row['booked_revenue']:.2f} (差异${row['diff']:.2f})")

            self._log_audit_issue(
                amount_mismatch['order_id'],
                'RECON_AMOUNT_MISMATCH',
                'MEDIUM',
                'Sales amount differs from AR amount'
            )
        else:
            print("\n   ✅ 金额准确性核对通过 (Accuracy Check Passed)")

        conn_ops.close()
        conn_fin.close()

    def audit_supply_chain_risks(self):
        """
        核心功能 2：供应链合规审计

        检测规则：
        1. 时间欺诈 (Timing Fraud): 发货早于订单
        2. 负毛利交易 (Negative Margin): 亏本销售

        面试要点：
        - 这展示了你对"业务规则"的理解，不只是技术能力
        - 时间倒流 = 先货后票 = 合规风险
        - 负毛利 = 可能的销售舞弊或错误
        """
        print("\n" + "=" * 70)
        print("🛡️  [Process 2] 供应链合规审计 (Compliance Audit)")
        print("=" * 70)

        conn_ops = self._get_conn(self.db_ops)

        # 联合查询订单和物流表
        # 这里展示你的 SQL 能力：虽然用 pandas read_sql，但 query 本身是复杂的
        query = """
        SELECT
            t1.order_id,
            t1.order_date,
            t2.shipping_date,
            t1.profit,
            t1.sales,
            t1.order_status,
            t1.customer_name
        FROM sales_orders t1
        JOIN shipping_logs t2 ON t1.order_id = t2.order_id
        WHERE t1.order_status NOT IN ('CANCELED', 'CANCELLED')
        """
        df = pd.read_sql(query, conn_ops)

        # 转换日期
        df['order_date'] = pd.to_datetime(df['order_date'], errors='coerce')
        df['shipping_date'] = pd.to_datetime(df['shipping_date'], errors='coerce')

        print(f"\n📊 审计范围: {len(df):,} 笔订单")

        # Rule 1: 时间欺诈 (发货早于订单)
        # 这在真实世界意味着：先货后票(合规风险) 或者 虚假订单补录
        timing_fraud = df[df['shipping_date'] < df['order_date']]
        if not timing_fraud.empty:
            print(f"\n   ⚠️  检测到 {len(timing_fraud)} 笔'时间倒流'交易 (Timing Fraud)")
            print("   风险级别: CRITICAL - 发货日期早于订单日期")
            print("   业务含义: 先货后票 / 虚假订单补录 / 数据录入错误")

            # 显示案例
            print("\n   示例案例 (前3笔):")
            for _idx, row in timing_fraud.head(3).iterrows():
                days_diff = (row['order_date'] - row['shipping_date']).days
                print(f"      - Order {row['order_id']}: 订单日期 {row['order_date'].date()} | 发货日期 {row['shipping_date'].date()} (提前{days_diff}天)")

            self._log_audit_issue(
                timing_fraud['order_id'],
                'SC_TIMING_FRAUD',
                'CRITICAL',
                'Shipping Date < Order Date'
            )
        else:
            print("\n   ✅ 时间逻辑核对通过 (No Timing Anomalies)")

        # Rule 2: 负毛利交易 (Negative Margin)
        # 可能是销售录入错误，或者是倾销
        negative_margin = df[df['profit'] < 0]
        if not negative_margin.empty:
            print(f"\n   ⚠️  检测到 {len(negative_margin)} 笔负毛利交易 (Negative Margin)")
            print("   风险级别: MEDIUM - 利润为负的正常订单")
            print("   业务含义: 亏本销售 / 促销活动 / 价格录入错误")

            # 统计负毛利金额
            total_loss = negative_margin['profit'].sum()
            print(f"   累计亏损: ${abs(total_loss):,.2f}")

            # 显示案例
            print("\n   示例案例 (前3笔最严重的):")
            for _idx, row in negative_margin.nsmallest(3, 'profit').iterrows():
                margin_pct = (row['profit'] / row['sales'] * 100) if row['sales'] > 0 else 0
                print(f"      - Order {row['order_id']}: 销售${row['sales']:.2f} | 利润${row['profit']:.2f} | 毛利率{margin_pct:.1f}%")

            self._log_audit_issue(
                negative_margin['order_id'],
                'SC_NEGATIVE_MARGIN',
                'MEDIUM',
                'Profit < 0 on active order'
            )
        else:
            print("\n   ✅ 盈利性核对通过 (All Orders Profitable)")

        conn_ops.close()

    def generate_financial_statements(self):
        """
        核心功能 3：财务报表生成

        生成：
        1. P&L 概览 (损益表)
        2. 地区利润分析

        面试要点：
        - 这展示了你能将数据转化为"业务洞察"
        - 不只是技术，更是业务分析能力
        """
        print("\n" + "=" * 70)
        print("📊 [Process 3] 生成经营分析报表 (Business Analysis)")
        print("=" * 70)

        conn_ops = self._get_conn(self.db_ops)

        # 1. P&L 概览 (月度损益表)
        query_pnl = """
        SELECT
            strftime('%Y-%m', order_date) as Month,
            COUNT(*) as Order_Count,
            SUM(sales) as Revenue,
            SUM(profit) as Net_Profit
        FROM sales_orders
        WHERE order_status NOT IN ('CANCELED', 'CANCELLED')
            AND order_date IS NOT NULL
        GROUP BY Month
        ORDER BY Month DESC
        LIMIT 6
        """
        df_pnl = pd.read_sql(query_pnl, conn_ops)

        if not df_pnl.empty:
            df_pnl['Margin_%'] = (df_pnl['Net_Profit'] / df_pnl['Revenue'] * 100).round(2)

            print("\n📈 月度损益概览 (P&L - Last 6 Months)")
            print("-" * 70)
            print(f"{'月份':<10} {'订单数':>10} {'收入 (USD)':>15} {'净利润 (USD)':>15} {'毛利率':>10}")
            print("-" * 70)
            for _, row in df_pnl.iterrows():
                print(f"{row['Month']:<10} {int(row['Order_Count']):>10,} ${row['Revenue']:>14,.2f} ${row['Net_Profit']:>14,.2f} {row['Margin_%']:>9.2f}%")
            print("-" * 70)

            # 汇总统计
            total_revenue = df_pnl['Revenue'].sum()
            total_profit = df_pnl['Net_Profit'].sum()
            avg_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
            print(f"{'总计':<10} {int(df_pnl['Order_Count'].sum()):>10,} ${total_revenue:>14,.2f} ${total_profit:>14,.2f} {avg_margin:>9.2f}%")
        else:
            print("\n⚠️  未找到有效的订单数据")

        # 2. 地区利润分析
        query_region = """
        SELECT
            customer_country as Region,
            COUNT(*) as Orders,
            SUM(sales) as Revenue,
            SUM(profit) as Profit
        FROM sales_orders
        WHERE order_status NOT IN ('CANCELED', 'CANCELLED')
            AND customer_country IS NOT NULL
            AND customer_country != ''
        GROUP BY Region
        ORDER BY Profit DESC
        LIMIT 10
        """
        df_region = pd.read_sql(query_region, conn_ops)

        if not df_region.empty:
            df_region['Margin_%'] = (df_region['Profit'] / df_region['Revenue'] * 100).round(2)

            print("\n🌍 Top 10 盈利地区 (Regional Performance)")
            print("-" * 70)
            print(f"{'地区':<20} {'订单数':>10} {'收入 (USD)':>15} {'利润 (USD)':>15} {'毛利率':>10}")
            print("-" * 70)
            for _, row in df_region.iterrows():
                print(f"{row['Region']:<20} {int(row['Orders']):>10,} ${row['Revenue']:>14,.2f} ${row['Profit']:>14,.2f} {row['Margin_%']:>9.2f}%")
            print("-" * 70)
        else:
            print("\n⚠️  未找到有效的地区数据")

        conn_ops.close()

    def _log_audit_issue(self, order_ids, risk_type, severity, details):
        """
        将发现的问题写入审计数据库

        这是"闭环管理"的体现：
        - 不只发现问题，还要记录问题
        - 方便后续跟踪和处理
        """
        conn_audit = self._get_conn(self.db_audit)

        # 准备数据
        logs = pd.DataFrame({
            'order_id': order_ids,
            'risk_type': risk_type,
            'severity': severity,
            'details': details,
            'detected_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

        # 写入 audit_logs 表
        # 使用新的表结构映射
        audit_records = []
        for _, row in logs.iterrows():
            audit_records.append({
                'audit_type': 'Automated',
                'source_system': 'Financial_Control_Tower',
                'entity_type': 'Order',
                'entity_id': str(row['order_id']),
                'action': risk_type,
                'notes': details,
                'risk_level': severity,
                'status': 'Pending'
            })

        df_audit = pd.DataFrame(audit_records)
        df_audit.to_sql('audit_logs', conn_audit, if_exists='append', index=False)

        conn_audit.close()
        print(f"      💾 [System] 已将 {len(logs)} 条风险记录写入 Audit DB")


def main():
    """主函数 - 可独立运行"""
    try:
        tower = FinancialControlTower()
        tower.run_full_audit()
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
