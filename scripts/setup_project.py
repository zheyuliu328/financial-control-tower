"""
项目初始化脚本
自动下载数据并初始化数据库
"""

import os
import shutil
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import kagglehub
except ImportError:
    print("❌ kagglehub 未安装，正在安装...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "kagglehub"])
    import kagglehub

from src.data_engineering.init_erp_databases import ERPDatabaseInitializer


def setup():
    print("=" * 70)
    print("🚀 开始项目初始化设置...")
    print("=" * 70)

    # 1. 确保数据目录存在
    raw_dir = project_root / 'data' / 'raw'
    raw_dir.mkdir(parents=True, exist_ok=True)

    target_path = raw_dir / 'DataCoSupplyChainDataset.csv'

    # 2. 检查或获取数据
    if not target_path.exists():
        print("\n📥 正在通过 kagglehub 获取 DataCo 数据集...")
        try:
            # 这会下载或获取已缓存的路径
            path = kagglehub.dataset_download("shashwatwork/dataco-smart-supply-chain-for-big-data-analysis")
            print(f"✓ 数据集已下载到: {path}")

            # 查找 CSV 文件
            csv_file = None
            for root, _dirs, files in os.walk(path):
                for file in files:
                    if file.endswith('.csv'):
                        csv_file = os.path.join(root, file)
                        break
                if csv_file:
                    break

            if csv_file:
                print(f"📦 移动数据文件: {csv_file}")
                print(f"   -> {target_path}")
                shutil.copy(csv_file, target_path)
                print("✓ 数据文件移动完成")
            else:
                print("❌ 未找到 CSV 文件，请手动下载。")
                print("请访问: https://www.kaggle.com/datasets/shashwatwork/dataco-smart-supply-chain-for-big-data-analysis")
                print(f"下载后将文件放入: {raw_dir}")
                return False
        except Exception as e:
            print(f"❌ 下载失败: {e}")
            print("\n请手动下载 'DataCo Smart Supply Chain' 数据集：")
            print("1. 访问: https://www.kaggle.com/datasets/shashwatwork/dataco-smart-supply-chain-for-big-data-analysis")
            print("2. 下载 CSV 文件")
            print(f"3. 将文件放入: {raw_dir}")
            return False
    else:
        print(f"\n✅ 数据文件已存在: {target_path}")

    # 3. 初始化数据库
    print("\n" + "=" * 70)
    print("🏭 正在初始化 ERP 数据库架构...")
    print("=" * 70)
    try:
        initializer = ERPDatabaseInitializer()
        initializer.initialize()
        print("\n" + "=" * 70)
        print("✨ 项目设置完成！现在可以运行财务控制塔了。")
        print("=" * 70)
        print("\n💡 下一步：运行 'python main.py' 启动财务控制塔")
        return True
    except Exception as e:
        print(f"\n❌ 数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = setup()
    sys.exit(0 if success else 1)

