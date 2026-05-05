from __future__ import annotations

import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Lock
from typing import Any

from app.core.models import ConceptVersion, WorkflowRun
from app.infrastructure.llm.runtime import LLMServiceRuntime
from app.runtime.progress import ProgressRecorder, estimate_prompt_training_total_calls
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
    segment_prompt,
)
from app.workflows.bootstrap.prompt_spec import (
    concept_prompt_spec_from_guideline,
    ensure_concept_only_description,
    strip_frozen_protocol_sections,
)

LLM_OPTIMIZE_ONLY = "llm_optimize_only"
LLM_REFLECTION = "llm_reflection"
TEXT_GRADIENT_ADAMW = "text_gradient_adamw"
SGD_CANDIDATE_SEARCH = "sgd_candidate_search"
CRITIC_ADAMW_OPTIMIZER = "critic_adamw_optimizer"
MASK_GUIDED_OPTIMIZATION = "mask_guided_optimization"
PROMPT_OPTIMIZER_METHODS = (SGD_CANDIDATE_SEARCH, CRITIC_ADAMW_OPTIMIZER, MASK_GUIDED_OPTIMIZATION)
PROMPT_OPTIMIZER_ALIASES = {
    SGD_CANDIDATE_SEARCH: SGD_CANDIDATE_SEARCH,
    CRITIC_ADAMW_OPTIMIZER: CRITIC_ADAMW_OPTIMIZER,
    MASK_GUIDED_OPTIMIZATION: MASK_GUIDED_OPTIMIZATION,
    LLM_OPTIMIZE_ONLY: SGD_CANDIDATE_SEARCH,
    LLM_REFLECTION: CRITIC_ADAMW_OPTIMIZER,
    TEXT_GRADIENT_ADAMW: MASK_GUIDED_OPTIMIZATION,
}
PROMPT_TRAINING_METHODS = PROMPT_OPTIMIZER_METHODS
OPTIMIZER_DISPLAY_NAMES = {
    SGD_CANDIDATE_SEARCH: "SGD-like Candidate Search",
    CRITIC_ADAMW_OPTIMIZER: "AdamW-like Critic Optimizer",
    MASK_GUIDED_OPTIMIZATION: "Mask-guided Prompt Optimization",
}
OPTIMIZER_DISPLAY_NAMES_ZH = {
    SGD_CANDIDATE_SEARCH: "候选搜索优化",
    CRITIC_ADAMW_OPTIMIZER: "批判器 AdamW 优化",
    MASK_GUIDED_OPTIMIZATION: "遮挡梯度优化",
}
OPTIMIZER_FAMILIES = {
    SGD_CANDIDATE_SEARCH: "zero_order_candidate_search",
    CRITIC_ADAMW_OPTIMIZER: "agentic_adamw_critic",
    MASK_GUIDED_OPTIMIZATION: "explicit_mask_text_gradient",
}


def normalize_prompt_optimizer_method(method: str) -> str:
    normalized = PROMPT_OPTIMIZER_ALIASES.get(str(method or "").strip())
    if normalized is None:
        raise ValueError(f"Unsupported prompt training method: {method}")
    return normalized


def optimizer_display_name(method: str) -> str:
    return OPTIMIZER_DISPLAY_NAMES.get(PROMPT_OPTIMIZER_ALIASES.get(method, method), str(method))


def optimizer_display_name_zh(method: str) -> str:
    return OPTIMIZER_DISPLAY_NAMES_ZH.get(PROMPT_OPTIMIZER_ALIASES.get(method, method), str(method))


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
        self._lock = Lock()

    def wrap(self, predictor: Predictor | None) -> Predictor | None:
        if predictor is None:
            return None

        def counted(system_prompt: str, messages: list[dict], temperature: float) -> str:
            started = time.perf_counter()
            raw = predictor(system_prompt, messages, temperature)
            elapsed = time.perf_counter() - started
            tokens = _estimate_tokens(system_prompt, messages, raw)
            with self._lock:
                self.elapsed_seconds += elapsed
                self.call_count += 1
                self.estimated_tokens += tokens
            return raw

        return counted

    def snapshot(self) -> _UsageSnapshot:
        with self._lock:
            return _UsageSnapshot(self.call_count, self.estimated_tokens, self.elapsed_seconds)

    def delta(self, snapshot: _UsageSnapshot) -> dict[str, Any]:
        with self._lock:
            call_count = self.call_count
            estimated_tokens = self.estimated_tokens
            elapsed_seconds = self.elapsed_seconds
        return {
            "llm_call_count": call_count - snapshot.call_count,
            "estimated_tokens": estimated_tokens - snapshot.estimated_tokens,
            "estimated": True,
            "provider_elapsed_seconds": round(elapsed_seconds - snapshot.elapsed_seconds, 4),
        }

    def summary(self) -> dict[str, Any]:
        with self._lock:
            call_count = self.call_count
            estimated_tokens = self.estimated_tokens
            elapsed_seconds = self.elapsed_seconds
        return {
            "llm_call_count": call_count,
            "estimated_tokens": estimated_tokens,
            "estimated": True,
            "provider_elapsed_seconds": round(elapsed_seconds, 4),
        }


@dataclass(frozen=True)
class PromptTrainingConfig:
    methods: tuple[str, ...] = PROMPT_TRAINING_METHODS
    method_aliases: dict[str, str] | None = None
    max_rounds: int = 30
    candidate_count: int = 5
    target_pass_count: int = 15
    min_loss_delta: float = 0.01
    patience_rounds: int = 5
    stop_policy: str = "patience_no_loss_improvement"
    candidate_temperature: float = 0.3
    evaluation_temperature: float = 0.0
    length_penalty: bool = True
    no_corpus_memorization: bool = True
    memorization_policy: str = "repair_then_reject"
    raw_feedback_allowed: bool = True
    concurrency: int = 50
    repair_leaked_candidates: bool = True
    max_repair_attempts: int = 2
    provider_id: str = "deepseek"
    model: str = "deepseek-v4-pro"
    progress_update_interval_seconds: int = 2
    persist_progress_events: bool = True

    def normalized(self) -> "PromptTrainingConfig":
        methods: list[str] = []
        aliases: dict[str, str] = {}
        for raw_method in self.methods:
            normalized_method = normalize_prompt_optimizer_method(raw_method)
            if normalized_method not in methods:
                methods.append(normalized_method)
            if str(raw_method) != normalized_method:
                aliases[normalized_method] = str(raw_method)
        if not methods:
            raise ValueError("PromptTrainingConfig.methods must contain at least one supported method")
        return PromptTrainingConfig(
            methods=tuple(methods),
            method_aliases=aliases,
            max_rounds=max(1, min(int(self.max_rounds), 100)),
            candidate_count=max(1, min(int(self.candidate_count), 5)),
            target_pass_count=max(1, int(self.target_pass_count)),
            min_loss_delta=max(0.0, float(self.min_loss_delta)),
            patience_rounds=max(1, min(int(self.patience_rounds), 20)),
            stop_policy="patience_no_loss_improvement",
            candidate_temperature=max(0.0, min(float(self.candidate_temperature), 2.0)),
            evaluation_temperature=max(0.0, min(float(self.evaluation_temperature), 2.0)),
            length_penalty=bool(self.length_penalty),
            no_corpus_memorization=bool(self.no_corpus_memorization),
            memorization_policy="repair_then_reject",
            raw_feedback_allowed=bool(self.raw_feedback_allowed),
            concurrency=max(1, min(int(self.concurrency), 50)),
            repair_leaked_candidates=bool(self.repair_leaked_candidates),
            max_repair_attempts=max(0, min(int(self.max_repair_attempts), 5)),
            provider_id=str(self.provider_id or "deepseek"),
            model=str(self.model or "deepseek-v4-pro"),
            progress_update_interval_seconds=max(1, min(int(self.progress_update_interval_seconds), 30)),
            persist_progress_events=bool(self.persist_progress_events),
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
    progress_events: list[dict[str, Any]]
    usage_summary: dict[str, Any]
    repair_summary: dict[str, Any]
    real_provider_run: bool
    stop_policy: str
    experiment_case: str
    initial_description: str
    prompt_versions: list[dict[str, Any]]
    report_path: str
    prompt_evolution_path: str
    run_id: str = ""
    progress_summary: dict[str, Any] | None = None
    events_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_llm_optimize_only_prompt(current_description: str, accepted_history: list[dict[str, Any]] | None = None) -> str:
    concept_description = strip_frozen_protocol_sections(current_description)
    return f"""请优化下面的概念提示词，使它更清晰、更稳定、更适合执行标注任务。

当前可优化定义：
{concept_description}

历史优化摘要（旧 prompt -> 新 prompt -> loss 变化；只供判断哪些改写方向已经有效，不要原样复述）：
{_accepted_history_context(accepted_history or [])}

输出要求：
1. 只返回优化后的概念阐释正文。
2. 只允许包含任务定义、概念定义、边界规则和排除规则。
3. 不要输出标签集合、JSON schema、annotation 标注格式、输出格式或格式修复指令。
4. 不要解释你的修改，不要输出日志，不要输出分析过程。"""


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
    progress_recorder: ProgressRecorder | None = None,
    run_id: str | None = None,
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
    run_id = run_id or getattr(progress_recorder, "run_id", "") or f"run-prompt-training-{uuid.uuid4().hex[:10]}"
    estimated_total = estimate_prompt_training_total_calls(
        len(cfg.methods),
        cfg.max_rounds,
        len(task_ids),
        cfg.candidate_count,
    )
    if progress_recorder is not None:
        progress_recorder.emit(
            "run_started",
            stage="准备训练",
            message="提示词优化训练已开始",
            total=estimated_total,
            payload={
                "guideline_id": guideline_id,
                "method_count": len(cfg.methods),
                "gold_count": len(task_ids),
                "candidate_count": cfg.candidate_count,
                "max_rounds": cfg.max_rounds,
                "provider": cfg.provider_id,
                "model": cfg.model,
                "concurrency": cfg.concurrency,
            },
        )

    initial_description, initial_warnings = sanitize_concept_description(
        str(guideline.get("stable_description") or guideline.get("brief", "")),
        fallback=str(guideline.get("brief", "")),
    )
    initial_description, concept_only_warnings = ensure_concept_only_description(
        initial_description,
        fallback=concept_prompt_spec_from_guideline(guideline).text,
    )
    initial_warnings.extend(concept_only_warnings)
    memorization_guard = MemorizationGuard.from_store(
        store,
        task_ids,
        allowed_terms=[*guideline.get("labels", []), guideline.get("output_format", "")],
    )
    method_results: list[dict[str, Any]] = []
    real_provider_run = bool(getattr(predictor, "is_real_provider", False))
    ordered_results: list[dict[str, Any] | None] = [None] * len(cfg.methods)
    max_method_workers = max(1, min(len(cfg.methods), cfg.concurrency))
    with ThreadPoolExecutor(max_workers=max_method_workers) as pool:
        future_map = {}
        for index, method in enumerate(cfg.methods):
            usage_meter = _TrainingUsageMeter()
            future = pool.submit(
                _run_training_method,
                store,
                guideline_id,
                guideline,
                task_ids,
                method,
                initial_description,
                usage_meter.wrap(predictor),
                cfg,
                target_pass_count,
                memorization_guard,
                usage_meter,
                cfg.concurrency,
                progress_recorder,
            )
            future_map[future] = index
        for future in as_completed(future_map):
            ordered_results[future_map[future]] = future.result()
    method_results = [row for row in ordered_results if row is not None]
    best = _select_best_method(method_results)
    status = "stable" if best["reached_target"] and best.get("memorization_passed", True) else "needs_revision"
    applied = bool(auto_apply and status == "stable")
    leakage_report = _leakage_report(memorization_guard, method_results, best, cfg)
    artifact_path = _write_training_artifact(store, run_id, guideline_id, cfg, method_results, best, leakage_report)
    existing_run = store.get_run(run_id)
    existing_payload = existing_run["payload"] if existing_run else {}
    run_status = "running" if existing_run and existing_run.get("status") == "running" else "succeeded"
    store.upsert_run(
        WorkflowRun(
            id=run_id,
            workflow="prompt_training",
            status=run_status,
            input_ref=guideline_id,
            output_ref=best["best_description"],
            artifacts=(artifact_path,),
            summary=f"{best['method']} pass={best['best_pass_count']}/{target_pass_count}, loss={best['best_loss']}",
            meta={
                "guideline_id": guideline_id,
                "config": cfg.to_dict(),
                "best_method": best["method"],
                "reached_target": best["reached_target"],
                "stop_policy": cfg.stop_policy,
                "leakage_report": leakage_report,
                "progress_summary": progress_recorder.summary() if progress_recorder else {},
            },
            started_at=existing_payload.get("started_at") or existing_run.get("started_at") if existing_run else WorkflowRun(id=run_id, workflow="prompt_training").started_at,
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
        prompt_versions=_prompt_versions_for_best_method(initial_description, best),
    )
    if applied:
        updated_guideline = _guideline_from_payload(
            guideline,
            status=status,
            stable_description=best["best_description"],
        )
        store.upsert_guideline(updated_guideline)
    if progress_recorder is not None:
        progress_recorder.emit(
            "run_completed",
            stage="训练完成",
            message="提示词优化训练已完成",
            progress=1.0,
            payload={
                "status": status,
                "best_method": best["method"],
                "best_pass_count": int(best["best_pass_count"]),
                "best_loss": float(best["best_loss"]),
                "reached_target": bool(best["reached_target"]),
                "repair_attempt_count": _repair_summary(method_results).get("repair_attempt_count", 0),
            },
        )

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
        progress_events=[
            *[event for row in method_results for event in row.get("progress_events", [])],
            *_runtime_progress_events(predictor),
        ]
        if progress_recorder is None
        else progress_recorder.list_events(limit=5000),
        usage_summary=_usage_summary(method_results, cfg, predictor),
        repair_summary=_repair_summary(method_results),
        real_provider_run=real_provider_run,
        stop_policy=cfg.stop_policy,
        experiment_case=str(guideline.get("metadata", {}).get("experiment_case", "")),
        initial_description=initial_description,
        prompt_versions=_prompt_versions_for_best_method(initial_description, best),
        report_path="",
        prompt_evolution_path="",
        run_id=run_id,
        progress_summary=progress_recorder.summary() if progress_recorder else {},
        events_path="",
    )
    return result.to_dict()


def start_prompt_training_background_run(
    database_path: str | Path,
    guideline_id: str,
    config: PromptTrainingConfig | None = None,
    auto_apply: bool = False,
    use_llm: bool = True,
    output_dir: str | Path | None = None,
) -> str:
    """Start prompt training in a daemon thread and persist progress to SQLite."""

    cfg = (config or PromptTrainingConfig()).normalized()
    run_id = f"run-prompt-training-{uuid.uuid4().hex[:10]}"
    database = Path(database_path)
    submit_store = RuntimeStore(database)
    gold_count = _gold_count_for_guideline(submit_store, guideline_id, cfg.target_pass_count)
    estimated_total = estimate_prompt_training_total_calls(len(cfg.methods), cfg.max_rounds, gold_count, cfg.candidate_count)
    submit_store.upsert_run(
        WorkflowRun(
            id=run_id,
            workflow="prompt_training",
            status="running",
            input_ref=guideline_id,
            summary="提示词优化训练后台任务已提交。",
            meta={
                "guideline_id": guideline_id,
                "config": cfg.to_dict(),
                "provider": cfg.provider_id if use_llm else "local",
                "model": cfg.model if use_llm else "local-rule",
                "estimated_total_calls": estimated_total,
            },
        )
    )
    submit_recorder = ProgressRecorder(submit_store, run_id, estimated_total=estimated_total)
    submit_recorder.emit(
        "run_submitted",
        stage="后台排队",
        message="训练任务已提交到后台线程",
        total=estimated_total,
        payload={"guideline_id": guideline_id, "provider": cfg.provider_id, "model": cfg.model, "concurrency": cfg.concurrency},
    )

    def _target() -> None:
        thread_store = RuntimeStore(database)
        recorder = ProgressRecorder(thread_store, run_id, estimated_total=estimated_total)
        try:
            predictor = None
            if use_llm:
                runtime = LLMServiceRuntime.from_provider(
                    cfg.provider_id,
                    cfg.model,
                    concurrency=cfg.concurrency,
                    event_sink=recorder.event_sink,
                )

                def predictor(system_prompt: str, messages: list[dict], temperature: float) -> str:
                    return runtime.chat(system_prompt, messages, temperature=temperature)

                predictor.is_real_provider = True  # type: ignore[attr-defined]
                predictor.runtime = runtime  # type: ignore[attr-defined]
            result = run_prompt_training_experiment(
                thread_store,
                guideline_id,
                predictor=predictor,
                config=cfg,
                auto_apply=auto_apply,
                progress_recorder=recorder,
                run_id=run_id,
            )
            outputs_dir = Path(output_dir) if output_dir is not None else database.parent / "artifacts" / "prompt_training" / run_id
            written = write_prompt_training_comparison_outputs(result, outputs_dir)
            output_paths = {
                "comparison_result_path": written.get("comparison_result_path", ""),
                "report_path": written.get("report_path", ""),
                "prompt_evolution_path": written.get("prompt_evolution_path", ""),
                "events_path": written.get("events_path", ""),
            }
            for kind, path in {
                "prompt_training_report": output_paths["report_path"],
                "prompt_training_result": output_paths["comparison_result_path"],
                "prompt_training_evolution": output_paths["prompt_evolution_path"],
                "prompt_training_events": output_paths["events_path"],
            }.items():
                if path:
                    thread_store.add_artifact(run_id, path, kind, {"guideline_id": guideline_id})
            recorder.emit(
                "outputs_written",
                stage="写入产物",
                message="训练报告和事件日志已写入",
                progress=1.0,
                payload={"output_paths": output_paths},
            )
            final_events = recorder.list_events(limit=5000)
            written["progress_events"] = final_events
            written["progress_summary"] = recorder.summary()
            Path(output_paths["events_path"]).write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in final_events) + ("\n" if final_events else ""),
                encoding="utf-8",
            )
            Path(output_paths["comparison_result_path"]).write_text(
                json.dumps(written, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            Path(output_paths["report_path"]).write_text(build_prompt_training_comparison_report(written), encoding="utf-8")
            thread_store.update_run_status(
                run_id,
                "succeeded",
                {
                    "result_summary": {
                        "status": written.get("status"),
                        "best_method": written.get("best_method"),
                        "best_pass_count": written.get("best_pass_count"),
                        "best_loss": written.get("best_loss"),
                        "real_provider_run": written.get("real_provider_run"),
                        "usage_summary": written.get("usage_summary", {}),
                        "repair_summary": written.get("repair_summary", {}),
                    },
                    "output_paths": output_paths,
                    "progress_summary": recorder.summary(),
                },
            )
        except Exception as exc:
            recorder.emit(
                "run_failed",
                stage="运行失败",
                message="提示词优化训练失败",
                payload={"error": str(exc)[:500]},
            )
            try:
                thread_store.update_run_status(run_id, "failed", {"error": str(exc)[:500], "progress_summary": recorder.summary()})
            except Exception:
                pass

    thread = threading.Thread(target=_target, name=f"prompt-training-{run_id}", daemon=True)
    thread.start()
    return run_id


def _gold_count_for_guideline(store: RuntimeStore, guideline_id: str, fallback: int) -> int:
    gold_sets = store.list_gold_example_sets(guideline_id=guideline_id, limit=1)
    if not gold_sets:
        return fallback
    return max(1, len(gold_sets[0]["payload"].get("task_ids", [])))


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
    memorization_guard: MemorizationGuard,
    usage_meter: _TrainingUsageMeter,
    concurrency: int,
    progress_recorder: ProgressRecorder | None = None,
) -> dict[str, Any]:
    method = normalize_prompt_optimizer_method(method)
    optimizer_name = optimizer_display_name(method)
    optimizer_family = OPTIMIZER_FAMILIES.get(method, "")
    alias_from = (config.method_aliases or {}).get(method, "")
    method_started = time.perf_counter()
    _emit_training_progress(
        progress_recorder,
        "method_started",
        "方法训练",
        f"{optimizer_name} 开始训练",
        {
            "method": method,
            "optimizer_name": optimizer_name,
            "optimizer_family": optimizer_family,
            "alias_from": alias_from,
            "max_rounds": config.max_rounds,
            "candidate_count": config.candidate_count,
        },
    )
    current_description = initial_description
    rounds: list[dict[str, Any]] = []
    best_description = current_description
    best_result: dict[str, Any] | None = None
    best_loss: dict[str, Any] | None = None
    best_round_index = 0
    initial_loss: dict[str, Any] | None = None
    initial_pass_count = 0
    no_improvement_streak = 0
    accepted_round_count = 0
    evaluated_candidate_count = 0
    stop_reason = "max_rounds"
    final_status = "needs_revision"
    prompt_versions: list[dict[str, Any]] = []
    accepted_history: list[dict[str, Any]] = []

    for round_index in range(1, config.max_rounds + 1):
        round_started = time.perf_counter()
        _emit_training_progress(
            progress_recorder,
            "round_started",
            "训练轮次",
            f"{method} 第 {round_index} 轮开始",
            {"method": method, "round_index": round_index, "no_improvement_streak": no_improvement_streak},
        )
        usage_start = usage_meter.snapshot()
        current_guideline = {**guideline, "stable_description": current_description}
        _emit_training_progress(
            progress_recorder,
            "gold_validation_started",
            "验证金样例",
            f"{method} 第 {round_index} 轮正在验证当前提示词",
            {"method": method, "round_index": round_index, "gold_count": len(task_ids), "candidate_id": "current"},
        )
        current_result = _evaluate_gold_tasks(
            store,
            guideline_id,
            current_guideline,
            task_ids,
            predictor,
            config.evaluation_temperature,
            round_index,
            source=f"prompt_training_{method}",
            candidate_id=f"{method}-current-{round_index}",
            concurrency=concurrency,
        )
        current_loss = _concept_loss(current_result)
        current_pass_count = len(current_result["passed"])
        _emit_training_progress(
            progress_recorder,
            "gold_validation_completed",
            "验证金样例",
            f"{method} 第 {round_index} 轮当前提示词验证完成",
            {
                "method": method,
                "round_index": round_index,
                "pass_count": current_pass_count,
                "failed_count": len(current_result["failed"]),
                "unstable_count": len(current_result["unstable"]),
                "loss": current_loss["loss"],
            },
        )
        if initial_loss is None:
            initial_loss = current_loss
            initial_pass_count = current_pass_count
            prompt_versions.append(
                {
                    "version_label": "v0",
                    "method": method,
                    "optimizer_name": optimizer_name,
                    "optimizer_family": optimizer_family,
                    "alias_from": alias_from,
                    "round_index": 0,
                    "candidate_id": "initial",
                    "description": current_description,
                    "loss": current_loss["loss"],
                    "pass_count": current_pass_count,
                    "loss_delta": 0.0,
                    "accepted": True,
                    "event": "initial",
                }
            )
        if _is_better_training_result(
            current_result,
            current_loss,
            best_result,
            best_loss,
            target_pass_count,
            current_description,
            best_description,
        ):
            best_description = current_description
            best_result = current_result
            best_loss = current_loss
            best_round_index = round_index
        if current_pass_count >= target_pass_count and not current_result["failed"] and not current_result["unstable"]:
            final_status = "stable"
            stop_reason = "reached_target"
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
                    round_improved=False,
                    no_improvement_streak_after_round=no_improvement_streak,
                    stop_reason_if_stopped=stop_reason,
                    elapsed_seconds=time.perf_counter() - round_started,
                    usage=usage_meter.delta(usage_start),
                )
            )
            _emit_training_progress(
                progress_recorder,
                "round_completed",
                "训练轮次",
                f"{method} 第 {round_index} 轮达到目标",
                {
                    "method": method,
                    "round_index": round_index,
                    "status": "stable",
                    "pass_count": current_pass_count,
                    "loss": current_loss["loss"],
                    "round_improved": False,
                    "no_improvement_streak": no_improvement_streak,
                    "stop_reason": stop_reason,
                    "best_method": method,
                    "best_pass_count": current_pass_count,
                    "best_loss": current_loss["loss"],
                },
            )
            break

        failure_summary = _failure_summary(current_result["details"])
        round_guard = memorization_guard.with_validation_result(current_result)
        _emit_training_progress(
            progress_recorder,
            "candidate_generation_started",
            "生成候选",
            f"{method} 第 {round_index} 轮正在生成候选提示词",
            {"method": method, "round_index": round_index, "candidate_count": config.candidate_count},
        )
        candidates = _generate_training_candidates(
            store,
            guideline_id,
            task_ids,
            method,
            current_description,
            guideline,
            current_result,
            failure_summary,
            current_loss,
            predictor,
            config.candidate_count,
            config.candidate_temperature,
            accepted_history,
            concurrency=concurrency,
            progress_recorder=progress_recorder,
            round_index=round_index,
        )
        _emit_training_progress(
            progress_recorder,
            "candidate_generated",
            "生成候选",
            f"{method} 第 {round_index} 轮生成 {len(candidates)} 个候选",
            {
                "method": method,
                "round_index": round_index,
                "candidate_count": len(candidates),
                "candidate_ids": [candidate.get("candidate_id", "") for candidate in candidates],
            },
        )
        selected_result = current_result
        selected_loss = current_loss
        selected_description = current_description
        selected_candidate_id = "current"
        candidate_evaluations: list[dict[str, Any]] = []
        seen = {current_description}
        for candidate_index, candidate in enumerate(candidates, start=1):
            candidate_description = candidate["description"]
            repair_attempts: list[dict[str, Any]] = []
            guard_before_repair = None
            guard_after_repair = None
            repair_accepted = False
            memorization_check = (
                round_guard.check(candidate_description, field="candidate_description")
                if config.no_corpus_memorization
                else None
            )
            if memorization_check is not None and not memorization_check.passed:
                guard_before_repair = memorization_check
                if config.repair_leaked_candidates and predictor is not None and config.max_repair_attempts > 0:
                    _emit_training_progress(
                        progress_recorder,
                        "candidate_repair_started",
                        "去语料化修复",
                        f"{method} 第 {round_index} 轮候选 {candidate['candidate_id']} 进入去语料化修复",
                        {
                            "method": method,
                            "round_index": round_index,
                            "candidate_id": candidate["candidate_id"],
                            "memorization_status": memorization_check.severity,
                            "blocked_terms_count": memorization_check.match_count,
                        },
                    )
                    repair_result = _repair_leaked_candidate(
                        candidate_description=candidate_description,
                        current_description=current_description,
                        check=memorization_check,
                        guard=round_guard,
                        predictor=predictor,
                        temperature=config.candidate_temperature,
                        max_attempts=config.max_repair_attempts,
                    )
                    candidate_description = repair_result["description"]
                    repair_attempts = repair_result["repair_attempts"]
                    guard_after_repair = repair_result["final_check"]
                    repair_accepted = bool(guard_after_repair and guard_after_repair.passed)
                    memorization_check = guard_after_repair
                    _emit_training_progress(
                        progress_recorder,
                        "candidate_repair_completed",
                        "去语料化修复",
                        f"{method} 第 {round_index} 轮候选 {candidate['candidate_id']} 修复完成",
                        {
                            "method": method,
                            "round_index": round_index,
                            "candidate_id": candidate["candidate_id"],
                            "repair_attempt_count": sum(len(evaluation.get("repair_attempts", [])) for evaluation in candidate_evaluations)
                            + len(repair_attempts),
                            "repair_accepted": repair_accepted,
                            "memorization_status": memorization_check.severity,
                            "blocked_terms_count": memorization_check.match_count,
                        },
                    )
                if memorization_check is not None and not memorization_check.passed:
                    candidate_evaluations.append(
                        {
                            "method": method,
                            "round_index": round_index,
                            "candidate_id": candidate["candidate_id"],
                            "status": "memorization_repair_failed" if repair_attempts else "memorization_guard_blocked",
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
                            "memorization_status": memorization_check.severity,
                            "blocked_terms_count": memorization_check.match_count,
                            "repair_attempts": repair_attempts,
                            "repair_accepted": False,
                            "guard_before_repair": guard_before_repair.to_dict() if guard_before_repair else {},
                            "guard_after_repair": memorization_check.to_dict(),
                            "memorization_check": memorization_check.to_dict(),
                            "raw_feedback_allowed": method != SGD_CANDIDATE_SEARCH,
                            "sanitizer_warnings": candidate.get("sanitizer_warnings", []),
                            "raw_revision_response": "[redacted: candidate failed memorization repair]",
                            "description_preview": "[redacted: candidate failed memorization repair]",
                            "evaluation_index": candidate_index,
                        }
                    )
                    _emit_training_progress(
                        progress_recorder,
                        "candidate_rejected",
                        "候选筛选",
                        f"{method} 第 {round_index} 轮候选 {candidate['candidate_id']} 泄露修复失败",
                        {
                            "method": method,
                            "round_index": round_index,
                            "candidate_id": candidate["candidate_id"],
                            "status": "memorization_repair_failed" if repair_attempts else "memorization_guard_blocked",
                            "memorization_status": memorization_check.severity,
                            "blocked_terms_count": memorization_check.match_count,
                        },
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
                        "memorization_status": "clean",
                        "blocked_terms_count": 0,
                        "repair_attempts": repair_attempts,
                        "repair_accepted": repair_accepted,
                        "guard_before_repair": guard_before_repair.to_dict() if guard_before_repair else {},
                        "guard_after_repair": guard_after_repair.to_dict() if guard_after_repair else {},
                        "raw_feedback_allowed": method != SGD_CANDIDATE_SEARCH,
                        "sanitizer_warnings": candidate.get("sanitizer_warnings", []),
                    }
                )
                _emit_training_progress(
                    progress_recorder,
                    "candidate_rejected",
                    "候选筛选",
                    f"{method} 第 {round_index} 轮候选 {candidate['candidate_id']} 与已有提示词重复",
                    {
                        "method": method,
                        "round_index": round_index,
                        "candidate_id": candidate["candidate_id"],
                        "status": "skipped_duplicate",
                    },
                )
                continue
            seen.add(candidate_description)
            candidate_guideline = {**guideline, "stable_description": candidate_description}
            _emit_training_progress(
                progress_recorder,
                "candidate_evaluation_started",
                "候选回测",
                f"{method} 第 {round_index} 轮正在回测候选 {candidate['candidate_id']}",
                {"method": method, "round_index": round_index, "candidate_id": candidate["candidate_id"], "gold_count": len(task_ids)},
            )
            candidate_result = _evaluate_gold_tasks(
                store,
                guideline_id,
                candidate_guideline,
                task_ids,
                predictor,
                config.evaluation_temperature,
                round_index,
                source=f"prompt_training_{method}_candidate",
                candidate_id=candidate["candidate_id"],
                concurrency=concurrency,
            )
            evaluated_candidate_count += 1
            raw_loss = _concept_loss(candidate_result)
            candidate_loss = (
                length_penalized_loss(raw_loss, current_description, candidate_description)
                if config.length_penalty
                else _loss_without_length_penalty(raw_loss, current_description, candidate_description)
            )
            reached_target = len(candidate_result["passed"]) >= target_pass_count and not candidate_result["failed"] and not candidate_result["unstable"]
            improved_current = candidate_loss["loss"] + config.min_loss_delta < current_loss["loss"]
            round_best_so_far = candidate_loss["loss"] + config.min_loss_delta < selected_loss["loss"]
            optimization_trace = finalize_candidate_trace(
                candidate.get("prompt_optimization", {}),
                candidate["candidate_id"],
                current_description,
                candidate_description,
                current_loss,
                candidate_loss,
                round_best_so_far,
            )
            candidate_evaluations.append(
                {
                    "method": method,
                    "round_index": round_index,
                    "candidate_id": candidate["candidate_id"],
                    "status": "candidate_improved_current" if improved_current else "rejected_no_loss_improvement",
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
                    "accepted": False,
                    "improved_current": improved_current,
                    "round_best_so_far": round_best_so_far,
                    "reached_target": reached_target,
                    "memorization_passed": True,
                    "memorization_status": "clean",
                    "blocked_terms_count": 0,
                    "repair_attempts": repair_attempts,
                    "repair_accepted": repair_accepted,
                    "guard_before_repair": guard_before_repair.to_dict() if guard_before_repair else {},
                    "guard_after_repair": guard_after_repair.to_dict() if guard_after_repair else {},
                    "memorization_check": memorization_check.to_dict() if memorization_check else {},
                    "raw_feedback_allowed": method != SGD_CANDIDATE_SEARCH,
                    "sanitizer_warnings": candidate.get("sanitizer_warnings", []),
                    "raw_revision_response": "[redacted: candidate required memorization repair]"
                    if repair_attempts
                    else candidate.get("raw_response", ""),
                    "prompt_optimization_trace": optimization_trace,
                    "critic_diagnosis": candidate.get("critic_diagnosis", ""),
                    "controller_direction": candidate.get("controller_direction", ""),
                    "momentum_summary": candidate.get("momentum_summary", ""),
                    "mask_segment_id": candidate.get("mask_segment_id", ""),
                    "mask_loss_delta": candidate.get("mask_loss_delta", ""),
                    "mask_interpretation": candidate.get("mask_interpretation", ""),
                    "optimizer_display_name": optimizer_display_name(method),
                    "description_preview": candidate_description[:240],
                    "evaluation_index": candidate_index,
                }
            )
            _emit_training_progress(
                progress_recorder,
                "candidate_evaluated",
                "候选回测",
                f"{method} 第 {round_index} 轮候选 {candidate['candidate_id']} 回测完成",
                {
                    "method": method,
                    "round_index": round_index,
                    "candidate_id": candidate["candidate_id"],
                    "status": "candidate_improved_current" if improved_current else "rejected_no_loss_improvement",
                    "pass_count": len(candidate_result["passed"]),
                    "failed_count": len(candidate_result["failed"]),
                    "unstable_count": len(candidate_result["unstable"]),
                    "loss": candidate_loss["loss"],
                    "loss_delta": round(current_loss["loss"] - candidate_loss["loss"], 4),
                    "accepted": False,
                    "improved_current": improved_current,
                    "round_best_so_far": round_best_so_far,
                    "reached_target": reached_target,
                    "repair_attempt_count": sum(
                        len(evaluation.get("repair_attempts", [])) for evaluation in candidate_evaluations
                    ),
                },
            )
            if round_best_so_far:
                selected_result = candidate_result
                selected_loss = candidate_loss
                selected_description = candidate_description
                selected_candidate_id = candidate["candidate_id"]

        round_status = "stable" if len(selected_result["passed"]) >= target_pass_count and not selected_result["failed"] and not selected_result["unstable"] else "needs_revision"
        round_improved = selected_candidate_id != "current"
        if round_improved:
            for evaluation in candidate_evaluations:
                trace = evaluation.get("prompt_optimization_trace", {}).get("trace")
                if evaluation.get("candidate_id") == selected_candidate_id:
                    evaluation["status"] = "accepted"
                    evaluation["accepted"] = True
                    if isinstance(trace, dict):
                        trace["accepted"] = True
                elif evaluation.get("status") == "candidate_improved_current":
                    evaluation["status"] = "rejected_not_round_best"
                    evaluation["accepted"] = False
                    if isinstance(trace, dict):
                        trace["accepted"] = False
            _emit_training_progress(
                progress_recorder,
                "candidate_accepted",
                "候选选择",
                f"{method} 第 {round_index} 轮已接受 loss 最低候选 {selected_candidate_id}",
                {
                    "method": method,
                    "round_index": round_index,
                    "candidate_id": selected_candidate_id,
                    "status": "accepted",
                    "pass_count": len(selected_result["passed"]),
                    "loss": selected_loss["loss"],
                    "loss_delta": round(current_loss["loss"] - selected_loss["loss"], 4),
                    "accepted": True,
                },
            )
        if round_improved:
            no_improvement_streak = 0
            accepted_round_count += 1
            version_entry = {
                "version_label": f"v{len(prompt_versions)}",
                "method": method,
                "optimizer_name": optimizer_name,
                "optimizer_family": optimizer_family,
                "alias_from": alias_from,
                "round_index": round_index,
                "candidate_id": selected_candidate_id,
                "previous_description": current_description,
                "description": selected_description,
                "loss_before": current_loss["loss"],
                "loss": selected_loss["loss"],
                "pass_count": len(selected_result["passed"]),
                "loss_delta": round(current_loss["loss"] - selected_loss["loss"], 4),
                "accepted": True,
                "event": "accepted",
            }
            prompt_versions.append(version_entry)
            accepted_history.append(version_entry)
        else:
            no_improvement_streak += 1
            round_status = "no_improvement"
        round_stop_reason = ""
        if round_status == "stable":
            stop_reason = "reached_target"
            round_stop_reason = stop_reason
        elif no_improvement_streak >= config.patience_rounds:
            stop_reason = "no_loss_improvement_patience"
            round_stop_reason = stop_reason
        elif round_index >= config.max_rounds:
            stop_reason = "max_rounds"
            round_stop_reason = stop_reason
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
                round_improved=round_improved,
                no_improvement_streak_after_round=no_improvement_streak,
                stop_reason_if_stopped=round_stop_reason,
                elapsed_seconds=time.perf_counter() - round_started,
                usage=usage_meter.delta(usage_start),
            )
        )
        _emit_training_progress(
            progress_recorder,
            "round_completed",
            "训练轮次",
            f"{method} 第 {round_index} 轮完成",
            {
                "method": method,
                "round_index": round_index,
                "status": round_status,
                "pass_count": len(selected_result["passed"]),
                "loss": selected_loss["loss"],
                "round_improved": round_improved,
                "no_improvement_streak": no_improvement_streak,
                "stop_reason": round_stop_reason,
                "accepted_candidate_id": selected_candidate_id,
                "best_method": method,
                "best_pass_count": len(selected_result["passed"]),
                "best_loss": selected_loss["loss"],
            },
        )
        if _is_better_training_result(
            selected_result,
            selected_loss,
            best_result,
            best_loss,
            target_pass_count,
            selected_description,
            best_description,
        ):
            best_description = selected_description
            best_result = selected_result
            best_loss = selected_loss
            best_round_index = round_index
            _emit_training_progress(
                progress_recorder,
                "best_updated",
                "更新最优",
                f"{method} 第 {round_index} 轮刷新当前最优提示词",
                {
                    "method": method,
                    "round_index": round_index,
                    "best_pass_count": len(selected_result["passed"]),
                    "best_loss": selected_loss["loss"],
                    "best_method": method,
                },
            )
        final_status = "stable" if round_status == "stable" else "needs_revision"
        if round_status == "stable" or no_improvement_streak >= config.patience_rounds:
            break
        current_description = selected_description

    assert best_result is not None and best_loss is not None
    assert initial_loss is not None
    final_pass_count = len(best_result["passed"])
    reached_target = final_pass_count >= target_pass_count and not best_result["failed"] and not best_result["unstable"]
    final_memorization_check = (
        memorization_guard.with_validation_result(best_result).check(best_description, field="best_description")
        if config.no_corpus_memorization
        else None
    )
    _emit_training_progress(
        progress_recorder,
        "method_completed",
        "方法完成",
        f"{method} 训练结束",
        {
            "method": method,
            "status": final_status,
            "stop_reason": stop_reason,
            "best_pass_count": final_pass_count,
            "best_loss": best_loss["loss"],
            "accepted_round_count": accepted_round_count,
            "evaluated_candidate_count": evaluated_candidate_count,
            "round_count": len(rounds),
            "best_method": method,
        },
    )
    return {
        "method": method,
        "optimizer_name": optimizer_name,
        "optimizer_family": optimizer_family,
        "alias_from": alias_from,
        "method_trace_summary": _method_trace_summary(method, rounds),
        "status": "stable"
        if reached_target and (final_memorization_check is None or final_memorization_check.passed)
        else "needs_revision",
        "reached_target": reached_target,
        "best_description": best_description,
        "initial_loss": initial_loss["loss"],
        "initial_pass_count": initial_pass_count,
        "best_pass_count": final_pass_count,
        "best_loss": best_loss["loss"],
        "best_loss_detail": best_loss,
        "best_round_index": best_round_index,
        "total_loss_delta": round(initial_loss["loss"] - best_loss["loss"], 4),
        "stop_reason": stop_reason,
        "no_improvement_streak": no_improvement_streak,
        "accepted_round_count": accepted_round_count,
        "evaluated_candidate_count": evaluated_candidate_count,
        "failed": best_result["failed"],
        "unstable": best_result["unstable"],
        "rounds": rounds,
        "memorization_passed": True if final_memorization_check is None else final_memorization_check.passed,
        "final_memorization_check": final_memorization_check.to_dict() if final_memorization_check else {},
        "elapsed_seconds": round(time.perf_counter() - method_started, 4),
        "usage": usage_meter.summary(),
        "progress_events": _progress_events(method, rounds),
        "prompt_versions": prompt_versions,
    }


def _is_better_training_result(
    candidate_result: dict,
    candidate_loss: dict,
    current_best_result: dict | None,
    current_best_loss: dict | None,
    target_pass_count: int,
    candidate_description: str,
    current_best_description: str,
) -> bool:
    if current_best_result is None or current_best_loss is None:
        return True
    candidate_reached = (
        len(candidate_result.get("passed", [])) >= target_pass_count
        and not candidate_result.get("failed")
        and not candidate_result.get("unstable")
    )
    current_best_reached = (
        len(current_best_result.get("passed", [])) >= target_pass_count
        and not current_best_result.get("failed")
        and not current_best_result.get("unstable")
    )
    return (
        0 if candidate_reached else 1,
        float(candidate_loss.get("loss", 0.0)),
        -len(candidate_result.get("passed", [])),
        len(candidate_description),
    ) < (
        0 if current_best_reached else 1,
        float(current_best_loss.get("loss", 0.0)),
        -len(current_best_result.get("passed", [])),
        len(current_best_description),
    )


def _emit_training_progress(
    progress_recorder: ProgressRecorder | None,
    event_type: str,
    stage: str,
    message: str,
    payload: dict[str, Any] | None = None,
) -> None:
    if progress_recorder is None:
        return
    progress_recorder.emit(event_type, stage=stage, message=message, payload=payload or {})


def _generate_training_candidates(
    store: RuntimeStore,
    guideline_id: str,
    task_ids: list[str],
    method: str,
    current_description: str,
    guideline: dict,
    validation_result: dict,
    failure_summary: str,
    current_loss: dict,
    predictor: Predictor | None,
    candidate_count: int,
    temperature: float,
    accepted_history: list[dict[str, Any]] | None = None,
    concurrency: int = 1,
    progress_recorder: ProgressRecorder | None = None,
    round_index: int = 0,
) -> list[dict[str, Any]]:
    method = normalize_prompt_optimizer_method(method)
    if method == MASK_GUIDED_OPTIMIZATION:
        return _generate_mask_guided_candidates(
            store,
            guideline_id,
            task_ids,
            current_description,
            guideline,
            validation_result,
            failure_summary,
            current_loss,
            predictor,
            candidate_count,
            temperature,
            concurrency=concurrency,
            progress_recorder=progress_recorder,
            round_index=round_index,
        )
    if method == CRITIC_ADAMW_OPTIMIZER:
        return _generate_critic_adamw_candidates(
            current_description,
            validation_result,
            failure_summary,
            current_loss,
            predictor,
            candidate_count,
            temperature,
            accepted_history or [],
        )
    if method == SGD_CANDIDATE_SEARCH:
        return _generate_sgd_candidate_search_candidates(
            current_description,
            predictor,
            candidate_count,
            temperature,
            accepted_history or [],
        )
    raise ValueError(f"Unsupported prompt training method: {method}")


def _generate_sgd_candidate_search_candidates(
    current_description: str,
    predictor: Predictor | None,
    candidate_count: int,
    temperature: float,
    accepted_history: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if predictor is None:
        return [
            {
                "candidate_id": "sgd-candidate-search-local-fallback",
                "description": current_description,
                "raw_response": "",
                "sanitizer_warnings": ["local_fallback_no_predictor"],
                "source": SGD_CANDIDATE_SEARCH,
                "prompt_optimization": _base_trace(SGD_CANDIDATE_SEARCH, {"loss": 0.0}),
                "method": SGD_CANDIDATE_SEARCH,
            }
        ]
    candidates: list[dict[str, Any]] = []
    for index in range(1, candidate_count + 1):
        prompt = build_llm_optimize_only_prompt(current_description, accepted_history or [])
        raw = predictor("你是概念提示词优化助手。只返回最终可用的概念阐释正文。", [{"role": "user", "content": prompt}], temperature)
        cleaned, warnings = sanitize_concept_description(raw, fallback=current_description)
        cleaned, concept_only_warnings = ensure_concept_only_description(cleaned, fallback=current_description)
        warnings.extend(concept_only_warnings)
        candidates.append(
            {
                "candidate_id": f"sgd-candidate-search-{index:02d}",
                "description": cleaned,
                "raw_response": raw,
                "sanitizer_warnings": warnings,
                "source": SGD_CANDIDATE_SEARCH,
                "prompt_optimization": _base_trace(SGD_CANDIDATE_SEARCH, {"loss": 0.0}),
                "method": SGD_CANDIDATE_SEARCH,
            }
        )
    return candidates


def _generate_mask_guided_candidates(
    store: RuntimeStore,
    guideline_id: str,
    task_ids: list[str],
    current_description: str,
    guideline: dict,
    validation_result: dict,
    failure_summary: str,
    current_loss: dict,
    predictor: Predictor | None,
    candidate_count: int,
    temperature: float,
    concurrency: int = 1,
    progress_recorder: ProgressRecorder | None = None,
    round_index: int = 0,
) -> list[dict[str, Any]]:
    if predictor is None:
        return [
            {
                "candidate_id": "mask-guided-local-fallback",
                "description": current_description,
                "raw_response": "",
                "sanitizer_warnings": ["local_fallback_no_predictor"],
                "source": MASK_GUIDED_OPTIMIZATION,
                "prompt_optimization": _base_trace(MASK_GUIDED_OPTIMIZATION, current_loss),
                "method": MASK_GUIDED_OPTIMIZATION,
            }
        ]
    optimizer_context = _build_mask_guided_trace(
        store,
        guideline_id,
        task_ids,
        current_description,
        guideline,
        current_loss,
        predictor,
        temperature,
        concurrency=concurrency,
        progress_recorder=progress_recorder,
        round_index=round_index,
    )
    directions = _mask_guided_directions(optimizer_context)[: max(1, min(candidate_count, 5))]
    candidates: list[dict[str, Any]] = []
    fallback = str(guideline.get("stable_description") or current_description)
    for index, direction in enumerate(directions, start=1):
        mask_row = _mask_row_for_direction(optimizer_context, direction)
        prompt = _build_mask_guided_prompt(current_description, validation_result, failure_summary, current_loss, direction, optimizer_context)
        raw = predictor("你是概念阐释改写助手。只返回最终可用的概念阐释正文。", [{"role": "user", "content": prompt}], temperature)
        cleaned, warnings = sanitize_concept_description(raw, fallback=fallback)
        cleaned, concept_only_warnings = ensure_concept_only_description(cleaned, fallback=fallback)
        warnings.extend(concept_only_warnings)
        candidates.append(
            {
                "candidate_id": f"mask-guided-{index:02d}-{direction['id']}",
                "description": cleaned,
                "raw_response": raw,
                "sanitizer_warnings": warnings,
                "source": MASK_GUIDED_OPTIMIZATION,
                "direction": direction["id"],
                "prompt_optimization": optimizer_context,
                "method": MASK_GUIDED_OPTIMIZATION,
                "mask_segment_id": mask_row.get("mask_segment_id", ""),
                "mask_loss_delta": mask_row.get("mask_loss_delta", ""),
                "mask_interpretation": mask_row.get("mask_interpretation", ""),
            }
        )
    return candidates


def _generate_critic_adamw_candidates(
    current_description: str,
    validation_result: dict,
    failure_summary: str,
    current_loss: dict,
    predictor: Predictor | None,
    candidate_count: int,
    temperature: float,
    accepted_history: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    fallback = current_description
    if predictor is None:
        return [
            {
                "candidate_id": "critic-adamw-local-fallback",
                "description": fallback,
                "raw_response": "",
                "sanitizer_warnings": ["local_fallback_no_predictor"],
                "source": CRITIC_ADAMW_OPTIMIZER,
                "prompt_optimization": _base_trace(CRITIC_ADAMW_OPTIMIZER, current_loss),
                "method": CRITIC_ADAMW_OPTIMIZER,
            }
        ]
    critic_diagnosis = predictor(
        "你是提示词优化批判器。只输出简洁诊断，不生成最终提示词。",
        [{"role": "user", "content": _build_critic_diagnosis_prompt(current_description, validation_result, failure_summary, accepted_history or [])}],
        temperature,
    )
    controller_direction = predictor(
        "你是提示词优化控制器。只输出下一轮优化方向，不生成最终提示词。",
        [{"role": "user", "content": _build_controller_prompt(current_description, current_loss, critic_diagnosis, accepted_history or [])}],
        temperature,
    )
    momentum_summary = _momentum_summary(accepted_history or [], critic_diagnosis, controller_direction)
    optimizer_context = _base_trace(CRITIC_ADAMW_OPTIMIZER, current_loss)
    optimizer_context.update(
        {
            "optimizer": CRITIC_ADAMW_OPTIMIZER,
            "critic_diagnosis": critic_diagnosis,
            "controller_direction": controller_direction,
            "momentum_summary": momentum_summary,
            "proposed_trace": {
                **optimizer_context.get("proposed_trace", {}),
                "gradient_direction": controller_direction[:240],
                "diagnostics": critic_diagnosis[:500],
                "metadata": {
                    "optimizer": CRITIC_ADAMW_OPTIMIZER,
                    "critic_diagnosis": critic_diagnosis,
                    "controller_direction": controller_direction,
                    "momentum_summary": momentum_summary,
                    "length_decay": True,
                },
            },
        }
    )
    candidates: list[dict[str, Any]] = []
    for index in range(1, candidate_count + 1):
        prompt = _build_critic_generator_prompt(
            current_description,
            validation_result,
            failure_summary,
            critic_diagnosis,
            controller_direction,
            momentum_summary,
            accepted_history or [],
        )
        raw = predictor("你是概念阐释反思优化助手。只返回最终可用的概念阐释正文。", [{"role": "user", "content": prompt}], temperature)
        cleaned, warnings = sanitize_concept_description(raw, fallback=fallback)
        cleaned, concept_only_warnings = ensure_concept_only_description(cleaned, fallback=fallback)
        warnings.extend(concept_only_warnings)
        candidates.append(
            {
                "candidate_id": f"critic-adamw-{index:02d}",
                "description": cleaned,
                "raw_response": raw,
                "sanitizer_warnings": warnings,
                "source": CRITIC_ADAMW_OPTIMIZER,
                "prompt_optimization": optimizer_context,
                "method": CRITIC_ADAMW_OPTIMIZER,
                "critic_diagnosis": critic_diagnosis,
                "controller_direction": controller_direction,
                "momentum_summary": momentum_summary,
            }
        )
    return candidates


def _build_reflection_prompt(
    current_description: str,
    validation_result: dict,
    failure_summary: str,
    accepted_history: list[dict[str, Any]] | None = None,
) -> str:
    concept_description = strip_frozen_protocol_sections(current_description)
    return f"""请根据逐条批改对照，优化下面的概念阐释。

training_feedback_only=true

当前提示词（只包含可优化的概念定义和边界规则）：
{concept_description}

历史优化摘要（旧 prompt -> 新 prompt -> loss 变化；只供判断哪些方向有效，不要原样复述）：
{_accepted_history_context(accepted_history or [])}

整体失败摘要（只供你判断改写方向，不要原样写进最终提示词）：
{failure_summary}

失败样例批改对照（每个样例的原文、标准答案和模型回答彼此相邻，只供学习，不要复制到最终提示词）：
{_reflection_detail_context(validation_result.get("details", []))}

输出要求：
1. 只输出可以直接用于下一轮标注的概念阐释正文。
2. 只允许包含任务定义、概念定义、边界规则和排除规则。
3. 不要输出标签集合、JSON schema、annotation 标注格式、输出格式或格式修复指令。
4. 不要输出解释、失败样例编号、失败摘要或修订日志。
5. 不要出现 gold-编号、“失败摘要”、“本轮失败”、“修订建议”、“漏标”、“多标”、“边界不稳定样例”等诊断文字。"""


def _build_critic_diagnosis_prompt(
    current_description: str,
    validation_result: dict,
    failure_summary: str,
    accepted_history: list[dict[str, Any]] | None = None,
) -> str:
    concept_description = strip_frozen_protocol_sections(current_description)
    return f"""请作为 Evaluator 评价当前可优化提示词。你只做诊断，不生成最终提示词。

training_feedback_only=true

当前可优化提示词：
{concept_description}

历史优化摘要：
{_accepted_history_context(accepted_history or [])}

整体失败摘要：
{failure_summary}

失败样例批改对照：
{_reflection_detail_context(validation_result.get("details", []))}

请用简短条目回答：
1. 哪些概念规则不足。
2. 哪些规则已经有效，应保持。
3. 哪些规则可能过长、污染或过拟合。
4. 哪些失败更像格式问题，哪些才是语义边界问题。

不要输出候选提示词，不要改写输出协议，不要复制 gold 答案。"""


def _build_controller_prompt(
    current_description: str,
    current_loss: dict,
    critic_diagnosis: str,
    accepted_history: list[dict[str, Any]] | None = None,
) -> str:
    concept_description = strip_frozen_protocol_sections(current_description)
    return f"""请作为 Controller 给出下一轮提示词优化方向。你只输出方向，不生成最终提示词。

当前可优化提示词：
{concept_description}

当前 loss：{current_loss.get("loss", 0.0)}

历史动量摘要：
{_accepted_history_context(accepted_history or [])}

Evaluator 诊断：
{critic_diagnosis}

请按以下四类给方向：
- 加强：需要扩写或明确的概念/边界。
- 保持：不要破坏的已有规则。
- 删除：冗余、污染、可能过拟合的内容。
- 压缩：prompt 变长但 loss 没下降时应压缩的部分。

不要输出候选提示词，不要改写标签或输出格式。"""


def _build_critic_generator_prompt(
    current_description: str,
    validation_result: dict,
    failure_summary: str,
    critic_diagnosis: str,
    controller_direction: str,
    momentum_summary: str,
    accepted_history: list[dict[str, Any]] | None = None,
) -> str:
    concept_description = strip_frozen_protocol_sections(current_description)
    return f"""请根据 Evaluator 诊断和 Controller 方向，生成一个新的可优化概念提示词。

training_feedback_only=true

当前可优化提示词：
{concept_description}

历史优化摘要：
{_accepted_history_context(accepted_history or [])}

Momentum 摘要：
{momentum_summary}

Evaluator 诊断：
{critic_diagnosis}

Controller 优化方向：
{controller_direction}

失败样例批改对照（只供抽象边界规则，不要复制原文或答案）：
{_reflection_detail_context(validation_result.get("details", []))}

整体失败摘要（只供判断，不要写入最终提示词）：
{failure_summary}

输出要求：
1. 只输出可以直接用于下一轮标注的概念阐释正文。
2. 只允许包含任务定义、概念定义、边界规则和排除规则。
3. 不要输出标签集合、JSON schema、annotation 标注格式、输出格式或格式修复指令。
4. 不要输出解释、失败样例编号、失败摘要或修订日志。
5. 不要复制训练语料、gold answer 或模型 answer 中的具体片段。"""


def _momentum_summary(history: list[dict[str, Any]], critic_diagnosis: str, controller_direction: str) -> str:
    if not history:
        return "暂无已接受方向；本轮采用小步探索。"
    positive = [
        f"{item.get('version_label', 'v?')} loss 下降 {item.get('loss_delta', '')}"
        for item in history[-5:]
        if float(item.get("loss_delta") or 0.0) > 0
    ]
    return "；".join(positive) or "历史版本存在，但没有明确持续有效方向；本轮优先小步、短 prompt、保守更新。"


def _build_mask_guided_trace(
    store: RuntimeStore,
    guideline_id: str,
    task_ids: list[str],
    current_description: str,
    guideline: dict,
    current_loss: dict,
    predictor: Predictor,
    temperature: float,
    concurrency: int,
    progress_recorder: ProgressRecorder | None,
    round_index: int,
) -> dict[str, Any]:
    segments = [segment for segment in segment_prompt(strip_frozen_protocol_sections(current_description)) if segment.mutable][:5]
    mask_rows: list[dict[str, Any]] = []
    for segment in segments:
        _emit_training_progress(
            progress_recorder,
            "mask_ablation_started",
            "遮挡梯度估计",
            f"正在遮挡片段 {segment.id} 并回测 gold loss",
            {"method": MASK_GUIDED_OPTIMIZATION, "round_index": round_index, "mask_segment_id": segment.id},
        )
        masked_description = _mask_prompt_segment(current_description, segment.id)
        masked_guideline = {**guideline, "stable_description": masked_description}
        masked_result = _evaluate_gold_tasks(
            store,
            guideline_id,
            masked_guideline,
            task_ids,
            predictor,
            temperature,
            round_index,
            source="prompt_training_mask_guided_ablation",
            candidate_id=f"mask-{round_index:02d}-{segment.id}",
            concurrency=concurrency,
        )
        masked_loss = _concept_loss(masked_result)
        loss_delta = round(float(masked_loss.get("loss", 0.0)) - float(current_loss.get("loss", 0.0)), 4)
        interpretation = _mask_interpretation(loss_delta)
        mask_row = {
            "mask_segment_id": segment.id,
            "segment_kind": segment.kind,
            "segment_text_preview": segment.text[:160],
            "masked_loss": masked_loss.get("loss", 0.0),
            "current_loss": current_loss.get("loss", 0.0),
            "mask_loss_delta": loss_delta,
            "mask_interpretation": interpretation,
            "pass_count": len(masked_result.get("passed", [])),
        }
        mask_rows.append(mask_row)
        _emit_training_progress(
            progress_recorder,
            "mask_ablation_completed",
            "遮挡梯度估计",
            f"片段 {segment.id} 遮挡回测完成",
            {
                "method": MASK_GUIDED_OPTIMIZATION,
                "round_index": round_index,
                "mask_segment_id": segment.id,
                "mask_loss_delta": loss_delta,
                "mask_interpretation": interpretation,
                "loss": masked_loss.get("loss", 0.0),
            },
        )
    mask_rows.sort(key=lambda row: float(row.get("mask_loss_delta", 0.0)), reverse=True)
    top = mask_rows[0] if mask_rows else {}
    return {
        "optimizer": MASK_GUIDED_OPTIMIZATION,
        "segments": [segment.to_dict() for segment in segments],
        "mask_ablation": mask_rows,
        "text_gradients": [
            {
                "segment_id": row.get("mask_segment_id", ""),
                "method": "mask_ablation",
                "direction": row.get("mask_interpretation", ""),
                "score": row.get("mask_loss_delta", 0.0),
                "evidence": f"masked_loss_delta={row.get('mask_loss_delta', 0.0)}",
                "metadata": row,
            }
            for row in mask_rows
        ],
        "proposed_trace": {
            "segment_id": top.get("mask_segment_id", ""),
            "perturbation_method": "mask_ablation",
            "gradient_direction": top.get("mask_interpretation", "no_mask_signal"),
            "current_loss": float(current_loss.get("loss", 0.0)),
            "diagnostics": _mask_analysis_context(mask_rows),
            "metadata": {
                "optimizer": MASK_GUIDED_OPTIMIZATION,
                "mask_ablation": mask_rows,
                "length_decay": True,
            },
        },
        "top_segment_id": top.get("mask_segment_id", ""),
        "top_direction": top.get("mask_interpretation", "no_mask_signal"),
    }


def _mask_prompt_segment(description: str, segment_id: str) -> str:
    concept_text = strip_frozen_protocol_sections(description)
    segments = segment_prompt(concept_text)
    kept = [segment.text for segment in segments if segment.id != segment_id]
    masked = "\n\n".join(text for text in kept if text.strip()).strip()
    return masked or "概念定义：根据当前任务定义标注符合概念边界的文本片段。"


def _mask_interpretation(loss_delta: float) -> str:
    if loss_delta > 0.5:
        return "high_contribution_keep_or_refine"
    if loss_delta < -0.5:
        return "negative_contribution_rewrite_or_remove"
    return "low_or_uncertain_contribution_small_step"


def _mask_analysis_context(mask_rows: list[dict[str, Any]]) -> str:
    if not mask_rows:
        return "没有可遮挡的可优化片段；请做小步保守改写。"
    lines = []
    for row in mask_rows[:5]:
        lines.append(
            "- {segment}: delta={delta}, interpretation={interp}, kind={kind}, text={text}".format(
                segment=row.get("mask_segment_id", ""),
                delta=row.get("mask_loss_delta", 0.0),
                interp=row.get("mask_interpretation", ""),
                kind=row.get("segment_kind", ""),
                text=row.get("segment_text_preview", ""),
            )
        )
    return "\n".join(lines)


def _mask_guided_directions(optimizer_context: dict[str, Any]) -> list[dict[str, str]]:
    rows = list(optimizer_context.get("mask_ablation", []))
    if not rows:
        return [{"id": "minimal", "title": "最小改写", "instruction": "没有明确遮挡信号，保持短 prompt 并小步优化。"}]
    directions: list[dict[str, str]] = []
    for row in rows[:5]:
        segment_id = str(row.get("mask_segment_id", "segment"))
        interpretation = str(row.get("mask_interpretation", ""))
        if interpretation.startswith("high_contribution"):
            instruction = "保留该片段的核心含义，并把它改写得更清楚、更短、更可执行。"
        elif interpretation.startswith("negative_contribution"):
            instruction = "该片段遮挡后 loss 反而下降，请删除、压缩或重写它，避免误导。"
        else:
            instruction = "该片段贡献不确定，请只做小步精简，不要扩大概念。"
        directions.append({"id": segment_id.replace("seg-", ""), "title": f"遮挡片段 {segment_id}", "instruction": instruction})
    return directions


def _mask_row_for_direction(optimizer_context: dict[str, Any], direction: dict[str, str]) -> dict[str, Any]:
    suffix = str(direction.get("id", ""))
    for row in optimizer_context.get("mask_ablation", []):
        segment_id = str(row.get("mask_segment_id", ""))
        if suffix and (segment_id == suffix or segment_id.endswith(suffix)):
            return row
    rows = list(optimizer_context.get("mask_ablation", []))
    return rows[0] if rows else {}


def _build_mask_guided_prompt(
    current_description: str,
    validation_result: dict,
    failure_summary: str,
    current_loss: dict,
    direction: dict,
    optimizer_context: dict,
) -> str:
    concept_description = strip_frozen_protocol_sections(current_description)
    return f"""请根据 Mask 遮挡得到的文本梯度，优化下面的概念阐释。

training_feedback_only=true

当前可优化定义：
{concept_description}

本次遮挡优化方向：
{direction['title']}：{direction['instruction']}

当前 loss：
{current_loss.get('loss', 0.0)}

Mask 遮挡分析（只供判断哪句话有贡献或拖后腿，不要原样复述）：
{_mask_analysis_context(list(optimizer_context.get("mask_ablation", [])))}

失败批改摘要（只供抽象规则，不要复制语料或答案）：
{_raw_feedback_context(validation_result, failure_summary)}

输出要求：
1. 只输出可以直接用于下一轮标注的概念阐释正文。
2. 保留高贡献片段的核心含义，重写或删除负贡献片段。
3. 只允许包含任务定义、概念定义、边界规则和排除规则。
4. 不要输出标签集合、JSON schema、annotation 标注格式、输出格式或格式修复指令。
5. 不要复制原文、标准答案、模型答案、样例编号、失败摘要或修订日志。"""


def build_training_feedback_prompt(current_description: str, validation_result: dict, failure_summary: str) -> str:
    return _build_reflection_prompt(current_description, validation_result, failure_summary)


def _accepted_history_context(history: list[dict[str, Any]], limit: int = 5) -> str:
    if not history:
        return "暂无。"
    lines: list[str] = []
    for item in history[-limit:]:
        label = str(item.get("version_label", "v?"))
        previous = _compact_prompt_text(str(item.get("previous_description", "")))
        current = _compact_prompt_text(str(item.get("description", "")))
        loss_before = item.get("loss_before", "")
        loss_after = item.get("loss", "")
        loss_delta = item.get("loss_delta", "")
        lines.append(
            "\n".join(
                [
                    f"- {label}: loss {loss_before} -> {loss_after}，下降 {loss_delta}，候选 {item.get('candidate_id', '')}",
                    f"  旧 prompt 摘要：{previous}",
                    f"  新 prompt 摘要：{current}",
                ]
            )
        )
    return "\n".join(lines)


def _compact_prompt_text(text: str, limit: int = 360) -> str:
    normalized = " ".join(line.strip() for line in text.splitlines() if line.strip())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


def _reflection_detail_context(details: list[dict[str, Any]], limit: int = 15) -> str:
    failed = [detail for detail in details if detail.get("route") != "passed"][:limit]
    if not failed:
        return "无失败样例。"
    blocks: list[str] = []
    for index, detail in enumerate(failed, start=1):
        blocks.append(
            "\n".join(
                [
                    f"失败样例 {index}",
                    f"原文：{detail.get('text', '')}",
                    f"标准答案 annotation：{_spans_to_markup(detail.get('gold_spans', []))}",
                    f"模型回答 JSON：{_model_response_json_for_feedback(detail)}",
                    f"错误摘要：{_detail_error_summary(detail)}",
                ]
            )
        )
    return "\n\n".join(blocks)


def _spans_to_markup(spans: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for span in spans:
        text = str(span.get("text", "")).strip()
        label = str(span.get("label", "Term")).strip() or "Term"
        implicit = bool(span.get("implicit", False))
        prefix = "!" if implicit else ""
        if text:
            parts.append(f"[{prefix}{text}]{{{label}}}")
    return " ".join(parts)


def _model_response_json_for_feedback(detail: dict[str, Any]) -> str:
    raw = str(detail.get("model_raw_response") or "").strip()
    if raw:
        return raw
    payload = {
        "text": detail.get("text", ""),
        "annotation": _spans_to_markup(detail.get("predicted_spans", [])),
        "explanation": "model output reconstructed from parsed spans",
    }
    return json.dumps(payload, ensure_ascii=False)


def _detail_error_summary(detail: dict[str, Any]) -> str:
    parts: list[str] = []
    missing = _spans_to_markup(detail.get("missing_spans", []))
    extra = _spans_to_markup(detail.get("extra_spans", []))
    if missing:
        parts.append(f"应补：{missing}")
    if extra:
        parts.append(f"应排除或收紧：{extra}")
    if not parts:
        parts.append(f"route={detail.get('route', 'failed')}, score={detail.get('score', 0.0)}")
    return "；".join(parts)


def repair_leaked_prompt(
    candidate_description: str,
    leaked_terms: list[str],
    predictor: Predictor,
    temperature: float = 0.0,
    fallback: str = "",
) -> tuple[str, list[str]]:
    prompt = _build_leak_repair_prompt(candidate_description, leaked_terms)
    raw = predictor("你是提示词去语料化修复助手。只返回修复后的最终提示词。", [{"role": "user", "content": prompt}], temperature)
    cleaned, warnings = sanitize_concept_description(raw, fallback=fallback or candidate_description)
    cleaned, concept_only_warnings = ensure_concept_only_description(cleaned, fallback=fallback or candidate_description)
    warnings.extend(concept_only_warnings)
    return cleaned, warnings


def _repair_leaked_candidate(
    candidate_description: str,
    current_description: str,
    check,
    guard: MemorizationGuard,
    predictor: Predictor,
    temperature: float,
    max_attempts: int,
) -> dict[str, Any]:
    description = candidate_description
    current_check = check
    attempts: list[dict[str, Any]] = []
    for attempt_index in range(1, max_attempts + 1):
        repaired, warnings = repair_leaked_prompt(
            description,
            list(current_check.private_matches),
            predictor=predictor,
            temperature=temperature,
            fallback=current_description,
        )
        repaired_check = guard.check(repaired, field="candidate_description")
        attempts.append(
            {
                "attempt_index": attempt_index,
                "input_severity": current_check.severity,
                "blocked_terms_count": current_check.match_count,
                "repaired_passed": repaired_check.passed,
                "repaired_severity": repaired_check.severity,
                "repaired_blocked_terms_count": repaired_check.match_count,
                "sanitizer_warnings": warnings,
            }
        )
        description = repaired
        current_check = repaired_check
        if repaired_check.passed:
            break
    return {"description": description, "repair_attempts": attempts, "final_check": current_check}


def _build_leak_repair_prompt(candidate_description: str, leaked_terms: list[str]) -> str:
    forbidden = "\n".join(f"- {term}" for term in leaked_terms[:30]) or "- 无可见片段，仅根据 hash 检查结果修复"
    return f"""下面的候选概念阐释复制了训练语料、标准答案或模型答案中的具体片段。请删除这些具体片段，只保留抽象、可泛化的标注规则。

候选概念阐释：
{candidate_description}

禁止原样保留的具体片段：
{forbidden}

修复要求：
1. 只输出修复后的最终概念阐释正文。
2. 不要出现上面列出的具体词、短语、原句、答案片段或样例编号。
3. 把具体例子抽象成概念定义、边界规则或排除规则。
4. 只保留任务定义、概念定义、边界规则和排除规则。
5. 不要输出标签集合、JSON schema、annotation 标注格式、输出格式或格式修复指令。"""


def _build_text_gradient_prompt(
    current_description: str,
    validation_result: dict,
    failure_summary: str,
    current_loss: dict,
    direction: dict,
    optimizer_context: dict,
) -> str:
    concept_description = strip_frozen_protocol_sections(current_description)
    return f"""请根据批改对照和文本梯度，优化下面的概念阐释。

training_feedback_only=true

当前可优化定义：
{concept_description}

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
2. 可以把具体错误抽象成概念定义、边界规则或排除规则。
3. 不要输出标签集合、JSON schema、annotation 标注格式、输出格式或格式修复指令。
4. 不要复制原文、标准答案、模型答案、样例编号、失败摘要或修订日志。
5. 不要出现 gold-编号、“失败摘要”、“本轮失败”、“修订建议”、“漏标”、“多标”、“边界不稳定样例”等诊断文字。"""


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
            "metadata": {"optimizer": method, "optimizer_display_name": optimizer_display_name(method)},
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
    round_improved: bool = False,
    no_improvement_streak_after_round: int = 0,
    stop_reason_if_stopped: str = "",
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
        "round_best_candidate_id": accepted_candidate_id,
        "round_best_loss": selected_loss["loss"],
        "round_loss_delta": round(current_loss["loss"] - selected_loss["loss"], 4),
        "round_improved": round_improved,
        "no_improvement_streak_after_round": no_improvement_streak_after_round,
        "stop_reason_if_stopped": stop_reason_if_stopped,
        "reached_target": not selected_result["failed"] and not selected_result["unstable"],
        "failure_summary": failure_summary,
        "failure_cases": _failure_cases(selected_result["details"]),
        "candidate_evaluations": candidate_evaluations,
        "memorization_blocked_count": sum(
            1
            for evaluation in candidate_evaluations
            if evaluation.get("status") in {"memorization_guard_blocked", "memorization_repair_failed"}
        ),
        "repair_attempt_count": sum(len(evaluation.get("repair_attempts", [])) for evaluation in candidate_evaluations),
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
        "optimizer_name": row.get("optimizer_name", optimizer_display_name(row["method"])),
        "optimizer_family": row.get("optimizer_family", OPTIMIZER_FAMILIES.get(row["method"], "")),
        "alias_from": row.get("alias_from", ""),
        "method_trace_summary": row.get("method_trace_summary", _method_trace_summary(row["method"], row.get("rounds", []))),
        "status": row["status"],
        "reached_target": row["reached_target"],
        "stop_reason": row.get("stop_reason", ""),
        "initial_loss": row.get("initial_loss", 0.0),
        "initial_pass_count": row.get("initial_pass_count", 0),
        "best_pass_count": row["best_pass_count"],
        "best_loss": row["best_loss"],
        "best_round_index": row.get("best_round_index", 0),
        "total_loss_delta": row.get("total_loss_delta", 0.0),
        "no_improvement_streak": row.get("no_improvement_streak", 0),
        "accepted_round_count": row.get("accepted_round_count", 0),
        "evaluated_candidate_count": row.get("evaluated_candidate_count", 0),
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
        "repair_attempt_count": sum(
            len(candidate.get("repair_attempts", []))
            for round_row in row.get("rounds", [])
            for candidate in round_row.get("candidate_evaluations", [])
        ),
    }


def _method_trace_summary(method: str, rounds: list[dict[str, Any]]) -> dict[str, Any]:
    critic_count = 0
    controller_count = 0
    mask_count = 0
    mask_deltas: list[float] = []
    accepted_candidates = 0
    for round_row in rounds:
        for candidate in round_row.get("candidate_evaluations", []):
            if candidate.get("accepted"):
                accepted_candidates += 1
            if candidate.get("critic_diagnosis"):
                critic_count += 1
            if candidate.get("controller_direction"):
                controller_count += 1
            if candidate.get("mask_segment_id"):
                mask_count += 1
            if candidate.get("mask_loss_delta") not in {"", None}:
                try:
                    mask_deltas.append(float(candidate.get("mask_loss_delta")))
                except (TypeError, ValueError):
                    pass
    return {
        "method": method,
        "optimizer_name": optimizer_display_name(method),
        "optimizer_family": OPTIMIZER_FAMILIES.get(method, ""),
        "accepted_candidate_count": accepted_candidates,
        "critic_trace_count": critic_count,
        "controller_trace_count": controller_count,
        "mask_trace_count": mask_count,
        "max_mask_loss_delta": max(mask_deltas) if mask_deltas else 0.0,
        "min_mask_loss_delta": min(mask_deltas) if mask_deltas else 0.0,
    }


def _usage_summary(method_results: list[dict[str, Any]], config: PromptTrainingConfig, predictor: Predictor | None = None) -> dict[str, Any]:
    runtime = getattr(predictor, "runtime", None)
    if runtime is not None and hasattr(runtime, "usage_summary"):
        summary = dict(runtime.usage_summary())
        summary.setdefault("provider", config.provider_id)
        summary.setdefault("model", config.model)
        summary.setdefault("concurrency", config.concurrency)
        return summary
    usages = [row.get("usage", {}) for row in method_results]
    return {
        "provider": config.provider_id,
        "model": config.model,
        "concurrency": config.concurrency,
        "llm_call_count": sum(int(usage.get("llm_call_count", 0)) for usage in usages),
        "estimated_tokens": sum(int(usage.get("estimated_tokens", 0)) for usage in usages),
        "estimated": True,
        "provider_elapsed_seconds": round(sum(float(usage.get("provider_elapsed_seconds", 0.0)) for usage in usages), 4),
    }


def _runtime_progress_events(predictor: Predictor | None) -> list[dict[str, Any]]:
    runtime = getattr(predictor, "runtime", None)
    if runtime is None:
        return []
    return [
        dict(event, event_type=f"provider_{event.get('event_type', 'event')}")
        for event in getattr(runtime, "progress_events", [])
    ]


def _repair_summary(method_results: list[dict[str, Any]]) -> dict[str, Any]:
    attempts = 0
    successes = 0
    failures = 0
    for row in method_results:
        for round_row in row.get("rounds", []):
            for candidate in round_row.get("candidate_evaluations", []):
                candidate_attempts = candidate.get("repair_attempts", [])
                attempts += len(candidate_attempts)
                if candidate_attempts and candidate.get("memorization_passed"):
                    successes += 1
                if candidate.get("status") == "memorization_repair_failed":
                    failures += 1
    return {"repair_attempt_count": attempts, "repair_success_count": successes, "repair_failed_count": failures}


def _progress_events(method: str, rounds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for round_row in rounds:
        events.append(
            {
                "event_type": "round_completed",
                "method": method,
                "round_index": round_row.get("round_index"),
                "status": round_row.get("status"),
                "pass_count": round_row.get("pass_count"),
                "loss": round_row.get("loss"),
                "round_improved": round_row.get("round_improved", False),
                "no_improvement_streak": round_row.get("no_improvement_streak_after_round", 0),
                "stop_reason": round_row.get("stop_reason_if_stopped", ""),
                "llm_call_count": round_row.get("llm_call_count", 0),
                "estimated_tokens": round_row.get("estimated_tokens", 0),
                "elapsed_seconds": round_row.get("elapsed_seconds", 0.0),
            }
        )
        for candidate in round_row.get("candidate_evaluations", []):
            events.append(
                {
                    "event_type": "candidate_evaluated",
                    "method": method,
                    "round_index": round_row.get("round_index"),
                    "candidate_id": candidate.get("candidate_id"),
                    "status": candidate.get("status"),
                    "pass_count": candidate.get("pass_count"),
                    "loss": candidate.get("loss"),
                    "memorization_status": candidate.get("memorization_status", "clean"),
                    "repair_attempts": len(candidate.get("repair_attempts", [])),
                }
            )
    return events


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
        if candidate.get("status") in {"memorization_guard_blocked", "memorization_repair_failed"}
    )
    final_check = best.get("final_memorization_check") if config.no_corpus_memorization else None
    if final_check is None and config.no_corpus_memorization:
        final_check = guard.check(best.get("best_description", ""), field="best_description").to_dict()
    return {
        "no_corpus_memorization": config.no_corpus_memorization,
        "raw_feedback_allowed": config.raw_feedback_allowed,
        "memorization_policy": config.memorization_policy,
        "candidate_blocked_count": blocked_count,
        "repair_summary": _repair_summary(method_results),
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
        "usage_summary": _usage_summary(method_results, config),
        "repair_summary": _repair_summary(method_results),
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
    prompt_versions: list[dict[str, Any]],
) -> None:
    _store_prompt_version_history(store, guideline_id, prompt_versions, artifact_path, config)
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
                "best_optimizer_name": best.get("optimizer_name", optimizer_display_name(best["method"])),
                "best_optimizer_family": best.get("optimizer_family", OPTIMIZER_FAMILIES.get(best["method"], "")),
                "method_comparison": [_method_summary(row) for row in method_results],
                "target_pass_count": target_pass_count,
                "reached_target": best["reached_target"],
                "stop_policy": config.stop_policy,
                "stop_reason": best.get("stop_reason", ""),
                "training_trace_summary": {
                    "best_loss": best["best_loss"],
                    "best_pass_count": best["best_pass_count"],
                    "best_round_index": best.get("best_round_index", 0),
                    "prompt_version_count": len(prompt_versions),
                    "initial_loss": best.get("initial_loss", 0.0),
                    "total_loss_delta": best.get("total_loss_delta", 0.0),
                    "accepted_round_count": best.get("accepted_round_count", 0),
                    "no_improvement_streak": best.get("no_improvement_streak", 0),
                    "round_count": len(best["rounds"]),
                    "artifact_path": artifact_path,
                },
                "no_corpus_memorization": config.no_corpus_memorization,
                "memorization_policy": config.memorization_policy,
                "raw_feedback_allowed": config.raw_feedback_allowed,
                "concurrency": config.concurrency,
                "provider_id": config.provider_id,
                "model": config.model,
                "repair_summary": _repair_summary(method_results),
                "usage_summary": _usage_summary(method_results, config),
                "leakage_summary": leakage_report,
                "artifact_path": artifact_path,
                "sanitizer_warnings": initial_warnings,
                "auto_generated": True,
                "auto_applied": auto_apply,
                "guideline_name": guideline.get("name", ""),
            },
        )
    )


def _prompt_versions_for_best_method(initial_description: str, best: dict[str, Any]) -> list[dict[str, Any]]:
    rows = list(best.get("prompt_versions", []))
    if rows:
        return rows
    return [
        {
            "version_label": "v0",
            "method": best.get("method", ""),
            "optimizer_name": best.get("optimizer_name", optimizer_display_name(str(best.get("method", "")))),
            "optimizer_family": best.get("optimizer_family", OPTIMIZER_FAMILIES.get(str(best.get("method", "")), "")),
            "alias_from": best.get("alias_from", ""),
            "round_index": 0,
            "candidate_id": "initial",
            "description": initial_description,
            "loss": best.get("initial_loss", ""),
            "pass_count": best.get("initial_pass_count", ""),
            "loss_delta": 0.0,
            "accepted": True,
            "event": "initial",
        }
    ]


def _store_prompt_version_history(
    store: RuntimeStore,
    guideline_id: str,
    prompt_versions: list[dict[str, Any]],
    artifact_path: str,
    config: PromptTrainingConfig,
) -> None:
    next_version = _next_concept_version(store, guideline_id)
    for row in prompt_versions:
        description = str(row.get("description", "")).strip()
        if not description:
            continue
        store.upsert_concept_version(
            ConceptVersion(
                id=f"concept-version-{uuid.uuid4().hex[:10]}",
                guideline_id=guideline_id,
                version=next_version,
                description=description,
                notes=f"提示词优化版本 {row.get('version_label', '')}",
                metadata={
                    "prompt_training_version": True,
                    "prompt_version_label": row.get("version_label", ""),
                    "prompt_version_event": row.get("event", ""),
                    "method": row.get("method", ""),
                    "optimizer_name": row.get("optimizer_name", optimizer_display_name(str(row.get("method", "")))),
                    "optimizer_family": row.get("optimizer_family", OPTIMIZER_FAMILIES.get(str(row.get("method", "")), "")),
                    "alias_from": row.get("alias_from", ""),
                    "round_index": row.get("round_index", 0),
                    "candidate_id": row.get("candidate_id", ""),
                    "loss": row.get("loss", ""),
                    "loss_before": row.get("loss_before", ""),
                    "loss_delta": row.get("loss_delta", ""),
                    "pass_count": row.get("pass_count", ""),
                    "artifact_path": artifact_path,
                    "provider_id": config.provider_id,
                    "model": config.model,
                },
            )
        )
        next_version += 1


def write_prompt_training_comparison_outputs(result: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    """Write human-readable and machine-readable prompt training experiment outputs."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "comparison_report.md"
    result_path = out_dir / "comparison_result.json"
    evolution_path = out_dir / "prompt_evolution.jsonl"
    events_path = out_dir / "run_events.jsonl"
    result_with_paths = {
        **result,
        "report_path": str(report_path),
        "prompt_evolution_path": str(evolution_path),
        "events_path": str(events_path),
    }
    evolution_rows = _prompt_evolution_rows(result_with_paths)
    evolution_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in evolution_rows) + ("\n" if evolution_rows else ""),
        encoding="utf-8",
    )
    event_rows = list(result_with_paths.get("progress_events", []))
    events_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in event_rows) + ("\n" if event_rows else ""),
        encoding="utf-8",
    )
    report_path.write_text(build_prompt_training_comparison_report(result_with_paths), encoding="utf-8")
    result_path.write_text(json.dumps(result_with_paths, ensure_ascii=False, indent=2), encoding="utf-8")
    return {**result_with_paths, "comparison_result_path": str(result_path)}


def build_prompt_training_comparison_report(result: dict[str, Any]) -> str:
    method_rows = result.get("method_results", [])
    rounds = result.get("rounds", [])
    lines = [
        "# Prompt Training Comparison Report",
        "",
        "## Summary",
        "",
        f"- Experiment case: `{result.get('experiment_case') or 'custom'}`",
        f"- Best method: `{result.get('best_method', '')}` ({optimizer_display_name(str(result.get('best_method', '')))})",
        f"- Best pass count: `{result.get('best_pass_count', 0)}/15`",
        f"- Best loss: `{result.get('best_loss', 0.0)}`",
        "- Best fields use the historical best accepted prompt, not the last round snapshot.",
        f"- Stop policy: `{result.get('stop_policy', '')}`",
        f"- Real provider run: `{result.get('real_provider_run', False)}`",
        f"- Report path: `{result.get('report_path', '')}`",
        "",
        "## Progress Summary",
        "",
        _markdown_table(
            ["metric", "value"],
            [
                ["run_id", result.get("run_id", "")],
                ["events_path", result.get("events_path", "")],
                ["total_events", len(result.get("progress_events", []))],
                ["llm_calls", result.get("usage_summary", {}).get("llm_call_count", 0)],
                [
                    "tokens",
                    result.get("usage_summary", {}).get(
                        "total_tokens",
                        result.get("usage_summary", {}).get("estimated_tokens", 0),
                    ),
                ],
                ["repairs", result.get("repair_summary", {}).get("repair_attempt_count", 0)],
                ["concurrency", result.get("usage_summary", {}).get("concurrency", "")],
            ],
        ),
        "",
        "## Timeline Summary",
        "",
        _markdown_table(
            ["event_type", "stage", "message", "progress", "completed", "total", "created_at"],
            [
                [
                    event.get("event_type", ""),
                    event.get("stage", ""),
                    event.get("message", ""),
                    event.get("progress", ""),
                    event.get("completed", ""),
                    event.get("total", ""),
                    event.get("created_at", ""),
                ]
                for event in result.get("progress_events", [])[-50:]
            ],
        ),
        "",
        "## Method Comparison",
        "",
        _markdown_table(
            [
                "method",
                "optimizer",
                "status",
                "stop_reason",
                "initial_pass",
                "best_pass",
                "initial_loss",
                "best_loss",
                "loss_delta",
                "best_round",
                "rounds",
                "accepted_rounds",
                "evaluated_candidates",
                "llm_calls",
                "tokens",
                "seconds",
                "repairs",
            ],
            [
                [
                    row.get("method", ""),
                    row.get("optimizer_name", optimizer_display_name(str(row.get("method", "")))),
                    row.get("status", ""),
                    row.get("stop_reason", ""),
                    row.get("initial_pass_count", 0),
                    row.get("best_pass_count", 0),
                    row.get("initial_loss", 0.0),
                    row.get("best_loss", 0.0),
                    row.get("total_loss_delta", 0.0),
                    row.get("best_round_index", 0),
                    row.get("round_count", 0),
                    row.get("accepted_round_count", 0),
                    row.get("evaluated_candidate_count", 0),
                    row.get("llm_call_count", 0),
                    row.get("estimated_tokens", 0),
                    row.get("elapsed_seconds", 0.0),
                    row.get("repair_attempt_count", 0),
                ]
                for row in method_rows
            ],
        ),
        "",
        "## Round Speed",
        "",
        _markdown_table(
            [
                "method",
                "optimizer",
                "round",
                "status",
                "pass_count",
                "loss",
                "loss_delta",
                "improved",
                "streak",
                "accepted_candidate",
                "llm_calls",
                "tokens",
                "seconds",
                "stop_reason",
            ],
            [
                [
                    row.get("method", ""),
                    optimizer_display_name(str(row.get("method", ""))),
                    row.get("round_index", ""),
                    row.get("status", ""),
                    row.get("pass_count", 0),
                    row.get("loss", 0.0),
                    row.get("round_loss_delta", row.get("loss_delta", 0.0)),
                    row.get("round_improved", False),
                    row.get("no_improvement_streak_after_round", 0),
                    row.get("accepted_candidate_id", ""),
                    row.get("llm_call_count", 0),
                    row.get("estimated_tokens", 0),
                    row.get("elapsed_seconds", 0.0),
                    row.get("stop_reason_if_stopped", ""),
                ]
                for row in rounds
            ],
        ),
        "",
        "## Candidate Status",
        "",
        _markdown_table(
            ["method", "optimizer", "round", "candidate", "status", "pass_count", "loss", "memorization", "repairs"],
            [
                [
                    round_row.get("method", ""),
                    optimizer_display_name(str(round_row.get("method", ""))),
                    round_row.get("round_index", ""),
                    candidate.get("candidate_id", ""),
                    candidate.get("status", ""),
                    candidate.get("pass_count", ""),
                    candidate.get("loss", ""),
                    candidate.get("memorization_status", "clean"),
                    len(candidate.get("repair_attempts", [])),
                ]
                for round_row in rounds
                for candidate in round_row.get("candidate_evaluations", [])
            ],
        ),
        "",
        "## Prompt Evolution",
        "",
    ]
    for row in _prompt_evolution_rows(result):
        lines.extend(
            [
                f"### {row['method']} - {row['event']} round {row['round_index']}",
                "",
                f"- loss: `{row.get('loss', '')}`",
                f"- pass_count: `{row.get('pass_count', '')}`",
                "",
                "```text",
                str(row.get("description", "")),
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## Safety Notes",
            "",
            "- Training feedback may contain source text and answers, but public report tables do not expose raw matched leakage terms.",
            "- The result only describes training performance on the 15 gold examples; it does not prove held-out generalization.",
            "",
        ]
    )
    return "\n".join(lines)


def _prompt_evolution_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    prompt_versions = list(result.get("prompt_versions", []))
    if prompt_versions:
        return [
            {
                "method": row.get("method", result.get("best_method", "")),
                "optimizer_name": row.get("optimizer_name", optimizer_display_name(str(row.get("method", result.get("best_method", ""))))),
                "round_index": row.get("round_index", 0),
                "event": row.get("event", ""),
                "version_label": row.get("version_label", ""),
                "loss": row.get("loss", ""),
                "loss_delta": row.get("loss_delta", ""),
                "pass_count": row.get("pass_count", ""),
                "candidate_id": row.get("candidate_id", ""),
                "description": row.get("description", ""),
            }
            for row in prompt_versions
        ]
    rows: list[dict[str, Any]] = []
    initial_description = result.get("initial_description", "")
    methods = [row.get("method", "") for row in result.get("method_results", [])]
    for method in methods:
        rows.append(
            {
                "method": method,
                "round_index": 0,
                "event": "initial",
                "loss": "",
                "pass_count": "",
                "description": initial_description,
            }
        )
        for round_row in result.get("rounds", []):
            if round_row.get("method") != method:
                continue
            if round_row.get("round_improved") or round_row.get("status") == "stable":
                rows.append(
                    {
                        "method": method,
                        "round_index": round_row.get("round_index", 0),
                        "event": "accepted" if round_row.get("round_improved") else "final",
                        "loss": round_row.get("loss", ""),
                        "pass_count": round_row.get("pass_count", ""),
                        "description": round_row.get("description", ""),
                    }
                )
    return rows


def _markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    if not rows:
        return "_No rows._"
    header_line = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(_markdown_cell(value) for value in row) + " |" for row in rows]
    return "\n".join([header_line, separator, *body])


def _markdown_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")
