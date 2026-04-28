from __future__ import annotations

from pathlib import Path

from app.corpusgen.runner import build_memory_bank, generate_corpus, plan_corpus, prepare_seed_corpus
from app.runtime.store import RuntimeStore


def prepare(
    spec_path: str | Path,
    dataset_path: str | Path,
    output_dir: str | Path | None = None,
    limit: int | None = None,
    store: RuntimeStore | None = None,
) -> dict:
    manifest = prepare_seed_corpus(spec_path, dataset_path, output_dir=output_dir, limit=limit)
    _record_run(store, "corpus.prepare", manifest, input_ref=str(dataset_path))
    return manifest


def build_memory(
    spec_path: str | Path,
    chunks_path: str | Path,
    output_dir: str | Path | None = None,
    force_rebuild: bool = False,
    store: RuntimeStore | None = None,
) -> dict:
    manifest = build_memory_bank(
        spec_path=spec_path,
        chunks_path=chunks_path,
        output_dir=output_dir,
        force_rebuild=force_rebuild,
    )
    _record_run(store, "corpus.memory", manifest, input_ref=str(chunks_path))
    return manifest


def plan(
    spec_path: str | Path,
    memory_path: str | Path,
    output_dir: str | Path | None = None,
    store: RuntimeStore | None = None,
) -> dict:
    manifest = plan_corpus(spec_path, memory_path, output_dir=output_dir)
    _record_run(store, "corpus.plan", manifest, input_ref=str(memory_path))
    return manifest


def generate(
    spec_path: str | Path,
    memory_path: str | Path,
    plan_path: str | Path,
    output_dir: str | Path | None = None,
    limit_tasks: int | None = None,
    resume_dir: str | Path | None = None,
    store: RuntimeStore | None = None,
) -> dict:
    manifest = generate_corpus(
        spec_path=spec_path,
        memory_path=memory_path,
        plan_path=plan_path,
        output_dir=output_dir,
        limit_tasks=limit_tasks,
        resume_dir=resume_dir,
    )
    _record_run(store, "corpus.generate", manifest, input_ref=str(plan_path))
    return manifest


def _record_run(store: RuntimeStore | None, workflow: str, manifest: dict, input_ref: str) -> None:
    if store is None:
        return
    from app.core.models import WorkflowRun

    run = WorkflowRun(
        id=f"{workflow.replace('.', '-')}-{Path(manifest['output_dir']).name}",
        workflow=workflow,
        status="succeeded",
        input_ref=input_ref,
        output_ref=manifest["output_dir"],
        summary=f"{workflow} completed",
        meta=manifest,
    )
    store.upsert_run(run)
