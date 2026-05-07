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

## 9. 第 8 轮：公开介绍页语言与事实一致性复查

严苛中文产品文案审稿评价：

1. 公开 README 和用户教程明确承诺“中文 / English 全局切换”，但公开文档站没有这个切换入口，属于误导性功能声明。
2. 首页和能力表中英文混杂过重，`Agentic Annotation Tool`、`LLM service runtime`、`provider semaphore`、`harness` 等词像开发备忘录，不像中文产品介绍。
3. 用户侧同一动作仍有多套叫法：提示词验证、格式验证、本地结构验证、验证概念；定义优化与提示词优化也需要解释成“UI 名称”和“实际优化对象”的关系。
4. 公开入口应更早说明如何打开产品，而不只给文档站和 GitHub。

本轮优化：

1. 删除 README 核心能力表中不准确的“5 个主页面正文同步切换”能力声明。
2. 将应用侧栏语言选择从下拉框改为 `中文 / English` 两个按钮，并在用户教程“界面语言”章节说明切换边界。
3. 将 README 和文档首页的公开介绍改成中文主导：用“智能体式标注工具”“大模型服务运行时”“本地相似样例检索”等中文口径替代显眼英文术语。
4. 修正用户教程中的 prompt 框架，补回 `相似参考样例` 槽位。
5. 修正批量标注运行时口径：提示词验证和定义优化已接入统一运行时；批量标注当前仍使用本地任务队列和页面线程池调用 provider，后续再迁入统一运行时。
6. 更新 README 最后更新时间，并在 changelog 记录本轮 P0/P1 事实修正。

## 10. 第 9 轮：提示词构成与中英文边界复查

传统语言学 / 数字人文用户评价：

1. 用户需要一页直接回答“模型到底看见了什么”，否则会把界面语言、概念阐释语言、标签名和模型输出语言混为一谈。
2. “一句话概念描述 + 15 条金样例”必须更早说明边界：这是启动和校准，不是泛化保证。
3. top-k 参考样例验证不能写得像泛化评测；gold 验证必须说明排除当前样例自身和记录参考来源的实验要求。

PLM / NLP 研究者评价：

1. 研究主张页不能继续把输出格式、示例和失败记忆写成可训练文本参数；当前强 harness 契约只允许优化概念定义、边界规则和排除规则。
2. 用户侧旧术语“自举校准”应改成“定义优化”，开发侧可保留 bootstrap 作为内部 workflow 名称。
3. 旧方法名只能作为兼容 alias；公开用户文档优先使用 `sgd_candidate_search / critic_adamw_optimizer / mask_guided_optimization`。

维护者评价：

1. 中英文 prompt 构成应有权威入口，不应散落在 README、Annotation Format、Bootstrap Pipeline 和教程里。
2. 不能暗示界面切换会自动翻译用户输入、任务文本、模型输出或日志。
3. 最好用测试把文档和程序里的 prompt 段落标题绑在一起，减少漂移。

本轮优化：

1. 新增 [提示词构成](../user/PROMPT_COMPOSITION.md)，按 `zh-CN / en-US` 对照说明 system prompt、六段 user prompt、冻结输出协议和定义优化 prompt 边界。
2. `annotation_service.py` 将 system prompt、段落顺序和段落标题抽成中英文模板常量，并保留 `zh-CN` 默认行为。
3. 新增 `tests/unit/test_prompt_composition_docs.py`，检查提示词构成页包含程序中的中英文 system prompt 和运行时段落标题。
4. 更新 README、文档首页、用户教程、Annotation Format、Research Claims、Prompt-as-Parameter、Architecture 和 Core Annotation Bootstrap 的相关口径。

## 11. 第 10 轮：公开 docs 站地址纠错

传统语言学 / 数字人文用户评价：

1. 公开入口表必须把 docs 站和 demo 页面分开，否则新用户会跟错入口。
2. `rosetta-stone.xyz` 可以存在，但不能被称为官方文档站。

维护者评价：

1. 站点地址要回到 GitHub Pages 原入口。
2. 首页 badge、README 表格和 docs 首页必须保持一致。

本轮优化：

1. 将 `site_url` 和 README / docs 首页入口改回 `https://hy-liyihan.github.io/rosetta/`。
2. 把 `rosetta-stone.xyz` 明确标为 demo 页面。
3. 将首页版本更新为 `v4.5.21`，并记录到 changelog。
