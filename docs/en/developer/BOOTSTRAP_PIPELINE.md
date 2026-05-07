# Guideline Bootstrap

Last updated: 2026-05-08

The bootstrap workflow optimizes the concept definition against gold examples while keeping the output protocol frozen.

```text
ConceptPromptSpec
  -> candidate generation
  -> gold validation
  -> loss comparison
  -> accept only improving clean definitions
  -> ConceptVersion history
```

The optimizer must not edit labels, JSON fields, annotation markup, parser rules, or format repair instructions.

Canonical Chinese reference: [Guideline Bootstrap](../../developer/BOOTSTRAP_PIPELINE.md).
