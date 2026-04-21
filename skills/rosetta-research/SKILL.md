---
name: rosetta-research
description: Use this skill when working in the Rosetta repo on the lab-style research annotation pipeline, including editing research configs, previewing prompts, building embedding indexes, running batch or audit experiments, and summarizing review queues or conflicts.
---

# Rosetta Research

## Overview

Use this skill to operate Rosetta's research pipeline from Codex. The skill wraps the repo's `app/research` engine and `scripts/research/run_pipeline.py`; it does not duplicate pipeline logic.

## When To Use

- The user wants to tune `configs/research/*.json` for a pilot task.
- The user asks to preview prompts, build retrieval indexes, or run `batch` / `audit`.
- The user wants help reviewing `.runtime/research/*/manifest.json`, `review_queue.jsonl`, or `conflicts.jsonl`.

## Workflow

1. Confirm the repo root contains `scripts/research/run_pipeline.py` and the target config under `configs/research/`.
2. Read the config before editing anything. If retrieval is `embedding`, also check whether `embedding_model` and `index_dir` are set.
3. If the user is tuning definitions, inclusion rules, exclusion rules, negative constraints, or few-shot examples, run `preview` first.
4. For `embedding` retrieval, run `build-index` before a large `batch` or `audit`.
5. Use `run --mode audit` only when every sample has `gold_annotation`. Otherwise use `run --mode batch`.
6. After execution, inspect `manifest.json` first, then `review_queue.jsonl`, then `conflicts.jsonl` when present.

## Command Reference

Preview one sample:

```bash
python scripts/research/run_pipeline.py preview \
  --config configs/research/pilot_template.json \
  --dataset configs/research/pilot_dataset.example.jsonl
```

Build the cached CPU vector index for embedding retrieval:

```bash
python scripts/research/run_pipeline.py build-index \
  --config configs/research/glm5_embedding3_template.json
```

Run a pilot audit:

```bash
python scripts/research/run_pipeline.py run \
  --config configs/research/pilot_template.json \
  --dataset configs/research/pilot_dataset.example.jsonl \
  --mode audit
```

## Editing Guidance

- Prefer fixing task definitions, negative constraints, and example banks in `configs/research/*.json` before changing `app/research/*`.
- Keep annotation output in Rosetta's required format: `[原文]{标签}` or `[!隐含义]{标签}`.
- Treat `hard_examples` as the error bank promoted from prior audits.
- Use `.streamlit/secrets.toml` or environment variables for API keys; do not hardcode credentials into configs.

## Expected Outputs

- `manifest.json`: top-level run summary.
- `predictions.jsonl`: prompt, retrieved examples, raw response, parsed result, and verification issues per sample.
- `review_queue.jsonl`: model outputs that need manual review.
- `conflicts.jsonl`: gold mismatches in `audit` mode.
