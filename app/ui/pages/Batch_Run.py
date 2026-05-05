from __future__ import annotations

import json
import re
import threading
import uuid
from typing import Any

import streamlit as st

from app.data.text_ingestion import preview_tasks, tasks_from_csv, tasks_from_jsonl, tasks_from_txt
from app.infrastructure.llm.credentials import resolve_api_key
from app.infrastructure.llm.providers import PLATFORM_CONFIGS
from app.infrastructure.llm.registry import get_provider
from app.runtime.store import RuntimeStore
from app.ui.components.busy import busy_button, clear_busy
from app.ui.i18n import t
from app.workflows.annotation import run_batch_worker, submit_batch_annotation

st.title(t("batch_run.title"))
st.caption(t("batch_run.caption"))

store = RuntimeStore()


def _set_flash(kind: str, message: str) -> None:
    st.session_state["batch_run_flash"] = {"kind": kind, "message": message}


def _render_flash() -> None:
    flash = st.session_state.pop("batch_run_flash", None)
    if not flash:
        return
    renderer = getattr(st, flash.get("kind", "info"), st.info)
    renderer(flash.get("message", ""))


def _make_mock_predictor(label: str):
    def predictor(system_prompt: str, messages: list[dict], temperature: float) -> str:
        user_content = messages[-1]["content"] if messages else ""
        match = re.search(r"待标注文本：\s*(.*?)(?:\n\n任务强调：|$)", user_content, flags=re.S)
        text = match.group(1).strip() if match else user_content.strip()
        first = next((part.strip("，。,.!?;；：:()[]{}\"'") for part in text.split() if part.strip()), "")
        if not first:
            first = text[: min(2, len(text))]
        annotation = f"[{first}]{{{label or 'Term'}}}"
        return json.dumps(
            {
                "text": text,
                "annotation": annotation,
                "explanation": t("batch_run.local_mock_explanation"),
                "confidence": 0.82,
            },
            ensure_ascii=False,
        )

    return predictor


def _make_llm_predictor(platform_id: str, model: str):
    provider = get_provider(platform_id)
    if provider is None:
        raise RuntimeError(t("common.platform_unavailable"))
    api_key = resolve_api_key(platform_id)

    def predictor(system_prompt: str, messages: list[dict], temperature: float) -> str:
        full_messages = [{"role": "system", "content": system_prompt}, *messages]
        return provider.chat(api_key=api_key, model=model, messages=full_messages, temperature=temperature)

    return predictor


def _parse_upload(file, text_column: str):
    if file is None:
        return []
    content = file.getvalue().decode("utf-8")
    prefix = f"{file.name.rsplit('.', 1)[0]}-{uuid.uuid4().hex[:6]}"
    if file.name.endswith(".txt"):
        return tasks_from_txt(content, source_name=file.name, prefix=prefix)
    if file.name.endswith(".jsonl"):
        return tasks_from_jsonl(content, source_name=file.name, prefix=prefix)
    if file.name.endswith(".csv"):
        return tasks_from_csv(content, text_column=text_column, source_name=file.name, prefix=prefix)
    raise ValueError(t("batch_run.unsupported_file"))


def _start_worker(job_id: str, mode: str, platform_id: str, model: str, temperature: float, label: str) -> None:
    def target() -> None:
        worker_store = RuntimeStore()
        predictor = _make_mock_predictor(label) if mode == "mock" else _make_llm_predictor(platform_id, model)
        run_batch_worker(
            worker_store,
            job_id=job_id,
            predictor=predictor,
            platform=platform_id if mode != "mock" else "local",
            model=model if mode != "mock" else "mock",
            temperature=temperature,
        )

    thread = threading.Thread(target=target, name=f"rosetta-batch-{job_id}", daemon=True)
    thread.start()


projects = store.list_projects(limit=200)
guidelines = store.list_guidelines(limit=200)

_render_flash()

if not projects or not guidelines:
    st.warning(t("batch_run.need_concept"))
    if st.button(t("batch_run.go_concept"), use_container_width=True):
        st.switch_page("app/ui/pages/Concept_Lab.py")
    st.stop()

st.subheader(t("batch_run.section_concept"))
project_id = st.selectbox(
    t("batch_run.project"),
    [row["id"] for row in projects],
    format_func=lambda project_id: next(row["payload"]["name"] for row in projects if row["id"] == project_id),
)
project_guidelines = [row for row in guidelines if row["payload"]["project_id"] == project_id]
if not project_guidelines:
    st.warning(t("batch_run.no_project_guideline"))
    st.stop()
guideline_id = st.selectbox(
    t("batch_run.guideline"),
    [row["id"] for row in project_guidelines],
    format_func=lambda guideline_id: next(row["payload"]["name"] for row in project_guidelines if row["id"] == guideline_id),
)
guideline_payload = next(row["payload"] for row in project_guidelines if row["id"] == guideline_id)
default_label = (guideline_payload.get("labels") or ["Term"])[0]

with st.expander(t("batch_run.view_guideline"), expanded=False):
    st.write(guideline_payload.get("stable_description", ""))

st.divider()
st.subheader(t("batch_run.section_upload"))
uploaded_file = st.file_uploader(t("batch_run.upload"), type=["txt", "jsonl", "csv"])
csv_text_column = st.text_input(t("batch_run.csv_column"), value="text")
manual_text = st.text_area(t("batch_run.manual_text"), height=160, placeholder=t("batch_run.manual_placeholder"))

tasks = []
parse_error = ""
try:
    if uploaded_file is not None:
        tasks = _parse_upload(uploaded_file, csv_text_column)
    elif manual_text.strip():
        tasks = tasks_from_txt(manual_text, source_name="manual.txt", prefix=f"manual-{uuid.uuid4().hex[:6]}")
except Exception as exc:
    parse_error = str(exc)

if parse_error:
    st.error(parse_error)

if tasks:
    st.success(t("batch_run.parsed", count=len(tasks)))
    st.dataframe(preview_tasks(tasks, limit=8), use_container_width=True, hide_index=True)
else:
    st.info(t("batch_run.preview_empty"))

st.divider()
st.subheader(t("batch_run.section_submit"))
col1, col2, col3, col4 = st.columns(4)
sample_count = col1.selectbox(t("batch_run.sample_count"), [1, 3, 5], index=2)
concurrency = col2.number_input(t("batch_run.concurrency"), min_value=1, max_value=20, value=20, step=1)
review_threshold = col3.slider(t("batch_run.review_threshold"), 0.0, 1.0, 0.75, 0.01)
auto_sample_rate = col4.slider(t("batch_run.audit_rate"), 0.0, 0.5, 0.05, 0.01)

run_mode = st.radio(
    t("batch_run.run_mode"),
    ["queue", "mock", "llm"],
    horizontal=True,
    format_func=lambda mode: t(f"batch_run.mode_{mode}"),
)
platform_id = st.selectbox(
    t("common.platform"),
    list(PLATFORM_CONFIGS.keys()),
    format_func=lambda key: PLATFORM_CONFIGS[key].name,
    disabled=run_mode != "llm",
)
model = st.text_input(t("common.model"), value=PLATFORM_CONFIGS[platform_id].default_model, disabled=run_mode != "llm")
temperature = st.slider(t("common.temperature"), 0.0, 1.0, 0.3, 0.1, disabled=run_mode == "queue")

submit_button_key = "batch_run_submit_button"
if busy_button(
    t("batch_run.submit"),
    key=submit_button_key,
    pending_label=t("common.processing"),
    type="primary",
    use_container_width=True,
    disabled=not tasks,
):
    try:
        with st.spinner(t("batch_run.submitting_status")):
            job = submit_batch_annotation(
                store,
                project_id=project_id,
                guideline_id=guideline_id,
                tasks=tasks,
                sample_count=int(sample_count),
                concurrency=int(concurrency),
                review_threshold=float(review_threshold),
                auto_sample_rate=float(auto_sample_rate),
                metadata={"source_page": "batch_run"},
            )
            if run_mode != "queue":
                _start_worker(job.id, run_mode, platform_id, model, float(temperature), default_label)
        message = t("batch_run.submitted", job_id=job.id)
        if run_mode != "queue":
            message = f"{message} {t('batch_run.worker_started')}"
        st.session_state["last_batch_job_id"] = job.id
        _set_flash("success", message)
    except Exception as exc:
        _set_flash("error", t("common.action_failed", error=exc))
    finally:
        clear_busy(submit_button_key)
        st.rerun()

st.divider()
st.subheader(t("batch_run.section_progress"))
jobs = store.list_jobs(limit=20)
if not jobs:
    st.info(t("batch_run.no_jobs"))
else:
    for row in jobs:
        payload: dict[str, Any] = row["payload"]
        total = max(int(payload.get("total_items", 0)), 1)
        completed = int(payload.get("completed_items", 0))
        st.markdown(f"**{payload['id']}**: {payload['status']}")
        st.progress(min(completed / total, 1.0), text=t("batch_run.progress_text", completed=completed, total=payload.get("total_items", 0)))
        cols = st.columns(4)
        cols[0].metric(t("common.total"), payload.get("total_items", 0))
        cols[1].metric(t("common.completed"), payload.get("completed_items", 0))
        cols[2].metric(t("common.failed"), payload.get("failed_items", 0))
        cols[3].metric(t("common.pending_review"), payload.get("review_items", 0))
