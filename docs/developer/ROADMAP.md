# Roadmap (Developer)

更新时间: 2026-03-11

## 阶段状态

1. Stage 1（结构重排）：已完成。
2. Stage 2（领域模型与数据治理）：已完成。
3. Stage 3（平台适配抽象）：已完成。
4. Stage 4（测试体系）：已完成。
5. Stage 5（工程化/CI）：已完成。
6. Stage 6（存储升级，可选）：未开始。

## Stage 6 预案

1. 定义 repository 抽象接口（若需补齐）。
2. 增加 SQLite 实现（最低成本）。
3. 增加 JSON -> SQLite 迁移脚本。
4. 增加回滚策略（SQLite -> JSON 快照）。
5. 补充 integration tests 覆盖 DB 模式。

## 验收口径

1. 页面层不感知存储后端变化。
2. 数据可迁移可回滚。
3. CI 中新增 DB 模式测试任务（可选 matrix）。
