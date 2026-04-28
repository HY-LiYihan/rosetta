#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.runtime.store import RuntimeStore
from app.workflows.bootstrap import analyze_bootstrap
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
    store = RuntimeStore() if getattr(args, "record", False) or args.command == "runs" else None

    if args.command == "bootstrap-analyze":
        result = analyze_bootstrap(
            samples_path=args.samples,
            candidates_path=args.candidates,
            output_dir=args.output_dir,
            run_name=args.run_name,
            experiment_path=args.experiment,
            store=store,
        )
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


if __name__ == "__main__":
    raise SystemExit(main())
