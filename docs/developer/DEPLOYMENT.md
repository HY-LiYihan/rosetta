# Deployment (Developer)

更新时间: 2026-05-02

## 1. 目录约定

1. 服务器根目录：`/opt/streamlit`
2. 项目目录：`/opt/streamlit/rosetta`
3. 运行目录：`/opt/rosetta/runtime`（统一包含 `data/backups/logs/artifacts/exports/indexes/rosetta.sqlite3`）

## 2. 首次部署

```bash
sudo mkdir -p /opt/streamlit
cd /opt/streamlit

if [ ! -d rosetta ]; then
  git clone https://github.com/HY-LiYihan/rosetta.git
fi
cd /opt/streamlit/rosetta

sudo mkdir -p /opt/rosetta/runtime
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

## 5. Docker 约束

1. Streamlit 仍是唯一正式 UI，容器暴露 `8501`。
2. `Dockerfile` 在构建期安装 `requirements.txt`，不再在 ENTRYPOINT 每次 `pip install`。
3. `docker-compose.yml` 将仓库挂载到 `/app:ro`，将 runtime 挂载到 `/opt/rosetta/runtime`。
4. `.dockerignore` 排除 `.streamlit/secrets.toml`、`.runtime`、PDF 和本地缓存。

部署约束同样服务 Rosetta 的研究主线：runtime 目录必须能持久保存 SQLite、artifacts、exports 和 logs，否则概念版本、候选分歧、人工审核和实验报告无法回放。

## 6. 运行目录说明

1. 默认使用 `ROSETTA_RUNTIME_DIR=/opt/rosetta/runtime`。
2. 脚本会自动创建：
- `/opt/rosetta/runtime/data`
- `/opt/rosetta/runtime/backups`
- `/opt/rosetta/runtime/logs`
- `/opt/rosetta/runtime/artifacts`
- `/opt/rosetta/runtime/exports`
- `/opt/rosetta/runtime/indexes`
3. SQLite runtime store 默认写入 `/opt/rosetta/runtime/rosetta.sqlite3`。
4. 如需拆分目录，可在 `.env` 中单独覆盖 `ROSETTA_DATA_DIR`、`ROSETTA_BACKUP_DIR`、`ROSETTA_LOG_DIR`。

建议保留以下目录用于实验复现：

1. `/opt/rosetta/runtime/artifacts`: 概念版本、模型原始响应、报告中间产物。
2. `/opt/rosetta/runtime/exports`: 导出的 Prodigy-compatible JSONL、report、manifest。
3. `/opt/rosetta/runtime/indexes`: 本地 CPU 检索索引。
4. `/opt/rosetta/runtime/logs`: 调试日志和长任务事件。

## 7. Debug 模式（临时排障）

1. 开启方式（二选一）：
- `streamlit run streamlit_app.py -- --debug`
- `ROSETTA_DEBUG_MODE=1 streamlit run streamlit_app.py`
2. Debug 开启后，首次访问会展示中英双语提示（5 秒后可关闭）。
3. 调试日志写入 `.runtime/logs/debug/*.jsonl`，上传副本写入 `.runtime/data/debug_uploads/`。

## 8. 兼容 cron 入口

1. `./scripts/daily_restart.sh`
2. `./scripts/monthly_rebuild.sh`

## 9. 故障排查

```bash
docker compose ps
./scripts/ops/logs.sh
curl -f http://localhost:8501/_stcore/health
```
