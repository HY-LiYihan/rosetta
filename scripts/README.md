# Scripts

Rosetta 脚本当前分为统一 tool CLI、部署运维脚本和 legacy 兼容脚本。

## 统一 CLI

新入口：

```bash
python scripts/tool/rosetta_tool.py --help
```

常用命令：

```bash
python scripts/tool/rosetta_tool.py bootstrap-analyze --samples <samples.jsonl> --candidates <candidates.jsonl> --record
python scripts/tool/rosetta_tool.py corpus-prepare --config <spec.json> --dataset <seed.jsonl> --record
python scripts/tool/rosetta_tool.py corpus-memory --config <spec.json> --chunks <seed_chunks.jsonl> --record
python scripts/tool/rosetta_tool.py corpus-plan --config <spec.json> --memory <memory_records.jsonl> --record
python scripts/tool/rosetta_tool.py corpus-generate --config <spec.json> --memory <memory_records.jsonl> --plan <tasks.jsonl> --record
python scripts/tool/rosetta_tool.py runs
```

`--record` 会把 workflow run 写入本地 SQLite runtime store。

## 部署与运维

```bash
./scripts/deploy/deploy.sh
./scripts/deploy/update.sh
./scripts/ops/healthcheck.sh
./scripts/ops/logs.sh
./scripts/ops/restart.sh
./scripts/data/backup.sh
./scripts/data/restore.sh <backup-file>
```

## Legacy 入口

以下旧入口仍可用，但会提示迁移到统一 CLI：

1. `scripts/research/run_bootstrap.py`
2. `scripts/corpusgen/prepare_seeds.py`
3. `scripts/corpusgen/build_memory.py`
4. `scripts/corpusgen/plan_corpus.py`
5. `scripts/corpusgen/generate_corpus.py`

## Runtime 目录

默认运行目录由 `ROSETTA_RUNTIME_DIR` 控制：

```text
/opt/rosetta/runtime
  data/
  backups/
  logs/
  artifacts/
  exports/
  indexes/
  rosetta.sqlite3
```
