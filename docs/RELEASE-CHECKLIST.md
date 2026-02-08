# Release 检查清单 (RELEASE-CHECKLIST)

## 发布流程

### 1. 创建 Tag

```bash
git checkout main
git pull origin main
git tag -a v2.0.2 -m "Release v2.0.2"
git push origin v2.0.2
```

### 2. 验证 CI

```bash
gh run watch <tag-ci-run-id> --compact --exit-status
gh run view <tag-ci-run-id>
```

### 3. 创建 Release

```bash
gh release create v2.0.2 --title "Release v2.0.2" --notes "Release notes"
```

### 4. 分支保护

设置 main 分支保护:
- Required status checks: lint, test, e2e, verify
- Require pull request reviews

### 5. Required Checks

- [ ] lint
- [ ] test
- [ ] e2e
- [ ] verify
- [ ] gitleaks

### 6. Dependabot

检查 `.github/dependabot.yml` 配置。

### 7. Security 扫描

```bash
gh run list --workflow=Security --limit 5
```

## 验收命令

```bash
git ls-remote --tags origin | grep v2.0.2
gh release view v2.0.2
gh run list --limit 5 | grep v2.0.2
```

## 回滚

```bash
git push origin --delete v2.0.2
git tag -d v2.0.2
gh release delete v2.0.2 --yes
```
