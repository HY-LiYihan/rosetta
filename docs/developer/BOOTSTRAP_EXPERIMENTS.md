# Bootstrap Experiments (Developer)

更新时间: 2026-05-05

## 1. 目标

本文件定义 Concept Bootstrap Pipeline 的实验入口。当前优先使用 ACTER 风格的术语抽取任务，因为它同时覆盖 domain-specific terms、common terms、out-of-domain terms 和 named entities，适合测试低资源概念校准。

实验目标不是单纯证明“LLM 输出更好”，而是证明 Rosetta 的 agentic loop 在低资源和任务快速定义时，相比 PLM-first 流程具有样本效率、审核效率和可追溯优势。

## 2. 首个实验入口

示例配置位于：

```text
configs/research/bootstrap/
  acter_heart_failure.experiment.json
  acter_heart_failure.samples.example.jsonl
  acter_heart_failure.candidates.example.jsonl
```

运行离线分析：

```bash
python scripts/research/run_bootstrap.py analyze \
  --samples configs/research/bootstrap/acter_heart_failure.samples.example.jsonl \
  --candidates configs/research/bootstrap/acter_heart_failure.candidates.example.jsonl \
  --experiment configs/research/bootstrap/acter_heart_failure.experiment.json \
  --run-name acter-heart-failure
```

## 3. 推荐真实实验设计

### 3.1 常规高质量数据集

1. 从 ACTER English heart failure 子集开始。
2. 先抽 15 个金样例，要求覆盖 `Specific_Term / Common_Term / OOD_Term / Named_Entity`。
3. 继续扩展 50 / 100 gold 设置，用于 low-budget PLM 对比。
4. 对未标注样本运行 DeepSeek、Kimi 和 BigModel 平台中的可用模型。
5. 每条样本生成 5 次候选，至少测试 `temperature=0.3` 和 `temperature=0.7`。
6. 用 bootstrap runner 生成自洽性分数与专家复核队列。
7. 专家优先处理 `low`，再处理 `medium`，并抽检少量 `high`。

### 3.2 非常规可定义任务

至少设计一个没有现成大规模训练集、但可以被清晰定义的任务，例如：

1. 英文硬科学科普新闻中的科学概念和技术名词。
2. 论文方法段中的实验对象、材料、仪器和物理过程。
3. 历史语料中的隐含评价表达。
4. 语言学论文中的理论概念、证据类型和反例。

该组实验重点展示：传统 PLM 需要先有标签体系和训练集，而 Rosetta 可以从概念阐释与 15 条金样例启动，并把失败样例转化为后续提示策略。

### 3.3 ACTER en/corp 100 正例提示词训练

`v4.5.5` 文档契约新增一个更强的 prompt training 测试入口：ACTER `en/corp` 反腐败术语抽取。

本地数据源：

```text
/Users/liyh/rosetta/tmp/acter_en_corp/gold_examples_first100_markup.jsonl
```

任务口径：

1. 任务名：`ACTER 反腐败术语抽取`。
2. 数据集：`ACTER v1.5` 的 `en/corp` 子集。
3. 任务类型：terminology extraction，不是普通 NER。
4. 标签：`Term`。
5. 样例：100 条 positive-only gold sentences。
6. 模型：DeepSeek `deepseek-v4-flash`。
7. 目标：`100/100` 通过。
8. 停止条件：达到 `100/100`，或连续 5 轮 loss 没有下降，或达到 `max_rounds=30`。

第一阶段先跑 `llm_optimize_only`，用于回答一个最弱 baseline 问题：只告诉大模型“请优化当前概念提示词”，不给失败详情、gold answer、模型答案、loss 或文本梯度，它能不能仅靠自我改写提高 100 条正例上的通过数。

该实验必须使用冻结输出协议：

```text
ConceptPromptSpec
  -> 只包含概念定义、边界规则、排除规则
Frozen OutputProtocolSpec
  -> JSON schema, label=Term, annotation=[span]{Term}, format repair
```

`llm_optimize_only` 的优化模型只看到 `ConceptPromptSpec`，不看到 `Frozen OutputProtocolSpec` 的可编辑版本。标注模型实际执行时，由 harness 注入冻结协议并强制返回 JSON+markup。

每轮报告必须包含：

1. 当前 accepted prompt 的版本号和长度。
2. 本轮候选数、被接受候选、拒绝原因。
3. `pass_count / 100`。
4. semantic loss 与 loss delta。
5. format failure count。
6. format repair attempt count 与 repair success count。
7. token、耗时、并发上限和真实模型。
8. 是否触发防背答案或去语料化修复。

限制必须写在报告开头：100 条 positive-only 只能测试正例术语召回、边界稳定性和格式稳定性，不能证明模型不会在负例中过度标注。后续正式实验必须加入 negative sentences 或 held-out split。

## 4. Baselines

必须至少比较：

1. `zero_shot_definition_only`
2. `fixed_15_shot_icl`
3. `similarity_only_retrieval`
4. `majority_vote_self_consistency`
5. `allabel_style_uncertainty_sampling`
6. `deer_style_label_guided_retrieval`
7. `plm_15_gold_finetune`
8. `plm_50_gold_finetune`
9. `plm_100_gold_finetune`
10. `plm_full_data_finetune`
11. `llm_optimize_only`
12. `llm_reflection`
13. `text_gradient_adamw`
14. `mask_gradient_only`
15. `ablation_gradient_only`
16. `cma_es_prompt_search`

解释口径：

1. `plm_full_data_finetune` 是强上界和部署成本对照，不是 Rosetta 必须全面超过的唯一目标。
2. `plm_15/50/100_gold_finetune` 才是低预算主比较对象。
3. Rosetta 的 ablation 必须显示概念自举、对比式检索、自洽性路由和主动审核各自带来的收益。
4. Prompt-as-Parameter 的贡献必须通过 ablation 证明：文本梯度估算应优于“只告诉大模型优化提示词”、普通 LLM 反思和简单候选搜索。

## 5. 指标

核心指标：

1. span precision / recall / F1
2. boundary exact match
3. label exact match
4. expert review rate
5. candidate accept rate
6. manual rewrite rate
7. high-confidence audit error rate
8. concept refinement rounds
9. gold loss curve
10. model call cost
11. review minutes per accepted sample
12. PLM retraining cost under label definition change
13. per-round loss delta
14. invalid rewrite rate
15. prompt length growth
16. accepted candidate rate
17. gradient-method agreement
18. format failure rate
19. format repair success rate
20. positive-only pass count

## 6. 参考数据集

1. ACTER: term extraction and entity-style span annotation.
2. NCBI-disease: biomedical NER.
3. BC2GM: biomedical gene/protein NER.
4. CoNLL03: general-domain NER.

后续实验应先把这些数据集转换为 Rosetta Prodigy-compatible JSONL，而不是改变内部格式。span 放在顶层 `spans` 中，关系放在顶层 `relations` 中，句子级 / 段落级 / 文章级分类使用 `label / options / accept / answer / meta`。

## 7. 最小报告结构

每个实验报告至少包含：

1. 任务定义和概念阐释初版。
2. 15 条金样例选择策略。
3. 每轮概念版本、loss、失败样例和被接受候选。
4. 批量标注的 k 次候选、一致性分布和路由结果。
5. 人工审核样本数、选择候选比例、编辑比例和 hard examples 数。
6. 与 PLM baselines 的 F1 / 人工预算 / 成本对比。
7. 典型成功样例和失败样例。
8. Prompt-as-Parameter ablation，说明 Mask 遮挡、对比替换、消融链路、LLM 自诊断和 `LLM-AdamW` 是否真实降低 loss。
9. 格式错误与语义错误拆分：`format_failed` 不能和漏标、多标、边界错误混在同一个 loss 解释里。
10. 冻结输出协议说明：明确 prompt optimizer 没有编辑 JSON schema、标签集合、markup 格式或 repair 指令。

论文表述约束：不能只展示最终 F1，就声称文本梯度有效。必须报告每轮 loss delta、候选接受率、无效改写率和 prompt 长度增长，证明优化器不是靠堆叠规则偶然变好。
