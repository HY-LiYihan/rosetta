# Changelog

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
4. `pages/Home.py` 改为使用 `ensure_core_state()`，移除重复状态初始化代码。
5. `pages/Concept_Management.py` 改为调用 concept service，移除页面内重复业务逻辑。
6. `pages/Annotation.py` 改为调用 state/service，移除页面内 prompt 组装与解析细节。
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
