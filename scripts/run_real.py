#!/usr/bin/env python3
"""
FCT Run-Real Mode
支持用户提供 ERP 导出 CSV 进行对账
"""
import argparse
import json
import os
import sys
from datetime import datetime

import pandas as pd


def validate_erp_csv(csv_path: str) -> dict:
    """验证 ERP CSV 格式"""
    required_columns = ['transaction_id', 'amount', 'date', 'account_code']

    if not os.path.exists(csv_path):
        return {'valid': False, 'error': f'File not found: {csv_path}'}

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        return {'valid': False, 'error': f'Cannot read CSV: {e}'}

    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        return {'valid': False, 'error': f'Missing columns: {missing}'}

    return {'valid': True, 'rows': len(df), 'columns': list(df.columns)}

def run_reconciliation(csv_path: str, output_dir: str = 'artifacts') -> dict:
    """运行对账流程"""
    validation = validate_erp_csv(csv_path)
    if not validation['valid']:
        print(f"[ERROR] Validation failed: {validation['error']}")
        sys.exit(1)

    print(f"[INFO] Validated {validation['rows']} rows")

    df = pd.read_csv(csv_path)

    # Simple anomaly detection
    anomalies = []
    for idx, row in df.iterrows():
        if row['amount'] < 0:
            anomalies.append({'row': idx, 'type': 'negative_amount', 'value': row['amount']})
        if pd.isna(row['account_code']):
            anomalies.append({'row': idx, 'type': 'missing_account_code'})

    run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    report = {
        'run_id': run_id,
        'version': '2.0.0',
        'timestamp': datetime.now().isoformat(),
        'input_file': csv_path,
        'rows_processed': len(df),
        'anomalies_found': len(anomalies),
        'anomaly_list': anomalies[:10]  # Limit to first 10
    }

    os.makedirs(output_dir, exist_ok=True)

    report_path = os.path.join(output_dir, f'reconciliation_report_{run_id}.json')
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"[OK] Report saved: {report_path}")
    print(f"[OK] Found {len(anomalies)} anomalies")

    return report

def main():
    parser = argparse.ArgumentParser(description='FCT Run-Real Mode')
    parser.add_argument('csv', help='Input ERP CSV file path')
    parser.add_argument('--output', '-o', default='artifacts', help='Output directory')
    parser.add_argument('--validate-only', action='store_true', help='Only validate')

    args = parser.parse_args()

    if args.validate_only:
        result = validate_erp_csv(args.csv)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result['valid'] else 1)

    run_reconciliation(args.csv, args.output)

if __name__ == '__main__':
    main()
