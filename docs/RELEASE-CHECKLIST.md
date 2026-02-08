# Release Checklist - 版本发布清单

## 发布前检查

### 1. 代码准备

- [ ] 所有功能已合并到main/master分支
- [ ] 版本号已更新（pyproject.toml）
- [ ] CHANGELOG.md已更新
- [ ] 所有文档已更新

### 2. CI验证

- [ ] main/master分支CI全绿（lint/unit/e2e/verify）
- [ ] 获取最新CI run ID: `gh run list --branch main --limit 1`
- [ ] 确认ci-status作业通过

### 3. 分支保护检查

```bash
# 检查main分支保护
gh api repos/:owner/:repo/branches/main/protection

# 确认required status checks包含：
# - lint
# - unit
# - e2e
# - verify
# - ci-status
```

## 发布流程

### 步骤1: 创建Release Branch（可选）

```bash
# 从main创建release分支
git checkout -b release/vX.Y.Z

# 推送分支
git push origin release/vX.Y.Z
```

### 步骤2: 创建Tag

```bash
# 确保在main分支
git checkout main
git pull origin main

# 创建annotated tag
git tag -a vX.Y.Z -m "Release version X.Y.Z"

# 推送tag
git push origin vX.Y.Z
```

### 步骤3: 验证Tag触发CI

```bash
# 查看tag触发的CI
gh run list --tag vX.Y.Z

# 等待所有检查通过
gh run watch <run-id>
```

### 步骤4: 创建GitHub Release

```bash
# 使用gh CLI创建release
gh release create vX.Y.Z \
  --title "Release X.Y.Z" \
  --notes-file CHANGELOG.md \
  --verify-tag
```

## Required Status Checks 顺序

分支保护必须包含以下checks（按执行顺序）：

```
1. lint          → 代码格式检查
2. unit          → 单元测试
3. e2e           → 端到端测试
4. verify        → 安全扫描
5. ci-status     → 最终状态汇总
```

### 配置分支保护

```bash
# 更新分支保护规则（需要admin权限）
gh api repos/:owner/:repo/branches/main/protection \
  --method PUT \
  --input - <<EOF
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "Lint & Format Check",
      "Unit Tests",
      "E2E Tests",
      "Verify & Security Scan",
      "CI Status Check"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1
  },
  "restrictions": null
}
EOF
```

## 发布后验证

### 1. 验证Release

- [ ] GitHub Release页面可访问
- [ ] Tag指向正确commit
- [ ] Release notes完整

### 2. 验证Artifacts

- [ ] 所有artifacts已上传
- [ ] Docker镜像已推送（如适用）
- [ ] 文档已更新

### 3. 验证部署（如适用）

- [ ] 预发布环境验证通过
- [ ] 生产环境部署成功
- [ ] 健康检查通过

## 回滚准备

### 快速回滚命令

```bash
# 删除有问题的tag
git push --delete origin vX.Y.Z
git tag -d vX.Y.Z

# 基于上一个稳定版本创建修复tag
git tag -a vX.Y.Z-1 -m "Hotfix release X.Y.Z-1"
git push origin vX.Y.Z-1
```

### 回滚检查清单

- [ ] 回滚计划已准备
- [ ] 团队已通知
- [ ] 监控已配置
- [ ] 客户通知已准备（如需要）

## 版本号规范

遵循Semantic Versioning (SemVer):

- **MAJOR** (X): 不兼容的API更改
- **MINOR** (Y): 向后兼容的功能添加
- **PATCH** (Z): 向后兼容的问题修复

示例:
- `v1.0.0` - 初始发布
- `v1.1.0` - 新功能
- `v1.1.1` - Bug修复
- `v2.0.0` - 重大更新

## 紧急发布流程

对于紧急修复：

1. 从main创建hotfix分支
2. 应用修复
3. 快速PR review（可简化流程）
4. 合并后按正常流程发布
5. 更新CHANGELOG标记为hotfix

## 联系信息

| 角色 | 联系人 | 职责 |
|------|--------|------|
| Release Manager | TBD | 协调发布流程 |
| Tech Lead | TBD | 技术决策 |
| QA Lead | TBD | 质量验证 |
| DevOps | TBD | 部署支持 |
