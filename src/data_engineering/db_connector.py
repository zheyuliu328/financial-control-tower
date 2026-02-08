"""
数据库连接器
提供统一的接口访问三个 ERP 数据库
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd


class ERPDatabaseConnector:
    """ERP 数据库连接器 - 模拟跨系统数据访问"""

    def __init__(self, data_dir: Path = None):
        self.project_root = Path(__file__).parent.parent.parent
        self.data_dir = data_dir or (self.project_root / "data")

        # 数据库路径
        self.ops_db = self.data_dir / "db_operations.db"
        self.finance_db = self.data_dir / "db_finance.db"
        self.audit_db = self.data_dir / "audit.db"

    @contextmanager
    def get_connection(self, db_name: str):
        """
        获取数据库连接的上下文管理器

        Args:
            db_name: 'operations', 'finance', 或 'audit'
        """
        db_map = {"operations": self.ops_db, "finance": self.finance_db, "audit": self.audit_db}

        if db_name not in db_map:
            raise ValueError(f"未知的数据库: {db_name}. 可选: {list(db_map.keys())}")

        db_path = db_map[db_name]
        if not db_path.exists():
            raise FileNotFoundError(
                f"数据库不存在: {db_path}\n请先运行: python src/data_engineering/init_erp_databases.py"
            )

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
        try:
            yield conn
        finally:
            conn.close()

    def execute_query(self, db_name: str, query: str, params: Tuple = None) -> List[Dict]:
        """
        执行查询并返回结果

        Args:
            db_name: 数据库名称
            query: SQL 查询语句
            params: 查询参数

        Returns:
            结果列表（字典格式）
        """
        with self.get_connection(db_name) as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()

            return [dict(zip(columns, row)) for row in rows]

    def execute_query_df(self, db_name: str, query: str, params: Tuple = None) -> pd.DataFrame:
        """
        执行查询并返回 DataFrame

        Args:
            db_name: 数据库名称
            query: SQL 查询语句
            params: 查询参数

        Returns:
            pandas DataFrame
        """
        with self.get_connection(db_name) as conn:
            if params:
                return pd.read_sql_query(query, conn, params=params)
            else:
                return pd.read_sql_query(query, conn)

    def cross_db_query(
        self, query_operations: str, query_finance: str = None, query_audit: str = None
    ) -> Dict[str, pd.DataFrame]:
        """
        跨数据库查询（模拟跨系统 ETL）

        Args:
            query_operations: Operations DB 查询
            query_finance: Finance DB 查询（可选）
            query_audit: Audit DB 查询（可选）

        Returns:
            包含各数据库查询结果的字典
        """
        results = {}

        if query_operations:
            results["operations"] = self.execute_query_df("operations", query_operations)

        if query_finance:
            results["finance"] = self.execute_query_df("finance", query_finance)

        if query_audit:
            results["audit"] = self.execute_query_df("audit", query_audit)

        return results

    def get_table_info(self, db_name: str, table_name: str) -> pd.DataFrame:
        """获取表结构信息"""
        query = f"PRAGMA table_info({table_name})"
        return self.execute_query_df(db_name, query)

    def get_table_count(self, db_name: str, table_name: str) -> int:
        """获取表的记录数"""
        query = f"SELECT COUNT(*) as count FROM {table_name}"  # nosec B608
        result = self.execute_query(db_name, query)
        return result[0]["count"] if result else 0

    def list_tables(self, db_name: str) -> List[str]:
        """列出数据库中的所有表"""
        query = "SELECT name FROM sqlite_master WHERE type='table'"
        results = self.execute_query(db_name, query)
        return [row["name"] for row in results]


# 便捷函数
def get_db_connector(data_dir: Path = None) -> ERPDatabaseConnector:
    """获取数据库连接器实例"""
    return ERPDatabaseConnector(data_dir)
