# Research Pipeline (Developer)

更新时间: 2026-04-21

## 1. 目标

1. 将 PDF 中提出的“LLM-Assisted Iterative Annotation Framework”落为可执行的研究工程骨架。
2. 优先支持 prompt 迭代、pilot audit、批处理推断、规则验证与冲突导出。
3. 保证实验可复现：配置、prompt、检索示例、模型输出与验证结果全部落盘。

## 2. 当前实现范围（Initial Lab Build）

本次初版聚焦可执行研究骨架，而非一次性完成全部科研功能：

1. `configs/research/*.json`
- 研究配置模板。
- 包含操作化定义、负向约束、动态示例库、冲突规则与模型参数。

2. `configs/research/*.jsonl`
- Pilot 样本模板。
- 每行一个样本，支持 `id/text/gold_annotation/gold_explanation/metadata`。

3. `app/research/`
- `config.py`: 研究配置加载与校验。
- `prompting.py`: 研究 prompt 组装。
- `indexing.py`: 基于 CPU 的向量索引构建与缓存。
- `retrieval.py`: 支持 lexical 与 embedding 两种动态 few-shot 检索。
- `verifier.py`: 规则校验（格式、显性跨度、互斥标签）。
- `runner.py`: `preview` / `batch` / `audit` 执行入口。

4. `scripts/research/run_pipeline.py`
- `preview`: 预览单条样本的动态 prompt。
- `build-index`: 预构建 `embedding-3` 的 CPU 向量索引缓存。
- `run --mode batch`: 面向未标注数据的批处理推断。
- `run --mode audit`: 面向带 gold 标签数据的审查模式，导出冲突样本。

## 3. 运行产物

默认输出目录：`.runtime/research/<config-name>/<mode>_<timestamp>/`

每次运行会生成：

1. `manifest.json`
- 记录配置、模型、样本数、accepted/review/conflict 数量。

2. `predictions.jsonl`
- 每条样本的 prompt、检索示例、模型原始输出、解析结果与验证问题。

3. `review_queue.jsonl`
- 自动验证未通过、需要人工复核的样本。

4. `conflicts.jsonl`
- 仅在 `audit` 模式下生成。
- 记录模型输出与 gold 标签冲突的样本。

## 4. 当前约束与设计取舍

1. 动态检索当前支持两种策略：
- `lexical`：零依赖、纯文本重叠召回
- `embedding`：使用 `Embedding-3` 构建 CPU 向量索引，并缓存到 `.runtime/research/indexes/`

2. 当前验证器专注“硬约束”：
- JSON 可解析
- annotation 格式合法
- 显性标注片段必须在原文中
- 标签互斥规则不冲突

3. 当前 `audit` 采用 annotation token signature 对比：
- 主要比较 `[文本]{标签}` token 集合是否与 gold 一致。
- 适合 pilot 阶段发现显著冲突样本。

## 5. 推荐工作流

1. 先编辑 `configs/research/pilot_template.json`
- 补齐你的任务定义、few-shot、负向约束与冲突规则。
- 如果要直接使用智谱模型，优先参考 `configs/research/glm5_embedding3_template.json`

2. 准备 pilot 样本集（建议 50-100 条）
- 保存为 `jsonl`
- 先做人工初标，再进入 `audit`

3. 预览 prompt

```bash
python scripts/research/run_pipeline.py preview \
  --config configs/research/pilot_template.json \
  --dataset configs/research/pilot_dataset.example.jsonl
```

如需先构建 `Embedding-3` 的 CPU 向量索引：

```bash
python scripts/research/run_pipeline.py build-index \
  --config configs/research/glm5_embedding3_template.json
```

4. 跑 pilot 审查

```bash
python scripts/research/run_pipeline.py run \
  --config configs/research/pilot_template.json \
  --dataset configs/research/pilot_dataset.example.jsonl \
  --mode audit
```

5. 阅读导出的 `conflicts.jsonl` 与 `review_queue.jsonl`
- 若人工错：修正 gold，转为 hard example
- 若模型系统性错：修正定义与 negative constraints

## 6. 下一步演进

1. 增加 self-consistency 不确定性估计（`k` 次采样 + 投票阈值）。
2. 增加 blind review 与 Kappa 统计。
3. 增加 discrepancy attribution 报告。
4. 将 CPU index 扩展为更大规模的 FAISS/HNSW 方案。
5. 累积 gold data 后接入 SFT / distillation 流程。
