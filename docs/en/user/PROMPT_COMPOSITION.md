# Prompt Composition

Last updated: 2026-05-08

This page explains what the LLM receives during annotation calls.

## Language

Rosetta can use Chinese or English control templates for model-facing annotation prompts. Interface language, user input language, and model output language are separate: changing the interface language does not translate your definitions, task text, labels, model outputs, logs, or export filenames.

## Runtime Annotation Prompt

Each annotation call has one system prompt and one user prompt.

| Language | System prompt |
| --- | --- |
| `zh-CN` | `你是严谨的标注助手，只输出 JSON。` |
| `en-US` | `You are a rigorous annotation assistant. Output JSON only.` |

The user prompt has six sections:

| Order | Chinese section | English section |
| --- | --- | --- |
| 1 | `概念定义` | `Concept definition` |
| 2 | `相似参考样例（可选，只用于理解边界，不是当前文本答案）` | `Similar reference examples (optional; for boundary understanding only, not the answer for the current text)` |
| 3 | `标注格式` | `Annotation format` |
| 4 | `通用格式示例（只说明输出格式，不代表当前任务概念）` | `Generic format example (format only; not the current task concept)` |
| 5 | `待标注文本` | `Text to annotate` |
| 6 | `任务强调` | `Task emphasis` |

## Output Format

For ordinary span annotation, Rosetta asks the model to return JSON whose `annotation` field uses `[span]{Term}`:

```json
{
  "text": "Example source text.",
  "annotation": "[Example]{Term}",
  "explanation": "Briefly state why the marked span matches the concept."
}
```

Definition optimization changes the concept definition, boundary rules, exclusion rules, and abstract failure patterns. Rosetta keeps the response format stable:

1. JSON fields: `text / annotation / explanation`.
2. Label names such as `Term`.
3. `[span]{Term}` markup or full `AnnotationDoc` structure.
4. Format checks such as valid JSON, unchanged source text, valid labels, and locatable spans.
