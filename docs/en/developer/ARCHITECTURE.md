# Architecture

Last updated: 2026-05-08

Rosetta is a Streamlit-based local-first agentic annotation tool.

The main user workflow is:

```text
Project Overview -> Definition & Guideline -> Batch Run -> Review & Fix -> Results & Export
```

The main engineering workflow is:

```text
core models -> workflows -> agents/tools -> data formats -> runtime store
```

## Data Flow

```text
ConceptGuideline + GoldExampleSet
  -> bootstrap workflow
  -> ConceptVersion + failure memory
  -> annotation context builder
  -> Prediction candidates
  -> consistency / confidence / risk routing
  -> ReviewTask or auto-accepted task
  -> export / report
```

Canonical Chinese reference: [Architecture](../../developer/ARCHITECTURE.md).
