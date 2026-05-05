# Corpus Pipeline (Developer)

更新时间: 2026-05-02

> 本文档记录 Rosetta 的高级语料生成能力。它现在是 annotation tool 的数据工厂 workflow，不再和标注主线平行作为顶层产品边界。

## 1. 目标

1. 提供一条用于构造 seed corpus、示例语料或压力测试数据的数据工厂路径。
2. 面向“指定领域 / 题材 / 语言”的合成语料构建，而不是标注审查。
3. 默认基于 `GLM-5 + Embedding-3 + numpy CPU index` 运行，方便本地科研环境直接落地。
4. 为主标注流程提供可控文本输入，但不替代概念自举、批量标注和审核与修正。

## 2. 分离边界

早期 `corpusgen` 与 `research` 是两条平行流水线。当前架构中，它们都应被视为 legacy implementation 或 advanced workflow：

1. `app/corpusgen/*` 不直接依赖 `app/research/*`。
2. 两者只共享底层 `app/infrastructure/llm/*` 的 provider / 凭据能力。
3. 新用户主流程仍是“定义与规范 -> 批量标注 -> 审核与修正 -> 结果与导出”。
4. 如果生成语料需要进入标注实验，必须先转换为 `AnnotationTask` 或 Prodigy-compatible JSONL。

## 3. 当前实现范围（Initial MVP）

1. `configs/corpusgen/domain/*.json`
- 语料生成 spec。
- 定义领域、语言、体裁权重、压缩预算、质量规则与模型配置。

2. `configs/corpusgen/domain/*.jsonl`
- seed 文档示例。
- 每行一个源文档，支持 `id/title/text/tags/metadata`。

3. `app/corpusgen/`
- `specs.py`: spec 解析与校验。
- `seeds.py`: seed 文档加载与 chunk 切分。
- `planner.py`: 按 genre weight / focus pool 生成任务计划。
- `memory/layers.py`: 构建 summary / canonical points / terminology。
- `memory/recall.py`: 构建与查询基于 `numpy` 的 CPU 向量索引。
- `memory/compression.py`: 构建 `task_brief / evidence_pack / term_pack / style_pack / failure_pack`。
- `generators.py`: 组装 prompt，解析模型 JSON 输出。
- `judges.py`: 长度、术语覆盖、来源 lineage、去重等规则检查。
- `runner.py`: `prepare -> memory -> plan -> generate` 执行编排。

4. `scripts/corpusgen/`
- `prepare_seeds.py`
- `build_memory.py`
- `plan_corpus.py`
- `generate_corpus.py`

5. `app/ui/pages/Corpus_Studio.py`
- Streamlit 分步式页面入口。
- 面向“一句话 brief -> 标题确认 -> 样稿确认 -> 批量生成 -> judge”的交互式工作流。
- 页面逻辑通过 `app/services/corpus_studio_*` 调用模型，不直接依赖 `app/research/*`。

## 4. 上下文压缩设计

这条流水线的压缩思路参考了 Claude 系列的 prompt caching / context editing 以及 OpenClaw 一类 agent 工程中的上下文分层与压缩做法，但当前实现保持为本地可控的简化版本：

1. L0 Seed Chunks
- 原始 seed 文档按字符窗口切成 chunk。

2. L1 Memory Records
- 每个 chunk 提炼为：
  - `summary`
  - `canonical_points`
  - `terminology`
  - `source_excerpt`

3. L2 Retrieval Hits
- 使用 `Embedding-3` 生成向量。
- 用 `numpy` 归一化矩阵做 cosine top-k 检索。
- 全程 CPU 可运行。

4. L3 Context Pack
- `task_brief`: 当前任务压缩描述
- `evidence_pack`: top-k 证据摘要
- `term_pack`: 术语包
- `style_pack`: 风格与写作要求
- `failure_pack`: 反模式与禁用项

这意味着模型每次看到的是压缩后的“任务包”，而不是整批原始种子文档。

## 5. 运行产物

默认输出目录：`.runtime/corpusgen/<spec-name>/<stage>_<timestamp>/`

各阶段核心产物：

1. `prepare`
- `seed_chunks.jsonl`
- `manifest.json`

2. `memory`
- `memory_records.jsonl`
- `manifest.json`
- 向量索引缓存写入 `.runtime/corpusgen/indexes/`

3. `plan`
- `tasks.jsonl`
- `manifest.json`

4. `generate`
- `accepted.jsonl`
- `review_queue.jsonl`
- `task_runs.jsonl`
- `manifest.json`

## 6. 推荐工作流

脚本式语料生成仍可用于构造实验输入。

1. 准备 spec 与 seed 文档

```bash
python scripts/corpusgen/prepare_seeds.py \
  --config configs/corpusgen/domain/linguistics_zh_qa.json \
  --dataset configs/corpusgen/domain/linguistics_zh_seed.example.jsonl
```

2. 构建 memory 与 CPU index

```bash
python scripts/corpusgen/build_memory.py \
  --config configs/corpusgen/domain/linguistics_zh_qa.json \
  --chunks .runtime/corpusgen/linguistics-zh-qa/prepare_*/seed_chunks.jsonl
```

3. 生成任务计划

```bash
python scripts/corpusgen/plan_corpus.py \
  --config configs/corpusgen/domain/linguistics_zh_qa.json \
  --memory .runtime/corpusgen/linguistics-zh-qa/memory_*/memory_records.jsonl
```

4. 执行生成

```bash
python scripts/corpusgen/generate_corpus.py \
  --config configs/corpusgen/domain/linguistics_zh_qa.json \
  --memory .runtime/corpusgen/linguistics-zh-qa/memory_*/memory_records.jsonl \
  --plan .runtime/corpusgen/linguistics-zh-qa/plan_*/tasks.jsonl \
  --limit-tasks 1
```

## 7. 当前约束

1. 当前 judge 主要是规则型检查，不包含二次 LLM 评审。
2. 当前 memory summary 是 extractive / heuristic 压缩，不是多轮反思式总结。
3. 当前去重使用文本相似度阈值，适合 MVP，不适合超大规模数据构建。
4. 当前仅内置 `qa` 与 `instruction_response` 两种 schema。

## 8. 下一步演进

1. 增加 judge model 二次打分与 rejection sampling。
2. 增加多语言 seed mixing 与跨语言 parallel corpus 生成。
3. 增加更稳健的重复检测与 topic coverage 统计。
4. 将压缩包升级为可缓存的“主题 memory bank”。
5. 与主标注流程打通：生成结果可以一键进入批量标注任务，但不能绕过概念校准。

## 9. Streamlit 向导页

除脚本式 pipeline 外，当前还提供一个面向人工确认的页面化入口：

1. 第 1 步：输入一句话 brief 与基础参数。
2. 第 2 步：生成标题候选与样稿方向，允许多轮重规划。
3. 第 3 步：先生成样稿，人工确认风格。
4. 第 4 步：批量生成完整语料库。
5. 第 5 步：调用独立 judge，对每篇文章给出评分与修改建议。

这个页面更适合“先探索，再定稿”的工作方式；脚本入口更适合固定配置下的批处理实验。

在默认 UI 中，Corpus Builder 应保持为高级工具，不进入 5 个核心页面，以免新用户误以为 Rosetta 的主线是生成语料而不是构建可审计标注。
