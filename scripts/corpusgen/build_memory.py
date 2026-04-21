#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.corpusgen.runner import build_memory_bank


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build compressed memory and CPU index for corpus generation")
    parser.add_argument("--config", required=True, help="Path to corpus generation spec JSON")
    parser.add_argument("--chunks", required=True, help="Path to prepared seed chunks JSONL")
    parser.add_argument("--output-dir", default=None, help="Optional output directory override")
    parser.add_argument("--force", action="store_true", help="Force rebuilding the cached CPU index")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = build_memory_bank(
        spec_path=args.config,
        chunks_path=args.chunks,
        output_dir=args.output_dir,
        force_rebuild=args.force,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
