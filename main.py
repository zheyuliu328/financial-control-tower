"""
DataCo Global Supply Chain & Finance Audit System
主程序入口
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.audit.financial_control_tower import FinancialControlTower


def run_sample_mode():
    """Demo mode with sample data"""
    print("\n[Demo Mode] 使用内置样例数据...")

    import sqlite3

    import pandas as pd

    # Create demo databases
    data_dir = project_root / 'data'
    data_dir.mkdir(exist_ok=True)

    # Create sample operations database
    conn_ops = sqlite3.connect(data_dir / 'db_operations.db')
    df_ops = pd.read_csv(project_root / 'data' / 'sample' / 'operations_sample.csv')
    df_ops.to_sql('sales_orders', conn_ops, if_exists='replace', index=False)
    conn_ops.close()

    # Create sample finance database
    conn_fin = sqlite3.connect(data_dir / 'db_finance.db')
    df_fin = pd.read_csv(project_root / 'data' / 'sample' / 'finance_sample.csv')
    df_fin.to_sql('order_revenue', conn_fin, if_exists='replace', index=False)
    conn_fin.close()

    # Create audit database
    conn_audit = sqlite3.connect(data_dir / 'audit.db')
    conn_audit.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            severity TEXT,
            description TEXT
        )
    ''')
    conn_audit.commit()
    conn_audit.close()

    print("✓ 样例数据库已创建")
    return True


def main():
    parser = argparse.ArgumentParser(description='Financial Control Tower')
    parser.add_argument('--sample', action='store_true', help='Use sample data (demo mode)')
    args = parser.parse_args()

    print("=" * 70)
    print("   DataCo Global Supply Chain & Finance Audit System")
    print("=" * 70)

    print("\n[Step 1] 检查环境...")
    db_path = project_root / 'data' / 'db_operations.db'

    if args.sample:
        run_sample_mode()
    elif not db_path.exists():
        print("\n⚠️  未检测到数据库文件")
        print("=" * 70)
        print("运行方式:")
        print("  1. Demo模式: python main.py --sample")
        print("  2. 完整数据: python scripts/setup_project.py")
        print("=" * 70)
        return

    print("✓ 数据库文件已就绪")

    print("\n[Step 2] 启动财务控制塔...")
    print("=" * 70)

    try:
        tower = FinancialControlTower()
        tower.run_full_audit()

        print("\n" + "=" * 70)
        print("💡 提示: 审计结果已保存到 data/audit.db")
        print("   你可以使用 SQL 工具查看 audit_logs 表")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
