# Core Idea: Concept-Driven Annotation Bootstrap

更新时间: 2026-05-02

## 1. 这份文档的作用

这份文档记录 Rosetta 当前最核心的科研想法。它不是普通功能清单，而是后续实现、实验设计、论文写作和 UI 取舍都必须优先遵守的中心假设。

核心目标是：让使用者用极少的人工输入，把一个模糊概念逐步压缩成可复现、可扩展、可审计的标注流水线。

更具体地说，Rosetta 要把 LLM 的 agent 能力用于标注任务本身：模型不是只输出标签，而是参与概念校准、上下文选择、自洽性比较、失败反思和人类审核路由。它要证明的主张见 [Research Claims](./RESEARCH_CLAIMS.md)。

这条主线的下一层方法是 [Prompt-as-Parameter](./PROMPT_AS_PARAMETER.md)：概念阐释不是静态 prompt，而是一组可训练的文本参数。由于自然语言 prompt 没有解析梯度，Rosetta 需要通过 Mask 遮挡、对比替换、消融链路和 LLM 自诊断估算 Text Gradient，再用类似 AdamW 的优化器生成候选概念版本，并用 gold loss 验证是否接受。

## 1.1 本项目的研究判断

Rosetta 的核心判断是：LLM agent 在低资源、概念可描述、任务边界会变化或任务不够常规的标注场景中，应该强于传统 PLM-first 流程。

这里的“强于”不是指完整高质量训练集条件下无条件超过 PLM，而是指：

1. 用更少人工 gold 更快启动任务。
2. 能处理没有成熟标签体系的可定义概念。
3. 能把失败样例、候选分歧和人工审核转化为下一轮标注资产。
4. 能保留比普通模型预测更完整的过程证据。

因此，Rosetta 的实验必须同时覆盖两类场景：

1. 已有高质量数据集的常规任务，用来证明低预算竞争力和可审计性。
2. 不常规但可以清晰定义的任务，用来展示 agentic concept bootstrapping 的优势。

这条边界很重要。Rosetta 不应该把论文主张写成“大模型全面替代 PLM”，而应该写成“LLM agent 让概念驱动标注在低资源和任务快速变化时成为可执行范式”。

## 2. 最核心的用户场景

第一次使用系统时，用户不需要先准备一个大规模标注集。用户只需要提供：

1. 一句话概念描述。
2. 15 个金样例。

这里的 15 个金样例不是普通 few-shot 示例，而是用于校准概念定义的最小人工锚点。系统首先不依赖复杂示例检索，而是让模型只根据概念描述尝试标注这 15 个样例。

如果某些样例标注失败，这些失败样例会被单独提出，用来反向优化概念描述。更准确地说，失败样例不会被直接拼进 prompt，而是被系统转化为文本梯度信号：哪些片段导致漏标，哪些规则导致多标，哪些边界描述需要收紧或放宽。这个过程反复执行：

```text
一句话概念描述
  -> 标注 15 个金样例
  -> 找出失败样例
  -> prompt 参数切分
  -> 文本梯度估算
  -> 优化器生成候选概念
  -> gold loss 验证
  -> 接受变好的干净概念描述
  -> 再次标注 15 个金样例
  -> 直到 15 个金样例全部通过
```

当 15 个金样例在仅使用概念描述的情况下都能被模型正确标注时，我们认为获得了两个关键资产：

1. 一个稳定、可操作化的概念描述。
2. 一组经过该概念描述验证的金样例。

这一步的本质不是“把 prompt 写好看”，而是把用户心中的概念压缩成模型可执行的操作化定义。

## 3. 大规模标注阶段

有了稳定概念描述和 15 个金样例后，系统进入大规模语料标注阶段。这个阶段可以分为无监督和半监督两种模式。

### 3.1 无监督模式

对每条待标注语料重复运行多次，例如 5 次。系统比较 5 次结果的一致性：

1. 如果 5 次结果高度一致，则认为该样本自洽性高，暂时作为高置信伪标注。
2. 如果 5 次结果差异较大，则认为该样本自洽性低，进入疑难样本池。

自洽性低的样本不能直接丢弃，也不能直接相信单次输出。系统需要调用更强的判断流程：

1. 对疑难样本做语义检索。
2. 找到最相似的金样例或高置信样例。
3. 找到少量不相似但具有边界意义的反例或远例。
4. 让大模型结合概念描述、相似样例、边界样例和多次候选标注，产出一个临时标准答案。
5. 将疑难样本和判定理由用于下一轮概念描述或提示策略调整。

这里的核心不是简单 majority vote，而是把低自洽样本转化为 hard examples，用它们暴露概念描述中的边界问题。

### 3.2 半监督模式

如果用户已有部分人工标注，则人工标注优先作为 gold data。系统仍然可以对未标注数据做 5 次自洽性估计，但在疑难样本判断时需要优先检索人工 gold，其次才使用高置信伪标注。

半监督模式的目标是用少量人工标注稳定概念边界，再用高置信伪标注扩展覆盖面。

### 3.3 人类专家批改模式

自洽性和模型自评都不应该只作为自动过滤信号，还应该决定样本进入人类视野的频率。核心原则是：模型越不确定，越应该让人类专家优先看到；模型越确定，人类只需要低比例抽检。

推荐把每条样本分成三类：

1. 高置信样本：多次输出高度一致，模型自评高，规则验证通过。进入伪标注池，只做少量抽检。
2. 中置信样本：多次输出大体一致，但边界、标签或解释存在小差异。进入轻量复核队列。
3. 低置信样本：多次输出互相冲突，或模型自评低，或规则验证失败。进入专家优先批改队列。

低置信样本给人类专家时，不应要求专家从零开始写答案。更好的交互是把多次模型输出做成“选择题”：

```text
原文: ...
候选 A: 第 1 次模型标注
候选 B: 第 2 次模型标注
候选 C: 第 3 次模型标注
候选 D: 第 4 次模型标注
候选 E: 第 5 次模型标注
候选 F: 以上都不对，我要手动修正
```

专家只需要选择最接近正确答案的候选，必要时做少量编辑。这比让专家直接做开放式标注更省力，也能保留模型候选之间的分歧信息。

这个环节的关键产物不是单条 gold label，而是：

1. 人类选择了哪个候选。
2. 被拒绝候选错在哪里。
3. 当前概念描述是否导致了系统性误解。
4. 这个样本是否应该进入 hard example bank。

因此，人类专家批改队列本质上是 active learning 的交互界面：低置信样本被更多次推给人类，高置信样本只做抽样质检。

## 4. 每次标注时的上下文组织

每次实际标注不应只靠“最相似样例”。最终 prompt 应优先包含：

1. 概念描述：始终是最高优先级。
2. 高置信样例：来自 15 个金样例和自洽性高的伪标注。
3. 最相似样例：通过语义相似度检索得到，帮助模型处理局部相似模式。
4. 少量最不相似或边界样例：数量更少，用来提醒模型概念边界，不让模型只学习局部相似模式。
5. 失败模式和反例：来自前几轮低自洽样本和人工纠错。

推荐比例可以先从以下经验值开始：

```text
概念描述: 必选
金样例 / 高置信近邻: 3-5 个
边界远例 / 反例: 1-2 个
失败模式摘要: 3-5 条
```

这个设计的核心是假设：好的标注 prompt 不是纯相似检索，而是“概念定义 + 相似支持 + 边界约束 + 失败记忆”的组合。

## 4.1 标注输出格式与存储格式解耦

模型实际标注时，不要求直接输出最终存储 JSONL。对于术语、实体、概念 span 这类任务，行内标注通常更适合模型：

```text
[heart failure]{Specific_Term}
```

最终落盘时再统一解析成 Prodigy-compatible JSONL：

```json
{
  "schema_version": "rosetta.prodigy_jsonl.v1",
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
  "meta": {"unit": "sentence"}
}
```

这个格式对齐已有 span annotation 工具生态，尤其是 Prodigy 的 `text + spans[start/end/label]` 设计，也和 spaCy 的字符 offset span 数据表达相近。Rosetta 直接沿用 Prodigy 风格的顶层 `spans / relations / label / options / accept / answer / meta` 字段，用于 span、关系、概念包含和文档级分类。核心原则仍是“prompt 友好、存储标准、转换可校验”。

## 5. 与 ALLabel 的关系

ALLabel 的关键启发是：在标注预算有限时，不应该随机选择 demonstration pool，而应该主动选择最有价值的样本。

可借鉴点：

1. Diversity sampling：15 个初始金样例不能全是相似样本，应覆盖概念的不同表达形态。
2. Similarity sampling：大规模标注时，相似样例仍然是最重要的上下文来源之一。
3. Uncertainty sampling：自洽性低的样本就是当前系统里的不确定样本，应进入 hard example loop。
4. 5%-10% 标注预算假设：可以把“少量人工 gold + 高置信伪标注”作为降低标注成本的实验主线。
5. Human budget allocation：人工批改预算不平均分配，而是优先投向低自洽、低自评、规则验证失败的样本。

和 ALLabel 的差异：

1. ALLabel 主要选择哪些样本交给人工标注，用于构建 retrieval corpus。
2. 本系统不仅选择样本，还迭代优化概念描述本身。
3. 本系统把低自洽样本作为 prompt / concept refinement 的反馈信号，而不是只作为待标注样本。

## 6. 与 DEER 的关系

DEER 的关键启发是：NER / span annotation 不能只靠句向量检索，因为任务本质是 token-level 和 boundary-level 的。

可借鉴点：

1. Label-guided retrieval：用已标注样例统计哪些 token 常出现在目标概念内、概念上下文、非概念区域。
2. Context token：概念周围的上下文词对判断边界很重要，尤其对未见术语或新表达有效。
3. Error reflection：对疑难样本，不应只让模型重新标一次，而要针对 unseen token、false negative token、boundary token 做定向反思。
4. Span-level demonstrations：对边界错误，应检索 span 周围的小片段，而不是整篇文本。

和 DEER 的差异：

1. DEER 假设已有较大训练标注集，用标签统计增强检索。
2. 本系统从 15 个金样例开始，需要在低资源场景下逐步积累统计。
3. 本系统的 concept description refinement 是 DEER 没有强调的部分，可以成为主要创新点之一。

## 7. 是否足够支撑 EMNLP 级别工作

判断：有潜力，但目前“工程流程”本身还不够。要达到 EMNLP 级别，需要把它形式化成一个可验证的新方法，而不是只描述一个交互式系统。

可能成立的论文贡献是：

1. Concept Description Bootstrapping：从一句话概念描述和 15 个金样例出发，自动迭代得到可操作化概念定义。
2. Self-Consistency Active Refinement：用多次采样自洽性识别 hard examples，并把它们反馈到概念定义和 prompt 策略中。
3. Contrastive Demonstration Retrieval：同时检索相似样例和少量边界远例，避免 prompt 只学习局部相似性。
4. Label-Statistic-Guided Reflection：随着 gold / high-confidence 样本累积，引入 token/span 统计来做边界反思。
5. Low-Budget Span Annotation Pipeline：系统性展示 15 个金样例如何扩展到大规模可用标注。
6. Prompt-as-Parameter Optimization：把概念 prompt 切成可训练语义参数，在无解析梯度条件下估算 Text Gradient，再用优化器更新 prompt。

但如果只做到“给 15 个样例、反复改 prompt、跑 5 次看一致性”，创新性不足。必须证明它相对以下基线有稳定收益：

1. 只用概念描述的 zero-shot。
2. 只用 15 个 few-shot 的普通 ICL。
3. 只检索最相似样例的 embedding retrieval。
4. ALLabel 风格的主动样本选择。
5. DEER 风格的 label-guided retrieval。
6. majority vote self-consistency。
7. 同等人工预算下的 PLM fine-tuning。

完整高质量训练集上的 PLM fine-tuning 应作为强上界或成本/部署对照，不应作为 Rosetta 必须全面超过的唯一目标。Rosetta 最重要的比较对象是 low-budget PLM 和不支持快速概念变化的固定标签系统。

## 8. 必须做出的实验形态

推荐优先用术语抽取 / span annotation 数据集验证，例如 ACTER、NCBI-disease、BC2GM、CoNLL03 的子任务。

实验需要分成两条线：

1. 常规高质量数据集：使用成熟 gold 数据，比较 Rosetta 与 PLM low-budget / full-data 的关系。
2. 非常规可定义任务：由研究者给出概念描述和 15 条金样例，比较 Rosetta 与 zero-shot、fixed ICL、retrieval-only 和去掉审核反馈的 ablation。

每个实验至少记录：

1. 初始一句话概念描述。
2. 15 个金样例的选择策略。
3. 每轮失败样例。
4. 每轮概念描述修订；最终提示词只保存干净概念阐释，失败样例编号和诊断解释单独进入日志。
5. 大规模标注时每条样本的 5 次输出。
6. 自洽性分数。
7. 检索到的相似样例和边界样例。
8. 最终标准答案和判定理由。
9. 与 gold 的 precision、recall、F1、boundary F1。
10. 人工标注预算和模型调用成本。
11. 模型自评分数。
12. 人类专家是否介入。
13. 人类专家在多个候选中选择了哪一个。
14. 人类修改量，例如选择即通过、轻微编辑、完全重写。

关键 ablation：

1. 去掉概念描述迭代。
2. 去掉自洽性筛选。
3. 去掉远例 / 边界样例。
4. 去掉 label-statistic reflection。
5. 只用人工 gold，不用高置信伪标注。
6. 只用高置信伪标注，不用人工 gold。
7. 去掉人类选择题界面，改为人类从零标注。
8. 去掉模型自评，只用多次输出一致性。
9. 去掉多次采样，只用单次 token / verbal confidence。
10. 去掉文本梯度估算，只用普通 LLM 反思改写 prompt。
11. 去掉 prompt 长度惩罚，观察概念阐释是否越优化越长。

建议至少比较三种人类预算策略：

1. Random review：随机抽样给专家。
2. Uncertainty-first review：优先给专家低自洽样本。
3. Hybrid review：低自洽样本优先，同时保留少量高置信样本抽检，用来估计自动通过样本的真实错误率。

## 9. 工程实现原则

这条研究线现在应作为 Rosetta 主工作流实现，优先进入 `app/workflows/bootstrap`、`app/workflows/annotation`、`app/workflows/review` 和 `app/workflows/evaluation`。旧 `app/research` 中的实现保留为算法参考和兼容层，不能再作为产品主入口，也不能和 `corpusgen` 混在一起。

推荐模块边界：

```text
app/workflows/bootstrap/     # 15 gold examples -> concept description refinement
app/workflows/annotation/    # k-run sampling, context building, consistency routing
app/workflows/review/        # human choice, hard examples, gold-like feedback
app/workflows/evaluation/    # reports, metrics, experiment summaries
app/research/                # legacy algorithms and offline compatibility
```

推荐输出目录：

```text
.runtime/research/<config-name>/bootstrap_<timestamp>/
  concept_versions.jsonl
  gold_examples.jsonl
  failed_examples.jsonl
  consistency_runs.jsonl
  hard_examples.jsonl
  human_review_queue.jsonl
  human_choices.jsonl
  retrieval_traces.jsonl
  refined_prompt.json
  manifest.json
```

## 10. 不可丢失的核心判断

本项目真正想做的不是普通自动标注工具，而是：

```text
用极少人工输入，把一个研究者心中的概念，
迭代压缩成模型可执行的概念定义，
再用自洽性、语义检索、边界反例和错误反思，
扩展成可复现的大规模标注流水线。
```

后续任何实现如果只是在做“上传数据 -> 调模型 -> 下载结果”，就偏离了这条主线。

同样，后续任何论文写作如果只声称“LLM 标注效果更好”，也偏离了这条主线。Rosetta 真正要展示的是 agent 如何把概念、样例、失败、检索、审核和报告连成一个可持续改进的标注系统。

## 11. 当前落地状态

当前主线已从“普通批量标注工具”升级为定义优化闭环：

1. `app/workflows/bootstrap` 提供定义优化和 prompt training workflow，正式定义优化建议 15 条金样例，并逐轮写入 `ConceptVersion`。
2. 定义与规范的主动作已经收敛为“提示词验证 / 提示词优化”；页面展示每轮通过数、失败样例、失败摘要、loss、候选评估和最终概念草案；最终草案不混入样例编号或诊断日志。
3. 概念修订不再单路径贪心追加，而是生成多个候选概念版本，在 15 条金样例上重新试标并计算 gold loss，只接受让 loss 下降的候选。
4. `app/workflows/annotation` 新增标注上下文构建器，每次批量标注会组合概念版本、相似样例、边界远例和失败模式摘要。
5. 候选自洽性从简单 exact signature 升级为 span-F1、完全一致率、模型自评和规则风险组合。
6. 审核与修正开始记录错误类型、hard example、人工修改和 gold-like 晋升信号。
7. 导出报告开始包含概念版本和主动审核反馈。
8. 提示词优化三方案已经收敛为 `sgd_candidate_search / critic_adamw_optimizer / mask_guided_optimization`，并把可优化定义和冻结输出协议分开。
9. top-k 参考样例和批量上下文检索默认使用本地轻量 embedding `rosetta-local-hash-384`。

仍未完成的研究级增强：

1. 还没有完整论文级 optimizer state；当前 `critic_adamw_optimizer` 是 AdamW-like 文本候选控制器，不等同于数值 AdamW 参数更新。
2. 对比替换、完整消融链路和多 seed Text Gradient 稳定性仍需要进一步实现和报告。
3. 还没有 LLM-as-a-judge 候选评审。
4. 还没有 token logprob 或 semantic entropy。
5. 还没有完整 ablation runner 和数据集级 F1 对比表。
