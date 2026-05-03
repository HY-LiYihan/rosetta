from __future__ import annotations

import json
import uuid
from typing import Any

import streamlit as st

from app.core.models import AnnotationTask, ConceptGuideline, ConceptVersion, Project
from app.data.text_ingestion import tasks_from_csv, tasks_from_jsonl
from app.infrastructure.llm.credentials import resolve_api_key
from app.infrastructure.llm.providers import PLATFORM_CONFIGS
from app.infrastructure.llm.registry import get_provider
from app.runtime.store import RuntimeStore
from app.ui.components.busy import busy_button, clear_busy
from app.ui.examples import HARD_SCIENCE_TERM_EXAMPLE, hard_science_gold_jsonl
from app.ui.i18n import t
from app.workflows.bootstrap import (
    PROMPT_TRAINING_METHODS,
    PromptTrainingConfig,
    gold_task_from_markup,
    revise_guideline,
    run_concept_refinement_loop,
    run_prompt_training_experiment,
    sanitize_concept_description,
    save_guideline_package,
    validate_gold_examples,
)

st.title(t("concept_lab.title"))
st.caption(t("concept_lab.caption"))

store = RuntimeStore()


def _set_flash(kind: str, message: str) -> None:
    st.session_state["concept_lab_flash"] = {"kind": kind, "message": message}


def _render_flash() -> None:
    flash = st.session_state.pop("concept_lab_flash", None)
    if not flash:
        return
    renderer = getattr(st, flash.get("kind", "info"), st.info)
    renderer(flash.get("message", ""))


def _lines(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


def _project_options() -> list[dict[str, Any]]:
    return store.list_projects(limit=200)


def _parse_uploaded_gold(file, text_column: str) -> list[AnnotationTask]:
    if file is None:
        return []
    content = file.getvalue().decode("utf-8")
    if file.name.endswith(".csv"):
        return tasks_from_csv(content, text_column=text_column, source_name=file.name, prefix="gold-csv")
    return _parse_gold_jsonl(content, source_name=file.name)


def _parse_gold_jsonl(content: str, source_name: str = "pasted.jsonl") -> list[AnnotationTask]:
    tasks: list[AnnotationTask] = []
    standard_lines: list[str] = []
    for index, line in enumerate(content.splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if "annotation" in row:
            task = gold_task_from_markup(
                task_id=str(row.get("id") or f"gold-{index:05d}"),
                text=str(row["text"]),
                annotation_markup=str(row["annotation"]),
                label_hint=str(row.get("label") or ""),
            )
            tasks.append(
                AnnotationTask(
                    id=task.id,
                    text=task.text,
                    tokens=task.tokens,
                    spans=task.spans,
                    relations=task.relations,
                    label=task.label,
                    options=task.options,
                    accept=task.accept,
                    answer=task.answer,
                    meta={**task.meta, "source": source_name},
                )
            )
        else:
            standard_lines.append(json.dumps(row, ensure_ascii=False))
    if standard_lines:
        tasks.extend(tasks_from_jsonl("\n".join(standard_lines), source_name=source_name, prefix="gold-jsonl"))
    return tasks


def _make_predictor(platform_id: str, model: str):
    provider = get_provider(platform_id)
    if provider is None:
        raise RuntimeError(t("common.platform_unavailable"))
    api_key = resolve_api_key(platform_id)

    def predictor(system_prompt: str, messages: list[dict], temperature: float) -> str:
        full_messages = [{"role": "system", "content": system_prompt}, *messages]
        return provider.chat(api_key=api_key, model=model, messages=full_messages, temperature=temperature)

    return predictor


def _training_method_label(method: str) -> str:
    return t(f"concept_lab.training_method_{method}")


def _training_status_label(status: str) -> str:
    return t(f"concept_lab.training_result_status_{status}")


def _fill_example() -> None:
    st.session_state["concept_lab_project_mode"] = "new"
    st.session_state["concept_lab_project_name"] = HARD_SCIENCE_TERM_EXAMPLE["project_name"]
    st.session_state["concept_lab_project_description"] = HARD_SCIENCE_TERM_EXAMPLE["project_description"]
    st.session_state["concept_lab_name"] = HARD_SCIENCE_TERM_EXAMPLE["concept_name"]
    st.session_state["concept_lab_brief"] = HARD_SCIENCE_TERM_EXAMPLE["brief"]
    st.session_state["concept_lab_labels"] = HARD_SCIENCE_TERM_EXAMPLE["labels"]
    st.session_state["concept_lab_boundary"] = HARD_SCIENCE_TERM_EXAMPLE["boundary_rules"]
    st.session_state["concept_lab_negative"] = HARD_SCIENCE_TERM_EXAMPLE["negative_rules"]
    st.session_state["concept_lab_output_format"] = HARD_SCIENCE_TERM_EXAMPLE["output_format"]
    st.session_state["concept_lab_manual_text"] = ""
    st.session_state["concept_lab_manual_markup"] = ""
    st.session_state["concept_lab_pasted_jsonl"] = hard_science_gold_jsonl()
    st.session_state["concept_lab_csv_text_column"] = "text"


for key, value in {
    "concept_lab_project_mode": "existing",
    "concept_lab_project_name": "术语标注项目",
    "concept_lab_project_description": "用于概念阐释、金样例和批量标注。",
    "concept_lab_name": "硬科学术语",
    "concept_lab_brief": "标出英文科普新闻中与硬科学概念、技术、物理过程或实验对象直接相关的术语。",
    "concept_lab_labels": "Term",
    "concept_lab_boundary": "优先标注最小完整术语\n包含必要修饰词，但不要扩大到整个句子",
    "concept_lab_negative": "不标注泛泛的普通名词\n不标注没有科学含义的修辞表达",
    "concept_lab_output_format": "[原文]{标签}",
    "concept_lab_manual_text": "",
    "concept_lab_manual_markup": "",
    "concept_lab_pasted_jsonl": "",
    "concept_lab_csv_text_column": "text",
}.items():
    st.session_state.setdefault(key, value)

if st.session_state.get("concept_lab_project_mode") not in {"existing", "new"}:
    st.session_state["concept_lab_project_mode"] = "existing"
if st.session_state.get("concept_validation_mode") not in {None, "local", "llm"}:
    st.session_state["concept_validation_mode"] = "local"

_render_flash()

if st.button(t("concept_lab.load_example"), use_container_width=True):
    _fill_example()
    st.success(t("concept_lab.example_loaded"))
    st.rerun()

projects = _project_options()
st.subheader(t("concept_lab.section_project"))
project_mode = st.radio(
    t("concept_lab.project_source"),
    ["existing", "new"],
    horizontal=True,
    format_func=lambda mode: t(f"concept_lab.project_{mode}"),
    key="concept_lab_project_mode",
)

selected_project_id = ""
if project_mode == "new" or not projects:
    with st.form("create_project_form"):
        project_name = st.text_input(t("concept_lab.project_name"), key="concept_lab_project_name")
        project_description = st.text_area(t("concept_lab.project_description"), height=80, key="concept_lab_project_description")
        create_project = st.form_submit_button(t("concept_lab.save_project"), type="primary", use_container_width=True)
    if create_project:
        project = Project(
            id=f"project-{uuid.uuid4().hex[:10]}",
            name=project_name,
            description=project_description,
            task_schema="span",
        )
        store.upsert_project(project)
        st.success(t("concept_lab.project_saved"))
        st.rerun()
else:
    selected_project_id = st.selectbox(
        t("concept_lab.select_project"),
        [row["id"] for row in projects],
        format_func=lambda project_id: next(row["payload"]["name"] for row in projects if row["id"] == project_id),
    )

if not selected_project_id and projects and project_mode != "new":
    selected_project_id = projects[0]["id"]

st.divider()
st.subheader(t("concept_lab.section_guideline"))
with st.form("guideline_form"):
    concept_name = st.text_input(t("concept_lab.concept_name"), key="concept_lab_name")
    brief = st.text_area(t("concept_lab.brief"), height=100, key="concept_lab_brief")
    labels_text = st.text_input(t("concept_lab.labels"), key="concept_lab_labels")
    boundary_text = st.text_area(t("concept_lab.boundary"), height=90, key="concept_lab_boundary")
    negative_text = st.text_area(t("concept_lab.negative"), height=90, key="concept_lab_negative")
    output_format = st.text_input(t("concept_lab.output_format"), key="concept_lab_output_format")

    st.markdown(f"**{t('concept_lab.gold_examples')}**")
    manual_text = st.text_area(
        t("concept_lab.manual_text"),
        height=90,
        placeholder=t("concept_lab.manual_text_placeholder"),
        key="concept_lab_manual_text",
    )
    manual_markup = st.text_area(
        t("concept_lab.manual_markup"),
        height=90,
        placeholder=t("concept_lab.manual_markup_placeholder"),
        key="concept_lab_manual_markup",
    )
    pasted_jsonl = st.text_area(t("concept_lab.paste_jsonl"), height=160, key="concept_lab_pasted_jsonl")
    upload = st.file_uploader(t("concept_lab.upload_gold"), type=["jsonl", "csv"])
    csv_text_column = st.text_input(t("concept_lab.csv_text_column"), key="concept_lab_csv_text_column")
    save_clicked = st.form_submit_button(t("concept_lab.save_guideline"), type="primary", use_container_width=True)

if save_clicked:
    if not selected_project_id:
        st.error(t("concept_lab.need_project"))
        st.stop()
    gold_tasks: list[AnnotationTask] = []
    if manual_text.strip() and manual_markup.strip():
        gold_tasks.append(
            gold_task_from_markup(
                task_id=f"gold-manual-{len(store.list_tasks(limit=10000)) + 1:05d}",
                text=manual_text.strip(),
                annotation_markup=manual_markup.strip(),
                label_hint=labels_text.split(",")[0].strip() or "Concept",
            )
        )
    if pasted_jsonl.strip():
        gold_tasks.extend(_parse_gold_jsonl(pasted_jsonl, source_name="pasted.jsonl"))
    gold_tasks.extend(_parse_uploaded_gold(upload, csv_text_column))

    if not gold_tasks:
        st.error(t("concept_lab.need_gold"))
        st.stop()

    package = save_guideline_package(
        store=store,
        project_id=selected_project_id,
        name=concept_name,
        brief=brief,
        labels=[item.strip() for item in labels_text.split(",") if item.strip()],
        boundary_rules=_lines(boundary_text),
        negative_rules=_lines(negative_text),
        gold_tasks=gold_tasks,
    )
    st.success(t("concept_lab.saved_package", count=len(gold_tasks)))
    st.session_state["selected_guideline_id"] = package["guideline"].id

st.divider()
st.subheader(t("concept_lab.section_validate"))
guidelines = store.list_guidelines(project_id=selected_project_id or None, limit=100)
if not guidelines:
    st.info(t("concept_lab.no_guideline"))
else:
    selected_guideline = st.selectbox(
        t("concept_lab.select_concept"),
        [row["id"] for row in guidelines],
        index=0,
        format_func=lambda guideline_id: next(row["payload"]["name"] for row in guidelines if row["id"] == guideline_id),
        key="concept_lab_guideline_selector",
    )
    guideline_payload = next(row["payload"] for row in guidelines if row["id"] == selected_guideline)
    st.text_area(t("concept_lab.current_description"), value=guideline_payload.get("stable_description", ""), height=180)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        validation_mode = st.selectbox(
            t("concept_lab.validation_mode"),
            ["local", "llm"],
            key="concept_validation_mode",
            format_func=lambda mode: t(f"concept_lab.validation_{mode}"),
        )
    with col2:
        platform_id = st.selectbox(
            t("common.platform"),
            list(PLATFORM_CONFIGS.keys()),
            format_func=lambda key: PLATFORM_CONFIGS[key].name,
            disabled=validation_mode == "local",
        )
    with col3:
        model_name = st.text_input(
            t("common.model"),
            value=PLATFORM_CONFIGS[platform_id].default_model,
            disabled=validation_mode == "local",
        )

    validate_button_key = "concept_lab_validate_button"
    if busy_button(
        t("concept_lab.validate"),
        key=validate_button_key,
        pending_label=t("common.processing"),
        type="primary",
        use_container_width=True,
    ):
        try:
            with st.spinner(t("concept_lab.validating_status")):
                predictor = _make_predictor(platform_id, model_name) if validation_mode == "llm" else None
                result = validate_gold_examples(store, selected_guideline, predictor=predictor)
            st.session_state["concept_lab_validation_result"] = result
            _set_flash(
                "success",
                t(
                    "concept_lab.validation_summary",
                    passed=len(result["passed"]),
                    failed=len(result["failed"]),
                    unstable=len(result["unstable"]),
                ),
            )
        except Exception as exc:
            _set_flash("error", t("common.action_failed", error=exc))
        finally:
            clear_busy(validate_button_key)
            st.rerun()

    result = st.session_state.get("concept_lab_validation_result")
    if result:
        metrics = st.columns(3)
        metrics[0].metric(t("concept_lab.passed"), len(result["passed"]))
        metrics[1].metric(t("common.failed"), len(result["failed"]))
        metrics[2].metric(t("concept_lab.unstable"), len(result["unstable"]))
        st.json(result)
        revise_button_key = "concept_lab_revise_button"
        if busy_button(
            t("concept_lab.revise"),
            key=revise_button_key,
            pending_label=t("common.processing"),
            use_container_width=True,
        ):
            try:
                with st.spinner(t("concept_lab.revising_status")):
                    revised = revise_guideline(guideline_payload, result)
                st.session_state["concept_lab_revised_text"] = revised
                st.session_state["concept_lab_revised_text_editor"] = revised
                _set_flash("success", t("concept_lab.revised_ready"))
            except Exception as exc:
                _set_flash("error", t("common.action_failed", error=exc))
            finally:
                clear_busy(revise_button_key)
                st.rerun()

    revised_text = st.session_state.get("concept_lab_revised_text")
    if revised_text:
        st.session_state.setdefault("concept_lab_revised_text_editor", revised_text)
        revised_text = st.text_area(t("concept_lab.revised_draft"), height=220, key="concept_lab_revised_text_editor")
        save_revision_button_key = "concept_lab_save_revision_button"
        if busy_button(
            t("concept_lab.save_revised"),
            key=save_revision_button_key,
            pending_label=t("common.processing"),
            use_container_width=True,
        ):
            try:
                with st.spinner(t("concept_lab.saving_revision_status")):
                    clean_revised_text, sanitizer_warnings = sanitize_concept_description(
                        revised_text,
                        fallback=str(guideline_payload.get("stable_description", "")),
                    )
                    updated = ConceptGuideline(
                        id=guideline_payload["id"],
                        project_id=guideline_payload["project_id"],
                        name=guideline_payload["name"],
                        brief=guideline_payload["brief"],
                        labels=tuple(guideline_payload.get("labels", [])),
                        boundary_rules=tuple(guideline_payload.get("boundary_rules", [])),
                        negative_rules=tuple(guideline_payload.get("negative_rules", [])),
                        output_format=guideline_payload.get("output_format", "[原文]{标签}"),
                        stable_description=clean_revised_text,
                        status="draft",
                        metadata=dict(guideline_payload.get("metadata", {})),
                        created_at=guideline_payload.get("created_at", ""),
                    )
                    store.upsert_guideline(updated)
                    versions = store.list_concept_versions(guideline_id=selected_guideline, limit=1000)
                    next_version = max((int(row["payload"].get("version", 0)) for row in versions), default=0) + 1
                    store.upsert_concept_version(
                        ConceptVersion(
                            id=f"concept-version-{uuid.uuid4().hex[:10]}",
                            guideline_id=selected_guideline,
                            version=next_version,
                            description=clean_revised_text,
                            notes="manual revision draft",
                            metadata={
                                "revision_source": "manual_revision",
                                "raw_revision_response": revised_text,
                                "sanitizer_warnings": sanitizer_warnings,
                            },
                        )
                    )
                _set_flash("success", t("concept_lab.revised_saved"))
            except Exception as exc:
                _set_flash("error", t("common.action_failed", error=exc))
            finally:
                clear_busy(save_revision_button_key)
                st.rerun()

    st.divider()
    st.subheader(t("concept_lab.bootstrap_section"))
    gold_sets = store.list_gold_example_sets(guideline_id=selected_guideline, limit=1)
    gold_count = len(gold_sets[0]["payload"].get("task_ids", [])) if gold_sets else 0
    target_count = int(gold_sets[0]["payload"].get("target_count", 15)) if gold_sets else 15
    st.caption(t("concept_lab.bootstrap_help"))
    if gold_count < target_count:
        st.warning(t("concept_lab.bootstrap_need_gold", target=target_count, count=gold_count))
    boot_col1, boot_col2 = st.columns([1, 1])
    max_rounds = int(boot_col1.number_input(t("concept_lab.max_rounds"), min_value=1, max_value=10, value=5, step=1))
    auto_apply = boot_col2.checkbox(t("concept_lab.auto_apply"), value=False)
    bootstrap_button_key = "concept_lab_bootstrap_button"
    if busy_button(
        t("concept_lab.start_bootstrap"),
        key=bootstrap_button_key,
        pending_label=t("common.processing"),
        type="primary",
        use_container_width=True,
        disabled=gold_count < target_count,
    ):
        try:
            with st.spinner(t("concept_lab.bootstrap_status")):
                predictor = _make_predictor(platform_id, model_name) if validation_mode == "llm" else None
                bootstrap_result = run_concept_refinement_loop(
                    store,
                    selected_guideline,
                    predictor=predictor,
                    max_rounds=max_rounds,
                    auto_apply=auto_apply,
                )
            st.session_state["concept_lab_bootstrap_result"] = bootstrap_result
            _set_flash(
                "success",
                t(
                    "concept_lab.bootstrap_summary",
                    rounds=len(bootstrap_result["rounds"]),
                    status=bootstrap_result["status"],
                ),
            )
        except Exception as exc:
            _set_flash("error", t("common.action_failed", error=exc))
        finally:
            clear_busy(bootstrap_button_key)
            st.rerun()

    bootstrap_result = st.session_state.get("concept_lab_bootstrap_result")
    if bootstrap_result:
        st.markdown(f"**{t('concept_lab.bootstrap_rounds')}**")
        st.dataframe(bootstrap_result["rounds"], use_container_width=True, hide_index=True)
        st.text_area(
            t("concept_lab.bootstrap_final"),
            value=bootstrap_result.get("final_description", ""),
            height=180,
        )
        with st.expander(t("concept_lab.bootstrap_logs"), expanded=False):
            for round_result in bootstrap_result.get("rounds", []):
                st.markdown(t("concept_lab.bootstrap_log_round", round=round_result.get("round_index")))
                st.json(
                    {
                        "failure_summary": round_result.get("failure_summary", ""),
                        "failure_cases": round_result.get("failure_cases", []),
                        "raw_revision_response": round_result.get("raw_revision_response", ""),
                        "sanitizer_warnings": round_result.get("sanitizer_warnings", []),
                        "loss": round_result.get("loss"),
                        "loss_delta": round_result.get("loss_delta"),
                        "accepted_candidate_id": round_result.get("accepted_candidate_id"),
                        "candidate_evaluations": round_result.get("candidate_evaluations", []),
                    }
                )

    st.divider()
    st.subheader(t("concept_lab.training_section"))
    st.caption(t("concept_lab.training_help", target=target_count))
    training_methods = st.multiselect(
        t("concept_lab.training_methods"),
        list(PROMPT_TRAINING_METHODS),
        default=list(PROMPT_TRAINING_METHODS),
        format_func=_training_method_label,
        key="concept_lab_training_methods",
    )
    train_col1, train_col2, train_col3 = st.columns([1, 1, 1])
    training_max_rounds = int(
        train_col1.number_input(
            t("concept_lab.training_max_rounds"),
            min_value=1,
            max_value=10,
            value=5,
            step=1,
            key="concept_lab_training_max_rounds",
        )
    )
    training_candidate_count = int(
        train_col2.number_input(
            t("concept_lab.training_candidate_count"),
            min_value=1,
            max_value=5,
            value=3,
            step=1,
            key="concept_lab_training_candidate_count",
        )
    )
    training_min_delta = float(
        train_col3.number_input(
            t("concept_lab.training_min_delta"),
            min_value=0.0,
            max_value=1.0,
            value=0.01,
            step=0.01,
            key="concept_lab_training_min_delta",
        )
    )
    training_auto_apply = st.checkbox(
        t("concept_lab.training_auto_apply"),
        value=False,
        key="concept_lab_training_auto_apply",
    )
    training_button_key = "concept_lab_prompt_training_button"
    if busy_button(
        t("concept_lab.start_training"),
        key=training_button_key,
        pending_label=t("common.processing"),
        type="primary",
        use_container_width=True,
        disabled=gold_count < target_count or not training_methods,
    ):
        try:
            with st.spinner(t("concept_lab.training_status")):
                predictor = _make_predictor(platform_id, model_name) if validation_mode == "llm" else None
                training_result = run_prompt_training_experiment(
                    store,
                    selected_guideline,
                    predictor=predictor,
                    config=PromptTrainingConfig(
                        methods=tuple(training_methods),
                        max_rounds=training_max_rounds,
                        candidate_count=training_candidate_count,
                        target_pass_count=target_count,
                        min_loss_delta=training_min_delta,
                    ),
                    auto_apply=training_auto_apply,
                )
            st.session_state["concept_lab_prompt_training_result"] = training_result
            _set_flash(
                "success",
                t(
                    "concept_lab.training_summary",
                    method=_training_method_label(training_result["best_method"]),
                    passed=training_result["best_pass_count"],
                    target=target_count,
                    status=_training_status_label(training_result["status"]),
                ),
            )
        except Exception as exc:
            _set_flash("error", t("common.action_failed", error=exc))
        finally:
            clear_busy(training_button_key)
            st.rerun()

    training_result = st.session_state.get("concept_lab_prompt_training_result")
    if training_result:
        result_cols = st.columns(4)
        result_cols[0].metric(t("concept_lab.training_best_method"), _training_method_label(training_result["best_method"]))
        result_cols[1].metric(t("concept_lab.training_best_pass"), f"{training_result['best_pass_count']}/{target_count}")
        result_cols[2].metric(t("concept_lab.training_best_loss"), training_result["best_loss"])
        result_cols[3].metric(t("common.status"), _training_status_label(training_result["status"]))
        method_rows = [
            {
                t("concept_lab.training_table_method"): _training_method_label(row["method"]),
                t("common.status"): _training_status_label(row["status"]),
                t("concept_lab.training_table_reached"): t("common.yes") if row["reached_target"] else t("common.no"),
                t("concept_lab.training_best_pass"): row["best_pass_count"],
                t("concept_lab.training_best_loss"): row["best_loss"],
                t("concept_lab.training_table_rounds"): row["round_count"],
                t("concept_lab.training_table_failed"): row["failed_count"],
                t("concept_lab.training_table_unstable"): row["unstable_count"],
                t("concept_lab.training_table_length"): row["description_length"],
            }
            for row in training_result.get("method_results", [])
        ]
        st.dataframe(method_rows, use_container_width=True, hide_index=True)
        st.text_area(
            t("concept_lab.training_best_prompt"),
            value=training_result.get("best_description", ""),
            height=200,
        )
        with st.expander(t("concept_lab.training_logs"), expanded=False):
            st.markdown(t("concept_lab.training_artifact", path=training_result.get("artifact_path", "")))
            for round_result in training_result.get("rounds", []):
                st.markdown(
                    t(
                        "concept_lab.training_log_round",
                        method=_training_method_label(round_result.get("method", "")),
                        round=round_result.get("round_index"),
                    )
                )
                st.json(
                    {
                        "status": round_result.get("status"),
                        "pass_count": round_result.get("pass_count"),
                        "loss": round_result.get("loss"),
                        "loss_delta": round_result.get("loss_delta"),
                        "accepted_candidate_id": round_result.get("accepted_candidate_id"),
                        "failure_summary": round_result.get("failure_summary"),
                        "candidate_evaluations": round_result.get("candidate_evaluations", []),
                    }
                )

    st.divider()
    st.subheader(t("concept_lab.section_export"))
    gold_tasks = []
    if gold_sets:
        for task_id in gold_sets[0]["payload"].get("task_ids", []):
            task_row = store.get_task(task_id)
            if task_row:
                gold_tasks.append(task_row["payload"])
    guideline_md = f"# {guideline_payload['name']}\n\n{guideline_payload.get('stable_description', '')}\n"
    gold_jsonl = "".join(json.dumps(task, ensure_ascii=False) + "\n" for task in gold_tasks)
    versions_jsonl = "".join(
        json.dumps(row["payload"], ensure_ascii=False) + "\n"
        for row in store.list_concept_versions(guideline_id=selected_guideline, limit=1000)
    )
    c1, c2, c3 = st.columns(3)
    c1.download_button(t("concept_lab.download_guideline"), guideline_md, file_name="concept_guideline.md", use_container_width=True)
    c2.download_button(t("concept_lab.download_gold"), gold_jsonl, file_name="gold_examples.jsonl", use_container_width=True)
    c3.download_button(t("concept_lab.download_versions"), versions_jsonl, file_name="concept_versions.jsonl", use_container_width=True)
