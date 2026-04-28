from __future__ import annotations

from pathlib import Path

from app.research.bootstrap_runner import run_bootstrap_analysis
from app.runtime.store import RuntimeStore


def analyze_bootstrap(
    samples_path: str | Path,
    candidates_path: str | Path,
    output_dir: str | Path = ".runtime/workflows/bootstrap",
    run_name: str = "bootstrap",
    experiment_path: str | Path | None = None,
    store: RuntimeStore | None = None,
) -> dict:
    manifest = run_bootstrap_analysis(
        samples_path=samples_path,
        candidates_path=candidates_path,
        output_dir=output_dir,
        run_name=run_name,
        experiment_path=experiment_path,
    )
    if store is not None:
        from app.core.models import WorkflowRun

        run = WorkflowRun(
            id=f"bootstrap-{Path(manifest['output_dir']).name}",
            workflow="bootstrap",
            status="succeeded",
            input_ref=str(samples_path),
            output_ref=manifest["output_dir"],
            artifacts=(manifest.get("report_path", ""),),
            summary=f"{manifest['review_task_count']} review tasks generated",
            meta=manifest,
        )
        store.upsert_run(run)
    return manifest
