# Research Claims: LLM Agent vs PLM Annotation

更新时间: 2026-05-02

## 1. 一句话主张

Rosetta 要证明的不是“LLM 在所有条件下都比 PLM 强”，而是：

```text
当标注任务可以被清晰描述、样例预算很低、概念边界会变化或任务不够常规时，
LLM agent 能通过概念自举、上下文检索、自洽性评估和主动审核，
比传统 PLM 标注流程更快形成可复现、可审计、可扩展的数据生产能力。
```

这条主张比“调用大模型自动标注”更强，也更可验证。Rosetta 的核心对象不是单次模型输出，而是一个会记录概念版本、失败样例、候选分歧、人类选择和导出报告的 agentic annotation loop。

## 2. 最需要证明的三件事

1. **低资源样本效率**：在只有一句话概念描述和 15 条金样例时，Rosetta 能比 zero-shot、普通 few-shot ICL、只检索相似样例、以及低预算 PLM fine-tuning 更快达到可用 F1。
2. **非标准任务适应性**：当任务不是成熟 NER 标签集，而是“可清晰定义但没有现成大数据集”的概念标注时，Rosetta 能把概念描述逐步操作化，并把失败模式沉淀为可复用边界规则。
3. **可审计主动学习收益**：Rosetta 能把人类专家时间集中到低自洽、低置信、规则失败和 hard examples 上，并证明选择题式审核比从零标注更省人工。

## 3. 与 PLM 的关系

PLM 在 Rosetta 中不是反面教材，而是必须认真比较的基线。

### 3.1 PLM 擅长什么

1. 有足够高质量训练集时，PLM 可以低成本稳定推理。
2. 标签体系固定、领域稳定、标注边界清楚时，PLM fine-tuning 很强。
3. 大规模部署时，PLM 的单位推理成本和延迟通常更好。

### 3.2 Rosetta 要赢在哪里

1. 数据很少时，不需要先训练一个任务专用模型。
2. 概念还在迭代时，不需要反复重训，只需要更新概念版本和上下文策略。
3. 非常规任务出现时，用户可以先用自然语言定义，再通过 15 条金样例校准。
4. 每一次失败、候选冲突和人工修正都会变成后续 agent 的上下文资产。

### 3.3 不能夸大的地方

Rosetta 不应声称在完整高质量训练集条件下必然超过最优 PLM。更稳妥的论文表述是：

```text
Rosetta 在低资源、快速定义、概念漂移和人机协作标注场景中，
比传统 PLM-first 流程更具样本效率、可解释性和迭代速度；
在常规高质量数据集上，它应至少提供有竞争力的低预算表现和更好的审核记录。
```

## 4. 创新点

1. **Concept-to-Annotation**：从概念描述出发，而不是从大规模已标注数据出发。
2. **15 Gold Calibration**：15 条金样例不是普通 few-shot，而是测试概念定义能否独立执行的校准锚点。
3. **Loss-guided Concept Refinement**：概念修订像优化函数一样有内部 loss，只接受让 gold loss 下降的候选概念。
4. **Contrastive Context Pack**：每次标注同时使用相似样例、边界远例、高置信伪标注和失败模式摘要。
5. **Self-consistency Routing**：用多次采样、span-level F1、模型自评和规则风险把样本路由到自动通过、轻量复核或专家优先队列。
6. **Choice-first Human Review**：人类专家优先做候选选择和轻量编辑，而不是从零开放式标注。
7. **Runtime / Storage Decoupling**：模型运行时使用 `[span]{label}`，长期存储使用 Prodigy-compatible JSONL。
8. **Traceable Agent Loop**：概念版本、候选分歧、失败摘要、人工选择和导出报告可回放。

## 5. 实验分组

### 5.1 常规高质量数据集

目标是证明 Rosetta 在已有成熟数据集上具有低预算竞争力和可审计性。

推荐任务：

1. ACTER term extraction。
2. NCBI-disease biomedical NER。
3. BC2GM gene/protein NER。
4. CoNLL03 general NER。

比较设置：

1. Full-data PLM fine-tuning：作为强上界，不要求 Rosetta 必须超过。
2. 15 / 50 / 100 gold PLM fine-tuning：低预算 PLM 主基线。
3. LLM zero-shot definition。
4. LLM 15-shot ICL。
5. LLM retrieval-only。
6. Rosetta full loop。

### 5.2 非常规但可定义任务

目标是展示 Rosetta 的 agent 能力。任务可以来自研究者的一句话定义和少量样例，例如：

1. 硬科学科普新闻中的跨领域科学术语。
2. 论文方法段中的实验操作、材料和测量过程。
3. 历史语料中的隐含评价表达。
4. 语言学论文中的理论概念、证据类型和反例。

比较设置：

1. 只用概念描述。
2. 固定 15-shot ICL。
3. 只检索相似样例。
4. Rosetta 去掉概念自举。
5. Rosetta 去掉边界远例。
6. Rosetta 去掉主动审核。
7. Rosetta full loop。

## 6. 指标

### 6.1 标注质量

1. Span precision / recall / F1。
2. Boundary exact match。
3. Label exact match。
4. Relation F1，如果任务包含关系。
5. Sentence / paragraph / document classification accuracy 或 macro-F1。

### 6.2 人工效率

1. 每得到 1000 条可用标注需要多少人工审核条目。
2. 专家选择候选即可通过比例。
3. 轻量编辑比例。
4. 完全重写比例。
5. 高置信自动通过样本抽检错误率。

### 6.3 Agent 过程质量

1. 概念自举轮数。
2. 每轮 gold loss。
3. 被拒绝候选概念数量。
4. 低自洽样本比例。
5. hard examples 对下一轮 F1 的贡献。
6. 模型调用成本和平均延迟。

## 7. 最小可发表证据链

一篇论文或实验报告至少要包含：

1. 一个常规高质量数据集，用于证明 Rosetta 不是只会做玩具任务。
2. 一个非常规可定义任务，用于证明 agentic concept bootstrapping 的真实价值。
3. PLM low-budget 与 full-data 两组对照。
4. Rosetta full loop 与关键 ablation。
5. 人工审核收益曲线。
6. 每轮概念版本和 loss 曲线。
7. 典型 hard examples 分析。

## 8. 对实现的要求

后续程序更新必须能把上面的证据链落盘：

1. `ConceptVersion.metadata` 记录每轮 loss、失败样例和候选评估。
2. `Prediction.meta` 记录上下文样例、采样序号、规则风险和分歧类型。
3. `ReviewTask.meta` 记录人工选择、错误类型、hard example 和 promote-to-gold。
4. 导出报告必须能按项目、运行批次、概念版本和审核状态聚合。
5. 统一 CLI 必须能复现实验，不只能依赖页面点击。
