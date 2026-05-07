# Research Claims: LLM Agent vs PLM Annotation

Last updated: 2026-05-08

Rosetta does not claim that LLMs beat PLMs under every condition. The current research question is narrower:

```text
When an annotation task can be described clearly, gold examples are scarce, and boundaries may change,
can an LLM agentic workflow reach usable, auditable data faster than a PLM-first workflow under the same budget?
```

Current evidence only supports in-gold prompt training traces, memorization checks, runtime events, and reports. Held-out splits, cross-task runs, multiple seeds, PLM baselines, and confidence intervals are still required before making paper-level claims.

## What Must Be Tested

1. Low-resource sample efficiency against zero-shot LLM, fixed few-shot ICL, retrieval-only LLM, and low-budget PLM fine-tuning.
2. Adaptation to non-standard but definable concepts.
3. Prompt-as-Parameter optimization over the optimizable definition, not over labels or output format.
4. Review efficiency from routing uncertain items to human experts.

## Boundary

The 15 gold examples are calibration anchors. They are not simultaneously a few-shot answer bank, a training set, and a final generalization benchmark.

Canonical Chinese reference: [Research Claims](../../ideas/RESEARCH_CLAIMS.md).
