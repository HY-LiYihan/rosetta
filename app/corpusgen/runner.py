from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Callable

from app.corpusgen.generators import build_generation_prompt, normalize_generated_items, parse_generation_response
from app.corpusgen.judges import judge_generated_items
from app.corpusgen.memory.compression import build_context_pack
from app.corpusgen.memory.layers import build_memory_records, memory_record_from_dict, memory_record_to_dict
from app.corpusgen.memory.recall import build_memory_index, query_memory_index
from app.corpusgen.planner import generation_task_from_dict, generation_task_to_dict, plan_generation_tasks
from app.corpusgen.seeds import chunk_seed_documents, load_seed_documents, seed_chunk_from_dict, seed_chunk_to_dict
from app.corpusgen.specs import load_corpus_spec
from app.infrastructure.llm.credentials import resolve_api_key
from app.infrastructure.llm.registry import get_provider

Predictor = Callable[[object, str], str]
Embedder = Callable[[object, list[str]], list[list[float]]]


def prepare_seed_corpus(
    spec_path: str | Path,
    dataset_path: str | Path,
    output_dir: str | Path | None = None,
    limit: int | None = None,
) -> dict:
    spec = load_corpus_spec(spec_path)
    documents = load_seed_documents(dataset_path)
    if limit is not None:
        documents = documents[:limit]

    chunks = chunk_seed_documents(
        documents=documents,
        chunk_size=spec.seed_chunk_size,
        chunk_overlap=spec.seed_chunk_overlap,
    )

    run_dir = _create_run_dir(spec.output_dir, spec.name, "prepare", output_dir)
    _write_jsonl(run_dir / "seed_chunks.jsonl", [seed_chunk_to_dict(chunk) for chunk in chunks])

    manifest = {
        "spec_name": spec.name,
        "spec_path": str(Path(spec_path)),
        "dataset_path": str(Path(dataset_path)),
        "output_dir": str(run_dir),
        "document_count": len(documents),
        "chunk_count": len(chunks),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    _write_json(run_dir / "manifest.json", manifest)
    return manifest


def build_memory_bank(
    spec_path: str | Path,
    chunks_path: str | Path,
    output_dir: str | Path | None = None,
    embedder: Embedder | None = None,
    force_rebuild: bool = False,
) -> dict:
    spec = load_corpus_spec(spec_path)
    chunks = [seed_chunk_from_dict(row) for row in _read_jsonl(Path(chunks_path))]
    records = build_memory_records(spec, chunks)

    run_dir = _create_run_dir(spec.output_dir, spec.name, "memory", output_dir)
    records_path = run_dir / "memory_records.jsonl"
    _write_jsonl(records_path, [memory_record_to_dict(record) for record in records])

    resolved_embedder = embedder or _default_embedder
    index_manifest = build_memory_index(spec, records, embedder=resolved_embedder, force_rebuild=force_rebuild)
    manifest = {
        "spec_name": spec.name,
        "spec_path": str(Path(spec_path)),
        "chunks_path": str(Path(chunks_path)),
        "memory_records_path": str(records_path),
        "output_dir": str(run_dir),
        "record_count": len(records),
        "index_manifest": index_manifest,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    _write_json(run_dir / "manifest.json", manifest)
    return manifest


def plan_corpus(
    spec_path: str | Path,
    memory_path: str | Path,
    output_dir: str | Path | None = None,
) -> dict:
    spec = load_corpus_spec(spec_path)
    memory_records = [memory_record_from_dict(row) for row in _read_jsonl(Path(memory_path))]
    tasks = plan_generation_tasks(spec, memory_records)

    run_dir = _create_run_dir(spec.output_dir, spec.name, "plan", output_dir)
    tasks_path = run_dir / "tasks.jsonl"
    _write_jsonl(tasks_path, [generation_task_to_dict(task) for task in tasks])

    manifest = {
        "spec_name": spec.name,
        "spec_path": str(Path(spec_path)),
        "memory_path": str(Path(memory_path)),
        "tasks_path": str(tasks_path),
        "output_dir": str(run_dir),
        "task_count": len(tasks),
        "target_samples": spec.total_samples,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    _write_json(run_dir / "manifest.json", manifest)
    return manifest


def generate_corpus(
    spec_path: str | Path,
    memory_path: str | Path,
    plan_path: str | Path,
    output_dir: str | Path | None = None,
    limit_tasks: int | None = None,
    predictor: Predictor | None = None,
    embedder: Embedder | None = None,
    resume_dir: str | Path | None = None,
) -> dict:
    spec = load_corpus_spec(spec_path)
    memory_records = [memory_record_from_dict(row) for row in _read_jsonl(Path(memory_path))]
    tasks = [generation_task_from_dict(row) for row in _read_jsonl(Path(plan_path))]
    if limit_tasks is not None:
        tasks = tasks[:limit_tasks]

    run_dir = _create_run_dir(spec.output_dir, spec.name, "generate", output_dir)
    resolved_predictor = predictor or _default_predictor
    resolved_embedder = embedder or _default_embedder

    # Load checkpoint if resuming
    completed_task_ids: set[str] = set()
    accepted_items: list[dict] = []
    review_items: list[dict] = []
    task_runs: list[dict] = []
    if resume_dir is not None:
        checkpoint_path = Path(resume_dir) / "checkpoint.jsonl"
        if checkpoint_path.exists():
            for row in _read_jsonl(checkpoint_path):
                completed_task_ids.add(row["task_id"])
                accepted_items.extend(row.get("accepted_items", []))
                review_items.extend(row.get("review_items", []))
                task_runs.append(row.get("task_run", {}))

    pending_tasks = [t for t in tasks if t.task_id not in completed_task_ids]
    checkpoint_path = run_dir / "checkpoint.jsonl"

    index_manifest = build_memory_index(spec, memory_records, embedder=resolved_embedder)

    max_workers = min(8, len(pending_tasks)) if pending_tasks else 1
    futures_map: dict = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for task in pending_tasks:
            future = pool.submit(
                _run_single_task,
                spec, task, memory_records, resolved_predictor, resolved_embedder,
            )
            futures_map[future] = task

    ordered_results: list[tuple] = [None] * len(pending_tasks)
    task_index = {task.task_id: i for i, task in enumerate(pending_tasks)}
    for future, task in futures_map.items():
        ordered_results[task_index[task.task_id]] = future.result()

    for task_run, raw_items, parse_warning, context_pack, prompt, hits, task in ordered_results:
        normalized_items = normalize_generated_items(spec, task, context_pack, raw_items)
        judged = judge_generated_items(spec, task, context_pack, normalized_items, accepted_items)

        task_accepted: list[dict] = []
        task_review: list[dict] = []
        if parse_warning and not normalized_items:
            task_review.append(
                {
                    "task_id": task.task_id,
                    "query": task.query,
                    "judge_issues": [{"code": "parse_failure", "message": parse_warning}],
                    "raw_response": task_run["raw_response"],
                }
            )

        for row in judged:
            if row["status"] == "accepted":
                accepted_items.append(row["item"])
                task_accepted.append(row["item"])
            else:
                review_row = dict(row["item"])
                review_row["judge_issues"] = row["issues"]
                review_items.append(review_row)
                task_review.append(review_row)

        task_run["accepted_count"] = len(task_accepted)
        task_run["review_count"] = len(task_review)
        task_runs.append(task_run)

        # Append checkpoint entry for this task
        with checkpoint_path.open("a", encoding="utf-8") as ckpt:
            ckpt.write(
                json.dumps(
                    {
                        "task_id": task.task_id,
                        "accepted_items": task_accepted,
                        "review_items": task_review,
                        "task_run": task_run,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    _write_jsonl(run_dir / "task_runs.jsonl", task_runs)
    _write_jsonl(run_dir / "accepted.jsonl", accepted_items)
    if review_items:
        _write_jsonl(run_dir / "review_queue.jsonl", review_items)

    manifest = {
        "spec_name": spec.name,
        "spec_path": str(Path(spec_path)),
        "memory_path": str(Path(memory_path)),
        "plan_path": str(Path(plan_path)),
        "output_dir": str(run_dir),
        "task_count": len(tasks),
        "accepted_count": len(accepted_items),
        "review_count": len(review_items),
        "index_manifest": index_manifest,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    _write_json(run_dir / "manifest.json", manifest)
    return manifest


def _run_single_task(
    spec,
    task,
    memory_records: list,
    predictor: Predictor,
    embedder: Embedder,
) -> tuple:
    hits = query_memory_index(spec, memory_records, task.query, embedder=embedder)
    context_pack = build_context_pack(spec, task, hits)
    prompt = build_generation_prompt(spec, task, context_pack)
    raw_response = predictor(spec, prompt)
    raw_items, parse_warning = parse_generation_response(raw_response)
    task_run = {
        "task_id": task.task_id,
        "query": task.query,
        "prompt": prompt,
        "retrieved_chunks": [
            {"chunk_id": hit.record.chunk_id, "score": round(hit.score, 4), "title": hit.record.title}
            for hit in hits
        ],
        "context_pack": context_pack,
        "raw_response": raw_response,
        "parse_warning": parse_warning,
    }
    return task_run, raw_items, parse_warning, context_pack, prompt, hits, task


def _default_predictor(spec, prompt: str) -> str:
    provider = get_provider(spec.platform)
    if provider is None:
        raise ValueError(f"未知平台: {spec.platform}")

    api_key = resolve_api_key(
        platform_id=spec.platform,
        env_name=spec.api_key_env,
        secret_name=spec.api_key_secret,
    )
    return provider.chat(
        api_key=api_key,
        model=spec.model,
        messages=[
            {"role": "system", "content": spec.system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=spec.temperature,
    )


def _default_embedder(spec, texts: list[str]) -> list[list[float]]:
    provider = get_provider(spec.platform)
    if provider is None:
        raise ValueError(f"未知平台: {spec.platform}")

    api_key = resolve_api_key(
        platform_id=spec.platform,
        env_name=spec.api_key_env,
        secret_name=spec.api_key_secret,
    )
    vectors: list[list[float]] = []
    batch_size = 64
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        vectors.extend(
            provider.embed(
                api_key=api_key,
                model=spec.embedding_model,
                inputs=batch,
                dimensions=spec.embedding_dimensions,
            )
        )
    return vectors


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _create_run_dir(base_output_dir: str, spec_name: str, mode: str, output_dir: str | Path | None) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    root = Path(output_dir or base_output_dir)
    run_dir = root / spec_name / f"{mode}_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir
