# Rosetta Docs

更新时间: 2026-05-08

## 官方入口

| 入口 | 地址 | 说明 |
| --- | --- | --- |
| 官方文档站 | [https://hy-liyihan.github.io/rosetta/](https://hy-liyihan.github.io/rosetta/) | 对外使用、阅读教程和查看开发文档的主入口 |
| Demo 页面 | [https://rosetta-stone.xyz/](https://rosetta-stone.xyz/) | 演示页面，不是文档站 |
| GitHub 项目 | [https://github.com/HY-LiYihan/rosetta](https://github.com/HY-LiYihan/rosetta) | 源码、issue、部署文件、提交记录和项目协作入口 |

## 项目简介

Rosetta 是基于 Streamlit 的本地优先智能体式标注工具。它面向需要快速建立标注任务的研究者、语言学家、数字人文团队和领域专家。

它的核心不是“上传文本然后调一次大模型”，而是把一句话概念描述和 15 条金样例，迭代压缩成可执行、可复现、可审计的标注流水线：

```text
项目总览 -> 定义与规范 -> 批量标注 -> 审核与修正 -> 结果与导出
```

Rosetta 会把概念阐释、金样例、定义优化、批量标注、人工审核、运行记录和导出报告连成一个闭环。15 条金样例用于启动、校准和演示，不等于充分训练集，也不保证外部语料泛化。它要检验的是低资源、概念可描述、任务边界会迭代的场景中，大模型智能体是否能更快形成可审计的数据生产流程；它不声称在完整高质量训练集条件下无条件超过 PLM。

“本地优先”指项目数据、运行记录、导出文件和调试产物优先落在本机或你部署的运行目录中；它不等于默认离线，也不等于不会调用云端大模型。选择真实 provider 时，文本和 prompt 会按对应平台配置发送给模型服务。

文档面向两类主要读者：

1. **用户**：第一次使用工具的人，尤其是传统语言学、数字人文、领域专家和需要快速构建语料标注任务的研究者。文档要简单直接，告诉你应该填什么、点什么、导出什么。
2. **开发者**：维护 Rosetta 的开发者和研究工程人员。文档要清楚说明运行结构、文件架构、数据流、workflow 边界和实验产物。

文档站顶部提供 `中文 / English` 语言切换入口。`English` 不作为中文导航栏中的栏目出现；英文入口在独立路径下覆盖当前所有文档页面，避免把两种语言混在同一个介绍页里。

## 第一次只读这三页

如果你只是想跑通一次标注，不需要先读完整研究和架构文档：

1. 先读 [用户教程](./user/TUTORIAL.md) 的第 0-3 节，理解概念阐释、金样例、提示词验证和定义优化。
2. 再读 [提示词构成](./user/PROMPT_COMPOSITION.md)，确认界面语言、用户输入、运行时 prompt 和冻结输出协议各自是什么。
3. 最后按 [用户教程](./user/TUTORIAL.md) 的“完整使用案例：专业命名实体标注”跑官方样例：打开“定义与规范”做格式验证，到“批量标注”粘贴几句文本，用“本地模拟”提交，再到“结果与导出”下载 JSONL 和报告。

## 入口总览

| 你要做什么 | 先读 | 然后读 |
| --- | --- | --- |
| 第一次使用页面 | [用户教程](./user/TUTORIAL.md) | [Annotation JSONL](./developer/ANNOTATION_JSONL_FORMAT.md) |
| 理解模型实际看到的 prompt | [提示词构成](./user/PROMPT_COMPOSITION.md) | [Annotation Format](./developer/ANNOTATION_FORMAT.md) |
| 让大模型快速接手项目 | [Agent Onboarding](./developer/AGENT_ONBOARDING.md) | [架构总览](./developer/ARCHITECTURE.md) |
| 理解 Rosetta 要证明什么 | [研究主张](./ideas/RESEARCH_CLAIMS.md) | [Prompt-as-Parameter](./ideas/PROMPT_AS_PARAMETER.md) |
| 理解新架构 | [开发者入口](./developer/README.md) | [架构总览](./developer/ARCHITECTURE.md) |
| 设计大模型调用并发与进度 | [LLM 服务运行时](./developer/LLM_SERVICE_RUNTIME.md) | [路线图](./developer/ROADMAP.md) |
| 理解本地 embedding 检索 | [Embedding Retrieval](./developer/EMBEDDING_RETRIEVAL.md) | [架构总览](./developer/ARCHITECTURE.md) |
| 本机排查 LLM prompt | [Deployment Debug 模式](./developer/DEPLOYMENT.md) | [LLM 服务运行时](./developer/LLM_SERVICE_RUNTIME.md) |
| 做 guideline / bootstrap | [核心想法](./ideas/CORE_ANNOTATION_BOOTSTRAP.md) | [Concept Bootstrap](./developer/BOOTSTRAP_PIPELINE.md) |
| 理解冻结输出协议和格式修复 | [Annotation Format](./developer/ANNOTATION_FORMAT.md) | [Concept Bootstrap](./developer/BOOTSTRAP_PIPELINE.md) |
| 设计 PLM / LLM 对比实验 | [研究主张](./ideas/RESEARCH_CLAIMS.md) | [Bootstrap Experiments](./developer/BOOTSTRAP_EXPERIMENTS.md) |
| 生成语料 | [Corpus Pipeline](./developer/CORPUS_PIPELINE.md) | [用户教程](./user/TUTORIAL.md) |
| 跑统一 CLI | [Scripts](./developer/SCRIPTS.md) | [Workflow](./developer/WORKFLOW.md) |
| 部署 Docker | [Deployment](./developer/DEPLOYMENT.md) | [Scripts](./developer/SCRIPTS.md) |

## 核心主张

Rosetta 当前要检验的核心假设是：LLM agent 在低资源、概念可描述、任务边界会迭代或任务不够常规的标注场景中，是否能比 PLM-first 流程更快形成可用数据，并且保留完整的概念版本、候选分歧、人工审核和成本轨迹。

这不等于声称 LLM 在完整高质量训练集条件下必然超过 PLM。更准确的比较方式是：用 full-data PLM 作为强上界，用 15 / 50 / 100 gold 的 low-budget PLM 作为主要对照，再比较 Rosetta 的概念自举、上下文检索、自洽性路由和主动审核是否带来稳定收益。

`v4.5.0` 将 [Prompt-as-Parameter](./ideas/PROMPT_AS_PARAMETER.md) 从“能比较优化方法”推进到真实服务化训练路径：默认真实模型为 DeepSeek `deepseek-v4-pro`，大模型服务运行时用平台级共享并发上限控制提示词验证和定义优化调用，并记录调用进度、token、耗时和重试。批量标注当前仍使用本地任务队列和页面线程池调用 provider，后续继续迁入统一运行时。训练反馈可以包含原文、标准答案和模型回答；候选提示词若复制语料词、gold span、模型 span 或可识别答案片段，会先进入去语料化修复，修复后仍泄露才拒绝。当前结论仍只限于 15 条 gold 内的训练表现，不宣称跨样本泛化。

`v4.5.1` 将三方法 prompt training 变成可交付的对比实验；当前 canonical 方法为 `sgd_candidate_search / critic_adamw_optimizer / mask_guided_optimization`。三者从同一简单提示词和同一批 15 条专业命名实体 gold 出发，达到 `15/15` 即成功，否则连续 5 轮 loss 无下降才停止，默认最多 30 轮。报告中的最佳方法、最佳 loss 和最佳提示词按历史最优接受版本计算，不用最后一轮快照误导方法排名。统一 CLI 会输出 Markdown 报告、完整 JSON trace 和提示词演化 JSONL。

`v4.5.2` 将“定义与规范”里的 prompt training 从同步等待升级为后台轮询：点击后创建 `WorkflowRun(status=running)`，后台线程执行三方法训练并把 `RunProgressEvent` 写入 SQLite。页面每 2 秒显示阶段、ETA、调用数、token、修复次数、当前最佳方法和折叠日志；实验产物新增 `run_events.jsonl`。

`v4.5.3` 将默认运行库改为干净官方 demo 模式：Streamlit 进程重启时只刷新主 SQLite `.runtime/rosetta.sqlite3`，恢复唯一官方样例“专业命名实体标注”、15 条金样例和基础提示词，不删除 `.runtime/experiments/`、导出报告、PDF、HTML 或其他 artifact。

`v4.5.4` 将“验证概念”补齐为可见的并发验证：真实 LLM 模式会并发检查 15 条 gold，默认并发上限 `50`；页面显示进度条、运行中数量、已用时、ETA、调用数、token 和模型耗时。

`v4.5.5` 先做文档契约升级：Prompt training 不再被描述为“让 LLM 改整段提示词”，而是拆成可优化的 `ConceptPromptSpec` 和冻结的 `Frozen OutputProtocolSpec`。概念定义、边界规则和排除规则可以训练；标签、JSON schema、`[span]{Term}` markup、parser 和 format repair 指令由 harness 注入并冻结。后续统一代码实现必须先严格解析 JSON+markup，格式失败最多修复 2 次，repair 成功后才计算 semantic loss；实验报告要拆分 format failure、repair success 和 semantic loss。

`v4.5.6` 将主流程命名收敛为更贴近用户动作的 `项目总览 -> 定义与规范 -> 批量标注 -> 审核与修正 -> 结果与导出`。“定义与规范”页面顶部新增任务摘要，先告诉用户这里要完成项目选择、规范确认、金样例维护、提示词验证和定义优化，而不是直接进入表单。

`v4.5.7` 将“定义与规范”页面升级为强 harness 视图：页面直接分出 `ConceptPromptSpec` 和 `Frozen OutputProtocolSpec`。前者包含任务定义、概念定义、边界规则和排除规则，是 prompt training 的唯一优化对象；后者包含标签、JSON 字段、annotation markup、parser contract 和 format repair，由系统锁定注入。代码侧也先把候选生成提示词收紧为 concept-only，候选带回标签或输出格式时会剥离并记录 warning。

`v4.5.14` 将“提示词验证 / 提示词优化”改成页面内两张更大的入口按钮，当前选中项带主按钮态和勾选标记，下面配简短说明卡，更像两个子页。

`v4.5.15` 新增 debug 模式下的 `/debug` 调试追踪页。使用 `--debug` 或 `ROSETTA_DEBUG_MODE=1` 启动后，可访问 `http://localhost:8501/debug`，页面按可展开子对话窗完整展示每次 LLM 调用的 system prompt、user prompt、assistant response、provider、model、temperature 和耗时。该日志会保存完整语料与模型回复，只建议本机排障使用。

`v4.5.17` 修正 debug 模式直达 `/debug` 的入口体验：`http://localhost:8501/debug` 不再显示强制 debug notice，也不会因 notice 未确认触发 `st.stop()`；普通页面仍保留现有 debug notice。

`v4.5.18` 将通用标注 prompt 的相似样例位置固定化：运行时 prompt 现在是 `概念定义 -> 相似参考样例 -> 标注格式 -> 通用格式示例 -> 待标注文本 -> 任务强调`。`examples` 继续只用于标签推断；只有 `reference_examples` 或 top-k / 批量上下文显式传入时，才会把相似样例写入 prompt，避免普通 gold 样例被误当 few-shot 答案注入。

`v4.5.16` 将 `/debug` 改成隐藏导航的实时日志页：debug 模式下仍可直接访问 `http://localhost:8501/debug`，但不出现在主导航中；页面默认读取最新 debug session，每 `2` 秒自动刷新，优先显示 `llm_chat`，同时保留历史日志切换、事件筛选和 prompt / response 搜索。

`v4.5.13` 将“定义与规范”的定义输入面板进一步清理为 `当前定义与金样例`：项目区直接提供 `新建项目` 按钮；定义区把 `选择概念` 和编辑表单合并，用户可选已有定义直接编辑，也可选择 `新建定义`。表单只保留当前定义名称、当前概念阐释、金样例格式、标注输出协议、上传金样例和可选 JSONL 粘贴。金样例格式默认 `自动识别`，会根据扩展名和首条记录识别 `text + annotation` JSONL、Prodigy/Rosetta spans JSONL 或 CSV。

`v4.5.8` 将“定义与规范”的新概念表单收紧为更符合用户心智的输入契约：用户填写概念名称、概念描述或定义，并通过选项选择冻结的标注输出协议。标签不再手填，而是从 gold span label 自动推断，默认 `Term`；普通 span 任务允许模型运行时返回简单 `JSON + [span]{Term}`，Rosetta 会解析为统一 AnnotationDoc / Prodigy-compatible 存储结构，relation / attributes / 多层任务可选择完整 `AnnotationDoc` JSON。

`v4.5.9` 将运行时标注 prompt 固定为统一框架，`v4.5.18` 后完整顺序为：`概念定义 -> 相似参考样例 -> 标注格式 -> 通用格式示例 -> 待标注文本 -> 任务强调`。概念验证、候选回测、单条标注和批量标注共享这个框架；格式示例只说明 JSON / markup / AnnotationDoc 的返回结构，不使用当前任务 gold 答案，输出协议也不再被拼进可优化概念定义。

`v4.5.10` 进一步收紧标注调用和 reflection 反馈：概念验证、候选回测、单条标注和批量标注共享同一个 system prompt `你是严谨的标注助手，只输出 JSON。`；`llm_reflection` 的训练反馈先展示当前可优化提示词，再按失败 detail 就近列出原文、gold `[span]{Term}`、模型 JSON 回答和错误摘要。批改对照仍只用于 `training_feedback_only=true`，最终提示词继续保持 concept-only。

`v4.5.12` 将提示词优化三方案正式命名为 `sgd_candidate_search / critic_adamw_optimizer / mask_guided_optimization`，旧 `llm_optimize_only / llm_reflection / text_gradient_adamw` 作为 alias 兼容。定义与规范页面默认三方案全选，也可单独运行；后台日志展示 candidate generation、candidate 回测、critic evaluator/controller 和 mask ablation。真实 LLM 默认并发上限提升到 `50`，仍由 provider profile 与共享 semaphore 限制。同版还把 top-k 参考样例和批量上下文检索切到本地轻量 embedding：默认 `rosetta-local-hash-384` 使用 word/char n-gram feature hashing 与 `numpy` cosine，不调用智谱或 DeepSeek embedding API，不消耗 token，也不强制下载大模型权重。

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
6. `app/infrastructure`: provider profile、embedding、模型服务参数、token/cost 和限流边界。

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

## 更新历史

1. v4.5.22 已在文档站顶部新增 `中文 / English` 语言切换入口；`English` 不再作为中文导航栏栏目出现，英文路径补齐当前所有文档页面。
2. v4.5.21 已把官方文档站地址纠正回 `https://hy-liyihan.github.io/rosetta/`，并明确 `rosetta-stone.xyz` 是 demo 页面，不是文档站。
3. v4.5.20 已新增 [提示词构成](./user/PROMPT_COMPOSITION.md) 页面，按 `zh-CN / en-US` 对照说明 system prompt、六段 user prompt、冻结输出协议和定义优化边界，并用单元测试约束文档与程序模板同步。
4. v4.5.19 已把应用侧栏语言选择从下拉框改成 `中文 / English` 两个切换按钮；主导航和主要固定界面文案随按钮切换，用户输入、日志和模型输出不自动翻译。
5. v4.5.18 已把通用标注 prompt 的 `相似参考样例` 槽位固定到概念定义和冻结输出协议之间，并确保普通 `examples` 不会自动作为 few-shot 答案注入。
6. v4.5.17 已修正 debug 模式直达 `/debug` 被强制 notice 和 `st.stop()` 拦截的问题，普通页面 notice 行为不变。
7. v4.5.16 已将 debug 模式 `/debug` 调试追踪页改成隐藏导航的实时日志页，每 2 秒自动刷新 LLM prompt / response 子对话。
8. v4.5.15 已新增 debug 模式 `/debug` 调试追踪页，可完整查看 LLM prompt / response 子对话。
9. v4.5.14 已把“提示词验证 / 提示词优化”改成页面内两张大入口按钮，更像子页面切换。
10. v4.5.13 已把“定义与规范”的自定义输入清理为当前定义名称、当前概念阐释、金样例格式和上传/粘贴金样例。
11. v4.5.12 已把提示词优化三方案收敛为 canonical optimizer，将真实 LLM 默认并发上限提升到 50，并新增零 API / 零 token 的本地 embedding 检索。
12. v4.5.11 已把“定义与规范”主操作收敛为提示词验证和提示词优化，并新增 top-k 参考样例验证、三类优化方式和 v0-vn prompt 版本保存。
13. v4.5.10 已统一所有标注型调用的 system prompt 为同一个标注助手身份，并把 `llm_reflection` 反馈改为失败 detail 就近批改对照。
14. v4.5.9 已统一概念验证、候选回测、单条标注和批量标注的运行时 prompt 框架；v4.5.18 后完整顺序为：`概念定义 -> 相似参考样例 -> 标注格式 -> 通用格式示例 -> 待标注文本 -> 任务强调`。
15. v4.5.8 已把“定义与规范”的新概念表单收紧为概念名称、概念定义和标注输出协议选项；标签从 gold 自动推断，输出协议冻结。
16. v4.5.7 已把“定义与规范”页升级为强 harness 视图：可优化定义与冻结输出协议分栏展示，prompt training 候选生成只允许改概念语义，标签和输出格式会被剥离出候选提示词。
17. v4.5.6 已更新主流程命名：`项目总览 / 定义与规范 / 批量标注 / 审核与修正 / 结果与导出`，并在“定义与规范”顶部增加任务摘要。
18. v4.5.5 已文档化冻结输出协议与强格式 harness：prompt optimizer 只优化概念语义，输出协议由 JSON+markup parser 和 format repair contract 统一约束。
19. v4.5.4 已实现概念验证并发与页面进度条：真实 LLM 模式默认并发上限 50，并显示完成数、运行中数量、ETA、token 和耗时。
20. v4.5.3 已实现主运行库重启自动清洁：默认只保留官方“专业命名实体标注”项目、一个概念、15 条金样例和一个初始概念版本。
21. v4.5.2 已实现提示词优化训练后台运行、SQLite 实时进度事件、Definition & Guideline 轮询进度卡片、折叠日志和 `run_events.jsonl`。
22. v4.5.1 已实现三方法真实对比实验：每个方法连续 5 轮 loss 无下降才停止，默认最多 30 轮；CLI 输出 `comparison_report.md / comparison_result.json / prompt_evolution.jsonl`，并按历史最优接受版本汇总最佳提示词。
23. v4.5.0 已接入统一大模型服务运行时：DeepSeek 默认 `deepseek-v4-pro`，提示词验证和定义优化记录调用、token、耗时和修复统计；批量标注仍在逐步迁移到同一运行时。
24. v4.4.1 已实现提示词优化训练防背答案检查：训练反馈可看批改对照，最终可用提示词必须无语料和答案片段泄露。
25. v4.4.0 已实现提示词优化训练：同一批 15 条金样例比较三种定义优化方法，旧方法名只作为兼容 alias 保留。
26. v4.3.1 文档化 LLM service runtime 愿景：每次大模型调用都应作为服务调用被限流、排队、追踪、计费和可视化，默认并发上限当前收敛为 50。
27. v4.3.0 已实现 Prompt-as-Parameter 最小内核：prompt 分段、Mask 文本梯度、LLM-AdamW trace、长度惩罚和 loss 验证。
28. v4.2.4 将 Prompt-as-Parameter、Text Gradient 和 `LLM-AdamW` 写成核心方法框架。
29. v4.2.3 将文档重构为 user / developer / research claims 三条入口，并记录 6 轮三角色文档评审。
30. v4.2.2 将概念自举升级为 loss-guided candidate search：每轮比较当前概念和候选概念的 gold loss，只接受变好的版本。
31. v4.2.1 修正概念自举修订：最终提示词只保存干净概念阐释，失败摘要、样例编号和模型原始响应只进入日志与 metadata。
32. Streamlit 仍是唯一正式 UI。
33. 项目总览收敛为轻量状态入口，定义与规范启动即显示“专业命名实体标注”官方样例。
34. 定义与规范主界面负责提示词验证和提示词优化，批量标注负责 TXT/JSONL/CSV 导入和本地任务队列。
35. 审核与修正按置信度、抽检和错误类型逐条展示待审核样本，并沉淀 hard examples。
36. Prodigy-compatible JSONL 不推翻，只增强 project/run/session/job 层。
37. 旧 `research/corpusgen` 暂不删除，作为 compatibility wrapper 的实现来源。

## 维护规则

1. 代码或行为变更必须同步更新 [CHANGELOG.md](./CHANGELOG.md)。
2. 用户使用方式变化必须同步更新根目录 [README.md](https://github.com/HY-LiYihan/rosetta#readme)。
3. 文档站导航由 [mkdocs.yml](../mkdocs.yml) 维护。
4. 文档重大调整要按 [Documentation Review Iterations](./developer/DOCS_REVIEW_ITERATIONS.md) 的三角色方式检查。
5. 每个可验收子步骤一个 commit，commit message 使用 `stageX-scope: summary`。
