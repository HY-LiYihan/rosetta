# Deployment (Developer)

## 1. 目录约定

1. 服务器根目录：`/opt/streamlit`
2. 项目目录：`/opt/streamlit/rosetta`
3. 运行目录：`/opt/rosetta/runtime`（统一包含 `data/backups/logs`）

## 2. 首次部署

```bash
sudo mkdir -p /opt/streamlit
cd /opt/streamlit

if [ ! -d rosetta ]; then
  git clone https://github.com/HY-LiYihan/rosetta.git
fi
cd /opt/streamlit/rosetta

cp -n .env.example .env
./scripts/deploy/deploy.sh
./scripts/ops/healthcheck.sh
```

## 3. 已存在项目时更新（推荐）

```bash
cd /opt/streamlit

git -C rosetta fetch --all --prune
git -C rosetta pull --ff-only origin main

cd /opt/streamlit/rosetta
./scripts/deploy/update.sh
```

## 4. 运维脚本入口

1. 部署：`./scripts/deploy/deploy.sh`
2. 更新：`./scripts/deploy/update.sh`
3. 健康检查：`./scripts/ops/healthcheck.sh`
4. 日志：`./scripts/ops/logs.sh`
5. 备份：`./scripts/data/backup.sh`
6. 恢复：`./scripts/data/restore.sh <backup-file>`
7. 详细职责说明见 [SCRIPTS.md](/Users/liyh/rosetta/docs/developer/SCRIPTS.md)

## 7. 运行目录说明

1. 默认使用 `ROSETTA_RUNTIME_DIR=/opt/rosetta/runtime`。
2. 脚本会自动创建：
- `/opt/rosetta/runtime/data`
- `/opt/rosetta/runtime/backups`
- `/opt/rosetta/runtime/logs`
3. 如需拆分目录，可在 `.env` 中单独覆盖 `ROSETTA_DATA_DIR`、`ROSETTA_BACKUP_DIR`、`ROSETTA_LOG_DIR`。

## 5. 兼容 cron 入口

1. `./scripts/daily_restart.sh`
2. `./scripts/monthly_rebuild.sh`

## 6. 故障排查

```bash
docker compose ps
./scripts/ops/logs.sh
curl -f http://localhost:8501/_stcore/health
```
