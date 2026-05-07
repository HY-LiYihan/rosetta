# Quickstart

Last updated: 2026-05-08

Rosetta’s default app workflow has five pages:

```text
Project Overview -> Definition & Guideline -> Batch Run -> Review & Fix -> Results & Export
```

## Five-Minute Demo

1. Open `Definition & Guideline`.
2. Use the built-in official project, `Professional Named Entity Annotation`.
3. Run local format validation first.
4. Open `Batch Run`, paste two or three English science or technology sentences, and choose local simulation for a smoke test.
5. Open `Review & Fix` if review items appear.
6. Open `Results & Export` and download JSONL plus the report.

Local simulation only checks the UI, queue, review, and export flow. It does not represent real model quality. For a real experiment, use an LLM provider and record provider, model, concurrency, token usage, and the exported report.

## Key Terms

| Term | Meaning |
| --- | --- |
| Concept interpretation | The operational definition of what should and should not be annotated |
| Gold examples | Human-confirmed examples used to validate and optimize the definition |
| Prompt validation | Local format checks and LLM-based checks against gold examples |
| Definition optimization | Refining the annotation definition used by the model |
| Output format | The JSON fields, labels, and markup Rosetta expects in model responses |

## Gold Example Format

Use JSONL for serious definition optimization:

```jsonl
{"text":"Quantum dots can emit precise colors when excited by light.","annotation":"[Quantum dots]{Term} can emit precise colors when excited by light."}
{"text":"The telescope detected faint gravitational waves from a distant merger.","annotation":"The telescope detected faint [gravitational waves]{Term} from a distant merger."}
```

The `text` field is the original sentence. The `annotation` field marks target spans with `[span]{label}`.

## Language Notes

The app sidebar provides `中文 / English` buttons. They change interface labels only. Your definitions, task text, labels, model outputs, logs, and export filenames remain as entered.

For the model-facing prompt structure, read [Prompt Composition](./PROMPT_COMPOSITION.md).
