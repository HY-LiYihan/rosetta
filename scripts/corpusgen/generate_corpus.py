#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.corpusgen.runner import generate_corpus


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate grounded corpus items from planned tasks")
    parser.add_argument("--config", required=True, help="Path to corpus generation spec JSON")
    parser.add_argument("--memory", required=True, help="Path to memory_records.jsonl")
    parser.add_argument("--plan", required=True, help="Path to tasks.jsonl")
    parser.add_argument("--output-dir", default=None, help="Optional output directory override")
    parser.add_argument("--limit-tasks", type=int, default=None, help="Optional task limit for pilot runs")
    parser.add_argument("--resume-dir", default=None, help="Resume from a previous run directory (reads checkpoint.jsonl)")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = generate_corpus(
        spec_path=args.config,
        memory_path=args.memory,
        plan_path=args.plan,
        output_dir=args.output_dir,
        limit_tasks=args.limit_tasks,
        resume_dir=args.resume_dir,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
