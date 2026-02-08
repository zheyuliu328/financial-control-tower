"""
数据下载脚本
支持通过 kagglehub 或 opendatasets 下载 DataCo Smart Supply Chain Dataset
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def download_with_kagglehub():
    """使用 kagglehub 库下载数据并搬运到项目目录"""
    try:
        import shutil

        import kagglehub

        print("正在使用 kagglehub 下载数据...")
        # DataCo Smart Supply Chain Dataset
        dataset_path = kagglehub.dataset_download("rohanrao/data-co-supply-chain-dataset")

        print(f"数据已下载到缓存目录: {dataset_path}")

        # 创建目标目录
        target_dir = project_root / "data" / "raw"
        target_dir.mkdir(parents=True, exist_ok=True)

        # 查找 CSV 文件（递归搜索，因为 kagglehub 可能有多层目录）
        csv_files = list(Path(dataset_path).rglob("*.csv"))

        if not csv_files:
            # 也检查直接在当前目录
            csv_files = list(Path(dataset_path).glob("*.csv"))

        if csv_files:
            copied_count = 0
            for csv_file in csv_files:
                # 使用原始文件名，避免路径冲突
                target_file = target_dir / csv_file.name

                # 如果目标文件已存在且大小相同，跳过
                if target_file.exists() and target_file.stat().st_size == csv_file.stat().st_size:
                    print(f"文件已存在，跳过: {target_file.name}")
                    continue

                # 复制文件到项目目录
                shutil.copy2(csv_file, target_file)
                file_size_mb = target_file.stat().st_size / 1024 / 1024
                print(f"✓ 已复制文件: {target_file.name} ({file_size_mb:.2f} MB)")
                copied_count += 1

            if copied_count > 0:
                print(f"\n✅ 成功搬运 {copied_count} 个文件到项目目录: {target_dir}")
                return True
            else:
                print("\n✓ 所有文件已存在于项目目录")
                return True
        else:
            print(f"⚠️  在 {dataset_path} 中未找到 CSV 文件")
            print("尝试搜索所有文件...")
            all_files = list(Path(dataset_path).rglob("*"))
            print(f"找到 {len(all_files)} 个文件/目录")
            if all_files:
                print("前 10 个文件/目录:")
                for f in all_files[:10]:
                    print(f"  - {f}")
            return False

    except ImportError:
        print("kagglehub 未安装，尝试使用 opendatasets...")
        return False
    except Exception as e:
        print(f"使用 kagglehub 下载失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def download_with_opendatasets():
    """使用 opendatasets 库下载数据"""
    try:
        import opendatasets as od

        print("正在使用 opendatasets 下载数据...")

        # 创建目标目录
        target_dir = project_root / "data" / "raw"
        target_dir.mkdir(parents=True, exist_ok=True)

        # Kaggle 数据集 URL
        dataset_url = "https://www.kaggle.com/datasets/rohanrao/data-co-supply-chain-dataset"

        # 下载数据集（需要 Kaggle API 凭证）
        # 如果没有凭证，会提示用户输入
        od.download(dataset_url, data_dir=str(target_dir))

        print(f"数据已下载到: {target_dir}")
        return True

    except ImportError:
        print("opendatasets 未安装")
        return False
    except Exception as e:
        print(f"使用 opendatasets 下载失败: {e}")
        print("\n提示：如果下载失败，请手动下载：")
        print("1. 访问 https://www.kaggle.com/datasets/rohanrao/data-co-supply-chain-dataset")
        print("2. 下载 DataCoSupplyChainDataset.csv")
        print(f"3. 放置到 {target_dir} 目录")
        return False


def check_data_exists():
    """检查数据是否已存在"""
    data_dir = project_root / "data" / "raw"
    csv_files = list(data_dir.glob("*.csv")) if data_dir.exists() else []

    if csv_files:
        print(f"✓ 数据文件已存在: {csv_files[0]}")
        return True
    return False


def main():
    """主函数"""
    print("=" * 60)
    print("DataCo Smart Supply Chain Dataset 下载工具")
    print("=" * 60)
    print()

    # 检查数据是否已存在
    if check_data_exists():
        response = input("数据文件已存在，是否重新下载？(y/n): ")
        if response.lower() != "y":
            print("跳过下载")
            return

    print("\n尝试下载数据...")
    print("-" * 60)

    # 方法1: 尝试使用 kagglehub
    if download_with_kagglehub():
        print("\n✓ 下载成功！")
        return

    # 方法2: 尝试使用 opendatasets
    if download_with_opendatasets():
        print("\n✓ 下载成功！")
        return

    # 如果都失败了，提供手动下载说明
    print("\n" + "=" * 60)
    print("自动下载失败，请手动下载数据：")
    print("=" * 60)
    print("\n1. 访问 Kaggle 数据集页面：")
    print("   https://www.kaggle.com/datasets/rohanrao/data-co-supply-chain-dataset")
    print("\n2. 登录 Kaggle 账户并下载 DataCoSupplyChainDataset.csv")
    print("\n3. 将文件放置到以下目录：")
    data_dir = project_root / "data" / "raw"
    print(f"   {data_dir}")
    print("\n4. 如果目录不存在，脚本会自动创建")

    # 创建目录
    data_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n✓ 已创建目录: {data_dir}")


if __name__ == "__main__":
    main()
