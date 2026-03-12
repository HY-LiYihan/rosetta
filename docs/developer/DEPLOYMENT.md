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
7. 详细职责说明见 [SCRIPTS.md](./SCRIPTS.md)

## 7. 运行目录说明

1. 默认使用 `ROSETTA_RUNTIME_DIR=/opt/rosetta/runtime`。
2. 脚本会自动创建：
- `/opt/rosetta/runtime/data`
- `/opt/rosetta/runtime/backups`
- `/opt/rosetta/runtime/logs`
3. 如需拆分目录，可在 `.env` 中单独覆盖 `ROSETTA_DATA_DIR`、`ROSETTA_BACKUP_DIR`、`ROSETTA_LOG_DIR`。

## 8. Debug 模式（临时排障）

1. 开启方式（二选一）：
- `streamlit run streamlit_app.py -- --debug`
- `ROSETTA_DEBUG_MODE=1 streamlit run streamlit_app.py`
2. Debug 开启后，首次访问会展示中英双语提示（5 秒后可关闭）。
3. 调试日志写入 `.runtime/logs/debug/*.jsonl`，上传副本写入 `.runtime/data/debug_uploads/`。

## 5. 兼容 cron 入口

1. `./scripts/daily_restart.sh`
2. `./scripts/monthly_rebuild.sh`

## 6. 故障排查

```bash
docker compose ps
./scripts/ops/logs.sh
curl -f http://localhost:8501/_stcore/health
```
