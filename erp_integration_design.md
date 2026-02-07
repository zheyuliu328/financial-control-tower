# ERP Integration Design - 真实 ERP 对接设计

## 1. 概述

本文档定义了 FCT (Financial Control Tower) 系统与真实 ERP 系统（如 SAP、Oracle）的对接架构，解决 Kaggle 演示数据与真实 ERP 环境的差异问题。

## 2. 当前问题分析

### 2.1 Kaggle 数据 vs 真实 ERP 差异

| 维度 | Kaggle 演示数据 | 真实 ERP 系统 |
|:-----|:----------------|:--------------|
| 数据源 | 单一 CSV 文件 | 多个异构系统 |
| 数据更新 | 静态数据 | 实时/准实时流 |
| 数据质量 | 已清洗 | 需要 ETL 清洗 |
| 认证授权 | 无 | OAuth 2.0 / SAML |
| API 协议 | 无 | REST / SOAP / RFC |
| 字段映射 | 简单 | 复杂（多系统映射） |
| 错误处理 | 简单 | 需要重试、补偿机制 |

### 2.2 需要解决的核心问题

1. **数据接入**: 如何从 SAP/Oracle 实时获取数据
2. **字段映射**: 不同系统间的字段名称和格式差异
3. **数据同步**: 增量更新 vs 全量更新
4. **错误处理**: 网络中断、系统维护时的容错
5. **认证安全**: API 密钥、OAuth Token 管理

## 3. ERP 对接架构

### 3.1 总体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FCT Financial Control Tower                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    数据接入层 (Data Ingestion)                    │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │   │
│  │  │  SAP Connector│  │Oracle Connector│  │  API Gateway │          │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │   │
│  └─────────┼─────────────────┼─────────────────┼──────────────────┘   │
│            │                 │                 │                       │
│            └─────────────────┼─────────────────┘                       │
│                              │                                         │
│                              ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    数据转换层 (Data Transformation)               │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │   │
│  │  │ Field Mapper │  │ Data Cleanser│  │   Validator  │          │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                         │
│                              ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    数据存储层 (Data Storage)                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │   │
│  │  │ Operations DB│  │  Finance DB  │  │   Audit DB   │          │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
            ▲
            │
┌───────────┴─────────────────────────────────────────────────────────────┐
│                           外部 ERP 系统                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │   SAP S/4HANA   │  │  Oracle ERP     │  │   Other Systems │         │
│  │  (OData/RFC)    │  │  (REST/SOAP)    │  │   (API/DB)      │         │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 连接器架构

```python
# ERP 连接器抽象基类
from abc import ABC, abstractmethod
from typing import Dict, List, Iterator
import pandas as pd

class ERPConnector(ABC):
    """ERP 连接器抽象基类"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.connection = None
    
    @abstractmethod
    def connect(self) -> bool:
        """建立与 ERP 系统的连接"""
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """断开连接"""
        pass
    
    @abstractmethod
    def fetch_sales_orders(self, start_date: str, end_date: str) -> pd.DataFrame:
        """获取销售订单数据"""
        pass
    
    @abstractmethod
    def fetch_accounts_receivable(self, start_date: str, end_date: str) -> pd.DataFrame:
        """获取应收账款数据"""
        pass
    
    @abstractmethod
    def get_field_mapping(self) -> Dict[str, str]:
        """获取字段映射表"""
        pass
```

## 4. SAP 集成设计

### 4.1 SAP 连接方式

| 连接方式 | 协议 | 适用场景 | 优缺点 |
|:---------|:-----|:---------|:-------|
| OData API | HTTP/REST | 云部署 S/4HANA | 现代、易用，但功能有限 |
| RFC/BAPI | SAP NW RFC | 本地部署 | 功能完整，但需要 SAP 库 |
| IDoc | 文件/消息队列 | 批量数据交换 | 可靠，但实时性差 |
| CDS Views | OData | 自定义报表 | 灵活，需要 SAP 开发 |

### 4.2 SAP 字段映射表

```yaml
# sap_field_mapping.yaml
sap_to_fct_mapping:
  sales_orders:
    # SAP 字段 -> FCT 字段
    VBELN: order_id                    # 销售订单号
    AUDAT: order_date                  # 订单日期
    KUNNR: customer_id                 # 客户编号
    NAME1: customer_name               # 客户名称
    MATNR: product_id                  # 物料编号
    MAKTX: product_name                # 物料描述
    KWMENG: order_quantity             # 订单数量
    NETWR: sales                       # 销售金额
    WAERK: currency                    # 货币
    GBSTK: order_status                # 总体状态
    
  accounts_receivable:
    BELNR: document_id                 # 凭证号
    VBELN: order_id                    # 销售订单参考
    KUNNR: customer_id                 # 客户编号
    BLDAT: invoice_date                # 发票日期
    DMBTR: invoice_amount              # 金额
    WRBTR: amount_local_currency       # 本币金额
    AUGDT: clearing_date               # 清账日期
    AUGBL: clearing_document           # 清账凭证
    
  # 数据类型转换规则
  data_type_conversions:
    order_date: "YYYYMMDD -> YYYY-MM-DD"
    customer_id: "remove_leading_zeros"
    sales: "decimal_2 -> float"
    order_status: "sap_status_code -> fct_status"
    
  # 状态码映射
  status_mapping:
    order_status:
      A: "NEW"           # 未处理
      B: "PROCESSING"    # 部分处理
      C: "COMPLETE"      # 完全处理
      D: "CANCELED"      # 已取消
```

### 4.3 SAP 连接器实现

```python
# sap_connector.py
import pandas as pd
from pyrfc import Connection  # SAP Python RFC 库
from .base import ERPConnector

class SAPConnector(ERPConnector):
    """SAP ERP 连接器"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.ashost = config.get('ashost')      # SAP 应用服务器
        self.sysnr = config.get('sysnr', '00')  # 系统编号
        self.client = config.get('client')      # 客户端
        self.user = config.get('user')          # 用户名
        self.password = config.get('password')  # 密码
        
    def connect(self) -> bool:
        """建立 SAP RFC 连接"""
        try:
            self.connection = Connection(
                ashost=self.ashost,
                sysnr=self.sysnr,
                client=self.client,
                user=self.user,
                passwd=self.password
            )
            return True
        except Exception as e:
            print(f"SAP 连接失败: {e}")
            return False
    
    def disconnect(self) -> bool:
        """断开 SAP 连接"""
        if self.connection:
            self.connection.close()
            self.connection = None
        return True
    
    def fetch_sales_orders(self, start_date: str, end_date: str) -> pd.DataFrame:
        """从 SAP 获取销售订单"""
        # 调用 SAP BAPI: BAPI_SALESORDER_GETLIST
        result = self.connection.call(
            'BAPI_SALESORDER_GETLIST',
            CUSTOMER_NUMBER='',
            SALES_ORGANIZATION='',
            DOCUMENT_DATE_FROM=start_date.replace('-', ''),
            DOCUMENT_DATE_TO=end_date.replace('-', '')
        )
        
        # 转换结果为 DataFrame
        orders = result.get('SALES_ORDERS', [])
        df = pd.DataFrame(orders)
        
        # 应用字段映射
        df = self._apply_field_mapping(df, 'sales_orders')
        
        return df
    
    def fetch_accounts_receivable(self, start_date: str, end_date: str) -> pd.DataFrame:
        """从 SAP 获取应收账款"""
        # 调用 SAP BAPI: BAPI_AR_ACC_GETOPENITEMS
        result = self.connection.call(
            'BAPI_AR_ACC_GETOPENITEMS',
            COMPANYCODE=self.config.get('company_code'),
            KEYDATE=end_date.replace('-', '')
        )
        
        items = result.get('LINEITEMS', [])
        df = pd.DataFrame(items)
        
        # 应用字段映射
        df = self._apply_field_mapping(df, 'accounts_receivable')
        
        return df
    
    def _apply_field_mapping(self, df: pd.DataFrame, table: str) -> pd.DataFrame:
        """应用字段映射"""
        mapping = self.get_field_mapping().get(table, {})
        
        # 重命名列
        df = df.rename(columns=mapping)
        
        # 应用数据类型转换
        # TODO: 实现具体的转换逻辑
        
        return df
    
    def get_field_mapping(self) -> Dict[str, str]:
        """获取 SAP 字段映射"""
        return {
            'sales_orders': {
                'VBELN': 'order_id',
                'AUDAT': 'order_date',
                'KUNNR': 'customer_id',
                'NAME1': 'customer_name',
                'MATNR': 'product_id',
                'MAKTX': 'product_name',
                'KWMENG': 'order_quantity',
                'NETWR': 'sales',
                'WAERK': 'currency',
                'GBSTK': 'order_status',
            },
            'accounts_receivable': {
                'BELNR': 'document_id',
                'VBELN': 'order_id',
                'KUNNR': 'customer_id',
                'BLDAT': 'invoice_date',
                'DMBTR': 'invoice_amount',
                'AUGDT': 'clearing_date',
            }
        }
```

## 5. Oracle ERP 集成设计

### 5.1 Oracle 连接方式

| 连接方式 | 协议 | 适用场景 |
|:---------|:-----|:---------|
| REST API | HTTPS | Oracle Fusion Cloud |
| SOAP Web Services | HTTPS | Oracle E-Business Suite |
| JDBC/ODBC | 数据库协议 | 直接数据库访问 |
| BI Publisher | REST/SOAP | 报表数据提取 |

### 5.2 Oracle 字段映射表

```yaml
# oracle_field_mapping.yaml
oracle_to_fct_mapping:
  sales_orders:
    # Oracle 字段 -> FCT 字段
    ORDER_NUMBER: order_id
    ORDERED_DATE: order_date
    SOLD_TO_ORG_ID: customer_id
    CUSTOMER_NAME: customer_name
    INVENTORY_ITEM_ID: product_id
    ORDERED_QUANTITY: order_quantity
    UNIT_SELLING_PRICE: unit_price
    LINE_TOTAL: sales
    CURRENCY_CODE: currency
    FLOW_STATUS_CODE: order_status
    
  accounts_receivable:
    CUSTOMER_TRX_ID: invoice_id
    TRX_NUMBER: invoice_number
    TRX_DATE: invoice_date
    BILL_TO_CUSTOMER_ID: customer_id
    INVOICE_CURRENCY_CODE: currency
    EXCHANGE_RATE: exchange_rate
    TOTAL_LINE_AMOUNT: invoice_amount
    AMOUNT_DUE_REMAINING: outstanding_amount
    
  # 状态码映射
  status_mapping:
    order_status:
      ENTERED: "NEW"
      BOOKED: "PROCESSING"
      CLOSED: "COMPLETE"
      CANCELLED: "CANCELED"
```

### 5.3 Oracle 连接器实现

```python
# oracle_connector.py
import requests
import pandas as pd
from .base import ERPConnector

class OracleConnector(ERPConnector):
    """Oracle ERP 连接器 (Fusion Cloud)"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.base_url = config.get('base_url')      # https://{instance}.fa.oraclecloud.com
        self.username = config.get('username')
        self.password = config.get('password')
        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def connect(self) -> bool:
        """测试 Oracle 连接"""
        try:
            response = self.session.get(f"{self.base_url}/fscmRestApi/resources/latest/")
            return response.status_code == 200
        except Exception as e:
            print(f"Oracle 连接失败: {e}")
            return False
    
    def disconnect(self) -> bool:
        """关闭会话"""
        self.session.close()
        return True
    
    def fetch_sales_orders(self, start_date: str, end_date: str) -> pd.DataFrame:
        """从 Oracle 获取销售订单"""
        # Oracle REST API 查询
        url = f"{self.base_url}/fscmRestApi/resources/latest/salesOrdersForOrderHub"
        
        params = {
            'q': f"OrderedDate >= '{start_date}' and OrderedDate <= '{end_date}'",
            'limit': 500,  # 分页大小
            'offset': 0
        }
        
        all_orders = []
        while True:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            items = data.get('items', [])
            all_orders.extend(items)
            
            # 检查是否有更多数据
            if len(items) < params['limit']:
                break
            params['offset'] += params['limit']
        
        df = pd.DataFrame(all_orders)
        df = self._apply_field_mapping(df, 'sales_orders')
        
        return df
    
    def fetch_accounts_receivable(self, start_date: str, end_date: str) -> pd.DataFrame:
        """从 Oracle 获取应收账款"""
        url = f"{self.base_url}/fscmRestApi/resources/latest/receivablesInvoices"
        
        params = {
            'q': f"InvoiceDate >= '{start_date}' and InvoiceDate <= '{end_date}'",
            'limit': 500,
            'offset': 0
        }
        
        all_invoices = []
        while True:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            items = data.get('items', [])
            all_invoices.extend(items)
            
            if len(items) < params['limit']:
                break
            params['offset'] += params['limit']
        
        df = pd.DataFrame(all_invoices)
        df = self._apply_field_mapping(df, 'accounts_receivable')
        
        return df
    
    def get_field_mapping(self) -> Dict[str, str]:
        """获取 Oracle 字段映射"""
        return {
            'sales_orders': {
                'OrderNumber': 'order_id',
                'OrderedDate': 'order_date',
                'SoldToOrgId': 'customer_id',
                'CustomerName': 'customer_name',
                'InventoryItemId': 'product_id',
                'OrderedQuantity': 'order_quantity',
                'UnitSellingPrice': 'unit_price',
                'LineTotal': 'sales',
                'CurrencyCode': 'currency',
                'FlowStatusCode': 'order_status',
            },
            'accounts_receivable': {
                'CustomerTrxId': 'invoice_id',
                'TrxNumber': 'invoice_number',
                'TrxDate': 'invoice_date',
                'BillToCustomerId': 'customer_id',
                'InvoiceCurrencyCode': 'currency',
                'TotalLineAmount': 'invoice_amount',
                'AmountDueRemaining': 'outstanding_amount',
            }
        }
```

## 6. 数据同步策略

### 6.1 同步模式

```python
# sync_scheduler.py
from enum import Enum
from datetime import datetime, timedelta
import schedule
import time

class SyncMode(Enum):
    FULL = "full"           # 全量同步
    INCREMENTAL = "incremental"  # 增量同步
    CHANGE_DATA_CAPTURE = "cdc"  # 变更数据捕获

class DataSyncScheduler:
    """数据同步调度器"""
    
    def __init__(self, connectors: Dict[str, ERPConnector]):
        self.connectors = connectors
        self.last_sync_time = {}
    
    def schedule_sync(self, system: str, table: str, mode: SyncMode, schedule_expr: str):
        """调度同步任务"""
        if schedule_expr == "hourly":
            schedule.every().hour.do(self._sync_job, system, table, mode)
        elif schedule_expr == "daily":
            schedule.every().day.at("02:00").do(self._sync_job, system, table, mode)
        elif schedule_expr == "weekly":
            schedule.every().sunday.at("03:00").do(self._sync_job, system, table, mode)
    
    def _sync_job(self, system: str, table: str, mode: SyncMode):
        """执行同步任务"""
        connector = self.connectors.get(system)
        if not connector:
            print(f"未知的系统: {system}")
            return
        
        # 确定时间范围
        if mode == SyncMode.INCREMENTAL:
            start_date = self.last_sync_time.get(f"{system}.{table}", datetime.now() - timedelta(days=1))
            end_date = datetime.now()
        else:
            start_date = datetime.now() - timedelta(days=30)
            end_date = datetime.now()
        
        # 执行同步
        try:
            if table == "sales_orders":
                df = connector.fetch_sales_orders(start_date, end_date)
            elif table == "accounts_receivable":
                df = connector.fetch_accounts_receivable(start_date, end_date)
            
            # 保存到本地数据库
            self._save_to_local_db(df, table)
            
            # 更新最后同步时间
            self.last_sync_time[f"{system}.{table}"] = end_date
            
            print(f"同步完成: {system}.{table}, 记录数: {len(df)}")
            
        except Exception as e:
            print(f"同步失败: {system}.{table}, 错误: {e}")
            # TODO: 发送告警通知
    
    def run(self):
        """运行调度器"""
        while True:
            schedule.run_pending()
            time.sleep(60)
```

### 6.2 同步策略矩阵

| 数据表 | 同步模式 | 频率 | 保留策略 |
|:-------|:---------|:-----|:---------|
| sales_orders | 增量同步 | 每小时 | 保留2年 |
| accounts_receivable | 增量同步 | 每小时 | 保留7年 |
| general_ledger | 增量同步 | 每日 | 保留10年 |
| audit_logs | 实时写入 | 实时 | 永久保留 |

## 7. 错误处理与重试机制

### 7.1 错误分类

| 错误类型 | 示例 | 处理策略 |
|:---------|:-----|:---------|
| 网络错误 | 连接超时 | 指数退避重试 |
| 认证错误 | Token 过期 | 刷新 Token 后重试 |
| 数据错误 | 字段缺失 | 记录到错误队列 |
| 系统错误 | ERP 维护中 | 延迟重试 |

### 7.2 重试机制

```python
# retry_handler.py
import time
from functools import wraps
from typing import Callable, Type

def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """指数退避重试装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        raise
                    
                    print(f"尝试 {attempt + 1} 失败: {e}, {delay}秒后重试...")
                    time.sleep(delay)
                    delay *= backoff_factor
            
            return None
        return wrapper
    return decorator

# 使用示例
class ERPConnectorWithRetry(ERPConnector):
    
    @retry_with_backoff(max_retries=3, exceptions=(ConnectionError, TimeoutError))
    def fetch_sales_orders(self, start_date: str, end_date: str) -> pd.DataFrame:
        # 实际获取逻辑
        pass
```

## 8. 配置管理

### 8.1 ERP 连接配置

```yaml
# erp_config.yaml
erp_systems:
  sap_production:
    type: "SAP"
    enabled: true
    connection:
      ashost: "sap-prod.company.com"
      sysnr: "00"
      client: "100"
      user: "${SAP_USER}"          # 从环境变量读取
      password: "${SAP_PASSWORD}"  # 从环境变量读取
    sync:
      sales_orders:
        mode: "incremental"
        frequency: "hourly"
      accounts_receivable:
        mode: "incremental"
        frequency: "hourly"
    
  oracle_production:
    type: "Oracle"
    enabled: true
    connection:
      base_url: "https://company.fa.oraclecloud.com"
      username: "${ORACLE_USER}"
      password: "${ORACLE_PASSWORD}"
    sync:
      sales_orders:
        mode: "incremental"
        frequency: "hourly"
      accounts_receivable:
        mode: "incremental"
        frequency: "hourly"
```

## 9. 监控与告警

### 9.1 监控指标

| 指标 | 描述 | 告警阈值 |
|:-----|:-----|:---------|
| sync_latency | 同步延迟 | > 5分钟 |
| sync_failure_rate | 同步失败率 | > 1% |
| record_count_delta | 记录数变化 | > 20% |
| api_response_time | API 响应时间 | > 10秒 |
| auth_failure_count | 认证失败次数 | > 3次/小时 |

### 9.2 集成健康检查

```python
# health_check.py
class ERPHealthChecker:
    """ERP 集成健康检查"""
    
    def __init__(self, connectors: Dict[str, ERPConnector]):
        self.connectors = connectors
    
    def check_all(self) -> Dict[str, Dict]:
        """检查所有 ERP 系统健康状态"""
        results = {}
        
        for name, connector in self.connectors.items():
            results[name] = self._check_single(connector)
        
        return results
    
    def _check_single(self, connector: ERPConnector) -> Dict:
        """检查单个 ERP 系统"""
        start_time = time.time()
        
        try:
            connected = connector.connect()
            response_time = time.time() - start_time
            
            return {
                'status': 'healthy' if connected else 'unhealthy',
                'response_time_ms': round(response_time * 1000, 2),
                'last_check': datetime.now().isoformat(),
                'error': None
            }
        except Exception as e:
            return {
                'status': 'error',
                'response_time_ms': None,
                'last_check': datetime.now().isoformat(),
                'error': str(e)
            }
        finally:
            connector.disconnect()
```

## 10. 附录

### 10.1 相关文档

- `reconciliation_matrix.md` - 对账控制矩阵
- `security_architecture.md` - 权限分离架构
- `fraud_rule_metrics.py` - 欺诈规则性能指标

### 10.2 术语定义

| 术语 | 定义 |
|:-----|:-----|
| RFC | Remote Function Call - SAP 远程函数调用 |
| BAPI | Business Application Programming Interface |
| OData | Open Data Protocol - 开放数据协议 |
| CDC | Change Data Capture - 变更数据捕获 |
| ETL | Extract, Transform, Load - 数据抽取转换加载 |

### 10.3 依赖库

```txt
# requirements_erp.txt
pyrfc>=2.0.0          # SAP RFC 连接
requests>=2.28.0      # HTTP 请求
pandas>=1.5.0         # 数据处理
pyyaml>=6.0           # YAML 配置
schedule>=1.1.0       # 任务调度
```

---

**文档版本**: 1.0  
**最后更新**: 2026-02-07  
**维护者**: Financial Control Tower Integration Team
