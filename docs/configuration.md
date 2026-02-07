# Configuration Guide - 30 分钟真实接入

> 本指南帮助你将 FCT 接入真实 ERP 系统，完成字段映射和配置。

---

## 前置要求

- 已完成 [Quickstart](./quickstart.md)
- 拥有 ERP 系统访问权限（SAP/Oracle/其他）
- 了解源系统表结构

---

## 一、ERP 连接配置

### 1.1 复制配置模板

```bash
cp config/erp_config.example.yaml config/erp_config.yaml
```

### 1.2 配置 SAP S/4HANA

编辑 `config/erp_config.yaml`:

```yaml
sap:
  host: "your-sap-server.com"
  system_id: "PRD"
  client: "100"
  username: "FCT_USER"
  password: "${SAP_PASSWORD}"  # 使用环境变量
  
  # RFC 连接参数
  rfc:
    ashost: "your-sap-server.com"
    sysnr: "00"
    lang: "EN"
```

### 1.3 配置 Oracle ERP

```yaml
oracle:
  base_url: "https://your-oracle-erp.com"
  username: "FCT_USER"
  password: "${ORACLE_PASSWORD}"
  
  # REST API 参数
  api_version: "v2"
  timeout: 30
```

### 1.4 设置环境变量

```bash
# Linux/Mac
export SAP_PASSWORD="your_sap_password"
export ORACLE_PASSWORD="your_oracle_password"

# Windows PowerShell
$env:SAP_PASSWORD="your_sap_password"
```

---

## 二、字段映射规范

### 2.1 SAP 字段映射

| SAP 表 | SAP 字段 | FCT 字段 | 说明 |
|:-------|:---------|:---------|:-----|
| VBAK | VBELN | order_id | 销售订单号 |
| VBAK | AUDAT | order_date | 订单日期 |
| VBAK | KUNNR | customer_id | 客户编号 |
| VBAP | NETWR | sales | 销售金额 |
| VBAP | GBSTK | order_status | 订单状态 |
| LIKP | WADAT | shipping_date | 发货日期 |

### 2.2 Oracle 字段映射

| Oracle 表 | Oracle 字段 | FCT 字段 | 说明 |
|:----------|:------------|:---------|:-----|
| RA_CUSTOMER_TRX_ALL | trx_number | invoice_id | 发票编号 |
| RA_CUSTOMER_TRX_ALL | trx_date | invoice_date | 发票日期 |
| RA_CUSTOMER_TRX_ALL | bill_to_customer_id | customer_id | 客户ID |
| RA_CUSTOMER_TRX_ALL | invoice_amount | invoice_amount | 发票金额 |
| AR_PAYMENT_SCHEDULES | status | payment_status | 付款状态 |

### 2.3 自定义字段映射

编辑 `src/integration/field_mapping.py`:

```python
CUSTOM_MAPPING = {
    "sap": {
        "VBELN": "order_id",
        "AUDAT": "order_date",
        # 添加自定义映射
        "YOUR_FIELD": "fct_field"
    },
    "oracle": {
        "OrderNumber": "order_id",
        # 添加自定义映射
    }
}
```

---

## 三、运行生产模式

### 3.1 同步 ERP 数据

```bash
# 运行数据同步调度器
python -m src.integration.sync_scheduler
```

**这一步会做什么**:
- 连接 ERP 系统
- 抽取增量数据
- 写入 Operations/Finance 数据库

### 3.2 运行生产审计

```bash
python main.py --mode=production
```

---

## 四、常见失败点

### 4.1 连接失败

**现象**: `Connection refused` 或 `RFC_ERROR_COMMUNICATION`

**排查步骤**:
1. 检查网络连通性: `ping your-sap-server.com`
2. 验证端口开放: `telnet your-sap-server.com 3300`
3. 确认 SAP 网关服务运行中
4. 检查防火墙规则

### 4.2 字段映射错误

**现象**: 对账结果异常，匹配率过低

**排查步骤**:
1. 检查源数据编码（中文需 UTF-8）
2. 验证日期格式一致（建议统一为 YYYY-MM-DD）
3. 确认货币单位一致
4. 检查字段大小写（SAP 字段通常大写）

### 4.3 数据类型不匹配

**现象**: `TypeError` 或数据截断

**解决方案**:
```python
# 在字段映射中添加类型转换
"sales": {
    "source_field": "NETWR",
    "transform": lambda x: float(x) / 100  # SAP 金额通常需除100
}
```

### 4.4 权限不足

**现象**: `Authorization failed` 或无法写入 audit.db

**解决方案**:
```bash
# 检查目录权限
chmod 755 data/

# 确认 ERP 用户有读取权限
# 确认 FCT 进程有写入权限
```

---

## 五、验证清单

接入完成后，验证以下项目:

- [ ] ERP 连接成功，无报错
- [ ] 数据同步完成，记录数符合预期
- [ ] 字段映射正确，数据类型匹配
- [ ] 对账结果合理（匹配率 > 95% 为正常）
- [ ] 审计日志正常写入
- [ ] 性能满足要求（单次审计 < 5 分钟）

---

## 六、生产环境建议

### 6.1 数据库

- 使用 PostgreSQL 替代 SQLite
- 配置读写分离
- 启用自动备份

### 6.2 监控

- 设置审计任务定时运行（建议每日凌晨）
- 配置异常告警（孤儿记录数突增）
- 监控数据库连接池

### 6.3 安全

- 使用密钥管理服务存储密码
- 启用审计日志加密
- 配置 RBAC 权限

---

*最后更新: 2026-02-08*
