# Architecture (Developer)

更新时间: 2026-03-11

## 1. 目标

1. UI 与业务逻辑解耦。
2. 数据结构可校验、可迁移。
3. LLM 平台适配可插拔。
4. 双环境（Docker/Conda）一致可运行。

## 2. 代码结构

```text
rosetta/
  streamlit_app.py
  app/
    ui/
      pages/
        Home.py
        Concept_Management.py
        Annotation.py
      viewmodels/
        home_viewmodel.py
    state/
      keys.py
      session_state.py
    domain/
      models.py
      schemas.py
      validators.py
    services/
      concept_service.py
      concept_flow_service.py
      annotation_service.py
      annotation_flow_service.py
      platform_service.py
    repositories/
      base.py
      json_concept_repository.py
    infrastructure/
      llm/
        api_utils.py
        base.py
        providers.py
        registry.py
  scripts/
    deploy/
    ops/
    data/
    cron/
    lib/
  tests/
    unit/
    integration/
```

## 3. 关键层职责

1. `app/ui/pages/*`
- 负责页面渲染与交互。
- 调用 `state/service`，不实现复杂业务规则。

2. `app/ui/viewmodels`
- 负责页面展示数据聚合（如首页统计卡片）。

3. `app/state`
- 统一 session state 初始化。
- 通过 `keys.py` 统一维护状态键名。

4. `app/domain`
- 维护数据 schema 与验证器。
- 导入错误返回结构化字段：`field/reason/hint`。

5. `app/services`
- `concept_service`: 导入导出、预检摘要、合并替换。
- `concept_flow_service`: 概念导入/创建的页面流程编排。
- `annotation_service`: prompt 构建、响应解析、历史记录。
- `annotation_flow_service`: 标注流程端到端执行编排。
- `platform_service`: 平台探测、模型拉取、聊天编排。

6. `app/repositories`
- 数据访问抽象层。
- 当前 `json_concept_repository` 负责 JSON 文件读取/回退策略。

7. `app/infrastructure/llm`
- 平台配置注册。
- OpenAI 兼容 provider。
- `api_utils.py` 放在该层，作为页面侧统一调用入口。

## 4. 核心数据流

### 4.1 概念导入

1. 页面上传 JSON。
2. `validate_import_payload` 校验结构。
3. `build_import_preview` 输出版本、重复数、自动修复数。
4. 用户确认后 `replace_concepts` 或 `merge_concepts`。
5. 更新 `st.session_state.concepts` 与 `concepts_data_version`。

### 4.2 文本标注

1. 页面选概念/模型并输入文本。
2. `build_annotation_prompt` 生成提示。
3. `api_utils.get_chat_response` 转发到 `platform_service`。
4. `parse_annotation_response` 解析 JSON 并回写历史。

## 5. 当前技术债

1. 目前持久化仍是 JSON，数据库后端待 Stage 6。

## 6. 更新项目建议

1. 先读 [WORKFLOW.md](/Users/liyh/rosetta/docs/developer/WORKFLOW.md)。
2. 再改 `app/services` / `app/domain`。
3. 最后才动 `app/ui/pages/*`。
