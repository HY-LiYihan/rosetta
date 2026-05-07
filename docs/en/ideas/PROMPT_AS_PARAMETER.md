# Prompt-as-Parameter

Last updated: 2026-05-08

Rosetta treats the user-facing concept definition as an optimizable text parameter. The optimizer edits only `ConceptPromptSpec`: task definition, concept definition, boundary rules, exclusion rules, and abstract failure patterns.

The frozen output protocol is not optimized. Labels, JSON schema, markup, parser rules, and format repair stay in Rosetta’s harness.

## Current Optimizer Families

| Method | Purpose |
| --- | --- |
| `sgd_candidate_search` | Generate candidate definitions and keep the lowest-loss improving version |
| `critic_adamw_optimizer` | Use evaluator/controller/generator roles to produce an AdamW-like candidate update |
| `mask_guided_optimization` | Mask definition segments, measure loss changes, then rewrite high-impact segments |

`LLM-AdamW` is a narrative analogy unless a full optimizer state is explicitly recorded. Current implementation should be read as an AdamW-like text candidate controller.

Canonical Chinese reference: [Prompt-as-Parameter](../../ideas/PROMPT_AS_PARAMETER.md).
