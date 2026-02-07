# Rollback Guide

## Version Rollback

### Git Tag Rollback

```bash
# List available tags
git tag --list

# Checkout specific version
git checkout v1.9.0

# Verify make verify passes
make verify
```

## Rollback演练记录

### 演练1: Git Tag 回滚

```bash
# 当前版本
git log -1 --oneline
# be2cac9 Add run-real path for ERP reconciliation

# 回滚到上一版本
git checkout 3cb6c76

# 验证
make verify
# [OK] All checks passed!

# 回到最新版本
git checkout main
```
