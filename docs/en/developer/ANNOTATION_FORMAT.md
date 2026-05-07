# Annotation Format

Last updated: 2026-05-08

Rosetta separates runtime LLM output from long-term storage.

Runtime span annotation uses JSON plus inline markup:

```json
{
  "text": "Example source text.",
  "annotation": "[Example]{Term}",
  "explanation": "Briefly state why the marked span matches the concept."
}
```

Long-term storage uses Prodigy-compatible JSONL. Runtime markup is parsed, validated, converted to spans, and stored with metadata for review and export.

Canonical Chinese reference: [Annotation Format](../../developer/ANNOTATION_FORMAT.md).
