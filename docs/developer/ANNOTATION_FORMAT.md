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
1. 正例任务中 `annotation` 至少包含一个合法标注片段；如果当前文本没有目标片段，可以返回空字符串，系统会解析为空 spans。
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

从 `v4.5.9` 开始，概念验证、候选回测、单条标注和批量标注应共用同一个运行时 prompt 框架：

```text
请根据以下概念定义标注文本。

概念定义：
{ConceptPromptSpec}

标注格式：
{Frozen OutputProtocolSpec 的字段、markup 或 AnnotationDoc 要求}

通用格式示例（只说明输出格式，不代表当前任务概念）：
{概念无关的 JSON 示例}

待标注文本：
{当前任务 text}

任务强调：
{只输出 JSON、保持 text 完全一致、不要输出额外字段等执行提醒}
```

通用格式示例只能解释返回结构，不能使用当前 gold、相似样例、失败样例、待标注文本或任何任务答案片段。批量标注中的相似样例、边界远例和失败记忆只能作为概念边界上下文，不应替代或污染 `标注格式` 段落。

从 `v4.5.10` 开始，所有标注型调用还应共用同一个 system prompt：

```text
你是严谨的标注助手，只输出 JSON。
```

这条 system prompt 同时用于概念验证、候选回测、单条标注和批量标注。它只定义模型身份和输出纪律；具体概念、冻结标注格式、待标注文本和任务强调全部放在 user prompt 中。这样可以避免“概念校验助手”“批量标注助手”等不同身份造成额外变量，使三方法优化实验和批量标注使用同一标注助手条件。

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
