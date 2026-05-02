# Bootstrap Experiments (Developer)

更新时间: 2026-05-02

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

解释口径：

1. `plm_full_data_finetune` 是强上界和部署成本对照，不是 Rosetta 必须全面超过的唯一目标。
2. `plm_15/50/100_gold_finetune` 才是低预算主比较对象。
3. Rosetta 的 ablation 必须显示概念自举、对比式检索、自洽性路由和主动审核各自带来的收益。

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
