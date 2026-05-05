# Concept Bootstrap Pipeline (Developer)

更新时间: 2026-05-05

## 1. 目标

Concept Bootstrap Pipeline 是 Rosetta 的新研究主线。它把“一句话概念描述 + 15 个金样例”扩展成一条可复现的大规模标注流水线。

核心目标不是单次自动标注，而是：

1. 用少量金样例校准概念描述。
2. 用多次采样估计模型自洽性。
3. 把低置信样本优先交给人类专家。
4. 用专家选择结果持续更新 hard examples 与提示策略。
5. 生成可和 ACTER、NCBI、BC2GM、CoNLL03 等数据集对比的实验产物。

这条流水线也是 Rosetta 证明 LLM agent 强于低预算 PLM-first 标注流程的核心实验载体。它不以“单次 LLM 输出是否正确”为终点，而以“概念版本是否变好、人工审核是否更省、导出数据是否可复现”为终点。

## 2. 非目标

1. 不改 Docker/container 部署链路。
2. 不把这条线并入 legacy `corpusgen` 顶层边界；语料生成只能作为高级数据工厂 workflow 服务主标注线。
3. 不把系统做成复杂的多 agent 平台。
4. 不要求用户一开始准备大规模 gold dataset。
5. 不声称 LLM 在完整高质量训练集条件下无条件超过最优 PLM。

## 3. 端到端流程

```text
用户输入
  -> concept brief
  -> 15 gold examples

概念校准
  -> only-description annotation
  -> failed examples
  -> candidate concept generation
  -> gold loss scoring
  -> accept only improving clean revision
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
  -> PLM / LLM budget comparison
  -> EMNLP-style report tables
```

## 3.1 算法契约

正式自举循环必须满足：

1. 少于 15 条金样例只能保存草稿，不能启动正式自举。
2. 每轮先评估当前概念，得到 `current_loss`。
3. 大模型只负责生成候选概念正文，不负责组织日志。
4. 系统用同一批金样例重新评估候选概念。
5. 只有候选 loss 下降时才接受该候选。
6. 失败摘要、样例编号、漏标、多标和原始响应只进入 metadata / artifact，不进入最终概念阐释。
7. 如果连续无改进，停止搜索并保留当前最优版本。

内部 loss 不是最终论文指标。它是自举搜索时的优化目标，主要由失败样例数、边界不稳定样例数、漏标数、多标数和平均 span-F1 组成。最终实验仍应报告标准 precision / recall / F1、人工审核量和成本。

## 3.2 Prompt Optimization Subsystem

`v4.3.0` 开始，当前 `loss-guided candidate search` 已接入显式 Prompt-as-Parameter 最小内核。概念阐释不再只是整段字符串交给 LLM 改写，而是先切分为可训练文本参数，再估算 Text Gradient，并把优化方向、长度惩罚和候选验证结果写入 trace。

默认数据流：

```text
ConceptVersion
  -> segment prompt
  -> estimate text gradients
  -> generate candidate prompts
  -> evaluate gold loss
  -> accept / reject
  -> write optimization trace
```

未来实现应包含以下组件：

1. `PromptSegmenter`: 将概念阐释切成任务定义、概念定义、边界规则、负例规则和失败模式抽象。
2. `TextGradientEstimator`: 用 Mask 遮挡、对比替换、消融链路和 LLM 自我诊断估算文本梯度。
3. `PromptOptimizer`: 根据梯度方向、历史状态和长度惩罚生成更新策略。
4. `CandidateGenerator`: 调用 LLM 生成干净候选 prompt，不把失败日志拼进最终文本。
5. `PromptOptimizationTrace`: 记录每一步扰动、loss delta、候选、是否接受和诊断日志。

v1 文档默认优化器是 `LLM-AdamW`：

1. 保留历史有效方向，避免每轮随机漂移。
2. 对高频波动片段小步更新，对稳定有效方向加大权重。
3. 对 prompt 长度做 weight decay，禁止靠无限加规则降低短期 loss。
4. 所有候选必须通过同一批 gold examples 验证，只有 loss 下降才接受。

Trace 至少记录：

1. `segment_id`
2. `perturbation_method`
3. `gradient_direction`
4. `current_loss`
5. `candidate_loss`
6. `loss_delta`
7. `length_delta`
8. `accepted`
9. `diagnostics`

当前状态边界：`v4.3.0` 已实现最小 Prompt-as-Parameter 内核，包括 prompt 分段、启发式 Mask 文本梯度、`LLM-AdamW` trace、长度惩罚和 gold loss validation。`v4.4.0` 在此基础上新增提示词优化训练实验，能在同一批 15 条金样例上比较三种候选生成策略，并把完整训练轨迹写入 artifact。对比替换、消融链路和跨轮 optimizer state 仍是后续工作。

## 3.3 Prompt Training Experiment

`run_prompt_training_experiment` 是 `v4.4.0` 新增的高层训练入口。它不替代 `run_concept_refinement_loop`，而是用于把“一个简单任务描述能否训练到 15 条金样例全通过”变成可比较、可复现的实验。

输入：

1. `guideline_id`
2. 当前 guideline 的 15 条 gold tasks
3. `PromptTrainingConfig`
4. 可选 `predictor`
5. 可选 `auto_apply`

默认配置：

```python
PromptTrainingConfig(
    methods=("llm_optimize_only", "llm_reflection", "text_gradient_adamw"),
    max_rounds=30,
    candidate_count=3,
    target_pass_count=15,
    min_loss_delta=0.01,
    patience_rounds=5,
    stop_policy="patience_no_loss_improvement",
    candidate_temperature=0.3,
    evaluation_temperature=0.0,
    length_penalty=True,
    no_corpus_memorization=True,
    memorization_policy="repair_then_reject",
    raw_feedback_allowed=True,
    concurrency=20,
    repair_leaked_candidates=True,
    max_repair_attempts=2,
    provider_id="deepseek",
    model="deepseek-v4-pro",
)
```

三种方法必须使用同一套 gold loss、同一批金样例、同一套候选接受规则和同一个冻结输出协议：

| 方法 | 训练反馈材料 | 候选生成信息 | 防背答案约束 | 用途 |
| --- | --- | --- | --- | --- |
| `llm_optimize_only` | 不提供原文、标准答案、模型答案、失败详情、loss 或文本梯度 | 只告诉大模型“请优化当前概念语义提示词” | 候选只允许包含概念定义、边界规则和排除规则 | 最简单 baseline |
| `llm_reflection` | 提供原文、gold answer、model answer、错误类型和失败摘要，标记 `training_feedback_only=true` | 要求 LLM 把具体错误抽象成整体概念阐释 | 候选不能复制原文、gold span、model span 或可识别答案片段，也不能改输出协议 | 普通 LLM 反思 baseline |
| `text_gradient_adamw` | 提供原始批改对照、系统计算的文本梯度方向、loss 和长度变化 | 使用 Text Gradient / `LLM-AdamW` 方向生成概念候选 | 梯度可来自具体错误，但最终候选只能保留抽象规则；格式协议由 harness 注入 | Rosetta 默认方法 |

每种方法独立运行，不共享中间 prompt，避免方法之间互相污染。每轮固定执行：

```text
evaluate current prompt
  -> compute gold loss
  -> build training feedback prompt
  -> generate concept-only candidate prompts
  -> sanitize candidate prompts
  -> run MemorizationGuard on candidate prompts
  -> repair leaked candidate prompts when possible
  -> run MemorizationGuard again
  -> inject frozen output protocol
  -> strict parse and format repair
  -> evaluate each candidate on the same 15 gold examples
  -> accept only loss-decreasing clean candidate
  -> stop if 15/15 pass or 5 consecutive rounds have no loss improvement
```

`v4.5.1` 后，`max_rounds` 不再等于成功标准。每个方法独立维护 `no_improvement_streak`：

1. 任一候选让本轮 loss 下降超过 `min_loss_delta`，接受该候选并把 streak 重置为 0。
2. 本轮所有候选都没有让 loss 下降，streak 加 1。
3. 达到 `15/15` 时立即停止，`stop_reason=reached_target`。
4. 连续 5 轮无下降时停止，`stop_reason=no_loss_improvement_patience`。
5. 达到 `max_rounds` 仍未满足上述条件时停止，`stop_reason=max_rounds`。

结果汇总使用历史最优接受版本，而不是最后一轮快照。真实 LLM 即使 `evaluation_temperature=0.0` 也可能有轻微波动，因此 method result 中的 `best_loss / best_pass_count / best_round_index / best_description` 必须指向训练过程中观察到的最优已接受 prompt；`stop_reason / round_count / no_improvement_streak` 则描述该方法实际如何停止。

`training feedback prompt` 和 `learned operational prompt` 是不同对象：

1. `training feedback prompt` 是优化模型看的批改材料，可以包含原文、标准答案和模型回答，但必须标记 `training_feedback_only=true`。
2. `learned operational prompt` 是后续批量标注使用的概念阐释，不能复制语料词、gold span、model span、原句或可识别答案片段。
3. `ConceptVersion.description` 只保存通过防背答案检查的 concept-only operational prompt。
4. raw feedback、raw response、失败样例和完整候选日志只进入 artifact 或折叠日志。

`MemorizationGuard` 的输入来自同一批 15 条 gold：

1. gold task 原文。
2. gold spans 和 runtime annotation。
3. 当前轮模型答案中的 predicted spans。
4. 从这些文本抽取出的词、短语和 n-gram hash。
5. 允许项仅包含标签名、输出格式等任务公共词。

`v4.5.0` 后，候选泄露不再立即拒绝。默认策略是 `repair_then_reject`：

1. `MemorizationGuard` 先标记 `clean / soft_leak / critical_leak`。
2. 如果候选泄露，系统把候选提示词和 runtime 内部的 transient raw matches 交给 `repair_leaked_prompt()`。
3. 修复模型只做“去语料化”：删除具体词、短语、原句、答案片段和样例编号，把它们改写成抽象边界规则或排除规则。
4. 修复最多 2 次。修复后通过 guard 的候选才进入 gold loss 回测。
5. 修复后仍泄露时，记录 `status=memorization_repair_failed`、`memorization_passed=false`、`blocked_terms_count`、`guard_before_repair`、`guard_after_repair` 和 `repair_attempts`。
6. 主报告仍只展示 hash / count；raw matches 默认不写入公开 UI 和报告。

每种方法和每一轮还会记录轻量 usage：

1. `llm_call_count`: predictor 调用次数。
2. `estimated_tokens`: 基于 system prompt、messages 和 raw response 字符数的粗略估算。
3. `elapsed_seconds`: 该方法或该轮墙钟耗时。
4. `usage.estimated=true`: 当前优先使用 `LLMServiceRuntime` 的 token 估算；如果 provider 后续返回真实 usage，应替换为 provider usage 并标记 `estimated=false`。

最终选择规则：

1. 优先选择达到 `15/15` 的方法。
2. 达到目标的方法还必须通过最终提示词防背答案检查。
3. 如果多个方法都达到目标，选择 loss 更低者。
4. 如果 loss 相同，选择 prompt 更短者。
5. 如果仍相同，选择轮数更少者。
6. 如果没有方法达到 `15/15`，或最佳方法最终提示词不干净，选择最终 loss 最低者，但状态标记为 `needs_revision`。

落盘契约：

1. `ConceptVersion.description` 只保存胜出的干净提示词。
2. `ConceptVersion.metadata.prompt_training=true`。
3. `ConceptVersion.metadata.best_method` 保存胜出方法。
4. `ConceptVersion.metadata.method_comparison` 保存每种方法的状态、停止原因、初始 loss、最佳 loss、loss delta、通过数、轮数和提示词长度。
5. `ConceptVersion.metadata.leakage_summary` 保存 `candidate_blocked_count`、`final_prompt_clean`、fingerprint 摘要和最终检查结果。
6. 完整 round trace、training feedback、候选 raw response、净化警告、loss detail、轻量 usage、`MemorizationGuard` 检查和 `PromptOptimizationTrace` 写入 `.runtime/artifacts/prompt_training/*.json`。
7. CLI 对比实验额外输出 `comparison_report.md`、`comparison_result.json`、`prompt_evolution.jsonl` 和 `run_events.jsonl`，用于人工阅读、后续统计、提示词演化复核和运行过程复现。

`v4.5.2` 后，提示词优化训练增加后台运行与进度事件层，但不改变三方法优化算法：

```text
Concept Lab click
  -> create WorkflowRun(status=running)
  -> start_prompt_training_background_run()
  -> background thread creates RuntimeStore + LLMServiceRuntime
  -> run_prompt_training_experiment(progress_recorder=...)
  -> write run_progress_events
  -> write comparison_report.md / comparison_result.json / prompt_evolution.jsonl / run_events.jsonl
  -> update WorkflowRun(status=succeeded|failed)
```

阶段事件至少包括：

1. `run_started / run_completed / run_failed`
2. `method_started / method_completed`
3. `round_started / round_completed`
4. `gold_validation_started / gold_validation_completed`
5. `candidate_generation_started / candidate_generated`
6. `candidate_repair_started / candidate_repair_completed`
7. `candidate_evaluation_started / candidate_evaluated`
8. `candidate_accepted / candidate_rejected`
9. `call_queued / call_started / call_succeeded / call_failed / call_retried`

事件 payload 必须是安全摘要：不能包含 raw prompt、raw response、gold 原文、gold span、model span 或 private leakage matches。完整可复现实验依赖 artifact 中的受控 trace，而 UI 日志只展示阶段、计数、loss、候选状态、token 和错误摘要。

### 3.4 Annotation Harness Contract

`v4.5.5` 文档契约把标注 prompt 拆成两部分：

```text
ConceptPromptSpec
  -> concept_definition
  -> boundary_rules
  -> negative_rules

Frozen OutputProtocolSpec
  -> labels
  -> JSON schema
  -> annotation markup
  -> parser contract
  -> format repair instructions
```

`ConceptPromptSpec` 是 prompt training 的优化对象。`Frozen OutputProtocolSpec` 是 harness 责任，不进入 optimizer 的可编辑空间。后续代码实现时，页面、CLI 和 workflow 都应遵守同一条运行链路：

```text
ConceptPromptSpec
  -> inject Frozen OutputProtocolSpec
  -> LLM call
  -> strict JSON parse
  -> schema / text / label / markup validation
  -> format repair loop if needed
  -> semantic loss only after format is valid
```

冻结输出协议默认采用 `JSON+markup`：

```json
{
  "text": "原始输入文本，必须与任务 text 一致",
  "annotation": "使用 [span]{Term} 标出所有目标片段",
  "explanation": "一句简短理由"
}
```

约束：

1. JSON 外不能有 markdown fence、解释性 prose 或额外包装。
2. `annotation` 必须使用 `[span]{Term}` 行内 markup；`Term` 来自 harness 注入的标签集合，不由 optimizer 学习。
3. `text` 必须与当前任务原文一致；不能改写、翻译或摘要。
4. 每个 span 必须能在 `text` 中定位，label 必须属于冻结标签集合。
5. schema、标签、markup 格式、repair 指令和 parser 行为不能被候选提示词修改。

格式失败和语义失败必须分开：

1. 先做 strict parse 与 schema validation。
2. 如果 JSON、字段、markup、label 或 span 定位失败，进入最多 2 次 format repair。
3. format repair prompt 只能强调冻结输出协议，不能改写概念定义、边界规则或负例规则。
4. repair 成功后才计算 semantic loss。
5. repair 失败记录为 `format_failed`，不混入漏标、多标或边界错误。
6. 实验报告必须单独展示 `format_failure_rate`、`format_repair_success_rate`、`semantic_loss` 和 `pass_count`。

当前状态边界：现有解析器和部分 workflow 已能处理 JSON 响应与 markup 字段，但统一的 `AnnotationHarness`、跨 workflow 的 strict validation / repair loop 和格式指标拆分仍是下一阶段实现任务。本节是实现契约，不表示这些能力已经全部接入每条路径。

实现边界：

1. 第一版成功标准只看 15 条金样例，不加入 held-out validation；因此只能证明“没有直接背答案且能通过训练 gold”，不能证明泛化。
2. `v4.5.2` 已新增 SQLite `run_progress_events` 并把 Concept Lab prompt training 改为后台轮询；pause/resume/cancel 仍未实现。
3. 批量标注、概念自举和 LLM-as-a-judge 后续应复用同一 `ProgressRecorder`，但本轮只覆盖提示词优化训练。
4. 强格式 harness 是 `v4.5.5` 文档契约，后续代码实现必须复用同一冻结输出协议，不允许每个 workflow 自己拼格式 prompt。

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

所有不确定性信号都应写入 `Prediction.meta` 或 `ReviewTask.meta`。否则导出报告无法解释为什么某条样本被自动通过、进入审核或被标为 hard example。

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

与 PLM 对比时还要记录：

1. 同等 gold 数量下 PLM fine-tuning 的 F1。
2. Full-data PLM fine-tuning 的上界表现。
3. Rosetta 达到同等 F1 所需的人工审核量。
4. Rosetta 额外模型调用成本。
5. 概念漂移或标签定义变化后，Rosetta 更新概念版本和 PLM 重新训练的成本差异。

## 10. 历史 10 版本落地顺序

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

`v4.2.2` 将概念修订升级为 loss-guided search：

1. 每轮先评估当前概念在 15 条金样例上的表现，得到 `current_loss`。
2. 大模型按多个探索方向生成候选概念，例如提高召回、收紧边界、平衡改写。
3. 每个候选概念都重新试标同一组金样例，计算 `selected_loss` 候选指标。
4. 只有当候选 loss 下降超过阈值时，候选才会被接受为下一轮概念版本。
5. 如果没有候选改善 loss，则状态记为 `no_improvement`，保留当前最优概念，避免错误修订继续累积。
6. `ConceptVersion.metadata` 记录 `optimizer/current_loss/selected_loss/loss_delta/accepted_candidate_id/candidate_evaluations`，便于复现实验路径。

当前 loss 由失败样例数、边界不稳定数、漏标数、多标数和平均 span-F1 score 组成。候选只有在完整 span set 优于当前版本时才会被接受；多标额外片段不会被算作通过。这个 loss 不是最终论文指标，而是自举搜索时的内部优化目标。

`v4.2.4` 将 Prompt-as-Parameter 写为下一阶段方法框架：

1. Prompt 被视为可训练文本参数，而不是静态提示词。
2. Text Gradient 通过 Mask 遮挡、对比替换、消融链路和 LLM 自诊断估算。
3. 默认优化器叙事是 `LLM-AdamW + gold loss validation + length decay`。
4. 当前只完成文档升级，不宣称完整文本梯度优化器已经实现。

`v4.3.0` 将 Prompt-as-Parameter 接入概念自举最小电路：

1. 新增 `app/workflows/bootstrap/prompt_optimizer.py`。
2. `segment_prompt()` 将概念阐释切为 `task_definition / label_schema / boundary_rules / negative_rules / output_format` 等片段，其中标签集合和输出格式默认不可随意改写。
3. `estimate_text_gradients()` 根据失败数、边界不稳定数、漏标、多标和当前 loss 生成启发式 Mask 文本梯度。
4. `build_llm_adamw_trace()` 选择最高影响片段，形成候选改写方向，并把该方向注入修订 prompt。
5. `length_penalized_loss()` 对变长候选加入惩罚，防止“越优化越长、越优化越烂”。
6. `finalize_candidate_trace()` 写入候选 loss、loss delta、length delta 和 accepted 状态。
7. `ConceptVersion.metadata.prompt_optimization_trace` 保存最终接受候选的优化轨迹；所有候选的 trace 保存在 `candidate_evaluations` 中。

当前 v4.3.0 的梯度估算仍是轻量启发式，不等同于完整 Mask 遮挡重跑。它的价值是先把接口、trace 和接受准则落稳，为后续真实消融、对比替换和多策略实验留出可测试边界。

## 12. 下一步开发检查

每次改动 bootstrap 相关代码时，至少回答：

1. 是否仍然保证 15 条金样例是正式自举门槛。
2. 是否仍然只保存干净概念阐释到 `ConceptVersion.description`。
3. 是否仍然能从 metadata 复现失败样例、loss 和候选选择。
4. 是否能导出 PLM / LLM 对比所需字段。
5. 是否能让用户在概念实验室看懂“当前为什么变好或没有变好”。
6. 如果实现 Prompt-as-Parameter，是否记录了被扰动片段、梯度估算方法、loss delta 和长度变化。
