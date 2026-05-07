# Core Annotation Bootstrap

Last updated: 2026-05-08

Rosetta’s core loop turns a concept description and a small gold set into a usable annotation workflow:

```text
concept definition
  -> gold validation
  -> definition optimization
  -> context-enhanced batch annotation
  -> review and correction
  -> exportable dataset and report
```

The core idea is not “upload data, call an LLM, download results”. Rosetta records concept versions, failures, retrieved context, human decisions, and exported reports so the annotation process can be audited and improved.

## Current Status

1. Definition optimization and prompt training live in `app/workflows/bootstrap`.
2. Batch annotation context uses concept versions, similar examples, boundary examples, and failure memory.
3. Local lightweight embedding retrieval defaults to `rosetta-local-hash-384`.
4. The main UI exposes validation and optimization rather than a separate user-facing “bootstrap calibration” step.

Canonical Chinese reference: [Core Annotation Bootstrap](../../ideas/CORE_ANNOTATION_BOOTSTRAP.md).
