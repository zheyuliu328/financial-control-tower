# CI 作战手册 (CI-RUNBOOK)

## 证据模板

```
Repo: <repo-name>
Branch: <branch-name>
SHA: <commit-sha>
Run ID: <run-id>
Job: <job-name>
结论: <PASS/FAIL>
失败 Step 原文:
<失败日志片段>
```

## 追踪命令

```bash
# 追踪 CI 运行（实时）
gh run watch <run_id> --compact --exit-status

# 查看失败日志
gh run view <run_id> --log-failed

# 查看完整日志
gh run view <run_id> --log
```

## 红灯分流 - 最小修复口径

### lint 失败
```bash
ruff check . --fix
ruff format .
git add -A && git commit -m "fix: lint"
git push origin <branch>
```

### test 失败
```bash
pytest tests/ -v -m "not integration"
git add -A && git commit -m "fix: unit tests"
git push origin <branch>
```

### e2e 失败
```bash
pytest tests/test_e2e.py -v
git add -A && git commit -m "fix: e2e tests"
git push origin <branch>
```

### verify 失败
```bash
make verify
```

### gitleaks 失败
```bash
gitleaks detect --source . --verbose
git add -A && git commit -m "fix: remove secrets"
git push origin <branch>
```

## 常用 gh 命令

| 命令 | 用途 |
|:-----|:-----|
| `gh run list` | 列出最近 runs |
| `gh run watch <id>` | 实时追踪 |
| `gh run view <id>` | 查看详情 |
| `gh run view <id> --log-failed` | 查看失败日志 |
| `gh run rerun <id>` | 重新运行 |

## Timeout 配置

- lint: 5 minutes
- test: 15 minutes
- e2e: 15 minutes
- verify: 10 minutes
