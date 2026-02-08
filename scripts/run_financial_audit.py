"""
财务审计快速入口脚本
快速运行完整的财务控制塔审计流程
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.audit.financial_control_tower import FinancialControlTower


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="运行财务控制塔审计流程")
    parser.add_argument("--month", type=int, help="月份 (1-12)")
    parser.add_argument("--year", type=int, help="年份 (如 2023)")

    args = parser.parse_args()

    tower = FinancialControlTower()
    tower.run_monthly_close(month=args.month, year=args.year)


if __name__ == "__main__":
    main()
