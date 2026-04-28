# Scripts Reference (Developer)

更新时间: 2026-04-29

## 1. 设计目标

1. 新功能统一走 [rosetta_tool.py](../../scripts/tool/rosetta_tool.py)。
2. 部署、运维、备份脚本职责单一。
3. legacy research/corpusgen 脚本保留兼容，但不再作为新入口。

## 2. 统一 CLI

```bash
python scripts/tool/rosetta_tool.py --help
```

命令：

| 命令 | 说明 |
| --- | --- |
| `bootstrap-analyze` | 分析 bootstrap samples / candidates，输出 review queue 和 report |
| `corpus-prepare` | 切分 seed corpus |
| `corpus-memory` | 构建 memory records 与 CPU index |
| `corpus-plan` | 规划语料生成任务 |
| `corpus-generate` | 执行语料生成 |
| `runs` | 查看本地 SQLite runtime store 中的 workflow runs |

`--record` 会将运行写入本地 `RuntimeStore`。

## 3. 部署脚本

| 脚本 | 职责 |
| --- | --- |
| [deploy.sh](../../scripts/deploy/deploy.sh) | `compose up -d --build` 后健康检查 |
| [update.sh](../../scripts/deploy/update.sh) | 备份、拉取代码、重建、健康检查 |
| [rollback.sh](../../scripts/deploy/rollback.sh) | 当前为重启式占位回滚 |

## 4. 运维与数据脚本

| 脚本 | 职责 |
| --- | --- |
| [healthcheck.sh](../../scripts/ops/healthcheck.sh) | 检查 Streamlit 健康端点 |
| [logs.sh](../../scripts/ops/logs.sh) | 查看 Compose 日志 |
| [restart.sh](../../scripts/ops/restart.sh) | 重启服务 |
| [backup.sh](../../scripts/data/backup.sh) | 备份数据 |
| [restore.sh](../../scripts/data/restore.sh) | 恢复数据 |

## 5. 环境变量

变量由 [common.sh](../../scripts/lib/common.sh) 读取 `.env` 后设置默认值：

| 变量 | 默认值 |
| --- | --- |
| `ROSETTA_APP_DIR` | 当前仓库根目录 |
| `ROSETTA_SERVICE` | `rosetta` |
| `ROSETTA_RUNTIME_DIR` | `/opt/rosetta/runtime` |
| `ROSETTA_DATA_DIR` | `${ROSETTA_RUNTIME_DIR}/data` |
| `ROSETTA_BACKUP_DIR` | `${ROSETTA_RUNTIME_DIR}/backups` |
| `ROSETTA_LOG_DIR` | `${ROSETTA_RUNTIME_DIR}/logs` |

## 6. Legacy 入口

以下脚本仍可用，但会打印迁移提示：

1. [run_bootstrap.py](../../scripts/research/run_bootstrap.py)
2. [prepare_seeds.py](../../scripts/corpusgen/prepare_seeds.py)
3. [build_memory.py](../../scripts/corpusgen/build_memory.py)
4. [plan_corpus.py](../../scripts/corpusgen/plan_corpus.py)
5. [generate_corpus.py](../../scripts/corpusgen/generate_corpus.py)

## 7. 检查命令

```bash
python -m compileall app streamlit_app.py scripts/tool/rosetta_tool.py
python -m unittest discover -s tests -p 'test_*.py'
for f in $(find scripts -type f -name '*.sh'); do bash -n "$f"; done
```
