#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.corpusgen.runner import plan_corpus


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan generation tasks for the corpus generation pipeline")
    parser.add_argument("--config", required=True, help="Path to corpus generation spec JSON")
    parser.add_argument("--memory", required=True, help="Path to memory_records.jsonl")
    parser.add_argument("--output-dir", default=None, help="Optional output directory override")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = plan_corpus(
        spec_path=args.config,
        memory_path=args.memory,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
