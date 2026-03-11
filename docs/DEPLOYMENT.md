# Deployment Guide (Docker + Conda)

更新时间: 2026-03-10

本文件描述 Rosetta 的双环境策略：

1. 服务器运行: Docker + Docker Compose。
2. 本地开发: Conda。

目标是“首次部署简单、日常更新稳定、故障回滚可执行、本地开发可复现”。

## 1. 部署目标

1. 服务器只依赖 Docker + Docker Compose。
2. 使用脚本统一部署与更新，避免手工执行高风险命令。
3. 数据与配置外置，容器可替换。

## 2. 服务器目录规划

建议固定如下目录:

1. `/opt/rosetta/app`：项目仓库。
2. `/opt/rosetta/data`：业务数据（如 concepts 文件）。
3. `/opt/rosetta/backups`：每日/每次更新前备份。
4. `/opt/rosetta/logs`：部署日志和运行日志。

## 3. 环境准备

1. 安装 Docker。
2. 安装 Docker Compose 插件。
3. 创建目录并授权当前部署用户。

示例命令:

```bash
sudo mkdir -p /opt/rosetta/{app,data,backups,logs}
sudo chown -R $USER:$USER /opt/rosetta
```

## 4. 配置文件约定

1. `.env`：非敏感配置（端口、容器名、路径）。
2. `.streamlit/secrets.toml`：敏感配置（API keys），不提交仓库。
3. `.streamlit/config.toml`：主题与基础 UI 配置（TOML 优先）。
4. `docker-compose.yml`：生产基础编排。

建议 `.env` 字段:

```env
ROSETTA_CONTAINER=rosetta-app
ROSETTA_PORT=8501
ROSETTA_DATA_DIR=/opt/rosetta/data
ROSETTA_BACKUP_DIR=/opt/rosetta/backups
ROSETTA_LOG_DIR=/opt/rosetta/logs
```

## 5. 首次部署流程

1. 克隆仓库到 `/opt/rosetta/app`。
2. 准备 `.env` 与 `.streamlit/secrets.toml`。
3. 执行 `scripts/deploy/deploy.sh`。
4. 确认健康检查通过。

期望命令:

```bash
cd /opt/rosetta/app
cp .env.example .env
./scripts/deploy/deploy.sh
```

## 6. 日常更新流程

更新原则:

1. 更新前先备份。
2. 拉取代码后重建镜像。
3. 启动新容器并做健康检查。
4. 若失败执行回滚。

期望命令:

```bash
cd /opt/rosetta/app
./scripts/deploy/update.sh
```

## 7. 备份与恢复

### 7.1 备份

```bash
./scripts/data/backup.sh
```

备份内容:

1. `concepts.json` 或数据目录快照。
2. 生成时间戳文件名。

### 7.2 恢复

```bash
./scripts/data/restore.sh /opt/rosetta/backups/concepts_YYYYmmdd_HHMMSS.json
```

恢复后动作:

1. 替换数据。
2. 重启容器。
3. 运行健康检查。

## 8. 健康检查与排障

健康检查命令:

```bash
curl -f http://localhost:8501/_stcore/health
```

常用排障:

```bash
docker compose ps
docker compose logs -f
```

## 9. 与现有脚本兼容策略

当前已有:

1. `scripts/daily_restart.sh`
2. `scripts/monthly_rebuild.sh`

升级策略:

1. 保留文件名和 cron 入口。
2. 内部逐步改为调用 `deploy/update/backup/healthcheck`。
3. 避免 `git reset --hard` 这种不可逆流程作为默认路径。

建议目录形态:

1. `scripts/deploy/`：`deploy.sh`、`update.sh`、`rollback.sh`
2. `scripts/ops/`：`healthcheck.sh`、`logs.sh`、`restart.sh`
3. `scripts/data/`：`backup.sh`、`restore.sh`、`migrate.sh`
4. `scripts/cron/`：`daily_restart.sh`、`monthly_rebuild.sh`
5. `scripts/lib/`：公共函数（日志、错误处理、环境变量解析）

当前仓库状态（已落地）:

1. 已实现 `deploy/ops/data/cron/lib` 目录分层。
2. 旧入口 `scripts/daily_restart.sh` 与 `scripts/monthly_rebuild.sh` 保持兼容。

## 10. 发布与回滚规范

1. 镜像使用可追溯 tag（commit sha 或日期版本）。
2. `update.sh` 失败时回滚上一成功镜像。
3. 每次发布写入日志到 `/opt/rosetta/logs/deploy_*.log`。

## 11. 最小验收标准

1. 新服务器 3 条命令可完成部署。
2. 更新 1 条命令可完成并可回滚。
3. 数据目录在容器重建后不丢失。
4. 健康检查可稳定通过。

## 12. 本地 Conda 开发环境

### 12.1 创建环境

```bash
conda env create -f environment.yml
conda activate rosetta-dev
```

### 12.2 更新环境

当 `requirements.txt` 或 `environment.yml` 变更后，执行：

```bash
conda env update -f environment.yml --prune
conda activate rosetta-dev
```

### 12.3 本地运行

```bash
streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0
```

### 12.4 维护约束

1. Docker 依赖与 Conda 依赖必须保持同版本基线。
2. 新增 Python 包时，至少同步更新 `requirements.txt` 与 `environment.yml`。
3. CI 默认以 `requirements.txt` 为基线，Conda 作为开发体验层。
