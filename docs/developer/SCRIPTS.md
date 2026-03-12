# Scripts Reference (Developer)

更新时间: 2026-03-11

## 1. 设计目标

1. 所有运维脚本职责单一，可组合调用。
2. 所有脚本共享同一套环境变量加载逻辑。
3. 保留旧入口，避免历史 cron/运维命令失效。

## 2. 加载链路

1. `.env.example` 仅作为模板，不会被脚本直接读取。
2. 运行时由 `.env` 提供配置。
3. 绝大多数脚本通过 [common.sh](../../scripts/lib/common.sh) 加载 `.env`。

## 3. 环境变量来源

1. 默认值定义在 [common.sh](../../scripts/lib/common.sh)。
2. 同名变量可在项目根目录 `.env` 中覆盖。

关键变量：
1. `ROSETTA_APP_DIR`: 项目目录，默认当前仓库根目录。
2. `ROSETTA_SERVICE`: Compose 服务名，默认 `rosetta`。
3. `ROSETTA_CONTAINER`: 容器名，默认 `rosetta-app`。
4. `ROSETTA_PORT`: 服务端口，默认 `8501`。
5. `ROSETTA_RUNTIME_DIR`: 运行时根目录，默认 `/opt/rosetta/runtime`。
6. `ROSETTA_DATA_DIR`: 数据目录，默认 `${ROSETTA_RUNTIME_DIR}/data`。
7. `ROSETTA_BACKUP_DIR`: 备份目录，默认 `${ROSETTA_RUNTIME_DIR}/backups`。
8. `ROSETTA_LOG_DIR`: 日志目录，默认 `${ROSETTA_RUNTIME_DIR}/logs`。
9. `ROSETTA_HEALTH_URL`: 健康检查 URL，默认 `http://localhost:${ROSETTA_PORT}/_stcore/health`。

## 4. 脚本职责矩阵

1. 部署层
- [deploy.sh](../../scripts/deploy/deploy.sh): 首次/常规部署，执行 `compose up -d --build` 后健康检查。
- [update.sh](../../scripts/deploy/update.sh): 备份 -> `git pull --ff-only` -> 重建重启 -> 健康检查。
- [rollback.sh](../../scripts/deploy/rollback.sh): 当前是“回滚占位实现”，仅执行服务重启与健康检查。

2. 运维层
- [healthcheck.sh](../../scripts/ops/healthcheck.sh): 通过 `curl` 检查健康端点。
- [logs.sh](../../scripts/ops/logs.sh): 跟踪 Compose 服务日志。
- [restart.sh](../../scripts/ops/restart.sh): 重启服务后执行健康检查。

3. 数据层
- [backup.sh](../../scripts/data/backup.sh): 备份 `concepts.json` 到备份目录。
- [restore.sh](../../scripts/data/restore.sh): 从备份文件恢复后自动重启服务。

4. 定时任务层
- [cron/daily_restart.sh](../../scripts/cron/daily_restart.sh): 调用 `deploy/update.sh`。
- [cron/monthly_rebuild.sh](../../scripts/cron/monthly_rebuild.sh): 调用 `deploy/deploy.sh`。

5. 兼容入口
- [daily_restart.sh](../../scripts/daily_restart.sh): 转发到 `scripts/cron/daily_restart.sh`。
- [monthly_rebuild.sh](../../scripts/monthly_rebuild.sh): 转发到 `scripts/cron/monthly_rebuild.sh`。

## 5. 调用关系

1. [deploy.sh](../../scripts/deploy/deploy.sh)
- `common.sh` -> `compose up -d --build` -> `ops/healthcheck.sh`

2. [update.sh](../../scripts/deploy/update.sh)
- `common.sh` -> `data/backup.sh` -> `git pull --ff-only` -> `compose up -d --build` -> `ops/healthcheck.sh`

3. [restore.sh](../../scripts/data/restore.sh)
- `common.sh` -> 文件恢复 -> `ops/restart.sh` -> `ops/healthcheck.sh`

## 6. 建议与限制

1. 生产环境请先配置镜像不可变 tag，再完善 [rollback.sh](../../scripts/deploy/rollback.sh) 的真正回滚能力。
2. `update.sh` 会执行 `git pull`，仅适用于该目录由 Git 管理且工作区干净的场景。
3. 如需自定义路径/端口/服务名，优先改 `.env`，避免直接改脚本。
