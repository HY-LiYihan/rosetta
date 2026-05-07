# 提示词构成（中英文对照）

更新时间: 2026-05-08

这页回答一个很具体的问题：Rosetta 调用大模型时，模型实际会看到哪些内容。

Rosetta 可以使用中文或 English 的模型控制模板。界面语言、用户输入语言和模型输出语言是三件不同的事：切换界面语言不会自动翻译你的概念阐释、任务文本、标签名、模型输出、日志或导出文件名。

提示词优化的对象是“可优化定义”：任务定义、概念定义、边界规则和排除规则。标签、JSON 字段、markup 和格式检查规则保持稳定，用来保证同一批样例上的比较条件一致。

## 一眼看懂

| 部分 | 谁提供 | 会进入 LLM | 会随界面按钮自动翻译 | 说明 |
| --- | --- | --- | --- | --- |
| System prompt | Rosetta | 是 | 否 | 默认中文；程序也提供 English 版本供显式调用 |
| 当前概念阐释 | 用户或定义优化结果 | 是 | 否 | 这是提示词优化真正会改的主体 |
| 相似参考样例 | 本地检索 | 可选 | 否 | 只用于理解边界，不是当前文本答案 |
| 标注格式 | Rosetta 提供 | 是 | 按 prompt language 选择模板 | 规定 JSON 字段和 annotation 格式 |
| 通用格式示例 | Rosetta 生成 | 是 | 按 prompt language 选择模板 | 只说明格式，不使用当前任务 gold |
| 待标注文本 | 用户语料 | 是 | 否 | 必须原样返回在 JSON 的 `text` 字段 |
| 任务强调 | Rosetta 或调用方 | 是 | 按调用方传入内容 | 例如只输出 JSON、不要额外字段 |

## 运行时标注 Prompt

标注调用由一个 system prompt 和一个 user prompt 组成。两套模板的语义相同，差别只是系统控制文本的语言。

### System Prompt

| 语言 | 内容 |
| --- | --- |
| `zh-CN` | `你是严谨的标注助手，只输出 JSON。` |
| `en-US` | `You are a rigorous annotation assistant. Output JSON only.` |

### User Prompt 段落顺序

| 顺序 | `zh-CN` 标题 | `en-US` 标题 |
| --- | --- | --- |
| 1 | `概念定义` | `Concept definition` |
| 2 | `相似参考样例（可选，只用于理解边界，不是当前文本答案）` | `Similar reference examples (optional; for boundary understanding only, not the answer for the current text)` |
| 3 | `标注格式` | `Annotation format` |
| 4 | `通用格式示例（只说明输出格式，不代表当前任务概念）` | `Generic format example (format only; not the current task concept)` |
| 5 | `待标注文本` | `Text to annotate` |
| 6 | `任务强调` | `Task emphasis` |

### 中文模板

```text
请根据以下概念定义标注文本。

概念定义：
{ConceptPromptSpec}

相似参考样例（可选，只用于理解边界，不是当前文本答案）：
{ReferenceExamples 或 无。}

标注格式：
{输出格式说明}

通用格式示例（只说明输出格式，不代表当前任务概念）：
{Concept-neutral JSON example}

待标注文本：
{input_text}

任务强调：
{task_emphasis}
```

### English Template

```text
Annotate the text according to the concept definition.

Concept definition:
{ConceptPromptSpec}

Similar reference examples (optional; for boundary understanding only, not the answer for the current text):
{ReferenceExamples or None.}

Annotation format:
{Output format instructions}

Generic format example (format only; not the current task concept):
{Concept-neutral JSON example}

Text to annotate:
{input_text}

Task emphasis:
{task_emphasis}
```

## 输出格式

普通 span 标注默认使用 JSON + `[span]{Term}`：

```json
{
  "text": "Example source text.",
  "annotation": "[Example]{Term}",
  "explanation": "Briefly state why the marked span matches the concept."
}
```

多层任务可以选择完整 `AnnotationDoc` JSON。定义优化只调整概念语义，不调整以下格式要素：

1. JSON 字段：`text / annotation / explanation`。
2. 标签名，例如 `Term`。
3. `[span]{Term}` markup 或完整 `AnnotationDoc` 结构。
4. 格式检查规则：JSON 合法、原文一致、标签合法、span 可定位。

## 定义优化 Prompt

“提示词优化”页面的名称保留了 prompt 这个工程术语，但用户可以把它理解成“定义优化”。自动优化器只改 `ConceptPromptSpec`，也就是当前概念阐释中的任务定义、概念定义、边界规则和排除规则。

当前三种自动优化器是：

| 方法 | 会看什么 | 会生成什么 |
| --- | --- | --- |
| 候选搜索优化 / `sgd_candidate_search` | 当前可优化定义、已接受历史摘要 | 一个新的可优化定义 |
| 批判器 AdamW 优化 / `critic_adamw_optimizer` | 当前定义、loss、失败摘要、历史有效方向 | Evaluator 诊断、Controller 方向、Generator 候选定义 |
| 遮挡梯度优化 / `mask_guided_optimization` | 当前定义片段、遮挡回测 loss、失败摘要 | 根据高影响片段改写后的候选定义 |

训练反馈可以临时包含原文、gold annotation、模型回答和错误摘要，用来判断边界哪里不稳定；最终保存的定义不能复制原文、gold span、模型 span 或可识别答案片段。Rosetta 会用防背答案检查和去语料化修复把候选限制回抽象规则。
