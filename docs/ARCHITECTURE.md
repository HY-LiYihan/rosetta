# Rosetta Architecture (V1)

更新时间: 2026-03-10

## 1. 背景与目标

Rosetta 目前是一个 Streamlit 单体脚本应用。升级目标不是一次性重写，而是通过分阶段重构，让系统具备以下能力：

1. 可扩展: 新增模型平台或存储后端时，不改页面层。
2. 可维护: 页面层不再承载核心业务逻辑。
3. 可测试: 业务逻辑可在不启动 Streamlit 的条件下测试。
4. 可部署: 服务器环境可通过 Docker 和脚本稳定发布。

## 2. 重构原则

1. 先文档后代码。
2. 每阶段只解决一类问题，避免大爆炸重构。
3. 保持行为兼容，优先结构重排。
4. 每项变更必须可测试、可观测、可解释。

## 3. 当前架构痛点

1. `pages/*` 重复初始化 `session_state`。
2. 页面层包含数据治理与业务编排，职责混杂。
3. `concepts.json` 的读写和校验分散在页面中。
4. LLM 平台细节暴露在页面逻辑周围，扩展风险高。
5. 自动化测试几乎只覆盖静态结构，无法拦截核心回归。

## 4. 目标分层架构

```text
rosetta/
  app/
    ui/
      pages/
      components/
      theme/
    state/
      session_state.py
      keys.py
    domain/
      models.py
      schemas.py
      validators.py
    services/
      concept_service.py
      annotation_service.py
      platform_service.py
    repositories/
      interfaces.py
      json_repository.py
    infrastructure/
      llm/
        base.py
        deepseek_provider.py
        kimi_provider.py
        qwen_provider.py
        zhipu_provider.py
        registry.py
      config/
        settings.py
  pages/                       # 兼容层，逐步 thin 化
  tests/
    unit/
    integration/
    regression/
```

## 5. 分层职责和边界

### 5.1 `app/ui`

职责:
1. 展示页面内容。
2. 收集用户输入。
3. 调用 service 获取结果并渲染。

禁止:
1. 直接访问 JSON 文件。
2. 拼接复杂业务 prompt。
3. 处理平台差异分支。

### 5.2 `app/state`

职责:
1. 统一初始化 `session_state`。
2. 维护 state schema 版本和迁移函数。
3. 暴露读写助手函数，减少页面直接访问 dict。

禁止:
1. 实现业务规则。
2. 直接调用外部 LLM。

### 5.3 `app/domain`

职责:
1. 定义核心实体（Concept、Example、AnnotationRecord）。
2. 校验输入输出结构。
3. 提供错误类型与错误信息规范。

禁止:
1. 依赖 Streamlit。
2. 依赖具体存储实现。

### 5.4 `app/services`

职责:
1. 业务编排。
2. 统一错误处理和返回结构。
3. 组织 repository/provider 调用顺序。

禁止:
1. 直接渲染 UI。
2. 包含与平台强耦合的底层请求细节。

### 5.5 `app/repositories`

职责:
1. 抽象数据读写接口。
2. 提供 JSON 实现与后续 DB 实现。
3. 支持导入导出与兼容迁移。

禁止:
1. 承担业务编排。
2. 使用 Streamlit session 作为持久化介质。

### 5.6 `app/infrastructure/llm`

职责:
1. 封装平台差异。
2. 提供统一 provider 协议。
3. 处理模型列表探测和请求错误标准化。

禁止:
1. 接触页面状态。
2. 负责业务场景 prompt。

## 6. 关键契约（接口优先）

### 6.1 Repository 协议

```python
class ConceptRepository(Protocol):
    def load_concepts(self) -> list[dict]: ...
    def save_concepts(self, concepts: list[dict]) -> None: ...
    def export_concepts(self) -> dict: ...
    def import_concepts(self, payload: dict, mode: str) -> dict: ...
```

### 6.2 Provider 协议

```python
class LLMProvider(Protocol):
    platform_id: str
    display_name: str

    def list_models(self, api_key: str) -> list[str]: ...
    def chat(self, api_key: str, model: str, messages: list[dict], temperature: float) -> str: ...
```

### 6.3 Service 协议

```python
class AnnotationService:
    def build_prompt(self, concept: dict, text: str) -> str: ...
    def parse_response(self, raw: str) -> dict | None: ...
    def build_history_entry(self, ...) -> dict: ...
```

## 7. 数据模型与版本策略

1. `concepts.json` 顶层引入 `version`（向后兼容）。
2. `Concept` 字段规范:
- `name: str`
- `prompt: str`
- `category: str`
- `examples: list[Example]`
- `is_default: bool`
3. `Example` 字段规范:
- `text: str`
- `annotation: str`
- `explanation: str`（可空字符串）
4. 导入流程统一为: `解析 -> schema 校验 -> 兼容迁移 -> 写入`。
5. 所有失败返回结构化错误，包含 `field`、`reason`、`hint`。

## 8. 状态管理策略

统一 state key:

1. `concepts`
2. `annotation_history`
3. `available_config`
4. `selected_platform`
5. `selected_model`
6. `state_version`

页面入口只做一次:

```python
from app.state.session_state import ensure_session_state
ensure_session_state()
```

## 9. 运行时架构（Dual-Env）

Rosetta 维护两套并行开发/运行环境：

1. Docker 环境（服务器部署与生产运行，默认）。
2. Conda 环境（本地开发与调试，默认）。

### 9.1 Docker 环境

生产部署采用单容器应用架构（可选反向代理）：

1. `rosetta-app` 容器运行 Streamlit。
2. 数据目录挂载在宿主机，容器无状态。
3. 发布和更新通过 `scripts/*.sh` 完成。

目录建议:

1. `/opt/rosetta/app` 代码目录。
2. `/opt/rosetta/data` 业务数据。
3. `/opt/rosetta/backups` 备份目录。
4. `/opt/rosetta/logs` 运维日志。

### 9.2 Conda 环境

本地开发统一使用 `environment.yml` 管理依赖，避免每位开发者手工安装差异：

1. 环境名固定为 `rosetta-dev`（可通过团队约定调整）。
2. Python 版本与 Docker 保持一致（3.11）。
3. `pip` 依赖继续来源于 `requirements.txt`，避免双份依赖清单漂移。
4. 本地运行入口与生产一致：`streamlit run streamlit_app.py`。

## 10. 可观测性与运维策略

1. 健康检查: `/_stcore/health`。
2. 错误日志: 标准输出 + 文件落盘。
3. 脚本日志: 每次部署/更新产生时间戳日志。
4. 故障回滚: 失败时恢复到上一镜像 tag。

## 11. 阶段映射

1. Stage 1: 结构重排（state/service），行为不变。
2. Stage 2: 领域模型、schema 和迁移。
3. Stage 3: provider 抽象替换 `api_utils.py`。
4. Stage 4: 测试体系完善。
5. Stage 5: CI 与发布流水线。
6. Stage 6: JSON 到 DB 的可选升级。

## 12. Stage 1 验收口径

1. 首页、概念管理、标注三页面功能兼容。
2. `session_state` 初始化从页面移除，统一到 `app/state`。
3. 关键业务流程由 `app/services` 复用。
4. 文档与代码同步提交。
