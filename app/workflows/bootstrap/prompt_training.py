from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.core.models import ConceptVersion, WorkflowRun
from app.runtime.store import RuntimeStore
from app.workflows.bootstrap.guideline import (
    Predictor,
    _concept_loss,
    _evaluate_gold_tasks,
    _failure_cases,
    _failure_summary,
    _guideline_from_payload,
    _next_concept_version,
    _revision_terms,
    generate_revision_candidates,
    sanitize_concept_description,
)
from app.workflows.bootstrap.prompt_optimizer import (
    finalize_candidate_trace,
    length_penalized_loss,
)

LLM_OPTIMIZE_ONLY = "llm_optimize_only"
LLM_REFLECTION = "llm_reflection"
TEXT_GRADIENT_ADAMW = "text_gradient_adamw"
PROMPT_TRAINING_METHODS = (LLM_OPTIMIZE_ONLY, LLM_REFLECTION, TEXT_GRADIENT_ADAMW)


@dataclass(frozen=True)
class PromptTrainingConfig:
    methods: tuple[str, ...] = PROMPT_TRAINING_METHODS
    max_rounds: int = 5
    candidate_count: int = 3
    target_pass_count: int = 15
    min_loss_delta: float = 0.01
    length_penalty: bool = True

    def normalized(self) -> "PromptTrainingConfig":
        methods = tuple(method for method in self.methods if method in PROMPT_TRAINING_METHODS)
        if not methods:
            raise ValueError("PromptTrainingConfig.methods must contain at least one supported method")
        return PromptTrainingConfig(
            methods=methods,
            max_rounds=max(1, min(int(self.max_rounds), 10)),
            candidate_count=max(1, min(int(self.candidate_count), 5)),
            target_pass_count=max(1, int(self.target_pass_count)),
            min_loss_delta=max(0.0, float(self.min_loss_delta)),
            length_penalty=bool(self.length_penalty),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PromptTrainingResult:
    status: str
    best_method: str
    best_description: str
    best_pass_count: int
    best_loss: float
    method_results: list[dict[str, Any]]
    rounds: list[dict[str, Any]]
    artifact_path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_llm_optimize_only_prompt(current_description: str) -> str:
    return f"""请优化下面的概念提示词，使它更清晰、更稳定、更适合执行标注任务。

当前提示词：
{current_description}

输出要求：
1. 只返回优化后的概念阐释正文。
2. 保持“概念描述 / 标签集合 / 边界规则 / 排除规则 / 输出格式”这类清晰字段。
3. 不要解释你的修改，不要输出日志，不要输出分析过程。"""


def run_prompt_training_experiment(
    store: RuntimeStore,
    guideline_id: str,
    predictor: Predictor | None = None,
    config: PromptTrainingConfig | None = None,
    temperature: float = 0.0,
    auto_apply: bool = False,
) -> dict[str, Any]:
    cfg = (config or PromptTrainingConfig()).normalized()
    guideline_row = store.get_guideline(guideline_id)
    if guideline_row is None:
        raise ValueError(f"未找到概念阐释: {guideline_id}")
    guideline = guideline_row["payload"]
    gold_sets = store.list_gold_example_sets(guideline_id=guideline_id, limit=1)
    if not gold_sets:
        raise ValueError("该概念还没有金样例库")
    gold_set = gold_sets[0]["payload"]
    target_count = int(gold_set.get("target_count", cfg.target_pass_count))
    task_ids = list(gold_set.get("task_ids", []))
    if len(task_ids) < target_count:
        raise ValueError(f"提示词优化训练需要 {target_count} 条金样例，当前只有 {len(task_ids)} 条")
    target_pass_count = min(cfg.target_pass_count, len(task_ids))

    initial_description, initial_warnings = sanitize_concept_description(
        str(guideline.get("stable_description") or guideline.get("brief", "")),
        fallback=str(guideline.get("brief", "")),
    )
    run_id = f"run-prompt-training-{uuid.uuid4().hex[:10]}"
    method_results = [
        _run_training_method(
            store=store,
            guideline_id=guideline_id,
            guideline=guideline,
            task_ids=task_ids,
            method=method,
            initial_description=initial_description,
            predictor=predictor,
            config=cfg,
            target_pass_count=target_pass_count,
            temperature=temperature,
        )
        for method in cfg.methods
    ]
    best = _select_best_method(method_results)
    status = "stable" if best["reached_target"] else "needs_revision"
    applied = bool(auto_apply and status == "stable")
    artifact_path = _write_training_artifact(store, run_id, guideline_id, cfg, method_results, best)
    store.upsert_run(
        WorkflowRun(
            id=run_id,
            workflow="prompt_training",
            status="succeeded",
            input_ref=guideline_id,
            output_ref=best["best_description"],
            artifacts=(artifact_path,),
            summary=f"{best['method']} pass={best['best_pass_count']}/{target_pass_count}, loss={best['best_loss']}",
            meta={
                "guideline_id": guideline_id,
                "config": cfg.to_dict(),
                "best_method": best["method"],
                "reached_target": best["reached_target"],
            },
        )
    )
    store.add_artifact(run_id, artifact_path, "prompt_training_trace", {"guideline_id": guideline_id})
    _store_training_version(
        store=store,
        guideline=guideline,
        guideline_id=guideline_id,
        best=best,
        method_results=method_results,
        config=cfg,
        artifact_path=artifact_path,
        target_pass_count=target_pass_count,
        initial_warnings=initial_warnings,
        auto_apply=applied,
    )
    if applied:
        updated_guideline = _guideline_from_payload(
            guideline,
            status=status,
            stable_description=best["best_description"],
        )
        store.upsert_guideline(updated_guideline)

    result = PromptTrainingResult(
        status=status,
        best_method=best["method"],
        best_description=best["best_description"],
        best_pass_count=int(best["best_pass_count"]),
        best_loss=float(best["best_loss"]),
        method_results=[_method_summary(row) for row in method_results],
        rounds=[round_row for row in method_results for round_row in row["rounds"]],
        artifact_path=artifact_path,
    )
    return result.to_dict()


def _run_training_method(
    store: RuntimeStore,
    guideline_id: str,
    guideline: dict,
    task_ids: list[str],
    method: str,
    initial_description: str,
    predictor: Predictor | None,
    config: PromptTrainingConfig,
    target_pass_count: int,
    temperature: float,
) -> dict[str, Any]:
    current_description = initial_description
    rounds: list[dict[str, Any]] = []
    best_description = current_description
    best_result: dict[str, Any] | None = None
    best_loss: dict[str, Any] | None = None
    final_status = "needs_revision"

    for round_index in range(1, config.max_rounds + 1):
        current_guideline = {**guideline, "stable_description": current_description}
        current_result = _evaluate_gold_tasks(
            store,
            guideline_id,
            current_guideline,
            task_ids,
            predictor,
            temperature,
            round_index,
            source=f"prompt_training_{method}",
            candidate_id=f"{method}-current-{round_index}",
        )
        current_loss = _concept_loss(current_result)
        current_pass_count = len(current_result["passed"])
        best_result = current_result
        best_loss = current_loss
        if current_pass_count >= target_pass_count and not current_result["failed"] and not current_result["unstable"]:
            final_status = "stable"
            rounds.append(
                _round_record(
                    method,
                    round_index,
                    "stable",
                    current_description,
                    current_result,
                    current_loss,
                    current_loss,
                    "current",
                    [],
                )
            )
            break

        failure_summary = _failure_summary(current_result["details"])
        candidates = _generate_training_candidates(
            method,
            current_description,
            guideline,
            current_result,
            failure_summary,
            current_loss,
            predictor,
            config.candidate_count,
            temperature,
        )
        selected_result = current_result
        selected_loss = current_loss
        selected_description = current_description
        selected_candidate_id = "current"
        candidate_evaluations: list[dict[str, Any]] = []
        seen = {current_description}
        for candidate_index, candidate in enumerate(candidates, start=1):
            candidate_description = candidate["description"]
            if candidate_description in seen:
                candidate_evaluations.append(
                    {
                        "method": method,
                        "round_index": round_index,
                        "candidate_id": candidate["candidate_id"],
                        "status": "skipped_duplicate",
                        "loss": current_loss["loss"],
                        "raw_loss": current_loss["loss"],
                        "length_delta": 0,
                        "accepted": False,
                        "reached_target": False,
                        "sanitizer_warnings": candidate.get("sanitizer_warnings", []),
                    }
                )
                continue
            seen.add(candidate_description)
            candidate_guideline = {**guideline, "stable_description": candidate_description}
            candidate_result = _evaluate_gold_tasks(
                store,
                guideline_id,
                candidate_guideline,
                task_ids,
                predictor,
                temperature,
                round_index,
                source=f"prompt_training_{method}_candidate",
                candidate_id=candidate["candidate_id"],
            )
            raw_loss = _concept_loss(candidate_result)
            candidate_loss = (
                length_penalized_loss(raw_loss, current_description, candidate_description)
                if config.length_penalty
                else _loss_without_length_penalty(raw_loss, current_description, candidate_description)
            )
            reached_target = len(candidate_result["passed"]) >= target_pass_count and not candidate_result["failed"] and not candidate_result["unstable"]
            accepted = candidate_loss["loss"] + config.min_loss_delta < selected_loss["loss"]
            optimization_trace = finalize_candidate_trace(
                candidate.get("prompt_optimization", {}),
                candidate["candidate_id"],
                current_description,
                candidate_description,
                current_loss,
                candidate_loss,
                accepted,
            )
            candidate_evaluations.append(
                {
                    "method": method,
                    "round_index": round_index,
                    "candidate_id": candidate["candidate_id"],
                    "status": "accepted" if accepted else "rejected",
                    "source": candidate["source"],
                    "pass_count": len(candidate_result["passed"]),
                    "failed_count": len(candidate_result["failed"]),
                    "unstable_count": len(candidate_result["unstable"]),
                    "loss": candidate_loss["loss"],
                    "raw_loss": raw_loss["loss"],
                    "loss_detail": candidate_loss,
                    "raw_loss_detail": raw_loss,
                    "length_delta": candidate_loss["length_delta"],
                    "accepted": accepted,
                    "reached_target": reached_target,
                    "sanitizer_warnings": candidate.get("sanitizer_warnings", []),
                    "raw_revision_response": candidate.get("raw_response", ""),
                    "prompt_optimization_trace": optimization_trace,
                    "description_preview": candidate_description[:240],
                    "evaluation_index": candidate_index,
                }
            )
            if accepted:
                selected_result = candidate_result
                selected_loss = candidate_loss
                selected_description = candidate_description
                selected_candidate_id = candidate["candidate_id"]

        round_status = "stable" if len(selected_result["passed"]) >= target_pass_count and not selected_result["failed"] and not selected_result["unstable"] else "needs_revision"
        if selected_candidate_id == "current":
            round_status = "no_improvement"
        rounds.append(
            _round_record(
                method,
                round_index,
                round_status,
                selected_description,
                selected_result,
                selected_loss,
                current_loss,
                selected_candidate_id,
                candidate_evaluations,
            )
        )
        best_description = selected_description
        best_result = selected_result
        best_loss = selected_loss
        final_status = "stable" if round_status == "stable" else "needs_revision"
        if round_status in {"stable", "no_improvement"}:
            break
        current_description = selected_description

    assert best_result is not None and best_loss is not None
    final_pass_count = len(best_result["passed"])
    reached_target = final_pass_count >= target_pass_count and not best_result["failed"] and not best_result["unstable"]
    return {
        "method": method,
        "status": "stable" if reached_target else final_status,
        "reached_target": reached_target,
        "best_description": best_description,
        "best_pass_count": final_pass_count,
        "best_loss": best_loss["loss"],
        "best_loss_detail": best_loss,
        "failed": best_result["failed"],
        "unstable": best_result["unstable"],
        "rounds": rounds,
    }


def _generate_training_candidates(
    method: str,
    current_description: str,
    guideline: dict,
    validation_result: dict,
    failure_summary: str,
    current_loss: dict,
    predictor: Predictor | None,
    candidate_count: int,
    temperature: float,
) -> list[dict[str, Any]]:
    if method == TEXT_GRADIENT_ADAMW:
        return [
            {**candidate, "method": method}
            for candidate in generate_revision_candidates(
                {**guideline, "stable_description": current_description},
                validation_result,
                failure_summary,
                predictor=predictor,
                temperature=temperature,
                candidate_count=candidate_count,
                current_loss=current_loss,
            )
        ]
    if method == LLM_REFLECTION:
        return _generate_reflection_candidates(current_description, validation_result, failure_summary, predictor, candidate_count, temperature)
    if method == LLM_OPTIMIZE_ONLY:
        return _generate_optimize_only_candidates(current_description, predictor, candidate_count, temperature)
    raise ValueError(f"Unsupported prompt training method: {method}")


def _generate_optimize_only_candidates(
    current_description: str,
    predictor: Predictor | None,
    candidate_count: int,
    temperature: float,
) -> list[dict[str, Any]]:
    if predictor is None:
        return [
            {
                "candidate_id": "llm-optimize-only-local-fallback",
                "description": current_description,
                "raw_response": "",
                "sanitizer_warnings": ["local_fallback_no_predictor"],
                "source": LLM_OPTIMIZE_ONLY,
                "prompt_optimization": _base_trace(LLM_OPTIMIZE_ONLY, {"loss": 0.0}),
            }
        ]
    candidates: list[dict[str, Any]] = []
    for index in range(1, candidate_count + 1):
        prompt = build_llm_optimize_only_prompt(current_description)
        raw = predictor("你是概念提示词优化助手。只返回最终可用的概念阐释正文。", [{"role": "user", "content": prompt}], temperature)
        cleaned, warnings = sanitize_concept_description(raw, fallback=current_description)
        candidates.append(
            {
                "candidate_id": f"llm-optimize-only-{index:02d}",
                "description": cleaned,
                "raw_response": raw,
                "sanitizer_warnings": warnings,
                "source": LLM_OPTIMIZE_ONLY,
                "prompt_optimization": _base_trace(LLM_OPTIMIZE_ONLY, {"loss": 0.0}),
            }
        )
    return candidates


def _generate_reflection_candidates(
    current_description: str,
    validation_result: dict,
    failure_summary: str,
    predictor: Predictor | None,
    candidate_count: int,
    temperature: float,
) -> list[dict[str, Any]]:
    fallback = current_description
    if predictor is None:
        return [
            {
                "candidate_id": "llm-reflection-local-fallback",
                "description": fallback,
                "raw_response": "",
                "sanitizer_warnings": ["local_fallback_no_predictor"],
                "source": LLM_REFLECTION,
                "prompt_optimization": _base_trace(LLM_REFLECTION, {"loss": 0.0}),
            }
        ]
    candidates: list[dict[str, Any]] = []
    for index in range(1, candidate_count + 1):
        prompt = _build_reflection_prompt(current_description, validation_result, failure_summary)
        raw = predictor("你是概念阐释反思优化助手。只返回最终可用的概念阐释正文。", [{"role": "user", "content": prompt}], temperature)
        cleaned, warnings = sanitize_concept_description(raw, fallback=fallback)
        candidates.append(
            {
                "candidate_id": f"llm-reflection-{index:02d}",
                "description": cleaned,
                "raw_response": raw,
                "sanitizer_warnings": warnings,
                "source": LLM_REFLECTION,
                "prompt_optimization": _base_trace(LLM_REFLECTION, {"loss": 0.0}),
            }
        )
    return candidates


def _build_reflection_prompt(current_description: str, validation_result: dict, failure_summary: str) -> str:
    missing_terms, extra_terms = _revision_terms(validation_result.get("details", []))
    missing_line = "；".join(missing_terms[:12]) or "无"
    extra_line = "；".join(extra_terms[:8]) or "无"
    return f"""请根据金样例校准中的失败点，优化下面的概念阐释。

当前概念阐释：
{current_description}

失败摘要（只供你理解，不要原样写进最终提示词）：
{failure_summary}

需要更明确纳入的片段类型：{missing_line}
需要更明确排除或收紧边界的片段类型：{extra_line}

输出要求：
1. 只输出可以直接用于下一轮标注的概念阐释正文。
2. 保持“概念描述 / 标签集合 / 边界规则 / 排除规则 / 输出格式”这类清晰字段。
3. 不要输出解释、失败样例编号、失败摘要或修订日志。
4. 不要出现 gold-编号、“失败摘要”、“本轮失败”、“修订建议”、“漏标”、“多标”、“边界不稳定样例”等诊断文字。"""


def _base_trace(method: str, current_loss: dict) -> dict[str, Any]:
    return {
        "optimizer": method,
        "segments": [],
        "text_gradients": [],
        "proposed_trace": {
            "segment_id": "",
            "perturbation_method": method,
            "gradient_direction": "not_used",
            "current_loss": float(current_loss.get("loss", 0.0)),
            "diagnostics": "",
            "metadata": {"optimizer": method},
        },
    }


def _loss_without_length_penalty(candidate_loss: dict, current_description: str, candidate_description: str) -> dict:
    raw_loss = float(candidate_loss.get("loss", 0.0))
    updated = dict(candidate_loss)
    updated["raw_loss"] = round(raw_loss, 4)
    updated["length_penalty"] = 0.0
    updated["length_delta"] = len(candidate_description) - len(current_description)
    updated["loss"] = round(raw_loss, 4)
    return updated


def _round_record(
    method: str,
    round_index: int,
    status: str,
    description: str,
    selected_result: dict,
    selected_loss: dict,
    current_loss: dict,
    accepted_candidate_id: str,
    candidate_evaluations: list[dict[str, Any]],
) -> dict[str, Any]:
    failure_summary = _failure_summary(selected_result["details"])
    return {
        "method": method,
        "round_index": round_index,
        "status": status,
        "pass_count": len(selected_result["passed"]),
        "failed": selected_result["failed"],
        "unstable": selected_result["unstable"],
        "loss": selected_loss["loss"],
        "raw_loss": selected_loss.get("raw_loss", selected_loss["loss"]),
        "loss_delta": round(current_loss["loss"] - selected_loss["loss"], 4),
        "accepted_candidate_id": accepted_candidate_id,
        "reached_target": not selected_result["failed"] and not selected_result["unstable"],
        "failure_summary": failure_summary,
        "failure_cases": _failure_cases(selected_result["details"]),
        "candidate_evaluations": candidate_evaluations,
        "description": description,
    }


def _select_best_method(method_results: list[dict[str, Any]]) -> dict[str, Any]:
    if not method_results:
        raise ValueError("method_results must not be empty")
    return sorted(
        method_results,
        key=lambda row: (
            0 if row["reached_target"] else 1,
            float(row["best_loss"]),
            len(row["best_description"]),
            len(row["rounds"]),
            PROMPT_TRAINING_METHODS.index(row["method"]) if row["method"] in PROMPT_TRAINING_METHODS else 99,
        ),
    )[0]


def _method_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "method": row["method"],
        "status": row["status"],
        "reached_target": row["reached_target"],
        "best_pass_count": row["best_pass_count"],
        "best_loss": row["best_loss"],
        "round_count": len(row["rounds"]),
        "failed_count": len(row["failed"]),
        "unstable_count": len(row["unstable"]),
        "description_length": len(row["best_description"]),
    }


def _write_training_artifact(
    store: RuntimeStore,
    run_id: str,
    guideline_id: str,
    config: PromptTrainingConfig,
    method_results: list[dict[str, Any]],
    best: dict[str, Any],
) -> str:
    artifact_dir = Path(store.database_path).parent / "artifacts" / "prompt_training"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    path = artifact_dir / f"{run_id}.json"
    payload = {
        "run_id": run_id,
        "guideline_id": guideline_id,
        "config": config.to_dict(),
        "best_method": best["method"],
        "method_results": method_results,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def _store_training_version(
    store: RuntimeStore,
    guideline: dict,
    guideline_id: str,
    best: dict[str, Any],
    method_results: list[dict[str, Any]],
    config: PromptTrainingConfig,
    artifact_path: str,
    target_pass_count: int,
    initial_warnings: list[str],
    auto_apply: bool,
) -> None:
    next_version = _next_concept_version(store, guideline_id)
    store.upsert_concept_version(
        ConceptVersion(
            id=f"concept-version-{uuid.uuid4().hex[:10]}",
            guideline_id=guideline_id,
            version=next_version,
            description=best["best_description"],
            failed_task_ids=tuple(best.get("failed", [])),
            unstable_task_ids=tuple(best.get("unstable", [])),
            notes="提示词优化训练结果。",
            metadata={
                "prompt_training": True,
                "training_methods": config.methods,
                "best_method": best["method"],
                "method_comparison": [_method_summary(row) for row in method_results],
                "target_pass_count": target_pass_count,
                "reached_target": best["reached_target"],
                "training_trace_summary": {
                    "best_loss": best["best_loss"],
                    "best_pass_count": best["best_pass_count"],
                    "round_count": len(best["rounds"]),
                    "artifact_path": artifact_path,
                },
                "artifact_path": artifact_path,
                "sanitizer_warnings": initial_warnings,
                "auto_generated": True,
                "auto_applied": auto_apply,
                "guideline_name": guideline.get("name", ""),
            },
        )
    )
