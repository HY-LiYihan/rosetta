# Annotation Format (Developer)

更新时间: 2026-05-05

## 1. 目标

1. 统一 LLM 运行时输出协议，支撑后续可视化渲染、自动检查和 format repair。
2. 明确区分“原文显性标注”与“语义隐含标注”。
3. 让 LLM 在运行时使用更容易输出的 JSON+markup 格式，同时不牺牲长期存储和实验评测的标准化。
4. 将输出协议冻结为 harness 责任，避免 prompt optimizer 把 JSON schema、标签和 annotation 格式当成可优化内容。

## 2. 行内标注格式（V2）

1. 显性原文：`[原文片段]{概念标签}`
2. 隐含语义：`[!隐含义]{概念标签}`

约束：
1. `annotation` 至少包含一个合法标注片段。
2. 不再接受旧格式 `[...] (...)`。
3. `!` 仅用于隐含语义，且 `!` 后必须有内容。

## 2.1 长期存储格式

LLM 运行时使用 JSON 外壳承载行内标注字符串，但长期存储统一使用 Prodigy-compatible JSONL profile。完整规范见 [ANNOTATION_JSONL_FORMAT.md](./ANNOTATION_JSONL_FORMAT.md)。

这层解耦是 Rosetta 的核心设计之一：模型只需要完成“把标签贴在原文旁边”的任务，系统负责解析、校验 offset、写入 JSONL，并把候选差异、人工审核和失败日志保存在 runtime store 中。

## 2.2 运行时 JSON+markup 协议

从 `v4.5.5` 文档契约开始，LLM 标注调用的冻结输出协议固定为 JSON+markup：

```json
{
  "text": "原始输入文本，必须与任务 text 一致",
  "annotation": "使用 [span]{Term} 标出所有目标片段",
  "explanation": "一句简短理由"
}
```

运行时约束：

1. 响应必须是单个 JSON object。
2. JSON 外不能有 markdown fence、额外解释、列表编号或自然语言包装。
3. 必须包含且只依赖 `text / annotation / explanation` 三个核心字段；后续扩展字段必须由 harness 明确声明，不能由模型自由发明。
4. `text` 必须与当前任务原文一致，不能翻译、改写、摘要或删除字符。
5. `annotation` 使用行内标注 V2：显性 span 用 `[span]{Term}`，隐含语义用 `[!implicit]{Term}`。
6. `Term` 是 harness 注入的标签，不是 prompt optimizer 可改写的内容。
7. 每个显性 span 必须能在 `text` 中定位；解析后必须能转换为 Prodigy-compatible `spans`。

`ConceptPromptSpec` 和 `Frozen OutputProtocolSpec` 必须分开。概念优化器只生成概念定义、边界规则和排除规则；JSON schema、标签、markup 格式、解析规则和修复指令由 harness 注入。

## 2.3 格式校验与修复契约

每次模型输出先做格式验证，再做语义评估：

```text
raw model response
  -> strict JSON parse
  -> schema validation
  -> text equality check
  -> markup validation
  -> label validation
  -> span location check
  -> semantic loss
```

如果格式失败，系统应进入最多 2 次 format repair：

1. repair prompt 只要求修复 JSON、字段、markup、label 或 span 定位。
2. repair prompt 不允许改变概念定义、边界规则、负例规则或任务语义。
3. repair 成功后再计算 semantic loss。
4. repair 失败时记录 `format_failed`，不混入漏标、多标或边界错误。
5. 报告中必须单独展示 `format_failure_rate` 和 `format_repair_success_rate`。

当前状态边界：现有 parser 已能解析 JSON 响应中的 `annotation` 字段并校验行内 markup；统一的跨 workflow format repair harness 和格式指标拆分仍是下一阶段实现任务。

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
4. 后续统一 harness 建议落点：
- `app/workflows/annotation` 或 `app/services` 的薄兼容层，避免页面和 workflow 各自拼接输出协议。

## 5. 兼容策略

1. 数据版本提升为 `2.0`。
2. 历史样例应迁移到 `[] {}` 格式并补齐 `explanation`。
3. 对不符合规范的导入数据，返回结构化错误：`field/reason/hint`。

## 6. 与概念自举的关系

1. 金样例可以用行内 markup 手写，降低领域专家的输入成本。
2. 自举校准时，模型输出按 JSON+markup 协议解析，再和 gold spans 计算 loss。
3. 批量标注时，JSON+markup 只作为 runtime response；导出、评测和 PLM 对比都使用 Prodigy-compatible JSONL。
4. Prompt training 不优化输出协议；格式稳定性由冻结协议、严格 parser 和 format repair loop 负责。
