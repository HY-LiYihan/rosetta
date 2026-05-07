# Changelog

## 2026-05-08

### Docs / Bilingual MkDocs navigation v4.5.23

1. 将文档站语言切换改为 `mkdocs-static-i18n` 驱动，不再手写固定首页 `extra.alternate` 链接；语言菜单会优先跳到当前页面的对应语言版本。
2. 为英文构建配置独立英文导航栏，英文页面显示 `Home / Quickstart / Research Claims / Workflows / Annotation Formats / Developer / Deployment / Changelog`，不再继承中文导航标签。
3. GitHub Actions 文档部署同步安装 `mkdocs-static-i18n`，确保 GitHub Pages 与本地严格构建使用同一插件。

### Docs / MkDocs language switcher v4.5.22

1. 在 [mkdocs.yml](../mkdocs.yml) 中新增 Material `extra.alternate`，让文档站顶部出现 `中文 / English` 语言切换入口；同时用 `not_in_nav` 避免 `English` 作为中文导航栏栏目出现。
2. 新增英文路径下的完整页面矩阵，覆盖当前中文导航中的所有文档页面，把英文介绍从中文首页中拆出。
3. 更新 [README.md](../README.md)、[docs/README.md](./README.md) 和首页页脚版本为 `v4.5.22`。

### Docs / Public docs site URL correction v4.5.21

1. 将公开文档站地址改回 GitHub Pages: `https://hy-liyihan.github.io/rosetta/`，并把 `rosetta-stone.xyz` 明确标为 demo 页面而不是文档站。
2. 同步更新 [mkdocs.yml](../mkdocs.yml)、[README.md](../README.md)、[docs/README.md](./README.md) 和首页页脚版本为 `v4.5.21`。
3. 修正之前把 demo 页面误写成官方文档站的公开入口表述。

### Docs / Prompt composition contract v4.5.20

1. 新增 [提示词构成](./user/PROMPT_COMPOSITION.md) 页面，按 `zh-CN / en-US` 对照说明标注 system prompt、六段 user prompt、冻结输出协议、定义优化 prompt 边界和维护同步规则。
2. `app/services/annotation_service.py` 将运行时 prompt 段落标题、system prompt 和协议说明抽成中英文模板常量；默认仍为 `zh-CN`，调用方可显式传入 `prompt_language="en-US"` 生成英文控制模板。
3. 新增单元测试检查提示词构成页是否包含程序里的中英文 system prompt 和运行时段落标题，降低 prompt builder 更新后文档漂移风险。
4. 更新 [用户教程](./user/TUTORIAL.md)、[docs/README.md](./README.md)、[README.md](../README.md)、[Annotation Format](./developer/ANNOTATION_FORMAT.md)、[Research Claims](./ideas/RESEARCH_CLAIMS.md)、[Prompt-as-Parameter](./ideas/PROMPT_AS_PARAMETER.md)、[Documentation Review Iterations](./developer/DOCS_REVIEW_ITERATIONS.md) 和首页版本为 `v4.5.20`。
5. 按审读意见收紧公开口径：界面语言不自动翻译用户输入或模型输出；15 条 gold 只用于启动、校准和演示；用户侧“自举校准”改为“定义优化”；top-k gold 验证不等同 held-out 泛化评测。

## 2026-05-07

### UX / Sidebar language buttons v4.5.19

1. 将应用侧栏语言切换从下拉框改为 `中文 / English` 两个按钮；当前语言按钮高亮并禁用，点击另一个按钮后立即切换主导航和主要固定界面文案。
2. 更新 [README.md](../README.md)、[docs/README.md](./README.md)、[用户教程](./user/TUTORIAL.md) 和首页页脚版本为 `v4.5.19`。
3. 明确语言切换不翻译用户输入、数据库内容、任务文本、模型输出、标签值、调试日志或导出文件名。

### Docs / Public homepage entry

1. 记录当时公开入口调整；其中曾误将 demo 页面写为官方文档站，已在 `v4.5.21` 纠正回 GitHub Pages。
2. 更新 [README.md](../README.md) 首屏入口，明确官方文档站、GitHub 项目地址和 Rosetta 的对外简介。
3. 更新 [docs/README.md](./README.md) 首页结构，把官方入口、项目简介和用户路径前置，避免公开文档首页只像内部索引。
4. 将 [docs/README.md](./README.md) 中的“当前阶段”栏目改名为“更新历史”，让首页更像面向外部读者的版本记录入口。
5. 更新 [用户教程](./user/TUTORIAL.md) 的快速使用表述，将旧的“自举校准”改为当前页面实际动作“提示词验证 / 定义优化”。
6. 根据新用户和 PLM/NLP 研究者角色评审，补充 [docs/README.md](./README.md) 的首次阅读路径、[用户教程](./user/TUTORIAL.md) 的 5 分钟官方样例和术语小抄、[Research Claims](./ideas/RESEARCH_CLAIMS.md) 的证据/假设边界，以及 [Bootstrap Experiments](./developer/BOOTSTRAP_EXPERIMENTS.md) 的 PLM baseline 公平协议和 canonical 方法名。
7. 更新 [Documentation Review Iterations](./developer/DOCS_REVIEW_ITERATIONS.md)，记录本轮公开网站首页与快速使用复查。
8. 根据严苛中文产品文案复查，删除公开文档中“5 个主页面正文同步切换”等过满功能承诺，将 [用户教程](./user/TUTORIAL.md) 的“语言切换”改为“界面语言”，并把 [README.md](../README.md) 与 [docs/README.md](./README.md) 中显眼的英文术语改为中文主导表述。
9. 根据事实一致性复查，修正批量标注运行时口径：提示词验证和定义优化已接入统一运行时，批量标注当前仍使用本地任务队列和页面线程池调用 provider；同时补齐用户教程中的 `相似参考样例` prompt 槽位。

### Fix / Annotation prompt reference slot v4.5.18

1. 通用标注 prompt 在 `概念定义` 和冻结 `标注格式` 之间固定预留 `相似参考样例` 槽位，统一概念验证、批量标注和单条标注的 prompt 结构。
2. `examples` 继续只用于标签推断，不再自动作为 few-shot 参考答案注入 prompt；只有 `reference_examples` 或 top-k / 批量上下文显式传入时才填充该槽位。
3. `validate_gold_examples()` 的 top-k 参考样例继续由本地 `rosetta-local-hash-384` 检索，并通过专门槽位注入，不再拼进可优化概念定义。
4. 批量标注将相似样例、边界远例作为 `reference_examples` 传给 prompt builder，输出协议仍由冻结 harness 单独注入。
5. 更新 [README.md](../README.md)、[docs/README.md](./README.md)、[Annotation Format](./developer/ANNOTATION_FORMAT.md) 和首页版本为 `v4.5.18`。

### Fix / Debug route notice bypass v4.5.17

1. Debug 模式下直接访问 `http://localhost:8501/debug` 时，不再展示强制 debug notice 弹窗，也不会因为 notice 未确认而 `st.stop()`。
2. 普通页面在 debug 模式下继续保留现有中英双语 notice 和 5 秒确认流程。
3. `/debug` 仍只在 debug 模式下可直达，继续保持隐藏导航但可访问的行为。
4. 新增 `app.ui.routing` 路径判断 helper 与单元测试，避免依赖 Streamlit 页面环境测试 URL path。
5. 更新 [README.md](../README.md)、[docs/README.md](./README.md)、[Deployment](./developer/DEPLOYMENT.md) 和首页版本为 `v4.5.17`。

### UX / Hidden live debug log page v4.5.16

1. `/debug` 继续只在 debug 模式下可访问，但不再显示在主导航中；需要排障时直接打开 `http://localhost:8501/debug`。
2. 调试追踪页从普通事件列表改成实时日志流：默认读取最新 debug session，每 2 秒自动刷新，并优先展示 `llm_chat` 事件。
3. 页面仍支持切换历史日志、事件类型过滤、关键词搜索和显示数量控制；每条 LLM 调用继续完整展示 system prompt、user prompt 和 assistant response。
4. 更新 [README.md](../README.md)、[docs/README.md](./README.md)、[Developer README](./developer/README.md)、[Deployment](./developer/DEPLOYMENT.md) 和首页版本为 `v4.5.16`。

### Feature / Debug LLM prompt trace page v4.5.15

1. Debug 模式新增 `/debug` 调试追踪页面；只有通过 `--debug`、`--debug-mode`、`--rosetta-debug` 或 `ROSETTA_DEBUG_MODE=1` 启动时才可访问。
2. `OpenAICompatibleProvider.chat()` 在 debug 模式下记录完整 LLM 对话，包括 provider、model、temperature、system/user messages、模型 response、耗时和异常摘要；普通模式不记录完整 prompt / response。
3. 调试追踪页按日志文件、事件类型和关键词筛选事件；每次 `llm_chat` 以可展开子对话窗展示完整 system prompt、user prompt 和 assistant response。
4. 调试日志仍写入 `.runtime/logs/debug/session_*.jsonl`，页面明确提示该模式会保存敏感语料和金样例，只建议本机排障使用。
5. 更新 [README.md](../README.md)、[docs/README.md](./README.md)、[Developer README](./developer/README.md)、[Deployment](./developer/DEPLOYMENT.md) 和首页版本为 `v4.5.15`。

## 2026-05-05

### UX / Section buttons for validation and optimization v4.5.14

1. “提示词验证 / 提示词优化”从小 radio 改为页面内两张大号入口按钮，当前选中项带主按钮态和勾选标记，更像子页面切换。
2. 每个入口按钮下方增加简短说明卡，分别解释“检查当前定义是否能稳定通过金样例”和“人工编辑或运行自动优化器训练当前定义”。
3. 这两个入口仍共享同一个 `concept_lab_active_section` 状态，但不再在 widget 之后手动写回同名 session_state，避免 Streamlit 状态冲突。
4. 更新 [README.md](../README.md)、[docs/README.md](./README.md)、[用户教程](./user/TUTORIAL.md) 和首页版本为 `v4.5.14`。

### UX / Clean definition and gold input panel v4.5.13

1. “定义与规范”的自定义定义面板重命名为 `当前定义与金样例`，不再展示边界说明、负例规则、单条样例原文和单条样例标注等分散输入。
2. 面板只保留核心输入：`当前定义名称`、`当前概念阐释`、`金样例格式`、`标注输出协议`、金样例上传和可选 JSONL 粘贴。
3. 新增金样例格式选择：`自动识别`、`JSONL: text + annotation`、`JSONL: Prodigy / Rosetta spans`、`CSV: 文本列`。默认自动识别会根据文件扩展名和首条记录判断 JSONL markup、Prodigy/Rosetta JSONL 或 CSV。
4. 项目选择区改为 `选择项目 + 新建项目` 按钮，不再把新建项目藏在“高级”折叠区。
5. `选择概念` 合并进 `当前定义与金样例` 面板：用户可选已有定义直接编辑，也可选择 `新建定义` 创建新定义；已有定义保存时会写回当前 guideline 并记录新的 ConceptVersion。
6. 保存时标签继续从 gold span 推断，输出协议仍是冻结 harness 的一部分；用户不需要手填标签集合，也不需要在定义面板里维护负例规则。
7. 更新 [README.md](../README.md)、[docs/README.md](./README.md) 和 [用户教程](./user/TUTORIAL.md)，并将首页版本更新为 `v4.5.13`。

### Feature / Prompt optimizer canonical methods and progress v4.5.12

1. Prompt training 三种自动优化器正式命名为 `sgd_candidate_search`（候选搜索优化 / SGD-like Candidate Search）、`critic_adamw_optimizer`（批判器 AdamW 优化 / AdamW-like Critic Optimizer）和 `mask_guided_optimization`（遮挡梯度优化 / Mask-guided Prompt Optimization）；旧 `llm_optimize_only / llm_reflection / text_gradient_adamw` 保留为 legacy alias。
2. `PromptTrainingConfig.methods` 默认运行三种 canonical id，`normalized()` 会把旧 id 转成新 id；CLI `prompt-training-experiment` 新增 `--methods`，支持逗号分隔 canonical id 或 legacy alias。
3. 候选搜索优化每轮只给当前可优化 prompt 和已接受历史摘要；批判器 AdamW 优化新增 Evaluator -> Controller -> Generator trace；遮挡梯度优化会对最多 5 个可优化片段做 Mask 回测并记录 `mask_loss_delta`。
4. “定义与规范”页面的提示词优化区域改为人工优化 + 三方案自动优化器 selector，默认三者全选，也可只运行一个；页面用持久 section radio 替代 tab，减少验证/优化/日志操作后回到第一个 tab 的问题。
5. 提示词验证和提示词优化的进度 UI 继续展示估算进度、阶段、完成数、运行中、ETA、调用数和 token；训练事件日志能看到 candidate generation、candidate 回测、critic evaluator/controller、mask ablation 等阶段。
6. 真实 LLM 默认并发上限从 `20` 提升到 `50`，仍由 provider profile 与共享 semaphore 约束；批量标注和 CLI 默认值同步改为 `50`。
7. 新增 `app/infrastructure/embedding`，提供 `rosetta-local-hash-384` 本地轻量文本嵌入：基于 word n-gram 与 char n-gram 的稳定 feature hashing，使用 `numpy` 归一化向量和 cosine 检索。
8. `标注验证（top-k 参考）` 和批量标注上下文构建改为复用本地 embedding 检索，不调用 DeepSeek、智谱或其他远端 embedding API，不消耗 token，也不需要下载 transformer 权重。
9. 新增 [Embedding Retrieval](./developer/EMBEDDING_RETRIEVAL.md)，说明 OpenWebUI 式可插拔 embedding backend 思路、当前本地 fallback 边界和后续可替换后端。
10. 更新 [README.md](../README.md)、[docs/README.md](./README.md)、[用户教程](./user/TUTORIAL.md)、[Architecture](./developer/ARCHITECTURE.md)、[LLM Service Runtime](./developer/LLM_SERVICE_RUNTIME.md)、[Developer README](./developer/README.md)、[Agent Onboarding](./developer/AGENT_ONBOARDING.md) 和 [Concept Bootstrap Pipeline](./developer/BOOTSTRAP_PIPELINE.md)，并将首页版本更新为 `v4.5.12`。

### UX / Prompt validation and optimization workspace v4.5.11

1. “定义与规范”页面主操作收敛为两个 tab：`提示词验证` 和 `提示词优化`。项目、金样例和冻结输出协议保留为前置配置，不再把自举校准、修订草案和导出作为页面主功能。
2. `提示词验证` 拆成三种验证：`格式验证`、`无样例标注验证`、`标注验证（top-k 参考）`。格式验证只做本地 ConceptPromptSpec / FrozenOutputProtocolSpec / gold span contract 检查，不消耗模型。
3. `标注验证（top-k 参考）` 为每条待验证 gold 按文本向量余弦相似度选择 top-k 参考金样例，默认可选 `2-15` 个，并把参考原文与标准 annotation 注入概念上下文；无样例验证保持 reference_k=0。
4. `提示词优化` 拆成三种方式：`人工优化`、`无样例自监督优化` 和 `类训练优化`。人工优化直接保存编辑框内容为新版本；无样例自监督优化只调用 `llm_optimize_only`；类训练优化第一版调用 `llm_reflection`。
5. 类训练优化默认每轮生成 5 个候选，逐个回测 15 条 gold，先选出本轮 loss 最低候选，再仅在其 loss 下降超过阈值时接受；一轮最多产生一个新提示词版本，连续多轮无提升或达到目标后停止。
6. `llm_reflection` 下一轮候选生成会接收已接受历史摘要：`旧 prompt -> 新 prompt -> loss 变化`，用于避免重复走无效方向。
7. Prompt training 结果新增 `prompt_versions`，并把当前 run 的 v0、v1 ... vn 接受版本写入 `ConceptVersion`，metadata 标记 `prompt_training_version=true`；最终 summary 版本仍用 `prompt_training=true` 兼容旧报告。
8. 更新 [README.md](../README.md)、[docs/README.md](./README.md)、[用户教程](./user/TUTORIAL.md) 和 [Concept Bootstrap Pipeline](./developer/BOOTSTRAP_PIPELINE.md)，并将首页版本更新为 `v4.5.11`。

### Fix / Reflection feedback and annotation assistant prompt v4.5.10

1. 概念验证、候选回测、单条标注和批量标注统一使用同一个 system prompt：`你是严谨的标注助手，只输出 JSON。`。workflow 差异只保留在 user prompt 的概念定义、标注格式、待标注文本和任务强调中。
2. 新增 `ANNOTATION_ASSISTANT_SYSTEM_PROMPT` 常量，避免概念验证、单条标注和批量标注各自维护“标注校验助手 / 批量标注助手 / 语言学助手”等不同身份。
3. `llm_reflection` 的优化 prompt 改为先展示当前可优化提示词，再展示逐条失败样例批改对照。
4. 每个失败 detail 块内就近组织 `原文 -> 标准答案 annotation -> 模型回答 JSON -> 错误摘要`，避免同一句的 gold 和 model answer 被分散到不同段落。
5. 失败对照优先使用概念验证 detail 中的 `model_raw_response`；如果缺失，则根据 parsed spans 重构一个安全的模型 JSON 摘要。
6. `ConceptVersion.description` 仍只保存 concept-only 的干净提示词；失败 detail、gold answer、model answer 和错误摘要只作为 `training_feedback_only=true` 的训练反馈，不进入最终 operational prompt。
7. 更新 [README.md](../README.md)、[docs/README.md](./README.md)、[用户教程](./user/TUTORIAL.md)、[Annotation Format](./developer/ANNOTATION_FORMAT.md) 和 [Concept Bootstrap Pipeline](./developer/BOOTSTRAP_PIPELINE.md)，并将首页版本更新为 `v4.5.10`。

### Fix / Unified annotation prompt contract v4.5.9

1. 概念验证、候选回测、单条标注和批量标注改用同一个运行时 prompt 框架：`请根据以下概念定义标注文本 -> 概念定义 -> 标注格式 -> 通用格式示例 -> 待标注文本 -> 任务强调`。
2. 移除概念验证 prompt 中的“不要参考金答案”表述，改为更自然的“请根据以下概念定义标注文本”。
3. 标注格式段落保留通用、概念无关的 JSON 示例；示例只说明输出结构，不再把当前任务 gold 或相似样例当作格式示例。
4. 批量标注上下文不再把“模型输出格式”混进概念定义；输出协议只由冻结标注格式段落注入。
5. `parse_annotation_response()` 接受空 `annotation` 字符串并转换为空 spans，匹配“没有目标片段时返回空字符串”的运行时协议。
6. 更新单元测试，固定四段式 prompt contract，并确认通用格式示例不会复制 gold 样例。
7. 更新 [README.md](../README.md)、[docs/README.md](./README.md)、[用户教程](./user/TUTORIAL.md)、[Annotation Format](./developer/ANNOTATION_FORMAT.md) 和 [Concept Bootstrap Pipeline](./developer/BOOTSTRAP_PIPELINE.md)，并将首页版本更新为 `v4.5.9`。

### UX / Concept form and output protocol selector v4.5.8

1. “定义与规范”临时概念表单收敛为 `概念名称 / 概念描述或定义 / 边界说明 / 标注输出协议 / 金样例`，不再要求用户手填标签集合和负例规则。
2. 标签集合从金样例 span label 自动推断；如果 gold 中没有标签，则默认使用冻结 span 标签 `Term`，继续作为输出协议的一部分，而不是概念优化参数。
3. 标注格式从自由文本框改为选项：`Span 标注：JSON + [span]{Term}` 和 `全量 JSON：AnnotationDoc`。前者是当前默认 span 标注路径，后者为 relation / attributes / 多层标注任务提供完整 JSON 协议入口。
4. `parse_annotation_response()` 现在同时接受 `annotation` 为 `[span]{Term}` 字符串和完整 AnnotationDoc dict；完整 JSON 会校验 `version / text / layers / spans` 基础结构。
5. 官方样例初始 operational prompt 只保留概念描述和边界规则，标签与输出格式留在冻结协议中注入。
6. 标注输出协议选择器移到表单外，切换选项时说明文字会即时刷新，不需要先提交表单。
7. UI 文案明确区分模型运行时返回格式与最终存储格式：模型可以返回简单 `[span]{Term}`，Rosetta 会解析为统一 AnnotationDoc / Prodigy-compatible 存储结构。
8. 更新 [README.md](../README.md)、[docs/README.md](./README.md)、[用户教程](./user/TUTORIAL.md)、[Concept Bootstrap Pipeline](./developer/BOOTSTRAP_PIPELINE.md) 和 [Prompt-as-Parameter](./ideas/PROMPT_AS_PARAMETER.md)，并将首页版本更新为 `v4.5.8`。

### UX / Definition guideline harness view v4.5.7

1. “定义与规范”页面新增强 harness 视图，将当前规范分为 `可优化定义 / ConceptPromptSpec` 和 `冻结输出协议 / FrozenOutputProtocolSpec` 两栏展示。
2. 新增 `app/workflows/bootstrap/prompt_spec.py`，提供 `ConceptPromptSpec`、`FrozenOutputProtocolSpec`、`strip_frozen_protocol_sections()` 和 guideline 转换 helper。
3. 提示词优化训练候选生成收紧为 concept-only：`llm_optimize_only / llm_reflection / text_gradient_adamw` 只要求输出任务定义、概念定义、边界规则和排除规则。
4. 候选提示词若带回标签集合、输出格式、JSON schema 或 annotation markup，会被剥离并记录 `removed_frozen_output_protocol` warning，避免三方法比较时把冻结协议当作可训练参数。
5. 概念验证和候选回测时由系统重新注入冻结标签、JSON 字段和 annotation 格式，使输出协议保持一致。
6. 更新 [README.md](../README.md)、[docs/README.md](./README.md)、[用户教程](./user/TUTORIAL.md) 和 [Concept Bootstrap Pipeline](./developer/BOOTSTRAP_PIPELINE.md)，并将首页版本更新为 `v4.5.7`。

### UX / Main navigation naming v4.5.6

1. 主导航中文命名更新为 `项目总览 / 定义与规范 / 批量标注 / 审核与修正 / 结果与导出`，替换原先偏后台或研究感的入口名称。
2. 首页页脚版本更新为 `v4.5.6`，项目总览和定义与规范的页面说明同步使用新命名。
3. “定义与规范”页面顶部新增任务摘要，说明这里需要完成项目选择、概念定义与边界/负例规则确认、15 条金样例维护，以及验证、自举校准或提示词优化训练。
4. 批量标注、审核与修正、结果与导出的提示文案同步调整，使主流程语言保持一致。
5. 更新 [README.md](../README.md)、[docs/README.md](./README.md)、[用户教程](./user/TUTORIAL.md)、[Architecture](./developer/ARCHITECTURE.md)、[Agent Onboarding](./developer/AGENT_ONBOARDING.md)、[Developer README](./developer/README.md)、[LLM Service Runtime](./developer/LLM_SERVICE_RUNTIME.md) 和 [Concept Bootstrap Pipeline](./developer/BOOTSTRAP_PIPELINE.md)，确保当前文档入口使用新名称。

### Docs / Frozen output protocol and annotation harness v4.5.5

1. 更新 [Prompt-as-Parameter](./ideas/PROMPT_AS_PARAMETER.md)，将 prompt 参数空间拆成可优化的 `ConceptPromptSpec` 和冻结的 `Frozen OutputProtocolSpec`；概念定义、边界规则和排除规则可训练，标签、JSON schema、markup、parser 和 format repair 指令不可被 optimizer 修改。
2. 更新 [Concept Bootstrap Pipeline](./developer/BOOTSTRAP_PIPELINE.md)，新增 `Annotation Harness Contract`：运行链路固定为 `ConceptPromptSpec -> inject Frozen OutputProtocolSpec -> LLM call -> strict JSON parse -> format repair loop -> semantic loss`。
3. 更新 [Annotation Format](./developer/ANNOTATION_FORMAT.md)，将运行时协议明确为 JSON+markup：核心字段为 `text / annotation / explanation`，`annotation` 使用 `[span]{Term}`，JSON 外不允许 markdown fence、额外 prose 或自由 schema。
4. 更新 [Bootstrap Experiments](./developer/BOOTSTRAP_EXPERIMENTS.md)，新增 ACTER `en/corp` 100 正例实验计划：任务名为“ACTER 反腐败术语抽取”，数据源为 `/Users/liyh/rosetta/tmp/acter_en_corp/gold_examples_first100_markup.jsonl`，模型为 DeepSeek `deepseek-v4-flash`，目标为 `100/100`。
5. 明确三种提示词优化方法共用同一个冻结输出协议、同一个 parser、同一个 format repair loop 和同一个 semantic loss；方法差异只来自如何优化概念语义。
6. 文档要求后续报告拆分 `format_failure_rate`、`format_repair_success_rate`、`semantic_loss` 和 `pass_count`，避免把格式错误混入概念 loss。
7. 更新 [README.md](../README.md)、[docs/README.md](./README.md) 和 [用户教程](./user/TUTORIAL.md)，用用户语言说明：用户负责写概念，Rosetta 负责固定输出格式、校验格式和修复格式错误。
8. 本轮只更新文档契约，不声称统一 format repair harness 已经在所有 workflow 中实现，因此不更新 Home 页脚版本。

## 2026-05-04

### Fix / Concurrent concept validation progress v4.5.4

1. `validate_gold_examples()` 新增 `concurrency` 和 `progress_callback`，网页概念验证现在会并发验证 15 条 gold；真实 LLM 模式默认并发上限为 `20`，本地结构验证保持轻量顺序执行。
2. 概念实验室“验证概念”按钮新增实时进度条、完成数、运行中数量、并发上限、已用时和 ETA；真实 LLM 验证完成后展示调用数、token、模型耗时和实际并发。
3. 新增回归测试，确认概念验证会实际并发执行，并为每条 gold 写出进度事件。
4. 首页页脚版本更新为 `v4.5.4`。

### Fix / Official sample runtime reset v4.5.3

1. 新增 `app/data/official_sample.py`，将官方样例统一命名为“专业命名实体标注”，内置 15 条金样例和不包含 gold 具体实体词的基础提示词；内部标签继续保持 `Term`。
2. 新增 `app/runtime/official_seed.py`，Streamlit 进程首次启动时默认刷新主 SQLite `.runtime/rosetta.sqlite3`，只保留官方项目、概念、金样例和初始概念版本。
3. 清理范围限于主 SQLite 业务表，不删除 `.runtime/experiments/`、导出报告、PDF、HTML 或其他 artifact；可用 `ROSETTA_RESET_RUNTIME_ON_START=false` 临时关闭。
4. 概念实验室移除旧的“一键填入示例”按钮，默认展示官方项目和 15 条金样例；自定义项目创建入口保留在高级折叠区，并提示重启后会恢复官方样例。
5. CLI 内置 prompt training case 默认改为 `professional-ner`，旧 `hard-science` case 名仍保留兼容。
6. 新增 [test_official_seed.py](../tests/unit/test_official_seed.py)，覆盖官方 seed 计数、脏数据清理、gold task 合法性和 operational prompt 不包含 gold 实体词。
7. 更新 [README.md](../README.md)、[docs/README.md](./README.md)、[用户教程](./user/TUTORIAL.md) 和 [Developer README](./developer/README.md)，说明启动即内置官方样例的新体验。
8. 首页页脚版本更新为 `v4.5.3`。

### Feature / Prompt training realtime progress UI v4.5.2

1. 新增 `RunProgressEvent` 领域模型与 SQLite 表 `run_progress_events`，`RuntimeStore` 支持写入、过滤、读取最新事件和更新 `WorkflowRun` 状态。
2. 新增 `app/runtime/progress.py`，提供 `ProgressRecorder`、安全 payload 净化、ETA 估算和 prompt training LLM 调用总量估算；事件默认不暴露 raw prompt、raw response、gold 原文或泄露词。
3. `LLMServiceRuntime` 新增 `event_sink`，每次 `call_queued / call_started / call_succeeded / call_failed / call_retried` 都可同步写入运行事件流，仍保持 provider 级并发上限 `20`。
4. `run_prompt_training_experiment()` 保持同步 API，但新增 `progress_recorder` 与外部 `run_id`，在方法开始、轮次开始、gold 验证、候选生成、修复、回测、接受/拒绝和完成时写入阶段事件。
5. 新增 `start_prompt_training_background_run()`，概念实验室点击“开始优化训练”后立即创建 `WorkflowRun(status=running)` 并启动后台 daemon thread；页面通过 SQLite 每 2 秒轮询当前 run，用户可以离开页面再回来查看。
6. 概念实验室新增“当前训练任务”进度卡片，展示状态、阶段、ETA、已完成调用、运行中调用、token、重试、修复次数、当前最佳方法、最佳通过数和最佳 loss；日志进入折叠区，支持按事件类型和阶段筛选，并可下载 `run_events.jsonl`。
7. `write_prompt_training_comparison_outputs()` 新增 `run_events.jsonl`，`comparison_report.md` 增加 Progress Summary 和 Timeline Summary。
8. 新增 [test_runtime_progress.py](../tests/unit/test_runtime_progress.py)，并扩展 LLM runtime 与 prompt training 测试，覆盖事件落盘、payload 净化、event sink、后台运行和四类输出产物。
9. 更新 [README.md](../README.md)、[docs/README.md](./README.md)、[LLM Service Runtime](./developer/LLM_SERVICE_RUNTIME.md)、[Concept Bootstrap Pipeline](./developer/BOOTSTRAP_PIPELINE.md) 和 [用户教程](./user/TUTORIAL.md)，明确 v4.5.2 的后台轮询、实时日志和事件产物。
10. 首页页脚版本更新为 `v4.5.2`。

### Docs / Agent onboarding context

1. 新增 [Agent Onboarding](./developer/AGENT_ONBOARDING.md)，作为给后续大模型、代码 agent 和新维护者的压缩上下文包，概括 Rosetta 的产品定位、当前服务实现、主 workflow、LLM service runtime、SQLite runtime store、CLI 和常见边界。
2. 更新 [docs/README.md](./README.md)、[Developer README](./developer/README.md) 和 [mkdocs.yml](../mkdocs.yml)，为 agent 快速接手文档增加入口。

## 2026-05-03

### Feature / Prompt training comparison experiment v4.5.1

1. `PromptTrainingConfig` 新增 `patience_rounds=5`、`stop_policy="patience_no_loss_improvement"`、`candidate_temperature=0.3` 和 `evaluation_temperature=0.0`，默认 `max_rounds` 调整为 `30`。
2. `run_prompt_training_experiment` 的停止逻辑从“第一轮无改进即停止”改为“每个方法连续 5 轮 loss 无下降才停止”；达到 `15/15` 仍会提前以 `stop_reason=reached_target` 成功结束。
3. 每个 method result 新增 `stop_reason`、`initial_loss`、`initial_pass_count`、`best_round_index`、`total_loss_delta`、`no_improvement_streak`、`accepted_round_count` 和 `evaluated_candidate_count`；每轮 trace 新增 `round_improved`、`round_loss_delta`、`round_best_candidate_id`、`no_improvement_streak_after_round` 和 `stop_reason_if_stopped`。
4. 新增 `write_prompt_training_comparison_outputs()` 和 `build_prompt_training_comparison_report()`，输出 `comparison_report.md`、`comparison_result.json` 和 `prompt_evolution.jsonl`，报告包含方法总表、每轮进化速度、候选状态和提示词演化；最佳方法、最佳 loss 和最佳提示词按历史最优接受版本计算，不被最后一轮波动覆盖。
5. 新增 CLI：`scripts/tool/rosetta_tool.py prompt-training-experiment`，默认使用内置“专业命名实体标注”15 gold，在隔离 runtime 中运行 DeepSeek `deepseek-v4-pro` 三方法对比实验，避免污染当前 UI 数据库。
6. 概念实验室 UI 新增“连续无下降轮数”，结果表新增停止原因、初始损失、损失下降、接受轮数和无下降连续轮数。
7. 更新 [README.md](../README.md)、[docs/README.md](./README.md)、[Concept Bootstrap Pipeline](./developer/BOOTSTRAP_PIPELINE.md)、[用户教程](./user/TUTORIAL.md)、[Developer README](./developer/README.md) 和 [Roadmap](./developer/ROADMAP.md)，明确 v4.5.1 的实验停止口径与结果产物。
8. 首页页脚版本更新为 `v4.5.1`。

### Feature / Concurrent LLM runtime and prompt repair v4.5.0

1. 新增 `app/infrastructure/llm/runtime.py`，提供 `LLMProviderProfile`、`LLMServiceRuntime` 和 provider 级共享 semaphore，将真实 API 默认并发上限提升到 `20`，并记录调用进度、token 估算、耗时、重试和最大实际并发。
2. 概念实验室的大模型 predictor 改为通过 `LLMServiceRuntime` 调用真实 provider；DeepSeek 默认模型保持 `deepseek-v4-pro`，提示词优化训练配置新增 `provider_id / model / concurrency / repair_leaked_candidates / max_repair_attempts`。
3. `run_prompt_training_experiment` 的三种方法可并发运行；每种方法内部的 15 条金样例验证和候选回测也可并发执行，所有调用共享 provider semaphore，避免多个 workflow 叠加后突破并发上限。
4. `MemorizationGuard` 从二元拦截升级为分级检查：`clean / soft_leak / critical_leak`，并区分原文 n-gram、gold span、runtime annotation 和模型 span。默认报告只展示 hash / count，raw matches 只在 runtime 内部传给修复模型。
5. 候选提示词如果泄露语料或答案片段，不再一票否决；系统会先调用 `repair_leaked_prompt()` 进行去语料化修复，要求删除具体词、短语、原句和答案片段，只保留抽象边界规则。修复最多 2 次，仍泄露时才记为 `memorization_repair_failed`。
6. 概念实验室提示词优化训练 UI 新增并发上限、真实模型、实际并发、总调用、总 token、模型耗时和修复尝试指标，并在折叠日志中展示 usage summary 与 repair summary。
7. 批量标注默认并发从 `4` 调整为 `20`，并将 UI 最大值收敛到全局默认上限 `20`。SQLite runtime store 增加 busy timeout，降低并发写入时的临时锁冲突。
8. 新增 [test_llm_runtime.py](../tests/unit/test_llm_runtime.py)，覆盖 provider semaphore 并发约束、usage 聚合和 progress event；更新 prompt training 和 memorization guard 测试，覆盖修复后接受、修复失败拒绝和分级泄露判断。
9. 更新 [README.md](../README.md)、[docs/README.md](./README.md)、[Architecture](./developer/ARCHITECTURE.md)、[LLM Service Runtime](./developer/LLM_SERVICE_RUNTIME.md)、[Concept Bootstrap Pipeline](./developer/BOOTSTRAP_PIPELINE.md)、[用户教程](./user/TUTORIAL.md)、[Developer README](./developer/README.md)、[Roadmap](./developer/ROADMAP.md) 和 [Prompt-as-Parameter](./ideas/PROMPT_AS_PARAMETER.md)，明确 v4.5.0 的真实 DeepSeek、默认并发 20 与去语料化修复边界。
10. 首页页脚版本更新为 `v4.5.0`。

### Fix / Prompt training anti-memorization guard v4.4.1

1. 新增 `app/workflows/bootstrap/memorization.py`，提供 `MemorizationGuard`、`CorpusFingerprint` 和 `LeakageCheckResult`，从 15 条 gold 的原文、标准答案、runtime annotation 以及每轮模型答案中抽取 hash 指纹。
2. `run_prompt_training_experiment` 区分 `training feedback prompt` 和 `learned operational prompt`：优化模型可以看到原文、标准答案和自己的错误回答作为批改参考，但候选提示词和最终提示词必须通过防背答案检查。
3. `llm_optimize_only` 继续不接收失败详情；`llm_reflection` 接收批改反馈；`text_gradient_adamw` 接收批改反馈、文本梯度方向、loss 和长度惩罚，但三者生成的候选都统一经过 `MemorizationGuard`。
4. 候选评估新增 `memorization_passed`、`blocked_terms_count`、`memorization_check`、`raw_feedback_allowed`、`prompt_length`、`llm_call_count`、`estimated_tokens` 和 `elapsed_seconds`；被发现复制语料或答案片段的候选会以 `memorization_guard_blocked` 拒绝，不进入 gold loss 回测。
5. `ConceptVersion.metadata` 和 prompt training artifact 新增 `no_corpus_memorization`、`memorization_policy`、`raw_feedback_allowed` 和 `leakage_summary`，主报告只展示 hash / count，不直接暴露被复制片段。
6. 概念实验室的提示词优化训练结果新增“最终提示词干净”“拦截候选数”“大模型调用”“估算 token”和“耗时秒”指标，并在折叠日志中展示防背答案检查摘要。
7. 新增 [test_memorization_guard.py](../tests/unit/test_memorization_guard.py)，覆盖 gold 原文、gold span、模型 span 和多词 n-gram 的拦截；更新 [test_prompt_training.py](../tests/unit/test_prompt_training.py)，覆盖训练反馈可看批改对照但最终提示词不可背答案。
8. 更新 [README.md](../README.md)、[docs/README.md](./README.md)、[用户教程](./user/TUTORIAL.md)、[Concept Bootstrap Pipeline](./developer/BOOTSTRAP_PIPELINE.md) 和 [Prompt-as-Parameter](./ideas/PROMPT_AS_PARAMETER.md)，明确本轮只证明 15 条 gold 内“未直接背答案且能通过”，不声明跨样本泛化。
9. 首页页脚版本更新为 `v4.4.1`。

### Feature / Prompt training experiment v4.4.0

1. 新增 `app/workflows/bootstrap/prompt_training.py`，提供 `PromptTrainingConfig`、`PromptTrainingResult` 和 `run_prompt_training_experiment`，把“简单任务描述 + 15 条金样例”升级为训练式 prompt 优化流程。
2. 第一版公平比较三种方法：`llm_optimize_only` 只要求大模型优化提示词；`llm_reflection` 告诉大模型失败点；`text_gradient_adamw` 使用当前 Text Gradient / `LLM-AdamW` trace、长度惩罚和 gold loss 验证。
3. 训练循环固定为评估当前 prompt、计算 gold loss、生成候选、净化候选、重新评估 15 条金样例、只接受 loss 下降候选，并以最多 5 轮达到 `15/15` 作为成功标准。
4. `ConceptVersion.metadata` 新增 `prompt_training`、`training_methods`、`best_method`、`method_comparison`、`target_pass_count`、`reached_target` 和 `training_trace_summary`；完整候选与 raw response 写入 runtime artifact。
5. 概念实验室新增“提示词优化训练”区域，支持选择方法组合、最大轮数、候选数、最小 loss 下降阈值和成功后自动应用，页面展示最佳方法、通过数、loss、最佳干净提示词和折叠训练日志。
6. 新增 [test_prompt_training.py](../tests/unit/test_prompt_training.py)，覆盖 baseline prompt 不泄露失败信息、三方法比较、失败不误标 stable、反思输出净化和 15 条金样例门槛。
7. 更新 [README.md](../README.md)、[docs/README.md](./README.md)、[用户教程](./user/TUTORIAL.md)、[Concept Bootstrap Pipeline](./developer/BOOTSTRAP_PIPELINE.md) 和 [Prompt-as-Parameter](./ideas/PROMPT_AS_PARAMETER.md)，明确提示词优化训练已进入 v4.4.0 最小可用实现。
8. 首页页脚版本更新为 `v4.4.0`。

### Docs / LLM service runtime and progress vision v4.3.1

1. 新增 [LLM Service Runtime](./developer/LLM_SERVICE_RUNTIME.md)，把每次大模型调用定义为服务调用，要求统一进入 provider profile、限流、重试、进度事件、token/cost 和 artifact 记录。
2. 当时明确全局默认并发上限为 `10`；v4.5.0 已按新的真实测试需求提升为 `20`。概念验证、概念自举、批量标注、LLM-as-a-judge 和语料生成都应受 provider profile 与共享 semaphore 控制。
3. 细化概念验证和概念自举的目标 UI：显示当前阶段、已完成/总数、运行中数量、预计剩余时间、token、成本、失败与重试。
4. 细化 ETA 计算、ETA 可信度、RunProgressEvent、TokenUsage、错误重试、限流、取消和预算耗尽等运行时契约。
5. 更新 [docs/README.md](./README.md)、[Developer README](./developer/README.md)、[Architecture](./developer/ARCHITECTURE.md)、[Roadmap](./developer/ROADMAP.md) 和 [mkdocs.yml](../mkdocs.yml)，为后续 v4.4-v4.6 实现提供入口。

### Feature / Prompt-as-Parameter optimizer core v4.3.0

1. 新增 `app/workflows/bootstrap/prompt_optimizer.py`，提供 `PromptSegment`、`TextGradient`、`PromptOptimizationTrace`、prompt 分段、启发式 Mask 文本梯度、`LLM-AdamW` trace 和长度惩罚。
2. `run_concept_refinement_loop` 接入 prompt optimization context：每轮候选生成前根据当前 gold loss、失败详情和概念阐释片段估算改写方向。
3. 候选评估新增长度惩罚，避免靠无限加长 prompt 获得短期收益；只有惩罚后的 loss 明确下降才接受候选。
4. `ConceptVersion.metadata` 新增 `prompt_optimizer`、`prompt_optimization_trace`，候选评估中记录 `raw_loss_detail`、`prompt_optimization_trace`、loss delta、length delta 和 accepted 状态。
5. 大模型修订 prompt 增加“文本梯度信号”上下文，但仍要求只返回干净概念阐释正文，失败摘要、样例编号、漏标/多标诊断继续只进 metadata。
6. 新增 [test_prompt_optimizer.py](../tests/unit/test_prompt_optimizer.py)，覆盖 prompt 分段、梯度估算、trace 生成、长度惩罚和候选接受记录。
7. 更新概念自举循环测试，验证 `LLM-AdamW` trace、长度惩罚和干净提示词边界。
8. 更新 [README.md](../README.md)、[docs/README.md](./README.md)、[Concept Bootstrap Pipeline](./developer/BOOTSTRAP_PIPELINE.md)、[Prompt-as-Parameter](./ideas/PROMPT_AS_PARAMETER.md) 和 [Roadmap](./developer/ROADMAP.md)，明确 v4.3.0 是最小可用实现，并对齐 v4.4-v4.9 的架构、并发、进度、测试和实验报告路线。
9. 首页页脚版本更新为 `v4.3.0`。

## 2026-05-02

### Docs / Prompt-as-Parameter text gradient framework v4.2.4

1. 新增 [Prompt-as-Parameter](./ideas/PROMPT_AS_PARAMETER.md)，将概念 prompt 定义为可训练文本参数，并系统说明 Text Gradient、Prompt Loss 和 Prompt Optimizer。
2. 文档化四类文本梯度估算器：Mask 遮挡法、对比替换法、消融链路法和 LLM 自我诊断法。
3. 文档化 prompt 优化器类比：SGD、Momentum、Adam、AdamW、CMA-ES 和模拟退火，并将 `LLM-AdamW` 作为 Rosetta v1 概念优化器默认叙事。
4. 更新 [Research Claims](./ideas/RESEARCH_CLAIMS.md) 与 [Core Annotation Bootstrap](./ideas/CORE_ANNOTATION_BOOTSTRAP.md)，把 `Prompt-as-Parameter Optimization` 和文本梯度估算写为核心创新。
5. 更新 [Concept Bootstrap Pipeline](./developer/BOOTSTRAP_PIPELINE.md)，新增 Prompt Optimization Subsystem，规定未来 `PromptSegmenter / TextGradientEstimator / PromptOptimizer / CandidateGenerator / PromptOptimizationTrace` 边界。
6. 更新 [Bootstrap Experiments](./developer/BOOTSTRAP_EXPERIMENTS.md)，新增 prompt optimization ablation 和 prompt 长度增长、无效改写率等指标；v4.4.0 后 baseline 名称收敛为 `llm_optimize_only / llm_reflection / text_gradient_adamw`。
7. 更新 [README.md](../README.md)、[docs/README.md](./README.md)、[mkdocs.yml](../mkdocs.yml)、开发者入口和路线图，新增 Prompt-as-Parameter 文档入口。
8. 首页页脚版本更新为 `v4.2.4`。

### Docs / Research claims and documentation architecture v4.2.3

1. 新增 [Research Claims](./ideas/RESEARCH_CLAIMS.md)，明确 Rosetta 的核心证明目标：LLM agent 在低资源、概念可描述、任务边界会变化或任务不够常规的标注场景中，相比 PLM-first 流程具有样本效率、审核效率和可追溯优势。
2. 新增 [Documentation Review Iterations](./developer/DOCS_REVIEW_ITERATIONS.md)，记录 6 轮文档评审：传统语言学家、PLM 计量语言学家和 Rosetta 开发者分别提出问题，再逐轮优化文档。
3. 更新 [docs/README.md](./README.md) 与 [mkdocs.yml](../mkdocs.yml)，将文档站整理为用户入口、研究主张、workflow、标注格式、开发维护和部署运维。
4. 更新 [用户教程](./user/TUTORIAL.md)，新增“最少要知道的 4 个词”，强调用户可以按概念、15 条金样例、自举校准、批量标注、审核、导出的顺序直接使用。
5. 更新 [Core Annotation Bootstrap](./ideas/CORE_ANNOTATION_BOOTSTRAP.md) 与 [Bootstrap Experiments](./developer/BOOTSTRAP_EXPERIMENTS.md)，补齐 LLM agent vs PLM 的主张边界、常规数据集 / 非常规任务双实验线和 PLM low-budget / full-data baseline。
6. 更新 [Architecture](./developer/ARCHITECTURE.md)、[Developer README](./developer/README.md)、[Workflow](./developer/WORKFLOW.md) 和 [Roadmap](./developer/ROADMAP.md)，明确主数据流、代码落点、三角色文档评审和下一阶段路线。
7. 更新 legacy research / corpus docs，说明 `app/research` 与 `app/corpusgen` 只做兼容层和高级 workflow 来源，不再作为顶层产品边界。
8. 更新 [README.md](../README.md) 和首页页脚版本为 `v4.2.3`。

## 2026-05-01

### Fix / Loss-guided concept refinement v4.2.2

1. 概念自举从单路径贪心改写升级为 loss-guided candidate search：每轮先评估当前概念，再生成多个候选概念版本。
2. 每个候选版本都会回到 15 条金样例上试标，并计算 loss、通过数、失败数、漏标数、多标数和平均 span-F1。
3. 系统只接受 loss 明确下降的候选；如果没有候选变好，则保持当前最优概念并停止本轮搜索，避免“越优化越烂”。
4. 大模型修订 prompt 增加探索方向、失败片段上下文、应补/应排除片段类型，但最终仍只允许返回干净概念阐释正文。
5. `ConceptVersion.metadata` 新增 `optimizer/current_loss/selected_loss/loss_delta/accepted_candidate_id/candidate_evaluations`，用于复现每轮选择。
6. 概念实验室日志区展示 loss、loss delta、被接受候选和候选评估详情。
7. 新增完整概念自举电路测试，验证系统会选择让 gold loss 下降的候选，并拒绝无改进候选。
8. 首页页脚版本更新为 `v4.2.2`。

### Fix / Clean concept revision prompts v4.2.1

1. 概念自举修订不再把失败样例编号、失败摘要、漏标/多标诊断直接拼入 `ConceptVersion.description`。
2. 大模型修订任务简化为“只返回优化后的概念阐释正文”，系统侧负责保存失败详情、原始响应和净化警告。
3. 新增概念阐释净化 guard，拦截 `gold-000xx`、`失败摘要`、`修订建议`、`漏标`、`多标` 等诊断内容进入最终提示词。
4. 概念实验室新增“失败详情与修订日志”折叠区，最终概念版本草案只展示干净提示词。
5. DeepSeek 默认模型更新为 `deepseek-v4-pro`，并同步示例配置。
6. 新增概念自举净化、修订日志和默认模型单测。
7. 首页页脚版本更新为 `v4.2.1`。

### Feature / Concept bootstrap loop v4.2.0

1. 新增 `run_concept_refinement_loop`，正式自举要求 15 条金样例，并按轮次写入 `ConceptVersion.metadata`。
2. 概念实验室新增“开始自举校准”，展示每轮通过数、失败样例、失败摘要和最终概念版本草案。
3. 新增批量标注上下文构建器，prompt 现在包含稳定概念版本、相似样例、边界远例和失败模式摘要。
4. 批量候选评分从 exact signature 升级为 span-F1、完全一致率、模型自评和规则风险组合。
5. `Prediction.meta` 记录采样序号、共识分组、span-F1、规则风险和上下文样例 id。
6. 审核队列新增错误类型和 gold-like 晋升开关，审核保存会写入 hard example、人工修改和候选选择信息。
7. 导出报告升级为实验报告，包含概念版本、疑难样例、人工修改、候选一致性和主动审核反馈。
8. 更新 README、用户教程、架构文档和核心 idea 文档，明确主线是 concept bootstrap loop。
9. 新增概念自举、上下文构建、自洽性评分和审核反馈单测。
10. 首页页脚版本更新为 `v4.2.0`。

## 2026-04-29

### Fix / Busy button guard v4.1.2

1. 新增 `app/ui/components/busy.py`，为 Streamlit 长耗时动作提供两阶段按钮：点击后先重绘为禁用状态，再执行任务。
2. “概念实验室”的验证概念、生成修订草案、保存修订草案接入运行中禁用状态，按钮文案会切换为“正在处理…”，并配合 spinner 提示。
3. “批量标注”的提交任务接入运行中禁用状态，避免大文件解析或批量入库时重复提交多个任务。
4. “审核队列”的保存选择、保存手动修正、全部不对、跳过接入互斥禁用状态，任一动作运行时其余动作不可点击。
5. 全局 disabled 按钮样式改为低对比运行中样式，并关闭 hover / pointer 交互反馈。
6. 首页页脚版本更新为 `v4.1.2`。

### Fix / UI i18n and walkthrough example v4.1.1

1. 侧栏顶部新增全局 `中文 / English` 切换入口，不再把语言切换放在“设置”折叠区。
2. 扩展 `app/ui/i18n.py`，覆盖 5 个主页面的标题、正文、按钮、表单标签、提示和导出选项。
3. 工作台收敛为轻量状态入口，只保留核心指标、继续下一步、最近批量任务和最近审核状态。
4. 新增 `app/ui/examples.py`，内置“硬科学科普术语标注”完整案例和 15 条金样例 JSONL。
5. 概念实验室新增“填入硬科学术语示例”按钮，只填表单不自动保存。
6. 用户教程新增端到端填表示例，说明概念、批量标注、审核和导出各页该如何操作。
7. 新增 i18n 与示例数据单测，确认中英文 key 完整且 15 条金样例可解析为合法 `AnnotationTask`。
8. 首页页脚版本更新为 `v4.1.1`。

### Feature / Chinese-first batch annotation tool v4.1.0

1. Streamlit 默认导航收敛为 5 个中文主页面：工作台、概念实验室、批量标注、审核队列、导出与可视化。
2. 新增 `app/ui/i18n.py`，默认中文界面，并保留可选英文模式。
3. 新增概念实验室页面，支持创建项目、编辑概念阐释、保存金样例、验证概念、生成修订草案，并导出概念阐释和金样例。
4. 新增批量标注页面，支持 TXT / JSONL / CSV 导入、分句、轻量 tokenize、本地 SQLite 队列、后台执行和本地模拟。
5. 新增审核队列页面，按置信度阈值、自洽性和抽检策略逐条展示候选，支持保存选择、手动修正、跳过、全部拒绝和疑难样例标记。
6. 新增导出与可视化页面，支持按范围导出 Prodigy-compatible JSONL、报告和运行清单，并展示路由、标签和一致性分布。
7. 新增 `ConceptGuideline / GoldExampleSet / ConceptVersion / BatchJob / BatchJobItem` 领域模型，以及对应 SQLite 表。
8. 新增 `app/data/text_ingestion.py`、`app/data/exporters.py`、`app/workflows/annotation/batch.py`、`app/workflows/bootstrap/guideline.py` 和 `app/workflows/review/queue.py`。
9. 新增批量标注闭环单测，覆盖文本导入、概念验证、批量任务、审核决策和 JSONL round-trip。
10. 首页页脚版本更新为 `v4.1.0`。

### Feature / Agentic annotation tool architecture v4.0.0

1. 新增 `app/core`，定义 `Project / AnnotationTask / Prediction / ReviewTask / WorkflowRun / AgentStep` 统一领域模型。
2. 新增 `app/agents`，提供 `AgentKernel`、`ToolRegistry`、`ContextEngine` 和 reusable `Skill`。
3. 新增 `app/data`，提供 Prodigy-compatible JSONL round-trip 与 Label Studio edge adapter。
4. 新增 `app/runtime`，提供 runtime paths 和 SQLite `RuntimeStore`，用于本地保存 projects / tasks / predictions / reviews / runs / artifacts / agent_steps。
5. 新增 `app/workflows`，将 annotation / bootstrap / corpus / evaluation 作为用户可执行 workflow；旧 `research` / `corpusgen` 保留为 compatibility implementation。
6. `Annotate` 流程改为通过 `AgentKernel` 执行，旧 `annotation_flow_service` 作为 UI 兼容入口。
7. 新增统一 CLI [scripts/tool/rosetta_tool.py](../scripts/tool/rosetta_tool.py)，旧 `scripts/research/*` 与 `scripts/corpusgen/*` 保留并提示迁移。
8. Streamlit 导航改为 `Dashboard / Projects / Guidelines / Annotate / Review / Corpus Builder / Runs / Export / Settings / Tutorial`。
9. Dockerfile 改为构建期安装依赖，新增 `.dockerignore`，Compose 挂载 `/opt/rosetta/runtime`。
10. 更新 [README.md](../README.md)、[docs/README.md](./README.md)、[ARCHITECTURE.md](./developer/ARCHITECTURE.md)、[SCRIPTS.md](./developer/SCRIPTS.md)、[DEPLOYMENT.md](./developer/DEPLOYMENT.md) 和 [用户教程](./user/TUTORIAL.md)。
11. 首页页脚版本更新为 `v4.0.0`。

## 2026-04-28

### Docs / README and docs navigation refresh

1. 重写 [README.md](../README.md)，参考 `venom_vnv` 的入口组织方式，将文档站地址、快速入口、系统结构、快速开始、pipeline 和文档导航前置。
2. 重写 [docs/README.md](./README.md)，按用户路径、科研路径、数据格式、开发维护和当前阶段组织文档站首页。
3. 重写 [docs/developer/README.md](./developer/README.md)，按工程架构、标注格式、科研流水线、部署运维分组开发文档。
4. 更新 [mkdocs.yml](../mkdocs.yml)，补齐 Concept Bootstrap、Bootstrap Experiments、Annotation JSONL、核心想法等文档站导航入口，并启用更清晰的 Material 导航特性。

### Docs / Prodigy-compatible annotation JSONL format

1. 新增 [docs/developer/ANNOTATION_JSONL_FORMAT.md](./developer/ANNOTATION_JSONL_FORMAT.md)，系统记录 Rosetta 标注 JSONL 的来源、字段语义、约束和多类型标注示例。
2. 将 Concept Bootstrap 新写出格式收敛为 `rosetta.prodigy_jsonl.v1` / `rosetta.prodigy_candidate.v1`，顶层沿用 `text / tokens / spans / relations / label / options / accept / answer / meta`。
3. 更新 [app/research/bootstrap_io.py](../app/research/bootstrap_io.py) 与 ACTER 示例，使 normalized samples / candidates 写出 Prodigy-compatible JSONL，并继续兼容旧 `annotation.layers` 输入。
4. 更新 [README.md](../README.md)、[docs/README.md](./README.md)、[docs/developer/README.md](./developer/README.md)、[BOOTSTRAP_PIPELINE.md](./developer/BOOTSTRAP_PIPELINE.md) 和 [ANNOTATION_FORMAT.md](./developer/ANNOTATION_FORMAT.md)。
5. 首页页脚版本更新为 `v3.12.0`。

### Feature / Extensible annotation JSONL storage

1. 将 Concept Bootstrap 新写出格式从顶层 `spans` 升级为 `rosetta.annotation_jsonl.v1`，使用 `annotation.layers.spans` 存储 span，并预留 `relations / attributes / comments / document_labels` 扩展层。
2. 更新 [app/research/bootstrap_io.py](../app/research/bootstrap_io.py)，继续兼容旧顶层 `spans` 与 `gold_annotation` 输入，但 normalized samples / candidates 写出统一使用 Annotation JSONL。
3. 更新 ACTER 示例、实验配置、[BOOTSTRAP_PIPELINE.md](./developer/BOOTSTRAP_PIPELINE.md)、[ANNOTATION_FORMAT.md](./developer/ANNOTATION_FORMAT.md) 与 [README.md](../README.md)，明确存储格式与 LLM runtime markup 解耦。
4. 首页页脚版本更新为 `v3.11.0`。

### Docs / Core research idea archive

1. 新增 [docs/ideas/CORE_ANNOTATION_BOOTSTRAP.md](./ideas/CORE_ANNOTATION_BOOTSTRAP.md)，单独记录“15 个金样例 + 一句话概念描述 + 自洽性主动 refinement + 对比式检索”的核心科研设想。
2. 更新 [docs/README.md](./README.md)，新增 `Ideas` 文档入口，避免核心想法散落在对话中。
3. 补充 human-in-the-loop uncertainty triage：低自洽 / 低自评样本优先进入专家批改队列，并以多候选选择题降低人工标注成本。
4. 首页页脚版本更新为 `v3.1.0`，最后更新日期改为 `2026年4月28日`。

### Docs / Concept Bootstrap pipeline blueprint

1. 新增 [docs/developer/BOOTSTRAP_PIPELINE.md](./developer/BOOTSTRAP_PIPELINE.md)，将核心想法抽象为项目级研究流水线。
2. 更新 [docs/developer/ARCHITECTURE.md](./developer/ARCHITECTURE.md) 与 [docs/developer/RESEARCH_PIPELINE.md](./developer/RESEARCH_PIPELINE.md)，明确 bootstrap 属于 `research` 增强，且不依赖 `corpusgen`。
3. 更新 [README.md](../README.md)、[docs/README.md](./README.md) 与 [docs/developer/README.md](./developer/README.md)，加入 Concept Bootstrap 入口。
4. 明确 LLM prompt 标注格式与最终存储格式解耦：prompt 可用行内 `[span]{label}`，落盘统一为参考 Prodigy / spaCy span 表达的 JSONL。
5. 首页页脚版本更新为 `v3.2.0`。

### Feature / Bootstrap span JSONL contracts

1. 新增 [app/research/bootstrap_contracts.py](../app/research/bootstrap_contracts.py)，定义 concept bootstrap 的 `BootstrapSpan`、`BootstrapSample` 与 `BootstrapCandidate` 数据契约。
2. 新增 [app/research/bootstrap_io.py](../app/research/bootstrap_io.py)，支持 span JSONL 读写，并兼容旧的 `[span]{label}` 行内 gold annotation 输入。
3. 新增 [tests/unit/test_bootstrap_io.py](../tests/unit/test_bootstrap_io.py)，覆盖 offset 校验、legacy markup 转 span、JSONL 往返和 candidate confidence 校验。
4. 首页页脚版本更新为 `v3.3.0`。

### Feature / Bootstrap consistency scoring

1. 新增 [app/research/consistency.py](../app/research/consistency.py)，基于多候选 span set 计算 pairwise span-F1、exact-match rate、平均模型自评 confidence 与 uncertainty score。
2. 自洽性结果输出 `high / medium / low` 路由，为后续“低置信样本优先专家批改”提供稳定输入。
3. 新增 [tests/unit/test_consistency.py](../tests/unit/test_consistency.py)，覆盖空标注、部分重叠、完全一致、低一致性和分组评分。
4. 首页页脚版本更新为 `v3.4.0`。

### Feature / Bootstrap human review queue

1. 新增 [app/research/human_review.py](../app/research/human_review.py)，将低自洽 / 中自洽候选组转换为专家复核任务。
2. 每个复核任务包含候选 A/B/C... 与固定 `__manual__` 手动修正选项，把专家工作从开放式标注转为选择题优先。
3. 新增 [tests/unit/test_human_review.py](../tests/unit/test_human_review.py)，覆盖低置信队列、高置信跳过、任务字典化和候选排序。
4. 首页页脚版本更新为 `v3.5.0`。

### Feature / Bootstrap contrastive retrieval

1. 新增 [app/research/contrastive_retrieval.py](../app/research/contrastive_retrieval.py)，支持对每条 query 同时选择相似样例与少量边界远例。
2. 当前实现使用轻量 lexical similarity，保持可解释、低依赖；接口保留后续替换为 Embedding-3 CPU index 的空间。
3. 新增 [tests/unit/test_contrastive_retrieval.py](../tests/unit/test_contrastive_retrieval.py)，覆盖相似度、query 排除、similar/boundary 选择和字典化输出。
4. 首页页脚版本更新为 `v3.6.0`。

### Feature / Bootstrap label statistics and reflection plan

1. 新增 [app/research/label_statistics.py](../app/research/label_statistics.py)，从 gold / high-confidence 样本统计 token 的 entity/context/other 分布。
2. 新增 [app/research/reflection.py](../app/research/reflection.py)，基于统计结果生成 unseen token、possible false negative 与 boundary token 反思计划。
3. 新增 [tests/unit/test_label_statistics.py](../tests/unit/test_label_statistics.py) 与 [tests/unit/test_reflection.py](../tests/unit/test_reflection.py)。
4. 首页页脚版本更新为 `v3.7.0`。

### Feature / Bootstrap offline runner and CLI

1. 新增 [app/research/bootstrap_runner.py](../app/research/bootstrap_runner.py)，将 normalized samples 与 candidate runs 串联成离线分析产物。
2. 新增 [scripts/research/run_bootstrap.py](../scripts/research/run_bootstrap.py)，提供 `analyze` 子命令。
3. Runner 当前输出 normalized samples、candidate runs、consistency scores、human review queue、label statistics、reflection plans、retrieval traces 与 manifest。
4. 新增 [tests/unit/test_bootstrap_runner.py](../tests/unit/test_bootstrap_runner.py)。
5. 首页页脚版本更新为 `v3.8.0`。

### Feature / Bootstrap experiment templates

1. 新增 ACTER heart failure 风格实验入口：
- [acter_heart_failure.experiment.json](../configs/research/bootstrap/acter_heart_failure.experiment.json)
- [acter_heart_failure.samples.example.jsonl](../configs/research/bootstrap/acter_heart_failure.samples.example.jsonl)
- [acter_heart_failure.candidates.example.jsonl](../configs/research/bootstrap/acter_heart_failure.candidates.example.jsonl)
2. 新增 [docs/developer/BOOTSTRAP_EXPERIMENTS.md](./developer/BOOTSTRAP_EXPERIMENTS.md)，记录 ACTER 优先实验、baselines、指标和真实实验建议。
3. 更新 [docs/README.md](./README.md) 与 [docs/developer/README.md](./developer/README.md)，加入实验文档入口。
4. 首页页脚版本更新为 `v3.9.0`。

### Feature / Bootstrap report generation

1. 新增 [app/research/bootstrap_report.py](../app/research/bootstrap_report.py)，将离线分析产物汇总为 `report.md`。
2. 更新 [app/research/bootstrap_runner.py](../app/research/bootstrap_runner.py)，每次分析自动输出 `report.md`，并在 manifest 中记录 `report_path`。
3. 更新 [scripts/research/run_bootstrap.py](../scripts/research/run_bootstrap.py)，`analyze` 子命令新增 `--experiment` 参数。
4. 新增 [tests/unit/test_bootstrap_report.py](../tests/unit/test_bootstrap_report.py)，并更新 runner 测试确认报告落盘。
5. 首页页脚版本更新为 `v3.10.0`。

## 2026-04-26

### Feature / Annotation format migration — `[原文]{标签}` → AnnotationDoc (v3.0)

1. 新增 [app/domain/annotation_doc.py](../app/domain/annotation_doc.py)，提供结构化标注文档类型：
   - `legacy_string_to_spans()`：将 `[原文]{标签}` 字符串转换为带字符偏移量的 span 列表
   - `make_annotation_doc()`：组装完整 AnnotationDoc（version、text、layers、meta）
   - `validate_annotation_doc()`：校验 AnnotationDoc 结构合法性
   - `spans_to_legacy_string()`：将 spans 反向转为 `[原文]{标签}` 字符串（供 LLM prompt 注入）
2. [app/services/annotation_service.py](../app/services/annotation_service.py)：`parse_annotation_response()` 在验证 LLM 输出字符串后自动调用 `make_annotation_doc()` 将 annotation 字段转换为 AnnotationDoc；`build_annotation_prompt()` 支持 few-shot examples 的 annotation 字段为 dict 时自动转回字符串。
3. [app/domain/validators.py](../app/domain/validators.py)：`normalize_example()` 同时接受 str（legacy）和 dict（AnnotationDoc）两种格式，自动迁移 legacy 字符串。
4. [app/domain/schemas.py](../app/domain/schemas.py)：`DATA_VERSION` 从 `"2.0"` 升级到 `"3.0"`。
5. [app/ui/viewmodels/annotation_visualization.py](../app/ui/viewmodels/annotation_visualization.py)：`annotation_to_colored_html()` 支持 dict 输入，自动转换后渲染。
6. [app/ui/pages/Annotation.py](../app/ui/pages/Annotation.py)：新增 `_annotation_tokens()` 和 `_annotation_display_str()` helper，替换对 `extract_annotation_tokens` 的直接调用。
7. [app/research/runner.py](../app/research/runner.py)：`_annotation_signature()` 支持 AnnotationDoc dict 输入。
8. 新增 [scripts/migrate_annotation_format.py](../scripts/migrate_annotation_format.py)：一次性迁移脚本，将 `assets/concepts.json` 中所有 `annotation: str` 转换为 AnnotationDoc dict，并将 `version` 升级为 `"3.0"`。
9. 新增 [tests/unit/test_annotation_doc.py](../tests/unit/test_annotation_doc.py)，覆盖 4 个核心函数的 13 个测试用例。
10. 首页页脚版本更新为 `v3.0.0`，最后更新日期改为 `2026年4月26日`。

## 2026-04-23

### Refactor / Corpus pipeline unification — shared infra, concurrency, checkpoint

1. 新增 [app/corpusgen/utils.py](../app/corpusgen/utils.py)，提取 `strip_markdown_fences` 与 `dedupe_strings` 两个共享工具，消除 `generators.py`、`compression.py`、`corpus_studio_service.py`、`corpus_studio_flow_service.py` 中的重复实现。
2. [app/services/platform_service.py](../app/services/platform_service.py) 新增 `call_llm_with_repair()`，将 JSON 修复逻辑集中到 service 层；`corpus_studio_flow_service.py` 的 `_request_json_payload` 改为调用该函数，删除本地 `_build_json_repair_prompt`。
3. [app/corpusgen/runner.py](../app/corpusgen/runner.py) 提取 `_run_single_task()`，用 `ThreadPoolExecutor(max_workers=8)` 并行执行 LLM 生成任务，judge 阶段保持串行以保证去重确定性。
4. [app/corpusgen/runner.py](../app/corpusgen/runner.py) 新增 `resume_dir` 参数与 `checkpoint.jsonl` 断点续跑机制；[scripts/corpusgen/generate_corpus.py](../scripts/corpusgen/generate_corpus.py) 新增 `--resume-dir` 参数。
5. [app/services/corpus_studio_flow_service.py](../app/services/corpus_studio_flow_service.py) 提取 `_generate_batch()`，用 `ThreadPoolExecutor(max_workers=4)` 并行执行批次生成；新增 `session_dir` 参数，每批结果 append 写入 `batches.jsonl`。
6. [app/ui/pages/Corpus_Studio.py](../app/ui/pages/Corpus_Studio.py) 新增"断点续跑"折叠区，允许用户指定会话目录。
7. 更新单测 [test_corpus_studio_flow_service.py](../tests/unit/test_corpus_studio_flow_service.py)，将 mock 目标从 `flow_service.get_chat_response` 更新为 `platform_service.get_chat_response`。

## 2026-04-22

### Feature / Corpus Studio step-by-step page

1. 新增页面 [Corpus_Studio.py](../app/ui/pages/Corpus_Studio.py)，提供分步式语料生成工作台。
2. 新增服务层 [corpus_studio_service.py](../app/services/corpus_studio_service.py) 与 [corpus_studio_flow_service.py](../app/services/corpus_studio_flow_service.py)，支持：
- 一句话 brief 解析
- 标题候选与样稿方向生成
- 多轮策略重规划
- 样稿生成
- 批量语料生成
- 独立 judge 评估
3. 新增单测 [test_corpus_studio_service.py](../tests/unit/test_corpus_studio_service.py) 与 [test_corpus_studio_flow_service.py](../tests/unit/test_corpus_studio_flow_service.py)。
4. 更新 [streamlit_app.py](../streamlit_app.py) 导航，新增 `Corpus Studio` 页面入口。
5. 更新 [README.md](../README.md)、[docs/user/TUTORIAL.md](./user/TUTORIAL.md)、[CORPUS_PIPELINE.md](./developer/CORPUS_PIPELINE.md)、[ARCHITECTURE.md](./developer/ARCHITECTURE.md) 以说明新的页面化工作流。
6. 首页新增 `Corpus Studio` 快速入口，首页页脚版本更新为 `v2.13.0`，最后更新日期改为 `2026年4月22日`。

### Fix / Corpus Studio JSON repair and judge completeness

1. [corpus_studio_flow_service.py](../app/services/corpus_studio_flow_service.py) 新增 JSON repair fallback：当长批次生成返回非法 JSON 时，会自动发起一次“只修 JSON 不改语义”的修复调用，提升 `sample / corpus / judge` 阶段稳定性。
2. [corpus_studio_service.py](../app/services/corpus_studio_service.py) 的 judge prompt 不再截断文章正文，改为基于完整文章评估，修复“较长文章被误判为中途截断”的系统性偏差。
3. 新增与更新单测，覆盖 JSON repair fallback 与完整正文 judge prompt。
4. 用真实 `Corpus Studio` flow 完成了 10 篇英文硬科学科普新闻语料的端到端测试，并确认修复后的 judge 结果可用。
5. 首页页脚版本更新为 `v2.13.1`。

## 2026-04-21

### Feature / Corpusgen grounded corpus pipeline

1. 新增独立语料生成流水线目录 [app/corpusgen/](../app/corpusgen/)：
- `specs.py`: 语料 spec 解析
- `seeds.py`: seed 文档切分
- `planner.py`: 任务规划
- `memory/*`: context memory 压缩与 CPU 向量检索
- `generators.py`: 生成 prompt 与 JSON 解析
- `judges.py`: 质量规则检查与去重
- `runner.py`: `prepare / memory / plan / generate` 编排
2. 新增独立脚本入口 [scripts/corpusgen/](../scripts/corpusgen/)：
- `prepare_seeds.py`
- `build_memory.py`
- `plan_corpus.py`
- `generate_corpus.py`
3. 新增模板 [linguistics_zh_qa.json](../configs/corpusgen/domain/linguistics_zh_qa.json) 与 seed 示例 [linguistics_zh_seed.example.jsonl](../configs/corpusgen/domain/linguistics_zh_seed.example.jsonl)。
4. `corpusgen` 与 `research` 明确保持平行隔离，仅共享 `app/infrastructure/llm/*` 的底层 provider / 凭据能力。
5. 新增开发文档 [CORPUS_PIPELINE.md](./developer/CORPUS_PIPELINE.md)，并更新 [ARCHITECTURE.md](./developer/ARCHITECTURE.md)、[docs/README.md](./README.md)、[developer/README.md](./developer/README.md) 与 [README.md](../README.md)。
6. 新增单测覆盖 spec、memory recall 与 corpus runner。
7. 使用真实 `GLM-5 + Embedding-3` 完成了 1 个任务、2 条样本的 smoke run，验证 CPU index 与生成链路可运行。
8. 首页页脚版本更新为 `v2.12.0`。

### Feature / GLM-5 + Embedding-3 CPU retrieval

1. 新增本地凭据解析模块 [credentials.py](../app/infrastructure/llm/credentials.py)，研究流水线可在非 Streamlit 环境下自动读取 `.streamlit/secrets.toml` 中的 `zhipuai_api_key`。
2. 扩展 [base.py](../app/infrastructure/llm/base.py)：
- 新增 `embed()`，支持调用 `Embedding-3`
- 优化 chat 响应提取逻辑，兼容 `GLM-5` 的 `reasoning_content`
3. 更新 [providers.py](../app/infrastructure/llm/providers.py)，将智谱默认聊天模型更新为 `glm-5`，并默认关闭 `thinking` 以适配结构化科研标注输出。
4. 新增 [indexing.py](../app/research/indexing.py)，实现基于 `numpy` 的 CPU 向量索引构建、缓存与 top-k 相似度检索。
5. [retrieval.py](../app/research/retrieval.py) 从仅支持 `lexical` 扩展为支持 `lexical` 与 `embedding` 双检索策略。
6. [runner.py](../app/research/runner.py) 新增：
- `.streamlit/secrets.toml` 的 API Key 自动回退
- `build_index()` 入口
- `Embedding-3` 动态 few-shot 检索支持
7. [run_pipeline.py](../scripts/research/run_pipeline.py) 新增 `build-index` 子命令。
8. 新增智谱研究模板 [glm5_embedding3_template.json](../configs/research/glm5_embedding3_template.json)，默认使用 `GLM-5 + Embedding-3(512维)`。
9. 更新 [RESEARCH_PIPELINE.md](./developer/RESEARCH_PIPELINE.md) 与 [ARCHITECTURE.md](./developer/ARCHITECTURE.md) 以说明 CPU index 与双检索策略。
10. 首页页脚版本更新为 `v2.11.0`。

### Feature / Research lab pipeline bootstrap

1. 新增研究流水线骨架目录 [app/research/](../app/research/)：
- `config.py`: 研究配置加载与校验
- `prompting.py`: 研究 prompt 组装
- `retrieval.py`: lexical 动态 few-shot 检索
- `verifier.py`: 规则验证与逻辑冲突检测
- `runner.py`: `preview` / `batch` / `audit` 执行编排
2. 新增脚本 [scripts/research/run_pipeline.py](../scripts/research/run_pipeline.py)，支持：
- `preview`：预览单条样本的动态 prompt
- `run --mode batch`：执行批处理推断
- `run --mode audit`：执行带 gold 标签的审查流程并导出冲突样本
3. 新增研究配置模板 [configs/research/pilot_template.json](../configs/research/pilot_template.json) 与示例数据 [configs/research/pilot_dataset.example.jsonl](../configs/research/pilot_dataset.example.jsonl)。
4. 新增开发文档 [RESEARCH_PIPELINE.md](./developer/RESEARCH_PIPELINE.md)，说明当前研究流水线范围、运行方式与下一步演进方向。
5. 更新 [docs/README.md](./README.md)、[docs/developer/README.md](./developer/README.md)、[docs/developer/ARCHITECTURE.md](./developer/ARCHITECTURE.md) 以纳入研究流水线入口。
6. 新增单测覆盖研究配置、prompt 组装、验证器与批处理 runner。
7. 首页页脚版本更新为 `v2.10.0`，最后更新日期改为 `2026年4月21日`。

## 2026-03-12

### Docs / Markdown links fix

1. 修复 `README.md` 与 `docs/*` 中失效的本机绝对路径链接（`/Users/liyh/rosetta/...`）。
2. 统一改为仓库内相对路径，确保在 GitHub 和本地 Markdown 预览中均可跳转。
3. 同步更新首页页脚版本为 `v2.9.3`。

### Feature / User tutorial page

1. 新增页面 [Tutorial.py](../app/ui/pages/Tutorial.py)，在应用内直接展示用户教程文档。
2. 侧边栏导航顺序调整为：`首页 -> 使用教程 -> 概念管理 -> 智能标注`，其中“使用教程”固定为第二项。
3. 重写 [docs/user/TUTORIAL.md](./user/TUTORIAL.md) 为“网站使用版”，移除部署、Token 配置、运维脚本等非终端用户内容。
4. 首页页脚版本更新为 `v2.9.2`。

### Feature / Annotation history export

1. 在 [Annotation.py](../app/ui/pages/Annotation.py) 的「📜 标注历史」区域新增“下载全部历史”按钮，可一键导出当前 session 中的全部标注历史。
2. 新增导出构建函数 [annotation_service.py](../app/services/annotation_service.py)：
- `build_history_export_json(history)`：生成导出 JSON（含 `exported_at`、`history_count`、`history`）。
- `build_history_export_filename()`：生成时间戳文件名（如 `annotation_history_20260312_090807.json`）。
3. 新增单测覆盖导出文件名与导出 JSON 内容结构：`tests/unit/test_annotation_service.py`。
4. 首页页脚版本更新为 `v2.9.1`。

## 2026-03-11

### Format / Annotation V2

1. 新增统一标注格式校验模块 [annotation_format.py](../app/domain/annotation_format.py)。
2. 标注规范升级为：
- 显性标注：`[原文]{标签}`
- 隐含语义：`[!隐含义]{标签}`
3. `examples[*].explanation` 从可选改为必填且非空；导入校验同步升级。
4. 标注响应解析增加格式校验，不再接受旧格式 `[...] (...)`。
5. 迁移 [assets/concepts.json](../assets/concepts.json) 到 V2（版本 `2.0`），批量转换旧标注并补齐 explanation。
6. 概念管理页面编辑样例新增 explanation 输入项。
7. 新增文档：
- 用户文档更新 [TUTORIAL.md](./user/TUTORIAL.md)
- 开发文档新增 [ANNOTATION_FORMAT.md](./developer/ANNOTATION_FORMAT.md)
8. 新增测试：`test_annotation_format.py`，并更新相关单测与集成测以匹配新格式。
9. 修复 `assets/concepts.json` 中 `terminology` 概念样例的遗留格式：将 `[词]` 统一迁移为 `[词]{terminology}`，避免启动时回退默认概念。

### UX / Home navigation

1. 首页「核心功能」区域新增快速跳转按钮：
- 多模型支持 -> 智能标注页面
- 概念管理 -> 概念管理页面
- 智能标注 -> 智能标注页面
2. 首页页脚版本更新为 `v2.3`。

### UX / Annotation visualization

1. 在 [Annotation.py](../app/ui/pages/Annotation.py) 的「查看概念详情」样例区，新增标注可视化渲染：
- 按 `[]` 中被标注文本高亮显示
- 根据 `{}` 中标签稳定映射颜色
- 悬浮提示显示标签内容（tooltip）
2. 新增渲染器 [annotation_visualization.py](../app/ui/viewmodels/annotation_visualization.py)。
3. 新增单测：`tests/unit/test_annotation_visualization.py`。
4. 首页页脚版本更新为 `v2.4`。

### UX / Home core cards navigation refinement

1. 首页核心功能区移除额外小按钮，改为卡片标题文本直接可点击跳转（`st.page_link`）。
2. 跳转映射保持不变：
- 多模型支持 -> 智能标注
- 概念管理 -> 概念管理
- 智能标注 -> 智能标注
3. 首页页脚版本更新为 `v2.5`。

### UX / Annotation visualization refinement

1. 概念详情中的高亮文本不再显示中括号。
2. 为避免 tooltip 兼容性差异，改为在高亮片段后直接显示 `|标签`。
3. 首页页脚版本更新为 `v2.6`。

### UX / Home core cards clickable on original UI

1. 首页核心功能区取消额外链接控件，恢复原卡片视觉结构。
2. 跳转能力绑定到原卡片本体（整块圆角矩形可点击）：
- 多模型支持 -> `/Annotation`
- 概念管理 -> `/Concept_Management`
- 智能标注 -> `/Annotation`
3. 首页页脚版本更新为 `v2.7`。

### UX / Home core cards navigation adjustment

1. 核心功能区改为“仅原标题文字可点击跳转”，卡片视觉保持不变，不新增控件。
2. 跳转路径保持：
- 多模型支持 -> `/Annotation`
- 概念管理 -> `/Concept_Management`
- 智能标注 -> `/Annotation`
3. 首页页脚版本更新为 `v2.8.1`，开始采用三段式版本号（`主.次.修`）以标记 fix 类改动。

### UX / Annotation color rule update

1. 标注可视化改为“动态色相分配”规则：按当前标签数量分配颜色。
2. 绿色作为基准色（更深一点），背景保持白色，饱和度与亮度参数固定。
3. 两个标签时固定为绿色 + 红色；更多标签时按规则平均分配剩余色调。
4. 首页页脚版本更新为 `v2.8.2`。

### UX / Annotation color lightness tweak

1. 在保持既有配色规则不变的前提下，将标注颜色亮度小幅提升（视觉更浅）。
2. 首页页脚版本更新为 `v2.8.3`。

### UX / Annotation result visualization upgrade

1. 标注完成后的结果区新增 `JSON 结果（默认折叠）` 小标题，并将 JSON 默认折叠展示。
2. 新增“复制完整 JSON”按钮，可一键复制完整 JSON 文本。
3. 新增标注结果统计：标注片段数、标签种类、隐含标注数。
4. 新增标注结果可视化：按与概念详情一致的规则高亮，并展示标签分布表。
5. 首页页脚版本更新为 `v2.9.0`。

### Feature / Debug mode

1. 新增运行时开关解析 [runtime_flags.py](../app/infrastructure/config/runtime_flags.py)，支持 `--debug` 与 `ROSETTA_DEBUG_MODE=1`。
2. 新增调试运行时模块 [runtime.py](../app/infrastructure/debug/runtime.py)，可留存操作日志与上传副本。
3. 新增首次访问双语提示组件 [debug_notice.py](../app/ui/components/debug_notice.py)，5 秒倒计时后可关闭。
4. 在 `streamlit_app.py` 接入 debug 初始化与提示展示逻辑。
5. 标注与概念导入流程接入调试事件埋点，记录操作与中间结果（含导入文件副本）。
6. 调试日志落盘到 `.runtime/logs/debug/*.jsonl`，上传副本保存到 `.runtime/data/debug_uploads/`。
7. 新增单测：`test_runtime_flags.py`、`test_debug_runtime.py`。

### Refactor / service layering

1. 新增 `app/state/keys.py`，统一管理 `session_state` 键名常量。
2. 新增 `app/services/annotation_flow_service.py`，收敛标注端到端流程（调用、解析、历史记录构建）。
3. 新增 `app/services/concept_flow_service.py`，收敛概念导入预检与应用导入流程。
4. 新增 `app/repositories/base.py` 与 `app/repositories/json_concept_repository.py`，建立数据访问抽象并接入 `session_state`。
5. 新增 `app/ui/viewmodels/home_viewmodel.py`，收敛首页统计聚合逻辑。
6. 页面 `app/ui/pages/*` 改为优先调用 flow service + state keys，降低页面层业务耦合。
7. 新增单测：`test_annotation_flow_service.py`、`test_concept_flow_service.py`、`test_home_viewmodel.py`。

### Reliability / State observability

1. [app/state/session_state.py](../app/state/session_state.py) 为概念加载失败场景补充日志输出。
2. `load_concepts_from_file()` 不再静默吞掉异常，改为记录 warning/exception 后回退默认概念。

### Refactor / page relocation

1. 页面目录由根目录 `pages/` 迁移到 [app/ui/pages/](../app/ui/pages/)。
2. `streamlit_app.py` 的 `st.Page(...)` 路径全部更新为 `app/ui/pages/*`。
3. 页面内 `st.switch_page(...)` 路径全部同步更新。
4. 删除旧目录 `pages/`，实现 UI 层完全收敛到 `app/ui`。
5. 更新 [ARCHITECTURE.md](./developer/ARCHITECTURE.md) 的目录结构与职责描述。

### Refactor / api_utils relocation

1. 新增 [app/infrastructure/llm/api_utils.py](../app/infrastructure/llm/api_utils.py) 作为正式 LLM 调用入口。
2. [app/ui/pages/Annotation.py](../app/ui/pages/Annotation.py) 改为直接引用新位置的 `api_utils`。
3. 删除根目录 `api_utils.py`，不再保留兼容 shim。
4. 更新 [ARCHITECTURE.md](./developer/ARCHITECTURE.md) 以反映新模块位置。

### Runtime Layout / Docs Clarity

1. 引入统一运行目录变量 `ROSETTA_RUNTIME_DIR`（默认 `/opt/rosetta/runtime`）。
2. `scripts/lib/common.sh` 改为从 `ROSETTA_RUNTIME_DIR` 自动派生：
- `ROSETTA_DATA_DIR=${ROSETTA_RUNTIME_DIR}/data`
- `ROSETTA_BACKUP_DIR=${ROSETTA_RUNTIME_DIR}/backups`
- `ROSETTA_LOG_DIR=${ROSETTA_RUNTIME_DIR}/logs`
3. `.env.example` 重写为“主变量 + 可选覆盖”结构，减少配置理解成本。
4. `.gitignore` 增加 `.runtime/` 整目录忽略规则，避免本地/服务器运行产物进入版本库。
5. 更新 [SCRIPTS.md](./developer/SCRIPTS.md)、[DEPLOYMENT.md](./developer/DEPLOYMENT.md)、[README.md](../README.md)、[scripts/README.md](../scripts/README.md) 以匹配新目录约定。

## 2026-03-10

### Docs / Architecture V1

1. 重写 `docs/ARCHITECTURE.md`，补齐分层边界、接口契约、数据策略、运行架构。
2. 新增 `docs/DEPLOYMENT.md`，定义 Docker-first 服务器部署、更新、备份、回滚流程。
3. 重写 `docs/TUTORIAL.md`，明确重构开发流程与 Stage 1 边界。
4. 重写 `docs/ROADMAP.md`，细化 Stage 0-6 目标与验收口径。
5. 更新 `docs/README.md` 索引与推荐阅读顺序。
6. 新增 `environment.yml`，标准化 Conda 本地开发环境。
7. 新增 `.env.example`，标准化 Docker 部署环境变量模板。
8. 文档策略升级为双环境：Docker（服务器）+ Conda（本地）。
9. 路线图新增脚本目录分层改造计划（deploy/ops/data/cron/lib）。
10. 开发流程新增执行纪律：每个可验收步骤必须 commit 并 push 到 GitHub。

### Next

- Stage 1 代码改造将严格按上述文档执行。

### Stage 1 / Code Restructure (completed)

1. 新增 `app/state/session_state.py`，统一 `concepts`、`annotation_history`、平台配置与默认模型初始化。
2. 新增 `app/services/concept_service.py`，抽取概念导入导出、合并与创建逻辑。
3. 新增 `app/services/annotation_service.py`，抽取 prompt 构建、响应解析与历史记录构建逻辑。
4. `app/ui/pages/Home.py` 改为使用 `ensure_core_state()`，移除重复状态初始化代码。
5. `app/ui/pages/Concept_Management.py` 改为调用 concept service，移除页面内重复业务逻辑。
6. `app/ui/pages/Annotation.py` 改为调用 state/service，移除页面内 prompt 组装与解析细节。
7. 基础验证通过：`python -m compileall ...`、`python -m unittest discover -s tests -p 'test_*.py'`。
8. 全局样式改为 TOML 优先策略：`.streamlit/config.toml` 承担主题配置，`streamlit_app.py` 仅保留最小 CSS 覆盖。
9. `scripts/` 完成分层重构：新增 `deploy/ops/data/cron/lib`。
10. 新增标准脚本：`deploy.sh`、`update.sh`、`rollback.sh`、`healthcheck.sh`、`logs.sh`、`restart.sh`、`backup.sh`、`restore.sh`。
11. 旧入口 `scripts/daily_restart.sh` 与 `scripts/monthly_rebuild.sh` 改为兼容转发，不破坏现有 cron 路径。

### Stage 2 / Domain & Data Governance (completed)

1. 新增 `app/domain`：`models.py`、`schemas.py`、`validators.py`。
2. 概念导入导出开始引入版本化数据结构（`version` + `concepts`）。
3. 兼容旧数据格式（无 `version`），并在导入时进行规范化校验。
4. 新增 `tests/unit/test_domain_validators.py`，覆盖基础规范化与缺失字段异常场景。
5. 导入校验错误升级为结构化格式：`field / reason / hint`，并在概念导入页面显示。
6. 新增导入预检摘要：显示 `version`、重复概念数、自动修复字段数、可导入概念数。
7. 导出文件名加入版本和日期（如 `concepts_v1_0_20260310.json`），并在概念管理页面显示当前数据版本。

### Stage 3 / Platform Adapter (started)

1. 新增 `app/infrastructure/llm`，实现 OpenAI 兼容 provider 抽象与平台注册表。
2. 新增 `app/services/platform_service.py`，统一平台探测与对话调用编排。
3. `api_utils.py` 改为兼容门面，内部转发到 provider/service 层。
4. 新增 `tests/unit/test_platform_service.py`，覆盖平台探测核心逻辑。

### Stage 4 / Testing (completed)

1. 新增 `tests/unit/test_annotation_service.py`，覆盖 prompt 构建与响应解析。
2. 新增 `tests/unit/test_concept_service.py`，覆盖导出、替换、合并核心逻辑。
3. 新增 `tests/integration/test_import_flow.py`，覆盖导入预检到合并流程。
4. 测试执行统一为 `python -m unittest discover -s tests -p 'test_*.py'`。

### Stage 5 / Engineering (completed)

1. 新增 `.github/workflows/ci.yml`，包含编译检查、单元测试与脚本语法检查。
2. CI 使用 Python 3.11 与 `requirements.txt` 作为依赖基线。

### Docs / Classification Update

1. 文档分为两类：`docs/developer/`（开发）与 `docs/user/`（用户）。
2. 新增 `docs/developer/ARCHITECTURE.md`（详细架构说明）与 `docs/developer/WORKFLOW.md`（执行流程）。
3. 新增 `docs/user/TUTORIAL.md`（用户教程）。
4. 新增仓库级 `CLAUDE.md`，定义任务前必读与提交前检查清单。
5. 同步更新 `docs/README.md` 与仓库 `README.md` 文档索引。

### Docs / Cleanup

1. 删除已弃用的旧文档入口：`docs/ARCHITECTURE.md`、`docs/DEPLOYMENT.md`、`docs/ROADMAP.md`、`docs/TUTORIAL.md`。
2. 统一文档入口到 `docs/developer/*` 与 `docs/user/*`，避免重复维护。

### Repo / Root Cleanup

1. `concepts.json` 从根目录迁移到 `assets/concepts.json`，并同步更新加载与脚本路径。
2. 删除已弃用脚本 `test_concepts.py`，统一使用 `tests/` 自动化测试体系。
3. `api_utils.py` 保留为兼容门面（仍被页面调用），内部逻辑已下沉到 provider/service 层。

### Docs / README Simplification

1. README 调整为入口级文档，保留部署与导航信息。
2. 使用细节（API Key 配置、FAQ 等）下沉到 `docs/user/TUTORIAL.md`。

### Docs / Deployment & Link Style

1. README 的两种部署方式在“项目已存在”场景下增加 `fetch/pull` 更新命令。
2. 关键文档引用改为可点击链接格式，避免仅保留纯路径文本。

### Docs / Developer Refresh

1. 全量更新 `docs/developer/README.md`、`ARCHITECTURE.md`、`WORKFLOW.md`、`ROADMAP.md`、`DEPLOYMENT.md`。
2. 开发文档内容与当前代码、脚本、测试、CI 状态对齐。
3. 统一补充了可点击链接引用与 `/opt/streamlit` 路径约定。
