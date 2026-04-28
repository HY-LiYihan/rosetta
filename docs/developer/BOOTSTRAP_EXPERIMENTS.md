# Bootstrap Experiments (Developer)

更新时间: 2026-04-28

## 1. 目标

本文件定义 Concept Bootstrap Pipeline 的实验入口。当前优先使用 ACTER 风格的术语抽取任务，因为它同时覆盖 domain-specific terms、common terms、out-of-domain terms 和 named entities，适合测试低资源概念校准。

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

1. 从 ACTER English heart failure 子集开始。
2. 先抽 15 个金样例，要求覆盖 `Specific_Term / Common_Term / OOD_Term / Named_Entity`。
3. 对未标注样本运行 Kimi 和 BigModel 两个平台。
4. 每条样本生成 5 次候选，至少测试 `temperature=0.3` 和 `temperature=0.7`。
5. 用 bootstrap runner 生成自洽性分数与专家复核队列。
6. 专家优先处理 `low`，再处理 `medium`，并抽检少量 `high`。

## 4. Baselines

必须至少比较：

1. `zero_shot_definition_only`
2. `fixed_15_shot_icl`
3. `similarity_only_retrieval`
4. `majority_vote_self_consistency`
5. `allabel_style_uncertainty_sampling`
6. `deer_style_label_guided_retrieval`

## 5. 指标

核心指标：

1. span precision / recall / F1
2. boundary exact match
3. label exact match
4. expert review rate
5. candidate accept rate
6. manual rewrite rate
7. high-confidence audit error rate

## 6. 参考数据集

1. ACTER: term extraction and entity-style span annotation.
2. NCBI-disease: biomedical NER.
3. BC2GM: biomedical gene/protein NER.
4. CoNLL03: general-domain NER.

后续实验应先把这些数据集转换为 Rosetta Prodigy-compatible JSONL，而不是改变内部格式。span 放在顶层 `spans` 中，关系放在顶层 `relations` 中，句子级 / 段落级 / 文章级分类使用 `label / options / accept / answer / meta`。
