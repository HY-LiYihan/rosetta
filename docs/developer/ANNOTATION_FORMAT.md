# Annotation Format (Developer)

更新时间: 2026-03-11

## 1. 目标

1. 统一标注字符串格式，支撑后续可视化渲染与自动检查。
2. 明确区分“原文显性标注”与“语义隐含标注”。

## 2. 格式规范（V2）

1. 显性原文：`[原文片段]{概念标签}`
2. 隐含语义：`[!隐含义]{概念标签}`

约束：
1. `annotation` 至少包含一个合法标注片段。
2. 不再接受旧格式 `[...] (...)`。
3. `!` 仅用于隐含语义，且 `!` 后必须有内容。

## 3. 示例数据规范

`concepts[*].examples[*]` 必填字段：
1. `text: str`
2. `annotation: str`（必须符合 V2 格式）
3. `explanation: str`（必填且非空）

## 4. 代码落点

1. 标注格式解析/校验：
- [annotation_format.py](/Users/liyh/rosetta/app/domain/annotation_format.py)
2. 导入校验（examples 强校验）：
- [validators.py](/Users/liyh/rosetta/app/domain/validators.py)
3. 标注响应校验：
- [annotation_service.py](/Users/liyh/rosetta/app/services/annotation_service.py)

## 5. 兼容策略

1. 数据版本提升为 `2.0`。
2. 历史样例应迁移到 `[] {}` 格式并补齐 `explanation`。
3. 对不符合规范的导入数据，返回结构化错误：`field/reason/hint`。
