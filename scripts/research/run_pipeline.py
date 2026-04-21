#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.research.runner import preview_prompt, run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Research pipeline runner for Rosetta lab workflows")
    subparsers = parser.add_subparsers(dest="command", required=True)

    preview_parser = subparsers.add_parser("preview", help="Preview the composed research prompt for one sample")
    preview_parser.add_argument("--config", required=True, help="Path to research config JSON")
    preview_parser.add_argument("--dataset", required=True, help="Path to dataset JSONL")
    preview_parser.add_argument("--sample-id", default=None, help="Sample id to preview")
    preview_parser.add_argument("--sample-index", type=int, default=0, help="Fallback sample index when sample id is omitted")

    run_parser = subparsers.add_parser("run", help="Run the research pipeline in batch or audit mode")
    run_parser.add_argument("--config", required=True, help="Path to research config JSON")
    run_parser.add_argument("--dataset", required=True, help="Path to dataset JSONL")
    run_parser.add_argument("--mode", choices=["batch", "audit"], default="batch", help="Execution mode")
    run_parser.add_argument("--output-dir", default=None, help="Optional output directory override")
    run_parser.add_argument("--limit", type=int, default=None, help="Optional sample limit for pilot runs")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "preview":
        result = preview_prompt(
            config_path=args.config,
            dataset_path=args.dataset,
            sample_id=args.sample_id,
            sample_index=args.sample_index,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    manifest = run_pipeline(
        config_path=args.config,
        dataset_path=args.dataset,
        mode=args.mode,
        output_dir=args.output_dir,
        limit=args.limit,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
