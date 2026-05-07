# Documentation Review Iterations

更新时间: 2026-05-02

## 1. 目的

这份文档记录本轮文档重构的 5 轮以上评审过程。每轮都用三类读者检查一次：

1. 之前没有接触过数据标注的传统语言学家。
2. 研究 PLM 的计量语言学家。
3. Rosetta 开发人员。

目标不是写漂亮文档，而是让后续程序更新有稳定依据：用户知道怎么做，研究者知道要证明什么，开发者知道文件该放哪里、数据该怎么流。

## 2. 第 1 轮：入口是否能看懂

传统语言学家评价：

1. “Agentic Annotation Tool”“concept bootstrap loop”这样的词可以保留，但必须先用中文解释。
2. 第一次使用时，我只想知道先点哪个页面、填什么、保存什么。
3. 金样例、概念阐释、审核队列之间的关系需要一句话讲清楚。

计量语言学家评价：

1. 文档需要明确 Rosetta 和 PLM fine-tuning 不是同一个问题。
2. 如果要说 LLM 强于 PLM，必须说明是在低资源、概念变化、非常规任务这些条件下。
3. 需要实验基线和指标入口。

开发人员评价：

1. 文档入口已有，但 `research/corpusgen` 的历史表达容易误导新开发者。
2. 需要把用户流程和工程目录直接映射起来。
3. 需要明确 legacy 文件是兼容层，不是新功能入口。

本轮优化：

1. 文档首页改成“用户入口 / 开发者入口 / 研究主张”三条线。
2. 新增 [Research Claims](../ideas/RESEARCH_CLAIMS.md)，单独说明 LLM agent vs PLM 的可验证主张。
3. 在用户教程开头补充“最少要知道的 4 个词”。

## 3. 第 2 轮：用户流程是否够直接

传统语言学家评价：

1. “15 条金样例”不能只说重要，还要说为什么不能少。
2. “自举校准”听起来抽象，需要解释成“系统用你的 15 个标准答案反复考自己”。
3. 审核队列要强调是选择题优先，不是要求专家重新做一遍标注。

计量语言学家评价：

1. 需要区分 gold examples、pseudo labels、reviewed labels，否则实验数据来源会混。
2. 用户教程应该提醒首次测试先用本地模拟，避免一上来消耗 API 预算。
3. 导出报告要服务后续实验，不只是下载数据。

开发人员评价：

1. 页面名称和 workflow 名称需要稳定，避免后来改 UI 时破坏用户文档。
2. 用户教程中的每一步最好对应一个可测试的 workflow 函数。
3. 文档应明确 Streamlit 是正式 UI，不引入第二套前端。

本轮优化：

1. 用户教程改写为“填表 -> 校准 -> 批量 -> 审核 -> 导出”的直接路径。
2. 批量标注文档强调 TXT/JSONL/CSV 输入和本地模拟。
3. 导出与可视化部分强调实验报告、人工效率和概念版本记录。

## 4. 第 3 轮：研究主张是否可证明

传统语言学家评价：

1. 非常规任务的例子需要更贴近日常研究，例如历史语料、论文方法段、科普新闻。
2. 人类专家的价值不是被替代，而是被更精准地使用。

计量语言学家评价：

1. 必须有常规高质量数据集和非常规任务两类实验。
2. PLM full-data fine-tuning 应作为上界，低预算 PLM 才是主要公平比较。
3. 要有 ablation，否则无法证明 agent loop 中哪些部件有贡献。

开发人员评价：

1. 实验指标必须映射到已存在或计划中的字段，例如 `ConceptVersion.metadata`、`Prediction.meta`、`ReviewTask.meta`。
2. 报告生成要从 runtime store 和 artifacts 聚合，不应手写表格。

本轮优化：

1. Research Claims 增加“常规高质量数据集”和“非常规可定义任务”两组实验。
2. Bootstrap Experiments 增加 PLM low-budget / full-data 基线。
3. Core Idea 增加“Rosetta 不声称完整数据条件下总能超过 PLM”的边界声明。

## 5. 第 4 轮：开发结构是否够清楚

传统语言学家评价：

1. 开发文档可以有代码目录，但不要影响用户教程。
2. 术语最好稳定，不要一会儿叫 pipeline，一会儿叫 lab。

计量语言学家评价：

1. 需要知道每个实验产物在哪：概念版本、候选、审核、导出报告。
2. `research` 这个词如果保留为目录，会不会和产品主线冲突，需要说明。

开发人员评价：

1. 架构文档需要从“目录列表”升级为“数据如何穿过目录”。
2. 新功能落点必须明确：UI 只调用 workflow，workflow 编排 agents/data/runtime。
3. Legacy 文档要标注迁移状态，不要让新人继续往旧目录加功能。

本轮优化：

1. Architecture 增加“主数据流”和“研究命题到代码的映射”。
2. Developer README 增加按任务选择文档的入口。
3. Research Pipeline 和 Corpus Pipeline 被重新标注为 legacy / advanced workflow，而不是顶层产品边界。

## 6. 第 5 轮：文档能否驱动后续程序迭代

传统语言学家评价：

1. 文档要告诉我什么时候可以相信自动通过，什么时候必须人工看。
2. 如果概念越改越差，系统如何阻止，需要清楚说明。

计量语言学家评价：

1. Loss-guided refinement 是关键创新，必须说明它是内部优化目标，不等同最终论文指标。
2. 主动审核收益需要在报告里可量化。
3. 不同数据来源必须能在 JSONL 或 metadata 中追踪。

开发人员评价：

1. Roadmap 需要从旧 Stage 1-6 改成接下来的 agentic annotation 里程碑。
2. Workflow 文档需要加入文档优先和三角色评审要求。
3. Changelog 要记录此次文档重构，方便后续回溯。

本轮优化：

1. Roadmap 改成 v4.2.3 之后的实验闭环路线。
2. Workflow 增加三角色文档评审检查。
3. Changelog 增加本轮文档架构版本。

## 7. 第 6 轮：最终一致性检查

传统语言学家评价：

1. 用户入口已经能照着走，但仍需要保留完整案例。
2. 不需要在用户文档里解释所有目录。

计量语言学家评价：

1. 研究主张、实验基线、指标和报告字段已经形成闭环。
2. 需要持续警惕过度宣称：Rosetta 的强项是低资源和概念变化，不是无条件击败 PLM。

开发人员评价：

1. 新增文档必须进入 `mkdocs.yml` 导航。
2. 所有 docs 文件应共享同一条主线：Rosetta 是本地优先、Streamlit UI、agentic concept bootstrap annotation tool。
3. 后续代码变更必须同步检查用户文档、开发文档、核心 idea 和 changelog。

本轮优化：

1. 更新文档站导航，把“研究主张”作为独立入口。
2. 所有现有 docs 文件都补入或校正了与主线相关的说明。
3. 验证 `mkdocs build --strict --clean`，确保文档站可构建。

## 8. 第 7 轮：公开网站首页与快速使用复查

传统语言学 / 数字人文用户评价：

1. 首页和快速使用仍偏研究工程说明，新用户不知道“现在先点哪里、准备什么文件、多久能跑完”。
2. 用户教程需要更早给出 1-2 条金样例 JSONL 模板。
3. “定义优化 / 提示词优化 / 概念优化 / prompt training”应在用户侧统一成“定义优化”，只保留 UI 按钮名“提示词优化”。
4. “本地模拟”需要说明只能检查流程，不能代表真实模型效果。
5. 导出文件要说明 `annotations.jsonl`、`report.md` 和 `manifest.json` 分别用于什么。

PLM / NLP 研究者评价：

1. “Rosetta 要证明”容易被理解为已有结论，应该改成“当前要检验的假设”。
2. `Text Gradient`、`LLM-AdamW`、`SGD-like` 等术语需要避免被误读为连续数学梯度或完整优化器证明。
3. PLM baseline 需要写清模型族、训练预算、seed、split、负例采样、早停和置信区间。
4. canonical 方法名应优先使用 `sgd_candidate_search / critic_adamw_optimizer / mask_guided_optimization`，旧名只作为 alias。

本轮优化：

1. [docs/README.md](../README.md) 新增“第一次只读这两页”，把官方样例的最短路径前置。
2. [用户教程](../user/TUTORIAL.md) 新增 5 分钟官方样例、金样例 JSONL 小抄、执行方式解释、导出文件用途和用户术语小抄。
3. [Research Claims](../ideas/RESEARCH_CLAIMS.md) 新增“当前证据与待验证假设”，把 15 gold 内证据、held-out 假设和论文级结论分开。
4. [Bootstrap Experiments](./BOOTSTRAP_EXPERIMENTS.md) 新增 canonical 方法名表、PLM baseline 公平协议和主评测指标。
5. 验证 `mkdocs build --strict --clean` 和 `git diff --check`。
