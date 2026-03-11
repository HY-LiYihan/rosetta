# Rosetta 开发架构（详细版）

更新时间: 2026-03-11

## 1. 总体结构

当前项目采用单应用 + 分层目录架构：

```text
rosetta/
  streamlit_app.py               # 页面注册与全局样式
  pages/                         # Streamlit 页面（兼容层）
  app/
    state/                       # session_state 生命周期
    domain/                      # 数据模型、schema、校验
    services/                    # 业务编排层
    infrastructure/llm/          # LLM provider 适配层
  scripts/                       # 部署/运维脚本（分层）
  tests/                         # unit + integration
  docs/
    developer/                   # 开发文档
    user/                        # 用户文档
```

## 2. 启动与执行链路

1. 入口 `streamlit_app.py`
- 设置页面配置与最小 CSS 覆盖。
- 通过 `st.navigation` 注册三个页面。

2. 页面层 `pages/*`
- 页面只负责交互和渲染。
- 首行调用 `ensure_core_state()` 初始化共享状态。
- 页面不直接实现复杂业务规则。

3. 状态层 `app/state/session_state.py`
- 统一初始化：`concepts`、`annotation_history`、`concepts_data_version`。
- 从 `concepts.json` 读取时走 `domain.normalize_payload`。

4. 领域层 `app/domain/*`
- `schemas.py` 定义数据版本与字段要求。
- `validators.py` 执行规范化并抛出结构化校验错误（`field/reason/hint`）。

5. 服务层 `app/services/*`
- `concept_service.py`: 导入/导出、预检摘要、合并策略。
- `annotation_service.py`: prompt 构建、响应解析、历史记录生成。
- `platform_service.py`: 平台探测、模型列表、聊天请求编排。

6. 基础设施层 `app/infrastructure/llm/*`
- `providers.py` 管理平台配置。
- `base.py` 提供 OpenAI 兼容 provider。
- `registry.py` 管理 provider 获取与配置导出。

## 3. 双环境架构

1. 服务器环境（Docker）
- 入口脚本：`scripts/deploy/deploy.sh` / `scripts/deploy/update.sh`
- 健康检查：`scripts/ops/healthcheck.sh`

2. 开发环境（Conda）
- `conda env create -f environment.yml`
- `streamlit run streamlit_app.py`

## 4. 核心数据流

### 4.1 概念导入

1. 页面读取上传 JSON。
2. `validate_import_payload` 做结构校验。
3. `build_import_preview` 生成预检摘要（版本/重复数/自动修复数）。
4. 用户确认后执行 `replace_concepts` 或 `merge_concepts`。
5. 写回 `st.session_state` 并更新 `concepts_data_version`。

### 4.2 文本标注

1. 页面选概念 + 输入文本。
2. `annotation_service.build_annotation_prompt` 生成 prompt。
3. `api_utils.get_chat_response`（门面）转发到 `platform_service`。
4. `annotation_service.parse_annotation_response` 解析 JSON。
5. `build_history_entry` 写入历史。

## 5. 可维护性约束

1. 页面层禁止写复杂业务逻辑。
2. 导入校验必须通过 `domain.validators`。
3. 新增平台只改 `infrastructure/llm/providers.py`。
4. 文档更新与代码改动同提交。

## 6. 更新项目时你优先看哪些文件

1. `docs/developer/ARCHITECTURE.md`（先看）
2. `docs/developer/ROADMAP.md`
3. `app/services/*`（业务变更）
4. `app/domain/*`（数据结构变更）
5. `pages/*`（交互变更）

