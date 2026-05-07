# Bootstrap Experiments

Last updated: 2026-05-08

Prompt training experiments compare canonical methods under the same gold set, loss, frozen protocol, model settings, and stopping policy.

Canonical methods:

1. `sgd_candidate_search`
2. `critic_adamw_optimizer`
3. `mask_guided_optimization`

Current in-gold results should not be described as held-out generalization. Proper claims require held-out splits, negative examples where relevant, PLM baselines, multiple seeds, and confidence intervals.

Canonical Chinese reference: [Bootstrap Experiments](../../developer/BOOTSTRAP_EXPERIMENTS.md).
