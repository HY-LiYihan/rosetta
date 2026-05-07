# Prompt Composition

Last updated: 2026-05-08

This page explains what the LLM receives during annotation calls.

## Boundary

1. The documentation site has a language switcher.
2. The Streamlit app has `中文 / English` buttons for main UI labels.
3. User input, task text, labels, model output, logs, database content, and export filenames are not automatically translated.
4. The runtime annotation prompt builder supports `zh-CN` and `en-US` templates. The default workflow still uses `zh-CN` unless the caller explicitly passes `prompt_language="en-US"`.

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

## Frozen Output Protocol

For ordinary span annotation, Rosetta asks the model to return JSON whose `annotation` field uses `[span]{Term}`:

```json
{
  "text": "Example source text.",
  "annotation": "[Example]{Term}",
  "explanation": "Briefly state why the marked span matches the concept."
}
```

The optimizer does not edit:

1. JSON fields: `text / annotation / explanation`.
2. Label names such as `Term`.
3. `[span]{Term}` markup or full `AnnotationDoc` structure.
4. Parser rules.
5. Format repair rules.

The optimizer edits only the concept definition, boundary rules, exclusion rules, and abstract failure patterns.

## Source Of Truth

The runtime prompt contract is defined in:

1. `app/services/annotation_service.py::ANNOTATION_ASSISTANT_SYSTEM_PROMPTS`
2. `app/services/annotation_service.py::RUNTIME_PROMPT_SECTION_ORDER`
3. `app/services/annotation_service.py::RUNTIME_PROMPT_SECTION_LABELS`
4. `app/services/annotation_service.py::build_runtime_annotation_prompt()`
