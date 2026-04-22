# Changelog

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
