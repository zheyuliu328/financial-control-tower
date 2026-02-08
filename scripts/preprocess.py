"""
数据预处理脚本
对下载的原始数据进行清洗和预处理
"""

import sys
from pathlib import Path

import pandas as pd

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def load_raw_data():
    """加载原始数据"""
    data_dir = project_root / "data" / "raw"
    csv_files = list(data_dir.glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError("未找到数据文件，请先运行 scripts/download_data.py")

    print(f"正在加载数据: {csv_files[0]}")
    df = pd.read_csv(csv_files[0], low_memory=False)
    print(f"原始数据形状: {df.shape}")
    print(f"列数: {len(df.columns)}")

    return df, csv_files[0].name

def explore_data(df):
    """探索数据基本信息"""
    print("\n" + "=" * 60)
    print("数据基本信息")
    print("=" * 60)
    print(f"\n数据形状: {df.shape}")
    print("\n列名:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i:2d}. {col}")

    print("\n数据类型:")
    print(df.dtypes)

    print("\n缺失值统计:")
    missing = df.isnull().sum()
    missing_pct = (missing / len(df) * 100).round(2)
    missing_df = pd.DataFrame({
        '缺失数量': missing,
        '缺失百分比': missing_pct
    })
    print(missing_df[missing_df['缺失数量'] > 0])

    print("\n数据前5行:")
    print(df.head())

    return df

def clean_data(df):
    """清洗数据"""
    print("\n" + "=" * 60)
    print("数据清洗")
    print("=" * 60)

    original_shape = df.shape
    print(f"清洗前数据形状: {original_shape}")

    # 删除完全重复的行
    df = df.drop_duplicates()
    print(f"删除重复行后: {df.shape}")

    # 处理缺失值（根据实际情况调整）
    # 这里先保留所有数据，后续根据分析需求处理

    print(f"清洗后数据形状: {df.shape}")
    print(f"删除了 {original_shape[0] - df.shape[0]} 行")

    return df

def save_processed_data(df, original_filename):
    """保存处理后的数据"""
    output_dir = project_root / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存为 CSV
    output_file = output_dir / f"processed_{original_filename}"
    df.to_csv(output_file, index=False)
    print(f"\n✓ 已保存处理后的数据: {output_file}")

    # 保存为 Parquet（更高效）
    parquet_file = output_dir / f"processed_{original_filename.replace('.csv', '.parquet')}"
    df.to_parquet(parquet_file, index=False, engine='pyarrow')
    print(f"✓ 已保存为 Parquet 格式: {parquet_file}")

    return output_file, parquet_file

def main():
    """主函数"""
    print("=" * 60)
    print("DataCo 数据预处理")
    print("=" * 60)

    try:
        # 加载数据
        df, filename = load_raw_data()

        # 探索数据
        df = explore_data(df)

        # 清洗数据
        df = clean_data(df)

        # 保存处理后的数据
        save_processed_data(df, filename)

        print("\n" + "=" * 60)
        print("✓ 数据预处理完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

