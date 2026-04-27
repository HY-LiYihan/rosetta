from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from app.research.bootstrap_contracts import BootstrapSample
from app.research.bootstrap_io import (
    candidate_to_dict,
    read_candidates_jsonl,
    read_samples_jsonl,
    sample_to_dict,
)
from app.research.bootstrap_report import build_bootstrap_report
from app.research.consistency import consistency_score_to_dict, score_candidate_groups
from app.research.contrastive_retrieval import contrastive_selection_to_dict, select_contrastive_examples
from app.research.human_review import build_human_review_queue, human_review_task_to_dict
from app.research.label_statistics import build_label_statistics, label_statistics_to_dict
from app.research.reflection import build_reflection_plan, reflection_plan_to_dict


def run_bootstrap_analysis(
    samples_path: str | Path,
    candidates_path: str | Path,
    output_dir: str | Path = ".runtime/research/bootstrap",
    run_name: str = "bootstrap",
    experiment_path: str | Path | None = None,
) -> dict:
    samples = read_samples_jsonl(samples_path)
    candidates = read_candidates_jsonl(candidates_path)
    sample_by_id = {sample.id: sample for sample in samples}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(output_dir) / run_name / f"analysis_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    scores = score_candidate_groups(candidates)
    review_queue = build_human_review_queue(candidates, scores)
    stats_samples = _samples_for_statistics(samples, candidates, scores)
    label_stats = build_label_statistics(stats_samples)
    reflection_plans = _build_reflection_plans(sample_by_id, candidates, label_stats)
    retrieval_traces = _build_retrieval_traces(samples, stats_samples)
    experiment = _read_optional_experiment(experiment_path)

    _write_jsonl(run_dir / "samples.normalized.jsonl", [sample_to_dict(sample) for sample in samples])
    _write_jsonl(run_dir / "candidate_runs.normalized.jsonl", [candidate_to_dict(candidate) for candidate in candidates])
    _write_jsonl(run_dir / "consistency_scores.jsonl", [consistency_score_to_dict(score) for score in scores])
    _write_jsonl(run_dir / "human_review_queue.jsonl", [human_review_task_to_dict(task) for task in review_queue])
    _write_json(run_dir / "label_statistics.json", label_statistics_to_dict(label_stats))
    _write_jsonl(run_dir / "reflection_plans.jsonl", [reflection_plan_to_dict(plan) for plan in reflection_plans])
    _write_jsonl(run_dir / "retrieval_traces.jsonl", retrieval_traces)

    manifest = {
        "run_name": run_name,
        "samples_path": str(Path(samples_path)),
        "candidates_path": str(Path(candidates_path)),
        "experiment_path": str(Path(experiment_path)) if experiment_path else None,
        "output_dir": str(run_dir),
        "sample_count": len(samples),
        "candidate_count": len(candidates),
        "consistency_count": len(scores),
        "review_task_count": len(review_queue),
        "label_stat_count": len(label_stats),
        "reflection_plan_count": len(reflection_plans),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    report = build_bootstrap_report(
        manifest=manifest,
        scores=scores,
        review_queue=review_queue,
        label_stats=label_stats,
        reflection_plans=reflection_plans,
        experiment=experiment,
    )
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    manifest["report_path"] = str(run_dir / "report.md")
    _write_json(run_dir / "manifest.json", manifest)
    return manifest


def _samples_for_statistics(samples: list[BootstrapSample], candidates, scores) -> list[BootstrapSample]:
    sample_by_id = {sample.id: sample for sample in samples}
    stats_samples = [sample for sample in samples if sample.spans]
    high_ids = {score.sample_id for score in scores if score.route == "high"}
    for candidate in candidates:
        if candidate.sample_id not in high_ids or candidate.sample_id not in sample_by_id:
            continue
        source = sample_by_id[candidate.sample_id]
        stats_samples.append(
            BootstrapSample(
                id=f"{source.id}:{candidate.candidate_id}",
                text=source.text,
                spans=candidate.spans,
                metadata={**source.metadata, "source": "high_confidence_candidate"},
            )
        )
    return stats_samples


def _build_reflection_plans(sample_by_id: dict[str, BootstrapSample], candidates, label_stats) -> list:
    plans = []
    for candidate in candidates:
        sample = sample_by_id.get(candidate.sample_id)
        if sample is None:
            continue
        plan = build_reflection_plan(sample, candidate, label_stats)
        if plan.items:
            plans.append(plan)
    return plans


def _build_retrieval_traces(samples: list[BootstrapSample], stats_samples: list[BootstrapSample]) -> list[dict]:
    examples = [sample for sample in stats_samples if sample.spans]
    traces = []
    for sample in samples:
        if not examples:
            continue
        selection = select_contrastive_examples(sample, examples)
        traces.append(contrastive_selection_to_dict(selection))
    return traces


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_optional_experiment(path: str | Path | None) -> dict | None:
    if path is None:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))
