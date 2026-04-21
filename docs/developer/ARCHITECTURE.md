# Architecture (Developer)

更新时间: 2026-04-21

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
    corpusgen/
      contracts.py
      specs.py
      seeds.py
      planner.py
      generators.py
      judges.py
      runner.py
      memory/
        layers.py
        recall.py
        compression.py
    research/
      contracts.py
      config.py
      indexing.py
      prompting.py
      retrieval.py
      verifier.py
      runner.py
    ui/
      components/
        debug_notice.py
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
      config/
        runtime_flags.py
      debug/
        runtime.py
      llm/
        api_utils.py
        base.py
        providers.py
        registry.py
  scripts/
    corpusgen/
    deploy/
    ops/
    data/
    cron/
    research/
    lib/
  configs/
    corpusgen/
    research/
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
- 标注字符串格式由 [ANNOTATION_FORMAT.md](./ANNOTATION_FORMAT.md) 约束（`[原文]{标签}` / `[!隐含义]{标签}`）。

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

8. `app/infrastructure/config + debug`
- `runtime_flags.py` 解析运行开关（如 `--debug` / `ROSETTA_DEBUG_MODE`）。
- `debug/runtime.py` 负责调试日志与上传副本落盘。

9. `app/research`
- 负责科研流水线骨架，不直接依赖页面层。
- `config.py`: 研究任务配置解析。
- `prompting.py`: 操作化定义、负向约束与动态 few-shot prompt 组装。
- `indexing.py`: 基于 CPU 的向量索引构建、缓存与查询。
- `retrieval.py`: 提供 lexical/embedding 两种动态示例检索。
- `verifier.py`: 研究批处理的规则验证与冲突检测。
- `runner.py`: `preview/audit/batch` 级执行编排。

10. `app/corpusgen`
- 负责语料生成流水线骨架，不直接依赖页面层，也不依赖 `app/research/*`。
- `specs.py`: 语料 spec 解析。
- `seeds.py`: seed 文档切分。
- `planner.py`: 体裁与主题任务规划。
- `memory/*`: memory record、CPU index 与压缩上下文打包。
- `generators.py`: 生成 prompt 与 JSON 解析。
- `judges.py`: 规则检查与去重过滤。
- `runner.py`: `prepare/memory/plan/generate` 级执行编排。

## 3.1 科研流水线隔离约束

1. `app/research/*` 与 `app/corpusgen/*` 保持平行，不互相 import。
2. 允许共享的模块仅限通用基础设施，如 `app/infrastructure/llm/*`。
3. 运行目录、脚本入口、配置模板、文档说明分别独立维护。

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

1. 先读 [WORKFLOW.md](./WORKFLOW.md)。
2. 再改 `app/services` / `app/domain`。
3. 最后才动 `app/ui/pages/*`。
