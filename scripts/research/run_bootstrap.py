from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
import warnings

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.workflows.bootstrap import analyze_bootstrap


def main() -> None:
    parser = argparse.ArgumentParser(description="Run concept bootstrap analysis.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="Analyze existing candidate runs.")
    analyze.add_argument("--samples", required=True, help="Path to bootstrap samples JSONL.")
    analyze.add_argument("--candidates", required=True, help="Path to candidate runs JSONL.")
    analyze.add_argument("--output-dir", default=".runtime/research/bootstrap", help="Output root directory.")
    analyze.add_argument("--run-name", default="bootstrap", help="Run name.")
    analyze.add_argument("--experiment", default=None, help="Optional experiment config JSON.")

    args = parser.parse_args()
    if args.command == "analyze":
        warnings.warn(
            "scripts/research/run_bootstrap.py is a legacy entrypoint; use "
            "scripts/tool/rosetta_tool.py bootstrap-analyze instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        manifest = analyze_bootstrap(
            samples_path=args.samples,
            candidates_path=args.candidates,
            output_dir=args.output_dir,
            run_name=args.run_name,
            experiment_path=args.experiment,
        )
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
