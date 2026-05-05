# Rosetta Docs

更新时间: 2026-05-05

在线文档站：[https://hy-liyihan.github.io/rosetta/](https://hy-liyihan.github.io/rosetta/)

Rosetta 是基于 Streamlit 的本地优先 Agentic Annotation Tool。它的核心不是“上传文本然后调一次大模型”，而是把一句话概念描述和 15 条金样例，迭代压缩成可执行、可复现、可审计的标注流水线。

文档面向两类主要读者：

1. **User**：第一次使用工具的人，尤其是传统语言学、数字人文、领域专家和需要快速构建语料标注任务的研究者。文档要简单直接，告诉你应该填什么、点什么、导出什么。
2. **Developer**：维护 Rosetta 的开发者和研究工程人员。文档要清楚说明运行结构、文件架构、数据流、workflow 边界和实验产物。

## 入口总览

| 你要做什么 | 先读 | 然后读 |
| --- | --- | --- |
| 第一次使用页面 | [用户教程](./user/TUTORIAL.md) | [Annotation JSONL](./developer/ANNOTATION_JSONL_FORMAT.md) |
| 让大模型快速接手项目 | [Agent Onboarding](./developer/AGENT_ONBOARDING.md) | [架构总览](./developer/ARCHITECTURE.md) |
| 理解 Rosetta 要证明什么 | [研究主张](./ideas/RESEARCH_CLAIMS.md) | [Prompt-as-Parameter](./ideas/PROMPT_AS_PARAMETER.md) |
| 理解新架构 | [开发者入口](./developer/README.md) | [架构总览](./developer/ARCHITECTURE.md) |
| 设计大模型调用并发与进度 | [LLM 服务运行时](./developer/LLM_SERVICE_RUNTIME.md) | [路线图](./developer/ROADMAP.md) |
| 做 guideline / bootstrap | [核心想法](./ideas/CORE_ANNOTATION_BOOTSTRAP.md) | [Concept Bootstrap](./developer/BOOTSTRAP_PIPELINE.md) |
| 理解冻结输出协议和格式修复 | [Annotation Format](./developer/ANNOTATION_FORMAT.md) | [Concept Bootstrap](./developer/BOOTSTRAP_PIPELINE.md) |
| 设计 PLM / LLM 对比实验 | [研究主张](./ideas/RESEARCH_CLAIMS.md) | [Bootstrap Experiments](./developer/BOOTSTRAP_EXPERIMENTS.md) |
| 生成语料 | [Corpus Pipeline](./developer/CORPUS_PIPELINE.md) | [用户教程](./user/TUTORIAL.md) |
| 跑统一 CLI | [Scripts](./developer/SCRIPTS.md) | [Workflow](./developer/WORKFLOW.md) |
| 部署 Docker | [Deployment](./developer/DEPLOYMENT.md) | [Scripts](./developer/SCRIPTS.md) |

## 核心主张

Rosetta 最需要证明的是：LLM agent 在低资源、概念可描述、任务边界会迭代或任务不够常规的标注场景中，能比 PLM-first 流程更快形成可用数据，并且保留完整的概念版本、候选分歧、人工审核和成本轨迹。

这不等于声称 LLM 在完整高质量训练集条件下必然超过 PLM。更准确的比较方式是：用 full-data PLM 作为强上界，用 15 / 50 / 100 gold 的 low-budget PLM 作为主要对照，再比较 Rosetta 的概念自举、上下文检索、自洽性路由和主动审核是否带来稳定收益。

`v4.5.0` 将 [Prompt-as-Parameter](./ideas/PROMPT_AS_PARAMETER.md) 从“能比较优化方法”推进到真实服务化训练路径：默认真实模型为 DeepSeek `deepseek-v4-pro`，LLM service runtime 用 provider 级共享 semaphore 把默认并发上限提升到 `20`，并记录调用进度、token、耗时和重试。训练反馈可以包含原文、标准答案和模型回答；候选提示词若复制语料词、gold span、模型 span 或可识别答案片段，会先进入去语料化修复，修复后仍泄露才拒绝。当前结论仍只限于 15 条 gold 内的训练表现，不宣称跨样本泛化。

`v4.5.1` 将三方法 prompt training 变成可交付的对比实验：`llm_optimize_only / llm_reflection / text_gradient_adamw` 从同一简单提示词和同一批 15 条专业命名实体 gold 出发，达到 `15/15` 即成功，否则连续 5 轮 loss 无下降才停止，默认最多 30 轮。报告中的最佳方法、最佳 loss 和最佳提示词按历史最优接受版本计算，不用最后一轮快照误导方法排名。统一 CLI 会输出 Markdown 报告、完整 JSON trace 和提示词演化 JSONL。

`v4.5.2` 将“定义与规范”里的 prompt training 从同步等待升级为后台轮询：点击后创建 `WorkflowRun(status=running)`，后台线程执行三方法训练并把 `RunProgressEvent` 写入 SQLite。页面每 2 秒显示阶段、ETA、调用数、token、修复次数、当前最佳方法和折叠日志；实验产物新增 `run_events.jsonl`。

`v4.5.3` 将默认运行库改为干净官方 demo 模式：Streamlit 进程重启时只刷新主 SQLite `.runtime/rosetta.sqlite3`，恢复唯一官方样例“专业命名实体标注”、15 条金样例和基础提示词，不删除 `.runtime/experiments/`、导出报告、PDF、HTML 或其他 artifact。

`v4.5.4` 将“验证概念”补齐为可见的并发验证：真实 LLM 模式会并发检查 15 条 gold，默认并发上限 `20`；页面显示进度条、运行中数量、已用时、ETA、调用数、token 和模型耗时。

`v4.5.5` 先做文档契约升级：Prompt training 不再被描述为“让 LLM 改整段提示词”，而是拆成可优化的 `ConceptPromptSpec` 和冻结的 `Frozen OutputProtocolSpec`。概念定义、边界规则和排除规则可以训练；标签、JSON schema、`[span]{Term}` markup、parser 和 format repair 指令由 harness 注入并冻结。后续统一代码实现必须先严格解析 JSON+markup，格式失败最多修复 2 次，repair 成功后才计算 semantic loss；实验报告要拆分 format failure、repair success 和 semantic loss。

`v4.5.6` 将主流程命名收敛为更贴近用户动作的 `项目总览 -> 定义与规范 -> 批量标注 -> 审核与修正 -> 结果与导出`。“定义与规范”页面顶部新增任务摘要，先告诉用户这里要完成项目选择、规范确认、金样例维护和验证/训练，而不是直接进入表单。

`v4.5.7` 将“定义与规范”页面升级为强 harness 视图：页面直接分出 `ConceptPromptSpec` 和 `Frozen OutputProtocolSpec`。前者包含任务定义、概念定义、边界规则和排除规则，是 prompt training 的唯一优化对象；后者包含标签、JSON 字段、annotation markup、parser contract 和 format repair，由系统锁定注入。代码侧也先把候选生成提示词收紧为 concept-only，候选带回标签或输出格式时会剥离并记录 warning。

`v4.5.8` 将“定义与规范”的新概念表单收紧为更符合用户心智的输入契约：用户填写概念名称、概念描述或定义、边界说明，并通过选项选择冻结的标注输出协议。标签不再手填，而是从 gold span label 自动推断，默认 `Term`；普通 span 任务允许模型运行时返回简单 `JSON + [span]{Term}`，Rosetta 会解析为统一 AnnotationDoc / Prodigy-compatible 存储结构，relation / attributes / 多层任务可选择完整 `AnnotationDoc` JSON。

`v4.5.9` 将运行时标注 prompt 固定为统一框架：`概念定义 -> 标注格式 -> 通用格式示例 -> 待标注文本 -> 任务强调`。概念验证、候选回测、单条标注和批量标注共享这个框架；格式示例只说明 JSON / markup / AnnotationDoc 的返回结构，不使用当前任务 gold 或相似样例，输出协议也不再被拼进可优化概念定义。

`v4.5.10` 进一步收紧标注调用和 reflection 反馈：概念验证、候选回测、单条标注和批量标注共享同一个 system prompt `你是严谨的标注助手，只输出 JSON。`；`llm_reflection` 的训练反馈先展示当前可优化提示词，再按失败 detail 就近列出原文、gold `[span]{Term}`、模型 JSON 回答和错误摘要。批改对照仍只用于 `training_feedback_only=true`，最终提示词继续保持 concept-only。

`v4.5.11` 将“定义与规范”页面收敛为两个主动作：`提示词验证` 与 `提示词优化`。验证分为格式验证、无样例标注验证和带 top-k 相似参考样例的标注验证；优化分为人工优化、无样例自监督优化和第一版类训练优化。类训练优化每轮默认生成 5 个候选，回测 15 条 gold，先选择本轮 loss 最低候选，再仅在它超过阈值下降时接受，并把 v0 -> vn 的提示词版本和 loss 变化保存到 runtime。

## 用户路径

```text
项目总览 -> 定义与规范 -> 批量标注 -> 审核与修正 -> 结果与导出
```

页面说明见 [用户教程](./user/TUTORIAL.md)。

## 工程路径

新代码优先进入：

1. `app/core`: 稳定领域模型。
2. `app/workflows`: 用户可执行流程。
3. `app/agents`: agent kernel、tool registry、context engine。
4. `app/data`: Prodigy JSONL 与外部格式桥接。
5. `app/runtime`: SQLite store、runtime paths、artifact/run/trace。
6. `app/infrastructure/llm`: provider profile、模型服务参数、token/cost 和限流边界。

旧目录：

1. `app/research`: legacy bootstrap / evaluation implementation。
2. `app/corpusgen`: legacy corpus generation implementation。
3. `scripts/research` 和 `scripts/corpusgen`: legacy CLI，保留兼容。

开发文档的基本约束：

1. UI 只负责输入和展示，不承载复杂业务规则。
2. workflow 是用户可执行流程的主入口。
3. agent / data / runtime 是 workflow 的支撑层。
4. legacy 目录只能做兼容和迁移参考，不再作为新功能边界。

## 数据格式

| 格式 | 用途 | 文档 |
| --- | --- | --- |
| LLM runtime inline markup | prompt 与响应解析 | [Annotation Format](./developer/ANNOTATION_FORMAT.md) |
| Prodigy-compatible JSONL | 长期存储、复核、评测、导出 | [Annotation JSONL Format](./developer/ANNOTATION_JSONL_FORMAT.md) |
| SQLite runtime store | 本地 project/run/artifact/trace | [Architecture](./developer/ARCHITECTURE.md) |

## 当前阶段

1. v4.5.11 已把“定义与规范”主操作收敛为提示词验证和提示词优化，并新增 top-k 参考样例验证、三类优化方式和 v0-vn prompt 版本保存。
2. v4.5.10 已统一所有标注型调用的 system prompt 为同一个标注助手身份，并把 `llm_reflection` 反馈改为失败 detail 就近批改对照。
3. v4.5.9 已统一概念验证、候选回测、单条标注和批量标注的运行时 prompt 框架：`概念定义 -> 标注格式 -> 通用格式示例 -> 待标注文本 -> 任务强调`。
4. v4.5.8 已把“定义与规范”的新概念表单收紧为概念名称、概念定义、边界说明和标注输出协议选项；标签从 gold 自动推断，输出协议冻结。
5. v4.5.7 已把“定义与规范”页升级为强 harness 视图：可优化定义与冻结输出协议分栏展示，prompt training 候选生成只允许改概念语义，标签和输出格式会被剥离出候选提示词。
6. v4.5.6 已更新主流程命名：`项目总览 / 定义与规范 / 批量标注 / 审核与修正 / 结果与导出`，并在“定义与规范”顶部增加任务摘要。
7. v4.5.5 已文档化冻结输出协议与强格式 harness：prompt optimizer 只优化概念语义，输出协议由 JSON+markup parser 和 format repair contract 统一约束。
8. v4.5.4 已实现概念验证并发与页面进度条：真实 LLM 模式默认并发上限 20，并显示完成数、运行中数量、ETA、token 和耗时。
9. v4.5.3 已实现主运行库重启自动清洁：默认只保留官方“专业命名实体标注”项目、一个概念、15 条金样例和一个初始概念版本。
10. v4.5.2 已实现提示词优化训练后台运行、SQLite 实时进度事件、Definition & Guideline 轮询进度卡片、折叠日志和 `run_events.jsonl`。
11. v4.5.1 已实现三方法真实对比实验：每个方法连续 5 轮 loss 无下降才停止，默认最多 30 轮；CLI 输出 `comparison_report.md / comparison_result.json / prompt_evolution.jsonl`，并按历史最优接受版本汇总最佳提示词。
12. v4.5.0 已接入统一 LLM service runtime：DeepSeek 默认 `deepseek-v4-pro`，默认 provider 并发上限 `20`，提示词训练和批量标注记录调用、token、耗时和修复统计。
13. v4.4.1 已实现提示词优化训练防背答案检查：训练反馈可看批改对照，learned operational prompt 必须无语料和答案片段泄露。
14. v4.4.0 已实现提示词优化训练：同一批 15 条金样例比较 `llm_optimize_only / llm_reflection / text_gradient_adamw`。
15. v4.3.1 文档化 LLM service runtime 愿景：每次大模型调用都应作为服务调用被限流、排队、追踪、计费和可视化，默认并发上限后续收敛为 20。
16. v4.3.0 已实现 Prompt-as-Parameter 最小内核：prompt 分段、Mask 文本梯度、LLM-AdamW trace、长度惩罚和 loss 验证。
17. v4.2.4 将 Prompt-as-Parameter、Text Gradient 和 `LLM-AdamW` 写成核心方法框架。
18. v4.2.3 将文档重构为 user / developer / research claims 三条入口，并记录 6 轮三角色文档评审。
19. v4.2.2 将概念自举升级为 loss-guided candidate search：每轮比较当前概念和候选概念的 gold loss，只接受变好的版本。
20. v4.2.1 修正概念自举修订：最终提示词只保存干净概念阐释，失败摘要、样例编号和模型原始响应只进入日志与 metadata。
21. Streamlit 仍是唯一正式 UI。
22. 项目总览收敛为轻量状态入口，定义与规范启动即显示“专业命名实体标注”官方样例。
23. 定义与规范主界面负责提示词验证和提示词优化，批量标注负责 TXT/JSONL/CSV 导入和本地任务队列。
24. 审核与修正按置信度、抽检和错误类型逐条展示待审核样本，并沉淀 hard examples。
25. Prodigy-compatible JSONL 不推翻，只增强 project/run/session/job 层。
26. 旧 `research/corpusgen` 暂不删除，作为 compatibility wrapper 的实现来源。

## 维护规则

1. 代码或行为变更必须同步更新 [CHANGELOG.md](./CHANGELOG.md)。
2. 用户使用方式变化必须同步更新根目录 [README.md](https://github.com/HY-LiYihan/rosetta#readme)。
3. 文档站导航由 [mkdocs.yml](../mkdocs.yml) 维护。
4. 文档重大调整要按 [Documentation Review Iterations](./developer/DOCS_REVIEW_ITERATIONS.md) 的三角色方式检查。
5. 每个可验收子步骤一个 commit，commit message 使用 `stageX-scope: summary`。
