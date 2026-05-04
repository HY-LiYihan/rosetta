#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.core.models import Project
from app.infrastructure.llm.runtime import LLMServiceRuntime
from app.runtime.store import RuntimeStore
from app.data.official_sample import PROFESSIONAL_NER_EXAMPLE
from app.workflows.bootstrap import (
    PROMPT_TRAINING_METHODS,
    PromptTrainingConfig,
    analyze_bootstrap,
    gold_task_from_markup,
    run_prompt_training_experiment,
    save_guideline_package,
    write_prompt_training_comparison_outputs,
)
from app.workflows.corpus import build_memory, generate, plan, prepare


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rosetta local-first annotation tool CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap = subparsers.add_parser("bootstrap-analyze", help="Analyze bootstrap candidate runs.")
    bootstrap.add_argument("--samples", required=True)
    bootstrap.add_argument("--candidates", required=True)
    bootstrap.add_argument("--output-dir", default=".runtime/workflows/bootstrap")
    bootstrap.add_argument("--run-name", default="bootstrap")
    bootstrap.add_argument("--experiment", default=None)
    bootstrap.add_argument("--record", action="store_true", help="Record workflow run in the local SQLite store.")

    prompt_training = subparsers.add_parser("prompt-training-experiment", help="Run a prompt training method comparison experiment.")
    prompt_training.add_argument("--case", default="professional-ner", choices=["professional-ner", "hard-science"])
    prompt_training.add_argument("--provider", default="deepseek")
    prompt_training.add_argument("--model", default="deepseek-v4-pro")
    prompt_training.add_argument("--concurrency", type=int, default=20)
    prompt_training.add_argument("--candidate-count", type=int, default=3)
    prompt_training.add_argument("--patience-rounds", type=int, default=5)
    prompt_training.add_argument("--max-rounds", type=int, default=30)
    prompt_training.add_argument("--output-dir", default=".runtime/experiments/prompt_training_professional_ner")
    prompt_training.add_argument("--record", action="store_true", help="Record runs in the experiment-local SQLite store.")

    corpus_prepare = subparsers.add_parser("corpus-prepare", help="Prepare seed corpus chunks.")
    corpus_prepare.add_argument("--config", required=True)
    corpus_prepare.add_argument("--dataset", required=True)
    corpus_prepare.add_argument("--output-dir", default=None)
    corpus_prepare.add_argument("--limit", type=int, default=None)
    corpus_prepare.add_argument("--record", action="store_true")

    corpus_memory = subparsers.add_parser("corpus-memory", help="Build corpus memory records and CPU index.")
    corpus_memory.add_argument("--config", required=True)
    corpus_memory.add_argument("--chunks", required=True)
    corpus_memory.add_argument("--output-dir", default=None)
    corpus_memory.add_argument("--force-rebuild", action="store_true")
    corpus_memory.add_argument("--record", action="store_true")

    corpus_plan = subparsers.add_parser("corpus-plan", help="Plan corpus generation tasks.")
    corpus_plan.add_argument("--config", required=True)
    corpus_plan.add_argument("--memory", required=True)
    corpus_plan.add_argument("--output-dir", default=None)
    corpus_plan.add_argument("--record", action="store_true")

    corpus_generate = subparsers.add_parser("corpus-generate", help="Generate corpus items from planned tasks.")
    corpus_generate.add_argument("--config", required=True)
    corpus_generate.add_argument("--memory", required=True)
    corpus_generate.add_argument("--plan", required=True)
    corpus_generate.add_argument("--output-dir", default=None)
    corpus_generate.add_argument("--limit-tasks", type=int, default=None)
    corpus_generate.add_argument("--resume-dir", default=None)
    corpus_generate.add_argument("--record", action="store_true")

    runs = subparsers.add_parser("runs", help="List recorded local workflow runs.")
    runs.add_argument("--limit", type=int, default=20)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    store = (
        RuntimeStore()
        if args.command != "prompt-training-experiment" and (getattr(args, "record", False) or args.command == "runs")
        else None
    )

    if args.command == "bootstrap-analyze":
        result = analyze_bootstrap(
            samples_path=args.samples,
            candidates_path=args.candidates,
            output_dir=args.output_dir,
            run_name=args.run_name,
            experiment_path=args.experiment,
            store=store,
        )
    elif args.command == "prompt-training-experiment":
        result = _run_prompt_training_experiment_command(args)
    elif args.command == "corpus-prepare":
        result = prepare(args.config, args.dataset, output_dir=args.output_dir, limit=args.limit, store=store)
    elif args.command == "corpus-memory":
        result = build_memory(
            args.config,
            args.chunks,
            output_dir=args.output_dir,
            force_rebuild=args.force_rebuild,
            store=store,
        )
    elif args.command == "corpus-plan":
        result = plan(args.config, args.memory, output_dir=args.output_dir, store=store)
    elif args.command == "corpus-generate":
        result = generate(
            args.config,
            args.memory,
            args.plan,
            output_dir=args.output_dir,
            limit_tasks=args.limit_tasks,
            resume_dir=args.resume_dir,
            store=store,
        )
    elif args.command == "runs":
        result = store.list_runs(limit=args.limit) if store else []
    else:  # pragma: no cover - argparse enforces valid commands
        raise ValueError(args.command)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _run_prompt_training_experiment_command(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    experiment_store = RuntimeStore(output_dir / "runtime" / "rosetta.sqlite3")
    example = PROFESSIONAL_NER_EXAMPLE
    project = Project(
        id="project-professional-ner-prompt-training",
        name=example["project_name"],
        description=example["project_description"],
        task_schema="span",
    )
    experiment_store.upsert_project(project)
    gold_tasks = [
        gold_task_from_markup(
            task_id=f"professional-ner-gold-{index:05d}",
            text=row["text"],
            annotation_markup=row["annotation"],
            label_hint="Term",
        )
        for index, row in enumerate(example["gold_examples"], start=1)
    ]
    package = save_guideline_package(
        experiment_store,
        project_id=project.id,
        name=example["concept_name"],
        brief=example["brief"],
        labels=["Term"],
        boundary_rules=[
            "优先标注最小完整术语。",
            "多词术语应整体标注，不拆成单个普通词。",
        ],
        negative_rules=[
            "不标注过泛或没有明确专业含义的普通词。",
            "不标注机构名、新闻来源名或人物名，除非任务明确要求。",
        ],
        gold_tasks=gold_tasks,
    )
    guideline = replace(
        package["guideline"],
        metadata={
            **package["guideline"].metadata,
            "experiment_case": args.case,
            "experiment_note": "Simple prompt baseline without gold source terms in boundary rules.",
        },
    )
    experiment_store.upsert_guideline(guideline)
    runtime = LLMServiceRuntime.from_provider(args.provider, args.model, concurrency=args.concurrency)

    def predictor(system_prompt: str, messages: list[dict], temperature: float) -> str:
        return runtime.chat(system_prompt, messages, temperature=temperature)

    predictor.is_real_provider = True  # type: ignore[attr-defined]
    predictor.runtime = runtime  # type: ignore[attr-defined]
    result = run_prompt_training_experiment(
        experiment_store,
        guideline.id,
        predictor=predictor,
        config=PromptTrainingConfig(
            methods=PROMPT_TRAINING_METHODS,
            max_rounds=args.max_rounds,
            candidate_count=args.candidate_count,
            patience_rounds=args.patience_rounds,
            provider_id=args.provider,
            model=args.model,
            concurrency=args.concurrency,
        ),
    )
    result["experiment_case"] = args.case
    result = write_prompt_training_comparison_outputs(result, output_dir)
    return {
        "status": result["status"],
        "best_method": result["best_method"],
        "best_pass_count": result["best_pass_count"],
        "best_loss": result["best_loss"],
        "comparison_result_path": result["comparison_result_path"],
        "report_path": result["report_path"],
        "prompt_evolution_path": result["prompt_evolution_path"],
        "usage_summary": result.get("usage_summary", {}),
        "repair_summary": result.get("repair_summary", {}),
        "method_results": result.get("method_results", []),
    }


if __name__ == "__main__":
    raise SystemExit(main())
