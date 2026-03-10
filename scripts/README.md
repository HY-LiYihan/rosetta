# Scripts

Rosetta 脚本目录已按职责分层，保持旧入口兼容。

## 目录结构

- `scripts/deploy/`: 部署与更新
- `scripts/ops/`: 运行维护
- `scripts/data/`: 数据备份与恢复
- `scripts/cron/`: 定时任务入口
- `scripts/lib/`: 公共函数

## 常用命令

```bash
./scripts/deploy/deploy.sh
./scripts/deploy/update.sh
./scripts/ops/healthcheck.sh
./scripts/data/backup.sh
./scripts/data/restore.sh <backup-file>
```

## 兼容入口

以下旧路径仍可使用：

- `./scripts/daily_restart.sh`
- `./scripts/monthly_rebuild.sh`

它们会转发到 `scripts/cron/*`。
