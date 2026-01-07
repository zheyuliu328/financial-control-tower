"""
DataCo Global Supply Chain & Finance Audit System
主程序入口
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.audit.financial_control_tower import FinancialControlTower


def main():
    print("=" * 70)
    print("   DataCo Global Supply Chain & Finance Audit System")
    print("=" * 70)
    
    print("\n[Step 1] 检查环境...")
    db_path = project_root / 'data' / 'db_operations.db'
    
    if not db_path.exists():
        print("\n⚠️  未检测到数据库文件")
        print("=" * 70)
        print("请先运行项目初始化脚本:")
        print("  python scripts/setup_project.py")
        print("=" * 70)
        print("\n该脚本将:")
        print("  1. 下载 DataCo 数据集 (通过 kagglehub)")
        print("  2. 创建三个 ERP 数据库 (Operations, Finance, Audit)")
        print("  3. 导入并分类数据")
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
