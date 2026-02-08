# CI Runbook - 红灯分流与定位指南

## 概述

本文档提供CI流水线故障的快速分流和定位流程。

## CI流水线结构

```
lint → unit → e2e → verify
  ↓      ↓     ↓       ↓
  └──────┴─────┴───────┘ → ci-status (branch protection)
```

### 阶段说明

| 阶段 | 超时 | 目的 | 失败影响 |
|------|------|------|----------|
| lint | 10min | 代码格式和质量检查 | 阻止后续阶段 |
| unit | 15min | 单元测试（跳过integration） | 阻止后续阶段 |
| e2e | 20min | 端到端测试 | 阻止合并 |
| verify | 15min | 安全和依赖扫描 | 阻止合并 |
| ci-status | 5min | 最终状态汇总 | branch protection |

## 红灯分流流程

### 第一步：确定失败阶段

```bash
# 查看最新CI状态
gh run list --limit 5

# 查看特定run的详情
gh run view <run-id>
```

### 第二步：按阶段定位

#### Lint 失败

**常见原因：**
- Ruff lint错误
- Black格式不符
- Import排序错误

**定位命令：**
```bash
# 本地复现
ruff check src/
black --check src/

# 自动修复
ruff check --fix src/
black src/
```

#### Unit 失败

**常见原因：**
- 测试逻辑错误
- 依赖缺失
- 环境配置问题

**定位命令：**
```bash
# 本地复现
pytest -m "not integration and not e2e" -v

# 查看失败详情
pytest -m "not integration and not e2e" -v --tb=long

# 特定测试
pytest tests/test_specific.py::test_function -v
```

#### E2E 失败

**常见原因：**
- 外部服务不可用
- 测试数据问题
- 环境配置错误

**定位命令：**
```bash
# 本地复现
pytest -m e2e -v

# 带详细日志
pytest -m e2e -v --tb=long --log-cli-level=DEBUG

# 仅运行特定e2e测试
pytest -m e2e -k "test_name" -v
```

#### Verify 失败

**常见原因：**
- Gitleaks检测到secret
- Bandit安全警告
- Safety依赖漏洞

**定位命令：**
```bash
# Gitleaks本地扫描
gitleaks detect --source . --config .gitleaks.toml

# Bandit安全扫描
bandit -r src/ -f json

# Safety依赖检查
safety check
```

## GH CLI 常用命令

### 查看运行状态

```bash
# 列出最近运行
gh run list --limit 10

# 查看特定运行
gh run view <run-id>

# 查看失败日志
gh run view <run-id> --log-failed

# 实时监视运行
gh run watch <run-id>

# 重新运行失败作业
gh run rerun <run-id>

# 重新运行所有作业
gh run rerun <run-id> --failed
```

### 查看作业日志

```bash
# 查看特定作业的日志
gh run view <run-id> --job <job-id>

# 下载日志
gh run download <run-id>
```

### 分支保护检查

```bash
# 查看分支保护规则
gh api repos/:owner/:repo/branches/main/protection

# 查看required status checks
gh api repos/:owner/:repo/branches/main/protection/required_status_checks
```

## 取证流程

### 1. 获取Run ID

```bash
RUN_ID=$(gh run list --limit 1 --json databaseId --jq '.[0].databaseId')
echo "Latest Run ID: $RUN_ID"
```

### 2. 下载失败日志

```bash
gh run download $RUN_ID --dir ./ci-logs/$RUN_ID
```

### 3. 提取失败信息

```bash
# 查看失败的作业
gh run view $RUN_ID --json jobs --jq '.jobs[] | select(.conclusion == "failure") | {name: .name, conclusion: .conclusion, startedAt: .startedAt, completedAt: .completedAt}'
```

### 4. 保存证据

```bash
mkdir -p ci-evidence/$RUN_ID
gh run view $RUN_ID --json > ci-evidence/$RUN_ID/run_info.json
gh run view $RUN_ID --log-failed > ci-evidence/$RUN_ID/failed_logs.txt
```

## 常见修复口径

### Lint 失败

```bash
# 一键修复
ruff check --fix src/ && black src/
```

### Unit 测试失败

1. 检查测试是否本地通过
2. 检查依赖版本是否一致
3. 检查环境变量配置
4. 检查测试数据是否完整

### E2E 测试失败

1. 检查外部服务状态
2. 检查测试配置
3. 检查网络连接
4. 考虑标记为flaky并重新运行

### Verify 失败

**Gitleaks:**
- 确认是否为误报
- 更新.gitleaks.toml配置
- 清理历史记录（如需要）

**Bandit:**
- 评估安全风险
- 修复或标记为nosec

**Safety:**
- 更新依赖版本
- 评估漏洞影响

## 联系与升级

| 问题类型 | 联系人 | 升级条件 |
|----------|--------|----------|
| 代码问题 | 开发团队 | 无法本地复现 |
| 环境问题 | DevOps | 多PR同时失败 |
| 安全扫描 | 安全团队 | 确认漏洞风险 |
| 外部依赖 | 对应团队 | 服务不可用>30min |

## 附录

### 超时配置

所有作业都有timeout-minutes设置：
- lint: 10分钟
- unit: 15分钟
- e2e: 20分钟
- verify: 15分钟
- ci-status: 5分钟

### 禁止的"假绿"模式

以下模式**禁止**使用：
- `|| true` - 掩盖失败
- `continue-on-error: true` - 除非明确需要
- 不检查exit code的脚本

### 验证CI配置

```bash
# 验证workflow语法
gh workflow view ci.yml

# 手动触发CI
gh workflow run ci.yml --ref <branch>
```
