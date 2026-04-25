from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Callable

from app.domain.annotation_doc import spans_to_legacy_string
from app.domain.annotation_format import extract_annotation_tokens
from app.infrastructure.llm.credentials import resolve_api_key
from app.infrastructure.llm.registry import get_provider
from app.research.config import load_research_config
from app.research.contracts import ResearchConfig, ResearchSample
from app.research.indexing import build_example_index
from app.research.prompting import build_prompt
from app.research.retrieval import select_examples
from app.research.verifier import issue_to_dict, verify_annotation_result
from app.services.annotation_service import parse_annotation_response

Predictor = Callable[[ResearchConfig, str], str]
Embedder = Callable[[ResearchConfig, list[str]], list[list[float]]]


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


def _parse_sample(payload: dict, index: int) -> ResearchSample:
    if not isinstance(payload, dict):
        raise ValueError(f"dataset line {index}: 样本必须是 JSON 对象")
    text = payload.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"dataset line {index}: `text` 必须是非空字符串")

    sample_id = payload.get("id")
    if not isinstance(sample_id, str) or not sample_id.strip():
        sample_id = f"sample-{index:04d}"

    metadata = payload.get("metadata", {})
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise ValueError(f"dataset line {index}: `metadata` 必须是对象")

    gold_annotation = payload.get("gold_annotation")
    gold_explanation = payload.get("gold_explanation")
    if gold_annotation is not None and not isinstance(gold_annotation, str):
        raise ValueError(f"dataset line {index}: `gold_annotation` 必须是字符串")
    if gold_explanation is not None and not isinstance(gold_explanation, str):
        raise ValueError(f"dataset line {index}: `gold_explanation` 必须是字符串")

    return ResearchSample(
        id=sample_id.strip(),
        text=text.strip(),
        gold_annotation=gold_annotation.strip() if isinstance(gold_annotation, str) else None,
        gold_explanation=gold_explanation.strip() if isinstance(gold_explanation, str) else None,
        metadata=metadata,
    )


def load_samples(path: str | Path) -> list[ResearchSample]:
    dataset_path = Path(path)
    return [_parse_sample(row, index) for index, row in enumerate(_read_jsonl(dataset_path), start=1)]


def _annotation_signature(annotation) -> list[tuple[str, str, bool]]:
    if not annotation:
        return []
    if isinstance(annotation, dict):
        annotation = spans_to_legacy_string(annotation.get("layers", {}).get("spans", []))
    return sorted(
        (token["text"], token["label"], token["implicit"])
        for token in extract_annotation_tokens(annotation)
    )


def _default_predictor(config: ResearchConfig, prompt: str) -> str:
    provider = get_provider(config.platform)
    if provider is None:
        raise ValueError(f"未知平台: {config.platform}")

    api_key = resolve_api_key(
        platform_id=config.platform,
        env_name=config.api_key_env,
        secret_name=config.api_key_secret,
    )

    return provider.chat(
        api_key=api_key,
        model=config.model,
        messages=[
            {"role": "system", "content": config.system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=config.temperature,
    )


def _default_embedder(config: ResearchConfig, texts: list[str]) -> list[list[float]]:
    provider = get_provider(config.platform)
    if provider is None:
        raise ValueError(f"未知平台: {config.platform}")
    if not config.embedding_model:
        raise ValueError("当前研究配置未设置 embedding_model")

    api_key = resolve_api_key(
        platform_id=config.platform,
        env_name=config.api_key_env,
        secret_name=config.api_key_secret,
    )
    vectors: list[list[float]] = []
    batch_size = 64
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        vectors.extend(
            provider.embed(
                api_key=api_key,
                model=config.embedding_model,
                inputs=batch,
                dimensions=config.embedding_dimensions,
            )
        )
    return vectors


def preview_prompt(
    config_path: str | Path,
    dataset_path: str | Path,
    sample_id: str | None = None,
    sample_index: int = 0,
    embedder: Embedder | None = None,
) -> dict:
    config = load_research_config(config_path)
    samples = load_samples(dataset_path)
    if not samples:
        raise ValueError("数据集为空")

    sample: ResearchSample
    if sample_id is not None:
        sample = next((item for item in samples if item.id == sample_id), None)
        if sample is None:
            raise ValueError(f"未找到 sample_id={sample_id} 的样本")
    else:
        if sample_index < 0 or sample_index >= len(samples):
            raise ValueError(f"sample_index 超出范围: {sample_index}")
        sample = samples[sample_index]

    resolved_embedder = embedder or _default_embedder
    examples = select_examples(config, sample, embedder=resolved_embedder if config.retrieval_strategy == "embedding" else None)
    prompt = build_prompt(config, sample, examples)
    return {
        "config_name": config.name,
        "sample_id": sample.id,
        "retrieved_examples": [example.id for example in examples],
        "prompt": prompt,
    }


def run_pipeline(
    config_path: str | Path,
    dataset_path: str | Path,
    mode: str = "batch",
    output_dir: str | Path | None = None,
    limit: int | None = None,
    predictor: Predictor | None = None,
    embedder: Embedder | None = None,
) -> dict:
    config = load_research_config(config_path)
    samples = load_samples(dataset_path)
    if limit is not None:
        samples = samples[:limit]

    if mode not in {"batch", "audit"}:
        raise ValueError("mode 只能是 `batch` 或 `audit`")
    if mode == "audit" and any(sample.gold_annotation is None for sample in samples):
        raise ValueError("audit 模式要求每条样本都提供 gold_annotation")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_output_dir = Path(output_dir or config.output_dir)
    run_dir = base_output_dir / config.name / f"{mode}_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    resolved_predictor = predictor or _default_predictor
    resolved_embedder = embedder or _default_embedder

    index_manifest = None
    if config.retrieval_strategy == "embedding":
        index_manifest = build_example_index(config, embedder=resolved_embedder)

    predictions: list[dict] = []
    review_queue: list[dict] = []
    conflicts: list[dict] = []

    for sample in samples:
        examples = select_examples(config, sample, embedder=resolved_embedder if config.retrieval_strategy == "embedding" else None)
        prompt = build_prompt(config, sample, examples)
        raw_response = resolved_predictor(config, prompt)
        parsed_result, parse_warning = parse_annotation_response(raw_response)
        issues = verify_annotation_result(sample.text, parsed_result, config.conflict_rules)

        status = "accepted"
        gold_mismatch = False
        if mode == "audit":
            gold_mismatch = _annotation_signature(sample.gold_annotation) != _annotation_signature(
                parsed_result.get("annotation") if parsed_result else None
            )
            if gold_mismatch:
                status = "conflict"
        if status != "conflict" and (parse_warning or issues):
            status = "review"

        record = {
            "sample_id": sample.id,
            "status": status,
            "text": sample.text,
            "gold_annotation": sample.gold_annotation,
            "gold_explanation": sample.gold_explanation,
            "prompt": prompt,
            "retrieved_examples": [example.id for example in examples],
            "raw_response": raw_response,
            "parsed_result": parsed_result,
            "parse_warning": parse_warning,
            "verification_issues": [issue_to_dict(issue) for issue in issues],
            "metadata": sample.metadata,
        }
        predictions.append(record)

        if status == "review":
            review_queue.append(record)
        if status == "conflict":
            conflict_record = dict(record)
            conflict_record["conflict_reason"] = "gold_mismatch" if gold_mismatch else "verification_failure"
            conflicts.append(conflict_record)

    _write_jsonl(run_dir / "predictions.jsonl", predictions)
    if review_queue:
        _write_jsonl(run_dir / "review_queue.jsonl", review_queue)
    if conflicts:
        _write_jsonl(run_dir / "conflicts.jsonl", conflicts)

    manifest = {
        "config_name": config.name,
        "config_path": str(Path(config_path)),
        "dataset_path": str(Path(dataset_path)),
        "mode": mode,
        "sample_count": len(predictions),
        "accepted_count": sum(1 for record in predictions if record["status"] == "accepted"),
        "review_count": len(review_queue),
        "conflict_count": len(conflicts),
        "output_dir": str(run_dir),
        "platform": config.platform,
        "model": config.model,
        "temperature": config.temperature,
        "retrieval_strategy": config.retrieval_strategy,
        "top_k_examples": config.top_k_examples,
        "embedding_model": config.embedding_model,
        "embedding_dimensions": config.embedding_dimensions,
        "index_manifest": index_manifest,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def build_index(
    config_path: str | Path,
    embedder: Embedder | None = None,
    force_rebuild: bool = False,
) -> dict:
    config = load_research_config(config_path)
    resolved_embedder = embedder or _default_embedder
    manifest = build_example_index(config, embedder=resolved_embedder, force_rebuild=force_rebuild)
    manifest["config_name"] = config.name
    return manifest
