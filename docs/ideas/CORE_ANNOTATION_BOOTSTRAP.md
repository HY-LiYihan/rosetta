# Core Idea: Concept-Driven Annotation Bootstrap

更新时间: 2026-04-28

## 1. 这份文档的作用

这份文档记录 Rosetta 当前最核心的科研想法。它不是普通功能清单，而是后续实现、实验设计、论文写作和 UI 取舍都必须优先遵守的中心假设。

核心目标是：让使用者用极少的人工输入，把一个模糊概念逐步压缩成可复现、可扩展、可审计的标注流水线。

## 2. 最核心的用户场景

第一次使用系统时，用户不需要先准备一个大规模标注集。用户只需要提供：

1. 一句话概念描述。
2. 15 个金样例。

这里的 15 个金样例不是普通 few-shot 示例，而是用于校准概念定义的最小人工锚点。系统首先不依赖复杂示例检索，而是让模型只根据概念描述尝试标注这 15 个样例。

如果某些样例标注失败，这些失败样例会被单独提出，用来反向优化概念描述。这个过程反复执行：

```text
一句话概念描述
  -> 标注 15 个金样例
  -> 找出失败样例
  -> 根据失败原因修订概念描述
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

最终落盘时再统一解析成可扩展 Annotation JSONL：

```json
{
  "schema_version": "rosetta.annotation_jsonl.v1",
  "text": "Patients with heart failure may receive ventricular assist devices.",
  "annotation": {
    "version": "3.1",
    "layers": {
      "spans": [
        {
          "id": "T1",
          "start": 14,
          "end": 27,
          "text": "heart failure",
          "label": "Specific_Term",
          "implicit": false,
          "features": {}
        }
      ],
      "relations": [],
      "attributes": [],
      "comments": [],
      "document_labels": []
    }
  }
}
```

这个格式对齐已有 span annotation 工具生态，尤其是 Prodigy 的 `text + spans[start/end/label]` 设计，也和 spaCy 的字符 offset span 数据表达相近。Rosetta 在外层增加 `annotation.layers`，用于后续关系、属性、文档标签、人类备注和 provenance 扩展。核心原则仍是“prompt 友好、存储标准、转换可校验”。

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

但如果只做到“给 15 个样例、反复改 prompt、跑 5 次看一致性”，创新性不足。必须证明它相对以下基线有稳定收益：

1. 只用概念描述的 zero-shot。
2. 只用 15 个 few-shot 的普通 ICL。
3. 只检索最相似样例的 embedding retrieval。
4. ALLabel 风格的主动样本选择。
5. DEER 风格的 label-guided retrieval。
6. majority vote self-consistency。

## 8. 必须做出的实验形态

推荐优先用术语抽取 / span annotation 数据集验证，例如 ACTER、NCBI-disease、BC2GM、CoNLL03 的子任务。

每个实验至少记录：

1. 初始一句话概念描述。
2. 15 个金样例的选择策略。
3. 每轮失败样例。
4. 每轮概念描述修订。
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

建议至少比较三种人类预算策略：

1. Random review：随机抽样给专家。
2. Uncertainty-first review：优先给专家低自洽样本。
3. Hybrid review：低自洽样本优先，同时保留少量高置信样本抽检，用来估计自动通过样本的真实错误率。

## 9. 工程实现原则

这条研究线应放在 `research` pipeline 中，不能和 `corpusgen` 混在一起。

推荐模块边界：

```text
app/research/
  concept_bootstrap.py      # 15 gold examples -> concept description refinement
  consistency.py            # k-run self-consistency scoring
  active_selection.py       # diversity / uncertainty / hard example selection
  contrastive_retrieval.py  # similar + boundary distant examples
  label_statistics.py       # entity/context/other token statistics
  reflection.py             # boundary / false negative / low-consistency reflection
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
