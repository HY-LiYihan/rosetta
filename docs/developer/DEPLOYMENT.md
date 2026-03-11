# Developer Deployment Notes

本文件面向维护者，聚焦脚本入口和日常运维路径。

## 脚本入口

1. 部署：`./scripts/deploy/deploy.sh`
2. 更新：`./scripts/deploy/update.sh`
3. 回滚占位：`./scripts/deploy/rollback.sh`
4. 健康检查：`./scripts/ops/healthcheck.sh`
5. 备份：`./scripts/data/backup.sh`
6. 恢复：`./scripts/data/restore.sh <backup-file>`

## 兼容入口

1. `./scripts/daily_restart.sh`
2. `./scripts/monthly_rebuild.sh`

## 维护建议

1. 生产只跑 Docker。
2. 本地开发使用 Conda。
3. 每次更新前先备份数据。
