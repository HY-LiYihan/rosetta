# Concept Bootstrap Pipeline (Developer)

更新时间: 2026-04-28

## 1. 目标

Concept Bootstrap Pipeline 是 Rosetta 的新研究主线。它把“一句话概念描述 + 15 个金样例”扩展成一条可复现的大规模标注流水线。

核心目标不是单次自动标注，而是：

1. 用少量金样例校准概念描述。
2. 用多次采样估计模型自洽性。
3. 把低置信样本优先交给人类专家。
4. 用专家选择结果持续更新 hard examples 与提示策略。
5. 生成可和 ACTER、NCBI、BC2GM、CoNLL03 等数据集对比的实验产物。

## 2. 非目标

1. 不改 Docker/container 部署链路。
2. 不把这条线并入 `corpusgen`。
3. 不把系统做成复杂的多 agent 平台。
4. 不要求用户一开始准备大规模 gold dataset。

## 3. 端到端流程

```text
用户输入
  -> concept brief
  -> 15 gold examples

概念校准
  -> only-description annotation
  -> failed examples
  -> clean concept description revision
  -> until all gold examples pass

大规模标注
  -> k-run sampling
  -> consistency scoring
  -> high-confidence pseudo labels
  -> low-confidence human review queue

专家批改
  -> show candidate annotations as multiple choice
  -> expert chooses best candidate or edits manually
  -> hard examples and failure notes

增强推理
  -> similar example retrieval
  -> boundary/distant example retrieval
  -> label-statistic reflection

实验输出
  -> predictions
  -> human choices
  -> uncertainty metrics
  -> gold comparison
  -> EMNLP-style report tables
```

## 4. 分层边界

这条流水线现在是 Rosetta 主工作流的一部分。新功能优先进入 `app/workflows/*`，旧 `app/research/*` 和 `scripts/research/*` 只保留为离线分析、算法参考和兼容入口：

```text
app/workflows/bootstrap/      # 15 gold examples -> concept description refinement
app/workflows/annotation/     # k-run sampling, context building, consistency routing
app/workflows/review/         # human choice, hard examples, gold-like feedback
app/workflows/evaluation/     # reports, metrics, experiment summaries
app/research/                 # legacy offline analysis and algorithm references
scripts/research/             # legacy CLI entrypoints
```

允许共享的模块：

1. `app/domain/*`：标注格式与 AnnotationDoc。
2. `app/infrastructure/llm/*`：Kimi / BigModel / DeepSeek / Qwen provider。
3. `app/research/*`：已实现的 consistency、contrastive retrieval、label statistics、reflection 参考算法。

## 5. 最小数据格式

LLM 的输出格式和最终存储格式不需要一致。

标注时，为了让模型更容易完成任务，可以继续使用行内标注格式：

```text
Patients with [heart failure]{Specific_Term} may receive [ventricular assist devices]{Specific_Term}.
```

这种格式适合放进 prompt，因为标签紧贴原文，模型不需要手工计算字符偏移。

最终存储时，必须统一转换为 Prodigy-compatible JSONL。内部主格式保持简单 JSONL，避免直接绑定 INCEpTION `jsoncas`；同时沿用 Prodigy 常见字段 `spans / relations / label / options / accept / answer / meta`：

```json
{
  "schema_version": "rosetta.prodigy_jsonl.v1",
  "id": "sample-001",
  "text": "Patients with heart failure may receive ventricular assist devices.",
  "tokens": [],
  "spans": [
    {
      "id": "T1",
      "start": 14,
      "end": 27,
      "text": "heart failure",
      "label": "Specific_Term",
      "implicit": false
    }
  ],
  "relations": [],
  "answer": "accept",
  "meta": {
    "dataset": "ACTER",
    "language": "en",
    "domain": "heart_failure"
  }
}
```

这个格式不是新发明。它参考 Prodigy annotation task JSON：每条记录包含 `text`，并用 `spans` 保存实体或片段的字符起止偏移和标签；用 `relations` 保存片段或 token 关系；用 `options / accept / answer` 保存分类与人工决策。spaCy 的训练数据格式也使用字符 offset 表示 spans。完整格式规范见 [ANNOTATION_JSONL_FORMAT.md](./ANNOTATION_JSONL_FORMAT.md)。

每次模型输出候选：

```json
{
  "schema_version": "rosetta.prodigy_candidate.v1",
  "sample_id": "sample-001",
  "candidate_id": "run-001",
  "text": "Patients with heart failure may receive ventricular assist devices.",
  "tokens": [],
  "spans": [
    {
      "id": "T1",
      "start": 14,
      "end": 27,
      "text": "heart failure",
      "label": "Specific_Term",
      "implicit": false
    }
  ],
  "relations": [],
  "runtime_annotation": {
    "format": "inline_markup.v1",
    "annotation_markup": "[heart failure]{Specific_Term}"
  },
  "answer": null,
  "explanation": "The phrase names a domain-specific medical condition.",
  "model_confidence": 0.82,
  "uncertainty_reason": "Boundary is clear."
}
```

专家复核选择：

```json
{
  "sample_id": "sample-001",
  "selected_candidate_id": "candidate-003",
  "decision": "accept_candidate",
  "edited_annotation": null,
  "notes": "Candidate C has the correct span boundary."
}
```

转换原则：

1. Prompt 中优先使用行内 markup，降低模型输出难度。
2. 解析后立刻转换成 `spans`，并校验 `text[start:end] == span.text`。
3. 研究产物、评测、专家复核、导入导出一律以 Prodigy-compatible JSONL 为准。
4. 如果接入 INCEpTION，则只在边界层做 `jsoncas <-> prodigy_jsonl` 转换。

参考：

1. Prodigy NER / span annotation JSONL：`text` + `spans[{start,end,label}]`。
2. spaCy data formats：spans 使用字符 offset tuple 表达。
3. INCEpTION：复杂项目交换可使用 `UIMA CAS JSON`，但不作为 Rosetta 内部主格式。

## 6. 不确定性信号

单一信号不可靠，因此采用组合路由：

```text
uncertainty =
  annotation_disagreement
  + model_self_uncertainty
  + rule_verification_risk
  + judge_disagreement
```

第一版实现优先支持：

1. `annotation_disagreement`：多次输出之间的 span-level 差异。
2. `model_self_uncertainty`：模型自评 confidence，仅作辅助。
3. `rule_verification_risk`：格式、span、逻辑规则错误。

第二阶段再加入：

1. LLM-as-a-judge 候选评审。
2. token probability / logprob，如果目标平台稳定支持。
3. semantic entropy 风格的语义聚类。

## 7. 专家队列策略

专家不是平均批改所有样本，而是优先处理低置信样本。

推荐三种实验策略：

1. `random_review`：随机抽样给专家，作为弱基线。
2. `uncertainty_first`：优先给专家低自洽样本。
3. `hybrid_review`：低自洽样本优先，同时保留少量高置信样本抽检。

UI 或 CLI 输出都应尽量把复核任务做成选择题：

```text
候选 A: ...
候选 B: ...
候选 C: ...
候选 D: ...
候选 E: ...
候选 F: 以上都不对，手动修正
```

## 8. 运行产物

默认输出目录：

```text
.runtime/research/<config-name>/bootstrap_<timestamp>/
```

核心产物：

```text
concept_versions.jsonl
gold_examples.jsonl
candidate_runs.jsonl
consistency_scores.jsonl
human_review_queue.jsonl
human_choices.jsonl
hard_examples.jsonl
retrieval_traces.jsonl
label_statistics.json
report.md
manifest.json
```

## 9. 实验指标

必须优先覆盖：

1. span-level precision / recall / F1。
2. boundary exact match。
3. label exact match。
4. 同等人工预算下的收益。
5. 专家选择候选即可通过的比例。
6. 必须手动改写的比例。
7. 高置信自动通过样本的抽检错误率。
8. 低置信样本转为 hard examples 后的下一轮提升。

## 10. 推荐 10 版本落地顺序

1. `v3.1.0`: 核心研究想法归档。
2. `v3.2.0`: Pipeline 文档、架构边界与版本路线。
3. `v3.3.0`: 数据契约与 JSONL IO。
4. `v3.4.0`: 多次输出自洽性评分。
5. `v3.5.0`: 人类专家复核队列。
6. `v3.6.0`: 相似 / 边界对比式检索。
7. `v3.7.0`: 标签统计与反思计划。
8. `v3.8.0`: Bootstrap runner 与 CLI。
9. `v3.9.0`: ACTER / EMNLP 实验模板。
10. `v3.10.0`: 报告生成、对比表与最终文档串联。
11. `v3.11.0`: 存储格式升级为可扩展 Annotation JSONL。
12. `v3.12.0`: 存储格式收敛为 Prodigy-compatible JSONL profile。

## 11. 当前实现状态

`v3.3.0` 已完成最小数据层：

1. `app/research/bootstrap_contracts.py`
- 定义 `BootstrapSpan`、`BootstrapSample`、`BootstrapCandidate`。
- 校验 span offset 与原文一致。
- 校验模型自评 confidence 必须在 `0-1`。

2. `app/research/bootstrap_io.py`
- 支持读取 Annotation JSONL，并兼容旧顶层 `spans` JSONL。
- 支持从旧行内 `[span]{label}` gold annotation 迁移到 `spans`。
- 写出时统一落盘为 Prodigy-compatible JSONL。
- 支持候选标注记录的 JSONL 读写。

`v3.4.0` 已完成自洽性评分层：

1. `app/research/consistency.py`
- 计算同一样本多次候选之间的 pairwise span-F1。
- 计算 exact-match rate。
- 汇总模型自评 confidence。
- 输出 `high / medium / low` 路由，用于后续专家复核队列。

`v3.5.0` 已完成专家复核队列层：

1. `app/research/human_review.py`
- 将 `medium / low` 路由样本转成 `HumanReviewTask`。
- 每个复核任务包含候选 A/B/C... 与固定手动修正选项。
- 按 route 和 uncertainty score 生成优先级，低置信样本排在前面。

`v3.6.0` 已完成对比式检索层：

1. `app/research/contrastive_retrieval.py`
- 基于轻量 lexical similarity 选择最相似样例。
- 从剩余低相似样例中选择少量 boundary examples。
- 输出结构区分 `similar` 与 `boundary`，后续可替换为 Embedding-3 检索而不改变上层接口。

`v3.7.0` 已完成标签统计与反思计划层：

1. `app/research/label_statistics.py`
- 从 gold / high-confidence 样本统计 token 的 entity/context/other 分布。
- 输出 entity/context/other probability，为 DEER 风格 label-guided retrieval 做准备。

2. `app/research/reflection.py`
- 基于统计结果生成反思计划。
- 当前覆盖 unseen token、possible false negative、boundary token 三类风险。
- 该层只生成计划，不直接调用模型，避免自动反思失控。

`v3.8.0` 已完成离线 runner 与 CLI：

1. `app/research/bootstrap_runner.py`
- 输入 normalized samples 与 candidate runs。
- 输出 consistency scores、human review queue、label statistics、reflection plans 与 retrieval traces。
- 当前 runner 不直接调用模型，适合作为真实模型调用后的分析与实验汇总层。

2. `scripts/research/run_bootstrap.py`
- 提供 `analyze` 子命令：

```bash
python scripts/research/run_bootstrap.py analyze \
  --samples path/to/samples.jsonl \
  --candidates path/to/candidate_runs.jsonl \
  --run-name acter-heart-failure
```

`v3.10.0` 已完成报告生成：

1. `app/research/bootstrap_report.py`
- 根据 manifest、consistency scores、review queue、label statistics 和 reflection plans 生成 `report.md`。
- 报告包含 consistency route 分布、专家复核队列规模、top entity tokens、reflection item 类型统计、计划 baselines 与 metrics。

2. `scripts/research/run_bootstrap.py`
- `analyze` 子命令新增 `--experiment`，用于把实验配置中的 baselines / metrics 写入报告。

`v3.11.0` 已完成可扩展存储格式过渡：

1. `app/research/bootstrap_io.py`
- 支持读取 `rosetta.annotation_jsonl.v1`。
- 旧顶层 `spans`、旧 `annotation_markup` 与 `gold_annotation` 仍作为兼容输入。

2. 存储主结构
- `annotation.layers.spans` 作为过渡结构被保留为兼容输入。

`v3.12.0` 已完成 Prodigy-compatible JSONL 规范化：

1. `docs/developer/ANNOTATION_JSONL_FORMAT.md`
- 明确格式来源：Prodigy task JSON、spaCy span offsets、INCEpTION `jsoncas` 互操作边界。
- 明确 `label / options / accept / answer / meta` 等字段含义。
- 覆盖 span、relation、概念包含、句子级、段落级、文章级标注示例。

2. `app/research/bootstrap_io.py`
- 新写出的 normalized samples 使用 `rosetta.prodigy_jsonl.v1`。
- 新写出的 candidate runs 使用 `rosetta.prodigy_candidate.v1`。
- 继续兼容旧 `annotation.layers` 读取。

`v4.2.0` 已将 bootstrap 从离线研究原型接入主工作流：

1. `app/workflows/bootstrap/guideline.py`
- 新增 `run_concept_refinement_loop`。
- 正式自举要求 15 条金样例。
- 每轮写入 `ConceptVersion`，记录通过数、失败样例、边界不稳定样例和失败摘要。

2. `app/workflows/annotation/context.py`
- 构建批量标注上下文。
- 组合稳定概念版本、相似 gold/high-confidence 样例、边界远例和失败模式摘要。

3. `app/workflows/annotation/batch.py`
- 候选评分升级为 span-F1、exact match rate、模型自评和规则风险组合。
- `Prediction.meta` 记录采样序号、共识分组、span-F1、规则风险和上下文样例 id。

4. `app/workflows/review/queue.py`
- 审核保存记录错误类型、是否 hard example、是否 gold-like、是否人工编辑和选择的候选。

5. `app/data/exporters.py`
- 报告升级为实验报告，包含概念版本和主动审核反馈。

`v4.2.1` 修正概念修订的 prompt/log 边界：

1. `app/workflows/bootstrap/guideline.py`
- 大模型修订任务只要求返回优化后的概念阐释正文，不再要求复杂 JSON。
- `ConceptVersion.description` 只保存净化后的最终提示词。
- 失败样例编号、失败摘要、逐条 failure cases、模型原始响应和净化警告写入 `ConceptVersion.metadata`。
- 净化 guard 会阻止 `gold-000xx`、`失败摘要`、`修订建议`、`漏标`、`多标` 等诊断内容进入最终提示词。

2. `app/ui/pages/Concept_Lab.py`
- “最终概念版本草案”只展示干净提示词。
- “失败详情与修订日志”折叠区展示 failure cases、raw revision response 和 sanitizer warnings。
