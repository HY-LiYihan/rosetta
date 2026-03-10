# Roadmap

更新时间: 2026-03-10

## 总体原则

1. 按 Stage 顺序推进。
2. 每阶段独立验收，可回滚。
3. 每阶段交付固定包含代码、文档、测试结论。
4. 服务器 Docker 与本地 Conda 环境保持依赖基线一致。

## Stage 0 文档基线（完成）

交付:

1. `docs/README.md`
2. `docs/ARCHITECTURE.md`
3. `docs/DEPLOYMENT.md`
4. `docs/TUTORIAL.md`
5. `docs/ROADMAP.md`
6. `docs/CHANGELOG.md`

验收:

1. 能从文档直接理解现状、目标与下一步。

## Stage 1 结构重排（已完成）

目标:

1. 创建 `app/state` 与 `app/services`。
2. 抽取重复状态初始化逻辑。
3. 页面仅承担展示与交互。
4. 维持现有行为兼容。
5. 重构 `scripts` 目录结构（按 deploy/ops/data/cron 分层）并保持兼容入口。

验收:

1. 路由不变、功能可用。
2. 页面不再包含大段重复初始化代码。
3. 业务流程可通过 service 复用。
4. `scripts` 分层清晰，原定时入口可继续使用。

## Stage 2 领域模型与数据治理（当前）

目标:

1. 定义 domain 模型和 schema。
2. 统一导入导出格式与版本。
3. 建立兼容迁移和错误提示。

验收:

1. 脏数据可识别且错误信息明确。
2. 导入导出可回放。

## Stage 3 平台适配重构

目标:

1. 引入统一 provider 接口。
2. 平台细节迁移到 `infrastructure/llm`。
3. 增加缓存、默认模型和失败回退。

验收:

1. 新增平台不改页面层代码。

## Stage 4 测试体系建设

目标:

1. 单元测试覆盖服务层核心逻辑。
2. 集成测试覆盖概念管理和标注主流程。
3. 回归测试覆盖关键历史问题。

验收:

1. 关键流程自动化验证可稳定运行。

## Stage 5 工程化与发布

目标:

1. 建立 CI（lint/test/build checks）。
2. 统一配置规范与运行手册。
3. 发布与回滚流程标准化。

验收:

1. 每次变更可自动验证与追踪。

## 执行纪律（新增）

1. 每完成一个可验收子步骤，必须执行一次 Git 提交。
2. 每次提交后立即推送到 GitHub 远端分支。
3. 提交信息需包含阶段编号与变更范围（示例：`stage1-docs: dual-env and deployment policy`）。

## Stage 6 存储升级（可选）

目标:

1. 在 repository 接口下新增 SQLite/PostgreSQL 实现。
2. 提供 JSON 到 DB 迁移与回滚方案。
3. 引入审计字段和版本治理。

验收:

1. 存储后端可切换，业务层无侵入。
