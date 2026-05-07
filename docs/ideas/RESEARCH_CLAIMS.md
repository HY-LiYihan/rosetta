# Research Claims: LLM Agent vs PLM Annotation

更新时间: 2026-05-07

## 1. 一句话主张

Rosetta 当前要检验的不是“LLM 在所有条件下都比 PLM 强”，而是：

```text
当标注任务可以被清晰描述、样例预算很低、概念边界会变化或任务不够常规时，
LLM agent 是否能通过定义优化、上下文检索、自洽性评估和主动审核，
比传统 PLM 标注流程更快形成可复现、可审计的数据生产流程。
```

这条主张比“调用大模型自动标注”更强，也更可验证。Rosetta 的核心对象不是单次模型输出，而是一个会记录概念版本、失败样例、候选分歧、人类选择和导出报告的 agentic annotation loop。

## 2. 当前证据与待验证假设

| 层级 | 当前状态 | 可以怎样表述 |
| --- | --- | --- |
| 已有工程证据 | 已有 15 条 gold 内的 prompt training、去语料化检查、运行 trace 和报告产物 | “当前能记录 15 gold 内的训练表现和可审计过程” |
| 待验证实验假设 | 需要 held-out、跨任务或多 seed 对照，才能判断 Rosetta 是否优于 low-budget PLM / ICL / retrieval-only | “实验将检验 Rosetta 是否带来样本效率、审核效率和成本优势” |
| 论文级结论 | 需要明确数据集、split、主指标、baseline 预算、置信区间和失败分析 | 不能只凭 15 gold 内训练表现宣称泛化优势 |

文档中提到“更快”“更稳”“优于”时，都应绑定具体实验设置、数据划分和指标。没有 held-out 或外部数据集时，只能说“当前 gold 内表现”。

## 3. 最需要检验的四件事

1. **低资源样本效率**：在只有一句话概念描述和 15 条金样例时，Rosetta 能比 zero-shot、普通 few-shot ICL、只检索相似样例、以及低预算 PLM fine-tuning 更快达到可用 F1。
2. **非标准任务适应性**：当任务不是成熟 NER 标签集，而是“可清晰定义但没有现成大数据集”的概念标注时，Rosetta 能把概念描述逐步操作化，并把失败模式沉淀为可复用边界规则。
3. **Prompt-as-Parameter 优化**：Rosetta 能把自然语言 prompt 当作可训练参数，在无解析梯度条件下估算 Text Gradient，并用优化器更新概念阐释。
4. **可审计主动学习收益**：Rosetta 能把人类专家时间集中到低自洽、低置信、规则失败和 hard examples 上，并证明选择题式审核比从零标注更省人工。

## 4. 与 PLM 的关系

PLM 在 Rosetta 中不是反面教材，而是必须认真比较的基线。

这里的 **PLM-first** 指先围绕固定标签体系积累训练/开发数据，再 fine-tune 任务专用 PLM 的流程。实验中必须同时比较 full-data PLM 强上界和 15 / 50 / 100 gold 的 low-budget PLM，而不是让比较对象在不同段落中漂移。

### 4.1 PLM 擅长什么

1. 有足够高质量训练集时，PLM 可以低成本稳定推理。
2. 标签体系固定、领域稳定、标注边界清楚时，PLM fine-tuning 很强。
3. 大规模部署时，PLM 的单位推理成本和延迟通常更好。

### 4.2 Rosetta 要检验哪里可能有优势

1. 数据很少时，不需要先训练一个任务专用模型。
2. 概念还在迭代时，不需要反复重训，只需要更新概念版本和上下文策略。
3. 非常规任务出现时，用户可以先用自然语言定义，再通过 15 条金样例校准。
4. 每一次失败、候选冲突和人工修正都会变成后续 agent 的上下文资产。

### 4.3 不能夸大的地方

Rosetta 不应声称在完整高质量训练集条件下必然超过最优 PLM。更稳妥的论文表述是：

```text
Rosetta 在低资源、快速定义、概念漂移和人机协作标注场景中，
比传统 PLM-first 流程更具样本效率、可解释性和迭代速度；
在常规高质量数据集上，它应至少提供有竞争力的低预算表现和更好的审核记录。
```

## 5. 创新点

1. **Concept-to-Annotation**：从概念描述出发，而不是从大规模已标注数据出发。
2. **15 Gold Calibration**：15 条金样例不是普通 few-shot，而是测试概念定义能否独立执行的验证锚点；它不应同时被当作 few-shot 答案、训练集和最终泛化评测集。
3. **Prompt-as-Parameter Optimization**：概念阐释不是静态 prompt，而是由角色、任务定义、边界规则、负例规则、输出格式、示例和失败记忆组成的可训练文本参数。
4. **Text Gradient Estimation**：用 Mask 遮挡、对比替换、消融链路和 LLM 自诊断估算 prompt 片段对 gold loss 的方向性影响。
5. **Loss-guided Concept Refinement**：概念修订像优化函数一样有内部 loss，只接受让 gold loss 下降的候选概念。
6. **Contrastive Context Pack**：每次标注同时使用相似样例、边界远例、高置信伪标注和失败模式摘要。
7. **Self-consistency Routing**：用多次采样、span-level F1、模型自评和规则风险把样本路由到自动通过、轻量复核或专家优先队列。
8. **Choice-first Human Review**：人类专家优先做候选选择和轻量编辑，而不是从零开放式标注。
9. **Runtime / Storage Decoupling**：模型运行时使用 `[span]{label}`，长期存储使用 Prodigy-compatible JSONL。
10. **Traceable Agent Loop**：概念版本、候选分歧、失败摘要、人工选择和导出报告可回放。

## 6. 实验分组

### 6.1 常规高质量数据集

目标是检验 Rosetta 在已有成熟数据集上是否具有低预算竞争力和可审计性。

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

### 6.2 非常规但可定义任务

目标是检验 Rosetta 的 agent 能力。任务可以来自研究者的一句话定义和少量样例，例如：

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
7. Rosetta 去掉文本梯度估算，只用普通 LLM 反思改写。
8. Rosetta full loop。

## 7. 指标

### 7.1 主指标

1. Span precision / recall / F1。
2. Boundary exact match 或 boundary-F1。
3. Review minutes per accepted sample。
4. Cost per accepted sample。

### 7.2 标注质量扩展指标

1. Label exact match。
2. Relation F1，如果任务包含关系。
3. Sentence / paragraph / document classification accuracy 或 macro-F1。

### 7.3 人工效率

1. 每得到 1000 条可用标注需要多少人工审核条目。
2. 专家选择候选即可通过比例。
3. 轻量编辑比例。
4. 完全重写比例。
5. 高置信自动通过样本抽检错误率。

### 7.4 Agent 过程质量

1. 概念自举轮数。
2. 每轮 gold loss。
3. 被拒绝候选概念数量。
4. 低自洽样本比例。
5. hard examples 对下一轮 F1 的贡献。
6. 模型调用成本和平均延迟。
7. 文本梯度方法之间的一致度。
8. Prompt 长度增长率。
9. 无效改写率。

## 8. 最小可发表证据链

一篇论文或实验报告至少要包含：

1. 一个常规高质量数据集，用于检验 Rosetta 是否能迁移到成熟数据集，而不是只停留在玩具任务。
2. 一个非常规可定义任务，用于检验 agentic 定义优化的真实价值。
3. PLM low-budget 与 full-data 两组对照。
4. Rosetta full loop 与关键 ablation。
5. Prompt-as-Parameter ablation，检验文本梯度估算是否优于随机改写和普通 LLM 反思。
6. 人工审核收益曲线。
7. 每轮概念版本和 loss 曲线。
8. 典型 hard examples 分析。

## 9. 对实现的要求

后续程序更新必须能把上面的证据链落盘：

1. `ConceptVersion.metadata` 记录每轮 loss、失败样例和候选评估。
2. `Prediction.meta` 记录上下文样例、采样序号、规则风险和分歧类型。
3. `ReviewTask.meta` 记录人工选择、错误类型、hard example 和 promote-to-gold。
4. 导出报告必须能按项目、运行批次、概念版本和审核状态聚合。
5. 统一 CLI 必须能复现实验，不只能依赖页面点击。
6. 下一阶段 `PromptOptimizationTrace` 必须记录被扰动片段、梯度估算方法、loss delta、候选是否接受和 prompt 长度变化。
