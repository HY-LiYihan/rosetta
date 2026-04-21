#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.corpusgen.runner import prepare_seed_corpus


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare seed chunks for the corpus generation pipeline")
    parser.add_argument("--config", required=True, help="Path to corpus generation spec JSON")
    parser.add_argument("--dataset", required=True, help="Path to seed documents JSONL")
    parser.add_argument("--output-dir", default=None, help="Optional output directory override")
    parser.add_argument("--limit", type=int, default=None, help="Optional document limit")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = prepare_seed_corpus(
        spec_path=args.config,
        dataset_path=args.dataset,
        output_dir=args.output_dir,
        limit=args.limit,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
