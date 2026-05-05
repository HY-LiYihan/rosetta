# Prompt-as-Parameter: Text Gradient Optimization

更新时间: 2026-05-05

## 1. 核心定义

Prompt-as-Parameter 是 Rosetta 最核心的方法假设之一：把概念定义和边界规则视为一组可训练的文本参数，而不是一次性手写的静态 prompt。负例约束可以作为高级概念语义加入，但不是当前主表单的默认必填项。

从 `v4.5.5` 文档契约开始，Rosetta 明确区分两类 prompt 片段：

1. `ConceptPromptSpec`：可优化的概念语义，包括概念定义、边界规则，以及可选的高级负例约束。
2. `Frozen OutputProtocolSpec`：不可优化的输出协议，包括从 gold 推断的标签集合、JSON schema、行内 markup 或完整 AnnotationDoc JSON、解析规则和 format repair 指令。

这个区分是强 harness 的基础。Prompt optimizer 只能改“什么应该标、什么不应该标、边界如何取”，不能改“用什么标签、返回什么 JSON、annotation 字段怎么写、格式失败如何修复”。输出协议由 Rosetta harness 在每次标注调用时注入，并由统一 parser 和 repair loop 校验。

在传统模型训练中，参数是连续向量，优化器通过解析梯度更新权重。Rosetta 面对的是自然语言 prompt，无法直接计算解析梯度，因此需要估算“文本梯度”：

```text
文本梯度 = 某个 prompt 片段或语义方向对任务 loss 的方向性影响
```

这不是数学上的连续梯度，而是可操作的优化信号：哪段 prompt 最影响失败，往哪个语义方向改可能降低 gold loss，哪些修改只是让 prompt 变长但没有提升。

相关概念：

1. `Prompt Parameter`：可编辑的概念语义片段，例如任务定义、边界规则、可选负例约束和失败模式抽象。
2. `Prompt Loss`：用 15 条金样例或验证集计算出的任务损失，例如失败数、漏标数、多标数、边界错误和 span-F1。
3. `Text Gradient`：通过扰动、替换、消融或 LLM 诊断估算出的文本改写方向。
4. `Prompt Optimizer`：根据文本梯度生成候选 prompt，并用 gold loss 验证是否接受。

当前代码已经从 `loss-guided candidate search` 推进到可运行的 Prompt-as-Parameter 最小训练电路。`v4.3.0` 实现了 prompt 分段、启发式 Mask 文本梯度、`LLM-AdamW` trace 和长度惩罚；`v4.4.0` 加入提示词优化训练实验，可以在同一批 15 条金样例上比较 `llm_optimize_only`、`llm_reflection` 和 `text_gradient_adamw`；`v4.4.1` 增加防背答案检查，允许优化模型看批改对照，但禁止候选 prompt 和最终 prompt 复制语料词、gold span、model span 或可识别答案片段；`v4.5.0` 接入 LLM service runtime，默认真实模型为 DeepSeek `deepseek-v4-pro`，provider 并发上限为 50，并把泄露候选从“一票否决”改为“先去语料化修复，再回测 gold loss”；`v4.5.1` 将完整三方法实验改为连续 5 轮 loss 无下降才停止，并输出 Markdown/JSON/JSONL 对比产物；`v4.5.5` 文档化冻结输出协议与强格式 harness，规定后续代码必须把 output protocol 从 optimizer 的可编辑空间中拿出来；`v4.5.7` 先在页面和候选生成层落地这个契约，展示 `ConceptPromptSpec / Frozen OutputProtocolSpec` 分栏，并剥离候选中的标签、输出格式和 JSON schema；`v4.5.8` 进一步把用户表单收敛为概念名称、概念定义、边界说明和协议选项，标签从 gold 自动推断。完整优化器仍不是终局：对比替换、真实消融链路、跨轮 optimizer state 和统一 format repair harness 是下一阶段工作。

## 2. 参数空间

Rosetta 的概念 prompt 应先切分成可优化参数，而不是整段粗暴改写。切分时必须先把可训练语义和冻结协议分开。

`ConceptPromptSpec` 的建议参数位：

1. `task_definition`: 标注任务的一句话定义。
2. `concept_definition`: 概念的可执行定义。
3. `boundary_rules`: span 边界、最小完整短语、多词短语等规则。
4. `negative_constraints`: 可选高级项，用于表达“不包括什么”，当前主表单不默认暴露。
5. `failure_memory_abstraction`: 由 hard examples 和人工纠错信号抽象出的失败模式，不包含原文或答案片段。

`Frozen OutputProtocolSpec` 的建议字段：

1. `label_schema`: 标签集合和每个标签的意义。
2. `json_schema`: 模型必须返回的 JSON 字段。
3. `annotation_protocol`: 运行时标注协议，例如 `[span]{Term}` 行内 markup，或完整 AnnotationDoc JSON。
4. `parser_contract`: JSON parse、字段校验、span 可定位性和 label 合法性。
5. `format_repair_instructions`: 格式失败时的修复提示，只修格式、不改概念语义。

冻结字段不进入 optimizer prompt 的可编辑空间。它们由 harness 在标注调用时注入，也由 parser、repair loop 和报告指标统一约束。

参数空间必须有两个约束：

1. 每次优化只允许改动有限概念语义片段，避免整个 prompt 语义漂移。
2. Prompt 长度必须有惩罚项，避免越优化越长、越写越烂。
3. 输出协议、标签、JSON schema、行内 markup 和 repair 指令必须冻结，不能被候选生成策略改写。

## 3. 梯度估算方法

### 3.1 Mask 遮挡法

输入：当前 prompt、被切分的 prompt 片段、验证样例。

方法：逐个遮挡片段，再评估任务 loss 的变化。

```text
完整 prompt -> score = 0.88
遮挡角色定义 -> score = 0.86
遮挡边界规则 -> score = 0.63
遮挡负例规则 -> score = 0.71
```

输出：每个片段的重要性分数。遮挡后 loss 上升越多，说明该片段梯度越大、越关键。

适用场景：判断 prompt 中哪些部分最影响当前任务。

风险：遮挡会破坏 prompt 流畅性，可能高估某些连接性文本的重要性。

### 3.2 对比替换法

输入：当前片段、候选替换表达、验证样例。

方法：把同一片段替换成多个语义方向，并比较 loss delta。

```text
原始: 你是一个机器人专家
替换为: 你是一个工程师       -> loss -0.03
替换为: 你是一个科学家       -> loss +0.01
替换为: 你是资深技术人员     -> loss -0.05
```

输出：哪种语义方向更可能降低 loss。

适用场景：探索角色、任务定义、边界规则的改写方向。

风险：替换候选的质量会限制估计质量，需要保留随机探索或 LLM 生成替换。

### 3.3 消融链路法

输入：prompt 模块列表、验证样例。

方法：按模块逐步删除或恢复，比较每一步的 score / loss 变化。

```text
完整 prompt             -> score 0.95
删除最后一段示例         -> score 0.82
再删除格式约束           -> score 0.79
再删除角色定义           -> score 0.60
```

输出：每个模块的边际贡献。

适用场景：判断示例、格式约束、角色定义、失败记忆等模块是否真的有效。

风险：模块之间有交互，单独贡献不等于联合贡献。

### 3.4 LLM 自我诊断法

输入：当前 prompt、成功案例、失败案例、失败类型统计。

方法：让 LLM 只做诊断，判断可能是哪部分 prompt 导致失败，并给出可读的文本梯度方向。

输出：可读诊断，例如“边界规则过宽，导致普通名词被多标”。

适用场景：把失败样例转成候选改写方向，尤其适合边界模糊和负例不足。

风险：LLM 诊断不能直接相信，必须由 gold loss 验证；诊断解释也不能拼入最终 prompt。

## 4. 优化器

文本梯度估算之后，需要一个 prompt 优化器决定如何更新参数。

| 优化器 | Prompt-as-Parameter 实现 |
| --- | --- |
| SGD | 每轮只选梯度最大的一个片段改写一次 |
| Momentum | 记录历史有效方向，连续指向同一问题时加大改写力度 |
| Adam | 高频波动片段小步更新，低频但稳定有效片段大步更新 |
| AdamW | Adam + prompt 长度惩罚，禁止靠堆字数降低 loss |
| CMA-ES | 把 prompt 片段视为基因位，多维随机变异并保留优胜种群 |
| 模拟退火 | 前期允许大改动探索，后期逐步收敛到小改动精修 |

Rosetta 文档默认推荐 `LLM-AdamW` 作为 v1 概念优化器叙事：

1. 使用历史梯度方向，避免每轮随机漂移。
2. 对不稳定片段小步更新，对稳定有效方向加大权重。
3. 对 prompt 长度做 weight decay，防止概念阐释无限变长。
4. 每个候选都必须通过 gold loss validation 才能被接受。

`CMA-ES` 和模拟退火适合作为实验分支，不作为第一版默认实现。`SGD` 适合作为最小 baseline。

## 5. Rosetta 默认循环

```text
initial_prompt
  -> split ConceptPromptSpec from Frozen OutputProtocolSpec
  -> segment optimizable concept parameters
  -> evaluate current gold loss
  -> estimate text gradients
  -> optimizer proposes concept-only candidate prompts
  -> harness injects frozen output protocol
  -> strict parse / format repair / semantic evaluation
  -> evaluate candidates on the same gold examples
  -> accept only loss-decreasing clean prompt
  -> write PromptOptimizationTrace
```

伪代码：

```text
prompt = initial_prompt
best_prompt = prompt
best_loss = evaluate(prompt)

for step in range(max_steps):
    concept_spec, output_protocol = split_harness(prompt)
    segments = segment(concept_spec)
    gradients = estimate_text_gradients(prompt, segments)
    candidates = optimizer_step(concept_spec, gradients, method="LLM-AdamW")
    scored = [(candidate, evaluate(candidate, output_protocol)) for candidate in candidates]
    selected, selected_loss = min(scored, key=lambda item: item[1])

    if selected_loss < best_loss:
        prompt = selected
        best_prompt = selected
        best_loss = selected_loss
    else:
        stop_or_decay_learning_rate()
```

关键约束：

1. 失败样例、样例编号、漏标、多标和诊断解释只进入 trace，不进入最终 prompt。
2. 优化器可以探索多个方向，但最终版本必须是干净可用的概念阐释。
3. Prompt 修改必须有 loss delta 和长度变化记录。
4. 训练反馈可以包含原文、标准答案和模型答案，但这些内容必须标记为 `training_feedback_only=true`，只供优化模型学习错误类型。
5. learned operational prompt 不能复制语料中的具体词、答案片段或模型错答片段；Rosetta 用 `MemorizationGuard` 对候选和最终版本做 hash 指纹检查，泄露候选先进入 `repair_leaked_prompt()` 去语料化修复，修复失败才拒绝。
6. 输出格式不是训练目标。格式稳定性由 `Frozen OutputProtocolSpec`、strict parser 和 format repair loop 保证，不能靠 optimizer 在概念提示词中反复堆格式说明。
7. 如果候选提示词带回标签集合、JSON schema、annotation 格式或输出格式，系统应剥离这些冻结协议字段并记录 warning；后续报告还需要聚合 `protocol_tampering_count`。

## 6. 实验可证伪点

Prompt-as-Parameter 必须通过实验被证明，而不能只作为漂亮类比。

需要比较：

1. `llm_optimize_only`: 只告诉大模型优化当前 `ConceptPromptSpec`，不给失败细节、loss、文本梯度或冻结输出协议，是最简单 baseline。
2. `llm_reflection`: 告诉大模型哪里出了问题，让它自己改写整体概念阐释，但候选仍只能包含概念定义、边界规则和可选高级负例约束。
3. `text_gradient_adamw`: 使用文本梯度、长度惩罚和 gold loss 验证，是 Rosetta 当前默认方法；冻结输出协议只在评估时由 harness 注入。
4. `mask_gradient_only`: 只用 Mask 遮挡估算重要性。
5. `ablation_gradient_only`: 只用消融链路估算模块贡献。
6. `cma_es_prompt_search`: 多片段随机变异搜索。

核心指标：

1. 每轮 gold loss delta。
2. accepted candidate rate。
3. 无效改写率。
4. Prompt 长度增长率。
5. gradient-method agreement。
6. 最终 span-F1 / boundary-F1。
7. 人工审核量变化。
8. memorization blocked candidate rate。
9. final prompt clean rate。
10. format failure rate。
11. format repair success rate。

如果文本梯度估算不能稳定优于随机改写和普通 LLM 反思，这个方法就不能作为核心论文贡献。

当前 `v4.5.0` 的测试结论边界必须写清楚：只在 15 条 gold 上验证“最终提示词未直接背答案且训练集通过”，不能据此证明跨语料泛化。论文级实验需要增加 held-out 集、跨领域任务和人工审核收益分析。

## 7. 未来代码接口草案

以下是概念接口。`v4.3.0` 已实现其中的最小版本：`PromptSegment`、`TextGradient`、`PromptOptimizationTrace`、`segment_prompt()`、`estimate_text_gradients()`、`build_llm_adamw_trace()`、`length_penalized_loss()` 和 `finalize_candidate_trace()`。`v4.4.0` 新增 `PromptTrainingConfig`、`PromptTrainingResult` 和 `run_prompt_training_experiment()`，用于在同一批 15 条金样例上比较多个优化方法，并把完整训练轨迹写入 artifact。`v4.4.1` 新增 `MemorizationGuard`、`CorpusFingerprint` 和 `LeakageCheckResult`，用于保证训练反馈可见但最终 operational prompt 不背答案。`v4.5.0` 新增 `LLMServiceRuntime` 和 `repair_leaked_prompt()`，让真实 provider 并发调用、token 统计和去语料化修复成为训练电路的一部分。尚未实现的是跨轮 optimizer state、真实 Mask 重跑、对比替换和消融链路。

```text
ConceptPromptSpec
  fields: concept_definition, boundary_rules, negative_rules,
          failure_memory_abstraction

FrozenOutputProtocolSpec
  fields: labels, json_schema, annotation_markup,
          parser_contract, format_repair_instructions

PromptSegmenter
  input: ConceptPromptSpec
  output: PromptSegment[]

TextGradientEstimator
  input: prompt, segments, gold_examples, evaluation_fn
  output: TextGradient[]

PromptOptimizer
  input: prompt, gradients, optimizer_state
  output: PromptCandidate[]

CandidateGenerator
  input: prompt, target_segments, gradient_directions
  output: clean concept-only candidate prompts

AnnotationHarness
  input: ConceptPromptSpec, FrozenOutputProtocolSpec, text
  output: parsed annotation or format_failed result

PromptOptimizationTrace
  records: segment_id, perturbation_method, loss_delta,
           candidate_id, accepted, length_delta, diagnostics

MemorizationGuard
  input: candidate_prompt, gold_texts, gold_spans, model_spans
  output: passed, blocked_hash_count, matched_hashes
```

这些接口应优先进入 `app/workflows/bootstrap`，必要时把可复用的优化器状态和工具注册到 `app/agents`。页面只负责展示当前 loss、文本梯度方向、候选评估和最终干净 prompt。
