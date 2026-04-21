# Skill Integration (Developer)

更新时间: 2026-04-21

## 1. 目标

1. 将 Rosetta 的研究流水线包装为可被 Codex 直接调用的本地 skill。
2. 保持 skill 层足够薄，只负责触发、导航和命令入口，不复制研究引擎逻辑。
3. 让实验工作流同时支持“脚本直跑”和“Codex 代理驱动”两种入口。

## 2. 目录约定

1. [skills/rosetta-research/SKILL.md](../../skills/rosetta-research/SKILL.md)
- Skill 主说明。
- 定义何时触发、如何操作研究流水线、执行后优先查看哪些产物。

2. [skills/rosetta-research/agents/openai.yaml](../../skills/rosetta-research/agents/openai.yaml)
- Codex UI 元数据。
- 提供 skill 名称、短说明和默认调用提示。

3. [scripts/skill/install_rosetta_research_skill.sh](../../scripts/skill/install_rosetta_research_skill.sh)
- 将仓库内 skill 安装到 `${CODEX_HOME:-$HOME/.codex}/skills`。
- 默认使用软链接，确保仓库更新后 skill 内容同步生效。

## 3. 分层边界

1. `app/research/*`
- 研究引擎。
- 负责配置解析、prompt 组装、检索、验证、批处理执行与结果落盘。

2. `scripts/research/run_pipeline.py`
- 研究引擎 CLI 入口。
- skill 和人工命令行调用都应优先复用这一入口。

3. `skills/rosetta-research/*`
- Codex 指南层。
- 只描述工作流、命令和判断顺序，不重复实现研究逻辑。

## 4. 推荐工作流

1. 安装 skill

```bash
./scripts/skill/install_rosetta_research_skill.sh
```

2. 在 Codex 中显式调用 `$rosetta-research`
- 先读目标 `configs/research/*.json`
- 如需调 prompt 或 few-shot，先跑 `preview`
- 如使用 `embedding` 检索，先跑 `build-index`
- gold 数据集用 `run --mode audit`
- 未标注数据集用 `run --mode batch`

3. 运行后优先查看：
- `manifest.json`
- `review_queue.jsonl`
- `conflicts.jsonl`（仅 `audit`）

## 5. 维护原则

1. 改研究逻辑时，优先修改 `app/research/*` 和对应测试，而不是改 skill 文字绕过问题。
2. 改 skill 流程时，确保 [SKILL.md](../../skills/rosetta-research/SKILL.md) 与本文件同步。
3. 若变更影响用户如何安装或调用 skill，必须同步更新 [README.md](../../README.md)。
4. 提交前至少执行：

```bash
python -m compileall app streamlit_app.py
python -m unittest discover -s tests -p 'test_*.py'
for f in $(find scripts -type f -name '*.sh'); do bash -n "$f"; done
```
