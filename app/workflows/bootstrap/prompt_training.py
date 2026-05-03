from __future__ import annotations

import json
import time
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
    sanitize_concept_description,
)
from app.workflows.bootstrap.memorization import MemorizationGuard
from app.workflows.bootstrap.prompt_optimizer import (
    build_llm_adamw_trace,
    finalize_candidate_trace,
    length_penalized_loss,
)

LLM_OPTIMIZE_ONLY = "llm_optimize_only"
LLM_REFLECTION = "llm_reflection"
TEXT_GRADIENT_ADAMW = "text_gradient_adamw"
PROMPT_TRAINING_METHODS = (LLM_OPTIMIZE_ONLY, LLM_REFLECTION, TEXT_GRADIENT_ADAMW)


@dataclass(frozen=True)
class _UsageSnapshot:
    call_count: int
    estimated_tokens: int
    elapsed_seconds: float


class _TrainingUsageMeter:
    def __init__(self) -> None:
        self.call_count = 0
        self.estimated_tokens = 0
        self.elapsed_seconds = 0.0

    def wrap(self, predictor: Predictor | None) -> Predictor | None:
        if predictor is None:
            return None

        def counted(system_prompt: str, messages: list[dict], temperature: float) -> str:
            started = time.perf_counter()
            raw = predictor(system_prompt, messages, temperature)
            self.elapsed_seconds += time.perf_counter() - started
            self.call_count += 1
            self.estimated_tokens += _estimate_tokens(system_prompt, messages, raw)
            return raw

        return counted

    def snapshot(self) -> _UsageSnapshot:
        return _UsageSnapshot(self.call_count, self.estimated_tokens, self.elapsed_seconds)

    def delta(self, snapshot: _UsageSnapshot) -> dict[str, Any]:
        return {
            "llm_call_count": self.call_count - snapshot.call_count,
            "estimated_tokens": self.estimated_tokens - snapshot.estimated_tokens,
            "estimated": True,
            "provider_elapsed_seconds": round(self.elapsed_seconds - snapshot.elapsed_seconds, 4),
        }

    def summary(self) -> dict[str, Any]:
        return {
            "llm_call_count": self.call_count,
            "estimated_tokens": self.estimated_tokens,
            "estimated": True,
            "provider_elapsed_seconds": round(self.elapsed_seconds, 4),
        }


@dataclass(frozen=True)
class PromptTrainingConfig:
    methods: tuple[str, ...] = PROMPT_TRAINING_METHODS
    max_rounds: int = 5
    candidate_count: int = 3
    target_pass_count: int = 15
    min_loss_delta: float = 0.01
    length_penalty: bool = True
    no_corpus_memorization: bool = True
    memorization_policy: str = "block_candidate"
    raw_feedback_allowed: bool = True

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
            no_corpus_memorization=bool(self.no_corpus_memorization),
            memorization_policy="block_candidate",
            raw_feedback_allowed=bool(self.raw_feedback_allowed),
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
    leakage_report: dict[str, Any]

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


def _estimate_tokens(system_prompt: str, messages: list[dict], raw_response: str) -> int:
    text_parts = [system_prompt, raw_response]
    text_parts.extend(str(message.get("content", "")) for message in messages)
    char_count = sum(len(part) for part in text_parts)
    return max(1, int(char_count / 4))


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
    memorization_guard = MemorizationGuard.from_store(
        store,
        task_ids,
        allowed_terms=[*guideline.get("labels", []), guideline.get("output_format", "")],
    )
    run_id = f"run-prompt-training-{uuid.uuid4().hex[:10]}"
    method_results = []
    for method in cfg.methods:
        usage_meter = _TrainingUsageMeter()
        method_results.append(
            _run_training_method(
                store=store,
                guideline_id=guideline_id,
                guideline=guideline,
                task_ids=task_ids,
                method=method,
                initial_description=initial_description,
                predictor=usage_meter.wrap(predictor),
                config=cfg,
                target_pass_count=target_pass_count,
                temperature=temperature,
                memorization_guard=memorization_guard,
                usage_meter=usage_meter,
            )
        )
    best = _select_best_method(method_results)
    status = "stable" if best["reached_target"] and best.get("memorization_passed", True) else "needs_revision"
    applied = bool(auto_apply and status == "stable")
    leakage_report = _leakage_report(memorization_guard, method_results, best, cfg)
    artifact_path = _write_training_artifact(store, run_id, guideline_id, cfg, method_results, best, leakage_report)
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
                "leakage_report": leakage_report,
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
        leakage_report=leakage_report,
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
        leakage_report=leakage_report,
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
    memorization_guard: MemorizationGuard,
    usage_meter: _TrainingUsageMeter,
) -> dict[str, Any]:
    method_started = time.perf_counter()
    current_description = initial_description
    rounds: list[dict[str, Any]] = []
    best_description = current_description
    best_result: dict[str, Any] | None = None
    best_loss: dict[str, Any] | None = None
    final_status = "needs_revision"

    for round_index in range(1, config.max_rounds + 1):
        round_started = time.perf_counter()
        usage_start = usage_meter.snapshot()
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
                    elapsed_seconds=time.perf_counter() - round_started,
                    usage=usage_meter.delta(usage_start),
                )
            )
            break

        failure_summary = _failure_summary(current_result["details"])
        round_guard = memorization_guard.with_validation_result(current_result)
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
            memorization_check = (
                round_guard.check(candidate_description, field="candidate_description")
                if config.no_corpus_memorization
                else None
            )
            if memorization_check is not None and not memorization_check.passed:
                candidate_evaluations.append(
                    {
                        "method": method,
                        "round_index": round_index,
                        "candidate_id": candidate["candidate_id"],
                        "status": "memorization_guard_blocked",
                        "source": candidate["source"],
                        "pass_count": len(current_result["passed"]),
                        "failed_count": len(current_result["failed"]),
                        "unstable_count": len(current_result["unstable"]),
                        "loss": current_loss["loss"],
                        "raw_loss": current_loss["loss"],
                        "length_delta": len(candidate_description) - len(current_description),
                        "prompt_length": len(candidate_description),
                        "accepted": False,
                        "reached_target": False,
                        "memorization_passed": False,
                        "blocked_terms_count": memorization_check.match_count,
                        "memorization_check": memorization_check.to_dict(),
                        "raw_feedback_allowed": method != LLM_OPTIMIZE_ONLY,
                        "sanitizer_warnings": candidate.get("sanitizer_warnings", []),
                        "raw_revision_response": candidate.get("raw_response", ""),
                        "description_preview": candidate_description[:240],
                        "evaluation_index": candidate_index,
                    }
                )
                continue
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
                        "prompt_length": len(candidate_description),
                        "accepted": False,
                        "reached_target": False,
                        "memorization_passed": True,
                        "blocked_terms_count": 0,
                        "raw_feedback_allowed": method != LLM_OPTIMIZE_ONLY,
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
                    "prompt_length": len(candidate_description),
                    "accepted": accepted,
                    "reached_target": reached_target,
                    "memorization_passed": True,
                    "blocked_terms_count": 0,
                    "memorization_check": memorization_check.to_dict() if memorization_check else {},
                    "raw_feedback_allowed": method != LLM_OPTIMIZE_ONLY,
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
                elapsed_seconds=time.perf_counter() - round_started,
                usage=usage_meter.delta(usage_start),
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
    final_memorization_check = (
        memorization_guard.with_validation_result(best_result).check(best_description, field="best_description")
        if config.no_corpus_memorization
        else None
    )
    return {
        "method": method,
        "status": "stable"
        if reached_target and (final_memorization_check is None or final_memorization_check.passed)
        else "needs_revision",
        "reached_target": reached_target,
        "best_description": best_description,
        "best_pass_count": final_pass_count,
        "best_loss": best_loss["loss"],
        "best_loss_detail": best_loss,
        "failed": best_result["failed"],
        "unstable": best_result["unstable"],
        "rounds": rounds,
        "memorization_passed": True if final_memorization_check is None else final_memorization_check.passed,
        "final_memorization_check": final_memorization_check.to_dict() if final_memorization_check else {},
        "elapsed_seconds": round(time.perf_counter() - method_started, 4),
        "usage": usage_meter.summary(),
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
        return _generate_text_gradient_candidates(
            current_description,
            guideline,
            validation_result,
            failure_summary,
            current_loss,
            predictor,
            candidate_count,
            temperature,
        )
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


def _generate_text_gradient_candidates(
    current_description: str,
    guideline: dict,
    validation_result: dict,
    failure_summary: str,
    current_loss: dict,
    predictor: Predictor | None,
    candidate_count: int,
    temperature: float,
) -> list[dict[str, Any]]:
    if predictor is None:
        return [
            {
                "candidate_id": "text-gradient-local-fallback",
                "description": current_description,
                "raw_response": "",
                "sanitizer_warnings": ["local_fallback_no_predictor"],
                "source": TEXT_GRADIENT_ADAMW,
                "prompt_optimization": _base_trace(TEXT_GRADIENT_ADAMW, current_loss),
                "method": TEXT_GRADIENT_ADAMW,
            }
        ]
    optimizer_context = build_llm_adamw_trace(current_description, validation_result, failure_summary, current_loss)
    directions = _training_directions(validation_result)[: max(1, min(candidate_count, 5))]
    candidates: list[dict[str, Any]] = []
    fallback = str(guideline.get("stable_description") or current_description)
    for index, direction in enumerate(directions, start=1):
        prompt = _build_text_gradient_prompt(current_description, validation_result, failure_summary, current_loss, direction, optimizer_context)
        raw = predictor("你是概念阐释改写助手。只返回最终可用的概念阐释正文。", [{"role": "user", "content": prompt}], temperature)
        cleaned, warnings = sanitize_concept_description(raw, fallback=fallback)
        candidates.append(
            {
                "candidate_id": f"candidate-{index:02d}-{direction['id']}",
                "description": cleaned,
                "raw_response": raw,
                "sanitizer_warnings": warnings,
                "source": TEXT_GRADIENT_ADAMW,
                "direction": direction["id"],
                "prompt_optimization": optimizer_context,
                "method": TEXT_GRADIENT_ADAMW,
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

training_feedback_only=true

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


def build_training_feedback_prompt(current_description: str, validation_result: dict, failure_summary: str) -> str:
    return _build_reflection_prompt(current_description, validation_result, failure_summary)


def _build_text_gradient_prompt(
    current_description: str,
    validation_result: dict,
    failure_summary: str,
    current_loss: dict,
    direction: dict,
    optimizer_context: dict,
) -> str:
    return f"""请根据批改对照和文本梯度，优化下面的概念阐释。

training_feedback_only=true

当前概念阐释：
{current_description}

本次探索方向：
{direction['title']}：{direction['instruction']}

当前 loss：
{current_loss.get('loss', 0.0)}

文本梯度信号（只供判断改写方向，不要原样复述）：
{_training_gradient_context(optimizer_context)}

批改对照（只供学习，不要复制原文、标准答案或模型答案到最终提示词）：
{_raw_feedback_context(validation_result, failure_summary)}

输出要求：
1. 只输出可以直接用于下一轮标注的概念阐释正文。
2. 可以把具体错误抽象成边界规则、排除规则或输出格式要求。
3. 不要复制原文、标准答案、模型答案、样例编号、失败摘要或修订日志。
4. 不要出现 gold-编号、“失败摘要”、“本轮失败”、“修订建议”、“漏标”、“多标”、“边界不稳定样例”等诊断文字。"""


def _raw_feedback_context(validation_result: dict, failure_summary: str) -> str:
    lines = [f"失败摘要：{failure_summary}"]
    failed = [detail for detail in validation_result.get("details", []) if detail.get("route") != "passed"][:8]
    for index, detail in enumerate(failed, start=1):
        gold = ", ".join(item["text"] for item in detail.get("gold_spans", [])[:6]) or "无"
        predicted = ", ".join(item["text"] for item in detail.get("predicted_spans", [])[:6]) or "无"
        missing = ", ".join(item["text"] for item in detail.get("missing_spans", [])[:4]) or "无"
        extra = ", ".join(item["text"] for item in detail.get("extra_spans", [])[:4]) or "无"
        lines.append(
            f"样例{index}: 原文={detail.get('text', '')} | 标准答案={gold} | 模型答案={predicted} | 应补={missing} | 应排除={extra}"
        )
    return "\n".join(lines)


def _training_gradient_context(optimizer_context: dict) -> str:
    gradients = list(optimizer_context.get("text_gradients", []))
    if not gradients:
        return "没有检测到明确文本梯度，保持最小改动。"
    lines: list[str] = []
    for gradient in gradients[:3]:
        lines.append(
            f"- segment={gradient.get('segment_id', '')}, method={gradient.get('method', '')}, "
            f"direction={gradient.get('direction', '')}, score={gradient.get('score', 0)}"
        )
    return "\n".join(lines)


def _training_directions(validation_result: dict) -> list[dict[str, str]]:
    missing_count = sum(len(detail.get("missing_spans", [])) for detail in validation_result.get("details", []))
    extra_count = sum(len(detail.get("extra_spans", [])) for detail in validation_result.get("details", []))
    directions = [
        {"id": "recall", "title": "提高召回", "instruction": "把具体漏标现象抽象成更清晰的纳入边界。"},
        {"id": "precision", "title": "收紧边界", "instruction": "把具体多标现象抽象成更清晰的排除规则。"},
        {"id": "balanced", "title": "平衡改写", "instruction": "同时优化纳入边界和排除规则。"},
        {"id": "minimal", "title": "最小改动", "instruction": "只做必要改动，保留已有有效规则。"},
    ]
    if extra_count > missing_count:
        return [directions[1], directions[2], directions[3], directions[0]]
    return directions


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
    elapsed_seconds: float = 0.0,
    usage: dict[str, Any] | None = None,
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
        "elapsed_seconds": round(elapsed_seconds, 4),
        "usage": usage or {},
        "llm_call_count": int((usage or {}).get("llm_call_count", 0)),
        "estimated_tokens": int((usage or {}).get("estimated_tokens", 0)),
        "accepted_candidate_id": accepted_candidate_id,
        "reached_target": not selected_result["failed"] and not selected_result["unstable"],
        "failure_summary": failure_summary,
        "failure_cases": _failure_cases(selected_result["details"]),
        "candidate_evaluations": candidate_evaluations,
        "memorization_blocked_count": sum(
            1 for evaluation in candidate_evaluations if evaluation.get("status") == "memorization_guard_blocked"
        ),
        "description": description,
    }


def _select_best_method(method_results: list[dict[str, Any]]) -> dict[str, Any]:
    if not method_results:
        raise ValueError("method_results must not be empty")
    return sorted(
        method_results,
        key=lambda row: (
            0 if row["reached_target"] and row.get("memorization_passed", True) else 1,
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
        "memorization_passed": row.get("memorization_passed", True),
        "memorization_blocked_count": sum(
            round_row.get("memorization_blocked_count", 0) for round_row in row.get("rounds", [])
        ),
        "llm_call_count": int(row.get("usage", {}).get("llm_call_count", 0)),
        "estimated_tokens": int(row.get("usage", {}).get("estimated_tokens", 0)),
        "elapsed_seconds": float(row.get("elapsed_seconds", 0.0)),
    }


def _leakage_report(
    guard: MemorizationGuard,
    method_results: list[dict[str, Any]],
    best: dict[str, Any],
    config: PromptTrainingConfig,
) -> dict[str, Any]:
    blocked_count = sum(
        1
        for method_result in method_results
        for round_row in method_result.get("rounds", [])
        for candidate in round_row.get("candidate_evaluations", [])
        if candidate.get("status") == "memorization_guard_blocked"
    )
    final_check = best.get("final_memorization_check") if config.no_corpus_memorization else None
    if final_check is None and config.no_corpus_memorization:
        final_check = guard.check(best.get("best_description", ""), field="best_description").to_dict()
    return {
        "no_corpus_memorization": config.no_corpus_memorization,
        "raw_feedback_allowed": config.raw_feedback_allowed,
        "memorization_policy": config.memorization_policy,
        "candidate_blocked_count": blocked_count,
        "final_prompt_clean": True if final_check is None else bool(final_check.get("passed", False)),
        "final_check": final_check or {},
        "fingerprint": guard.summary(),
    }


def _write_training_artifact(
    store: RuntimeStore,
    run_id: str,
    guideline_id: str,
    config: PromptTrainingConfig,
    method_results: list[dict[str, Any]],
    best: dict[str, Any],
    leakage_report: dict[str, Any],
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
        "leakage_report": leakage_report,
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
    leakage_report: dict[str, Any],
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
                "no_corpus_memorization": config.no_corpus_memorization,
                "memorization_policy": config.memorization_policy,
                "raw_feedback_allowed": config.raw_feedback_allowed,
                "leakage_summary": leakage_report,
                "artifact_path": artifact_path,
                "sanitizer_warnings": initial_warnings,
                "auto_generated": True,
                "auto_applied": auto_apply,
                "guideline_name": guideline.get("name", ""),
            },
        )
    )
