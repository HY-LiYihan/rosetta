# Annotation Format (Developer)

更新时间: 2026-05-02

## 1. 目标

1. 统一标注字符串格式，支撑后续可视化渲染与自动检查。
2. 明确区分“原文显性标注”与“语义隐含标注”。
3. 让 LLM 在运行时使用更容易输出的格式，同时不牺牲长期存储和实验评测的标准化。

## 2. 格式规范（V2）

1. 显性原文：`[原文片段]{概念标签}`
2. 隐含语义：`[!隐含义]{概念标签}`

约束：
1. `annotation` 至少包含一个合法标注片段。
2. 不再接受旧格式 `[...] (...)`。
3. `!` 仅用于隐含语义，且 `!` 后必须有内容。

## 2.1 长期存储格式

LLM 运行时仍优先输出行内标注字符串，但长期存储统一使用 Prodigy-compatible JSONL profile。完整规范见 [ANNOTATION_JSONL_FORMAT.md](./ANNOTATION_JSONL_FORMAT.md)。

这层解耦是 Rosetta 的核心设计之一：模型只需要完成“把标签贴在原文旁边”的任务，系统负责解析、校验 offset、写入 JSONL，并把候选差异、人工审核和失败日志保存在 runtime store 中。

## 3. 示例数据规范

`concepts[*].examples[*]` 必填字段：
1. `text: str`
2. `annotation: str`（必须符合 V2 格式）
3. `explanation: str`（必填且非空）

## 4. 代码落点

1. 标注格式解析/校验：
- [annotation_format.py](../../app/domain/annotation_format.py)
2. 导入校验（examples 强校验）：
- [validators.py](../../app/domain/validators.py)
3. 标注响应校验：
- [annotation_service.py](../../app/services/annotation_service.py)

## 5. 兼容策略

1. 数据版本提升为 `2.0`。
2. 历史样例应迁移到 `[] {}` 格式并补齐 `explanation`。
3. 对不符合规范的导入数据，返回结构化错误：`field/reason/hint`。

## 6. 与概念自举的关系

1. 金样例可以用行内 markup 手写，降低领域专家的输入成本。
2. 自举校准时，模型输出仍按行内 markup 解析，再和 gold spans 计算 loss。
3. 批量标注时，行内 markup 只作为 runtime response；导出、评测和 PLM 对比都使用 Prodigy-compatible JSONL。
