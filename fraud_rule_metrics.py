"""
fraud_rule_metrics.py - 欺诈规则性能指标模块

本模块实现了欺诈检测规则的完整性能评估框架，包括：
- TP (True Positive): 真阳性 - 正确识别的欺诈
- FP (False Positive): 假阳性 - 误报的欺诈
- FN (False Negative): 假阴性 - 漏报的欺诈
- TN (True Negative): 真阴性 - 正确识别的正常交易

以及派生指标：
- 精确率 (Precision): TP / (TP + FP)
- 召回率 (Recall): TP / (TP + FN)
- F1 Score: 2 * (Precision * Recall) / (Precision + Recall)
- 误报率 (False Positive Rate): FP / (FP + TN)

生产环境要求：
1. 所有欺诈规则必须有明确的阈值定义
2. 定期（至少每月）评估规则性能
3. 误报率超过5%的规则必须优化或停用
4. 所有评估结果必须记录到审计数据库
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum
import json


class FraudRuleType(Enum):
    """欺诈规则类型枚举"""
    TIMING_FRAUD = "timing_fraud"           # 时间欺诈：发货早于订单
    NEGATIVE_MARGIN = "negative_margin"     # 负毛利交易
    AMOUNT_ANOMALY = "amount_anomaly"       # 金额异常
    FREQUENCY_ANOMALY = "frequency_anomaly" # 频率异常
    CUSTOMER_RISK = "customer_risk"         # 客户风险评分


@dataclass
class FraudRuleThreshold:
    """欺诈规则阈值配置"""
    rule_type: FraudRuleType
    threshold_value: float
    severity_levels: Dict[str, Tuple[float, float]]  # 级别 -> (最小值, 最大值)
    description: str
    enabled: bool = True
    
    def get_severity(self, value: float) -> str:
        """根据值判断严重程度"""
        for level, (min_val, max_val) in self.severity_levels.items():
            if min_val <= value < max_val:
                return level
        return "LOW"


@dataclass
class RulePerformanceMetrics:
    """规则性能指标"""
    rule_type: FraudRuleType
    evaluation_period: str
    
    # 基础计数
    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0
    
    # 派生指标
    @property
    def precision(self) -> float:
        """精确率 = TP / (TP + FP)"""
        denominator = self.true_positives + self.false_positives
        return self.true_positives / denominator if denominator > 0 else 0.0
    
    @property
    def recall(self) -> float:
        """召回率 = TP / (TP + FN)"""
        denominator = self.true_positives + self.false_negatives
        return self.true_positives / denominator if denominator > 0 else 0.0
    
    @property
    def f1_score(self) -> float:
        """F1 Score = 2 * (Precision * Recall) / (Precision + Recall)"""
        denominator = self.precision + self.recall
        return 2 * (self.precision * self.recall) / denominator if denominator > 0 else 0.0
    
    @property
    def false_positive_rate(self) -> float:
        """误报率 = FP / (FP + TN)"""
        denominator = self.false_positives + self.true_negatives
        return self.false_positives / denominator if denominator > 0 else 0.0
    
    @property
    def false_negative_rate(self) -> float:
        """漏报率 = FN / (FN + TP)"""
        denominator = self.false_negatives + self.true_positives
        return self.false_negatives / denominator if denominator > 0 else 0.0
    
    @property
    def accuracy(self) -> float:
        """准确率 = (TP + TN) / Total"""
        total = self.true_positives + self.false_positives + self.true_negatives + self.false_negatives
        return (self.true_positives + self.true_negatives) / total if total > 0 else 0.0
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'rule_type': self.rule_type.value,
            'evaluation_period': self.evaluation_period,
            'true_positives': self.true_positives,
            'false_positives': self.false_positives,
            'true_negatives': self.true_negatives,
            'false_negatives': self.false_negatives,
            'precision': round(self.precision, 4),
            'recall': round(self.recall, 4),
            'f1_score': round(self.f1_score, 4),
            'false_positive_rate': round(self.false_positive_rate, 4),
            'false_negative_rate': round(self.false_negative_rate, 4),
            'accuracy': round(self.accuracy, 4),
        }


class FraudRuleManager:
    """欺诈规则管理器"""
    
    # 生产环境标准阈值配置
    DEFAULT_THRESHOLDS = {
        FraudRuleType.TIMING_FRAUD: FraudRuleThreshold(
            rule_type=FraudRuleType.TIMING_FRAUD,
            threshold_value=0,  # 发货日期 < 订单日期
            severity_levels={
                'CRITICAL': (float('-inf'), 0),  # 发货早于订单
                'HIGH': (0, 1),                   # 发货等于订单（同日）
                'MEDIUM': (1, 7),                 # 1-7天内发货
                'LOW': (7, float('inf'))          # 7天后发货
            },
            description="检测发货日期早于订单日期的异常情况"
        ),
        FraudRuleType.NEGATIVE_MARGIN: FraudRuleThreshold(
            rule_type=FraudRuleType.NEGATIVE_MARGIN,
            threshold_value=0,  # 利润 < 0
            severity_levels={
                'CRITICAL': (float('-inf'), -1000),  # 亏损 > $1000
                'HIGH': (-1000, -500),                # 亏损 $500-$1000
                'MEDIUM': (-500, 0),                  # 亏损 <$500
                'LOW': (0, float('inf'))              # 盈利
            },
            description="检测负毛利交易，可能是定价错误或欺诈"
        ),
        FraudRuleType.AMOUNT_ANOMALY: FraudRuleThreshold(
            rule_type=FraudRuleType.AMOUNT_ANOMALY,
            threshold_value=3.0,  # Z-score > 3
            severity_levels={
                'CRITICAL': (5, float('inf')),   # Z-score > 5
                'HIGH': (4, 5),                   # Z-score 4-5
                'MEDIUM': (3, 4),                 # Z-score 3-4
                'LOW': (0, 3)                     # Z-score < 3
            },
            description="基于统计学的金额异常检测（Z-score方法）"
        ),
        FraudRuleType.FREQUENCY_ANOMALY: FraudRuleThreshold(
            rule_type=FraudRuleType.FREQUENCY_ANOMALY,
            threshold_value=10,  # 单日订单数 > 10
            severity_levels={
                'CRITICAL': (50, float('inf')),  # 单日 > 50单
                'HIGH': (30, 50),                 # 单日 30-50单
                'MEDIUM': (15, 30),               # 单日 15-30单
                'LOW': (0, 15)                    # 单日 < 15单
            },
            description="检测客户单日订单频率异常"
        ),
    }
    
    def __init__(self, data_dir: Path = None):
        self.project_root = Path(__file__).parent.parent.parent
        self.data_dir = data_dir or (self.project_root / 'data')
        self.db_ops = self.data_dir / 'db_operations.db'
        self.db_fin = self.data_dir / 'db_finance.db'
        self.db_audit = self.data_dir / 'audit.db'
        
        self.thresholds = self.DEFAULT_THRESHOLDS.copy()
    
    def _get_conn(self, db_path: Path):
        """获取数据库连接"""
        return sqlite3.connect(str(db_path))
    
    def evaluate_timing_fraud_rule(self, start_date: str = None, end_date: str = None) -> RulePerformanceMetrics:
        """
        评估时间欺诈规则的性能
        
        在生产环境中，需要人工标注来确认真正的欺诈案例。
        这里使用启发式方法：
        - 发货日期早于订单日期超过7天 -> 标记为确认欺诈 (TP)
        - 发货日期早于订单日期1-7天 -> 标记为可疑 (需要人工审核)
        - 发货日期等于或晚于订单日期 -> 标记为正常 (TN)
        """
        conn = self._get_conn(self.db_ops)
        
        date_filter = ""
        if start_date and end_date:
            date_filter = f"WHERE t1.order_date BETWEEN '{start_date}' AND '{end_date}'"
        
        query = f"""
        SELECT 
            t1.order_id,
            t1.order_date,
            t2.shipping_date,
            julianday(t2.shipping_date) - julianday(t1.order_date) as day_diff,
            t1.profit,
            t1.sales
        FROM sales_orders t1
        JOIN shipping_logs t2 ON t1.order_id = t2.order_id
        {date_filter}
        AND t1.order_status NOT IN ('CANCELED', 'CANCELLED', 'SUSPECTED_FRAUD')
        """
        
        df = pd.read_sql(query, conn)
        conn.close()
        
        if df.empty:
            return RulePerformanceMetrics(
                rule_type=FraudRuleType.TIMING_FRAUD,
                evaluation_period=f"{start_date} to {end_date}"
            )
        
        # 转换日期
        df['order_date'] = pd.to_datetime(df['order_date'], errors='coerce')
        df['shipping_date'] = pd.to_datetime(df['shipping_date'], errors='coerce')
        df['actual_day_diff'] = (df['shipping_date'] - df['order_date']).dt.days
        
        # 规则触发条件：发货早于订单 (day_diff < 0)
        df['rule_triggered'] = df['actual_day_diff'] < 0
        
        # 启发式标注（生产环境应使用人工标注）
        # 发货早于订单超过7天 -> 高置信度欺诈
        # 发货早于订单1-7天 -> 中等置信度
        # 发货日期等于或晚于订单 -> 正常
        df['is_fraud'] = df['actual_day_diff'] < -7  # 启发式：超过7天认为是确认欺诈
        
        # 计算混淆矩阵
        tp = len(df[(df['rule_triggered'] == True) & (df['is_fraud'] == True)])
        fp = len(df[(df['rule_triggered'] == True) & (df['is_fraud'] == False)])
        tn = len(df[(df['rule_triggered'] == False) & (df['is_fraud'] == False)])
        fn = len(df[(df['rule_triggered'] == False) & (df['is_fraud'] == True)])
        
        return RulePerformanceMetrics(
            rule_type=FraudRuleType.TIMING_FRAUD,
            evaluation_period=f"{start_date} to {end_date}",
            true_positives=tp,
            false_positives=fp,
            true_negatives=tn,
            false_negatives=fn
        )
    
    def evaluate_negative_margin_rule(self, start_date: str = None, end_date: str = None) -> RulePerformanceMetrics:
        """
        评估负毛利规则的性能
        
        启发式标注：
        - 负毛利且金额 > $1000 -> 高置信度问题 (TP)
        - 负毛利但金额 <= $1000 -> 可能是促销或错误
        - 正毛利 -> 正常 (TN)
        """
        conn = self._get_conn(self.db_ops)
        
        date_filter = ""
        if start_date and end_date:
            date_filter = f"WHERE order_date BETWEEN '{start_date}' AND '{end_date}'"
        
        query = f"""
        SELECT 
            order_id,
            profit,
            sales,
            order_status
        FROM sales_orders
        {date_filter}
        AND order_status NOT IN ('CANCELED', 'CANCELLED', 'SUSPECTED_FRAUD')
        """
        
        df = pd.read_sql(query, conn)
        conn.close()
        
        if df.empty:
            return RulePerformanceMetrics(
                rule_type=FraudRuleType.NEGATIVE_MARGIN,
                evaluation_period=f"{start_date} to {end_date}"
            )
        
        # 规则触发条件：利润 < 0
        df['rule_triggered'] = df['profit'] < 0
        
        # 启发式标注：负毛利且金额 > $1000 认为是确认问题
        df['is_fraud'] = (df['profit'] < -1000)
        
        tp = len(df[(df['rule_triggered'] == True) & (df['is_fraud'] == True)])
        fp = len(df[(df['rule_triggered'] == True) & (df['is_fraud'] == False)])
        tn = len(df[(df['rule_triggered'] == False) & (df['is_fraud'] == False)])
        fn = len(df[(df['rule_triggered'] == False) & (df['is_fraud'] == True)])
        
        return RulePerformanceMetrics(
            rule_type=FraudRuleType.NEGATIVE_MARGIN,
            evaluation_period=f"{start_date} to {end_date}",
            true_positives=tp,
            false_positives=fp,
            true_negatives=tn,
            false_negatives=fn
        )
    
    def evaluate_all_rules(self, start_date: str = None, end_date: str = None) -> List[RulePerformanceMetrics]:
        """评估所有启用的规则"""
        results = []
        
        for rule_type, threshold in self.thresholds.items():
            if not threshold.enabled:
                continue
            
            if rule_type == FraudRuleType.TIMING_FRAUD:
                metrics = self.evaluate_timing_fraud_rule(start_date, end_date)
            elif rule_type == FraudRuleType.NEGATIVE_MARGIN:
                metrics = self.evaluate_negative_margin_rule(start_date, end_date)
            else:
                continue  # 其他规则暂未实现
            
            results.append(metrics)
        
        return results
    
    def save_metrics_to_audit_db(self, metrics: RulePerformanceMetrics):
        """保存指标到审计数据库"""
        conn = self._get_conn(self.db_audit)
        
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fraud_rule_metrics (
                metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                evaluation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                rule_type TEXT,
                evaluation_period TEXT,
                true_positives INTEGER,
                false_positives INTEGER,
                true_negatives INTEGER,
                false_negatives INTEGER,
                precision REAL,
                recall REAL,
                f1_score REAL,
                false_positive_rate REAL,
                false_negative_rate REAL,
                accuracy REAL,
                threshold_config TEXT,
                notes TEXT
            )
        """)
        
        data = metrics.to_dict()
        cursor.execute("""
            INSERT INTO fraud_rule_metrics 
            (evaluation_date, rule_type, evaluation_period, true_positives, false_positives,
             true_negatives, false_negatives, precision, recall, f1_score,
             false_positive_rate, false_negative_rate, accuracy, threshold_config)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            data['rule_type'],
            data['evaluation_period'],
            data['true_positives'],
            data['false_positives'],
            data['true_negatives'],
            data['false_negatives'],
            data['precision'],
            data['recall'],
            data['f1_score'],
            data['false_positive_rate'],
            data['false_negative_rate'],
            data['accuracy'],
            json.dumps(self.thresholds[data['rule_type']].__dict__, default=str) if data['rule_type'] in self.thresholds else None
        ))
        
        conn.commit()
        conn.close()
    
    def generate_performance_report(self, metrics_list: List[RulePerformanceMetrics]) -> str:
        """生成性能报告"""
        report_lines = [
            "=" * 80,
            "FRAUD RULE PERFORMANCE REPORT - 欺诈规则性能报告",
            f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 80,
            ""
        ]
        
        for metrics in metrics_list:
            report_lines.extend([
                f"\n规则类型: {metrics.rule_type.value}",
                f"评估周期: {metrics.evaluation_period}",
                "-" * 80,
                f"  基础计数:",
                f"    - 真阳性 (TP): {metrics.true_positives:,}",
                f"    - 假阳性 (FP): {metrics.false_positives:,}",
                f"    - 真阴性 (TN): {metrics.true_negatives:,}",
                f"    - 假阴性 (FN): {metrics.false_negatives:,}",
                f"",
                f"  性能指标:",
                f"    - 精确率 (Precision): {metrics.precision:.2%}",
                f"    - 召回率 (Recall): {metrics.recall:.2%}",
                f"    - F1 Score: {metrics.f1_score:.4f}",
                f"    - 误报率 (FPR): {metrics.false_positive_rate:.2%}",
                f"    - 漏报率 (FNR): {metrics.false_negative_rate:.2%}",
                f"    - 准确率 (Accuracy): {metrics.accuracy:.2%}",
                ""
            ])
            
            # 生产环境告警
            if metrics.false_positive_rate > 0.05:
                report_lines.append(f"  ⚠️  WARNING: 误报率超过5%，建议优化规则阈值")
            if metrics.recall < 0.8:
                report_lines.append(f"  ⚠️  WARNING: 召回率低于80%，可能漏检欺诈案例")
        
        report_lines.append("=" * 80)
        return "\n".join(report_lines)


def main():
    """主函数 - 演示欺诈规则性能评估"""
    print("=" * 80)
    print("Fraud Rule Metrics Evaluation - 欺诈规则性能评估")
    print("=" * 80)
    
    manager = FraudRuleManager()
    
    # 评估最近30天的规则性能
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    print(f"\n评估周期: {start_date} 至 {end_date}\n")
    
    # 评估所有规则
    metrics_list = manager.evaluate_all_rules(start_date, end_date)
    
    # 生成并打印报告
    report = manager.generate_performance_report(metrics_list)
    print(report)
    
    # 保存到审计数据库
    for metrics in metrics_list:
        manager.save_metrics_to_audit_db(metrics)
    
    print(f"\n✅ 性能指标已保存到 audit.db 的 fraud_rule_metrics 表")
    
    return metrics_list


if __name__ == "__main__":
    main()
