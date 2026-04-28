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
from app.workflows.annotation import run_batch_worker, submit_batch_annotation

st.title("批量标注")
st.caption("上传 TXT、JSONL 或 CSV，自动切分为标注任务，提交后可离开页面。")

store = RuntimeStore()


def _make_mock_predictor(label: str):
    def predictor(system_prompt: str, messages: list[dict], temperature: float) -> str:
        user_content = messages[-1]["content"] if messages else ""
        match = re.search(r'文本：["“](.*?)["”]', user_content, flags=re.S)
        text = match.group(1).strip() if match else user_content.strip()
        first = next((part.strip("，。,.!?;；：:()[]{}\"'") for part in text.split() if part.strip()), "")
        if not first:
            first = text[: min(2, len(text))]
        annotation = f"[{first}]{{{label or 'Term'}}}"
        return json.dumps({"text": text, "annotation": annotation, "explanation": "本地模拟候选。", "confidence": 0.82}, ensure_ascii=False)

    return predictor


def _make_llm_predictor(platform_id: str, model: str):
    provider = get_provider(platform_id)
    if provider is None:
        raise RuntimeError("平台不可用")
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
    raise ValueError("不支持的文件类型")


def _start_worker(job_id: str, mode: str, platform_id: str, model: str, temperature: float, label: str) -> None:
    def target() -> None:
        worker_store = RuntimeStore()
        predictor = _make_mock_predictor(label) if mode == "本地模拟" else _make_llm_predictor(platform_id, model)
        run_batch_worker(
            worker_store,
            job_id=job_id,
            predictor=predictor,
            platform=platform_id if mode != "本地模拟" else "local",
            model=model if mode != "本地模拟" else "mock",
            temperature=temperature,
        )

    thread = threading.Thread(target=target, name=f"rosetta-batch-{job_id}", daemon=True)
    thread.start()


projects = store.list_projects(limit=200)
guidelines = store.list_guidelines(limit=200)

if not projects or not guidelines:
    st.warning("请先在“概念实验室”创建项目、概念阐释和金样例。")
    if st.button("去概念实验室", use_container_width=True):
        st.switch_page("app/ui/pages/Concept_Lab.py")
    st.stop()

st.subheader("1. 选择概念")
project_id = st.selectbox(
    "标注项目",
    [row["id"] for row in projects],
    format_func=lambda project_id: next(row["payload"]["name"] for row in projects if row["id"] == project_id),
)
project_guidelines = [row for row in guidelines if row["payload"]["project_id"] == project_id]
if not project_guidelines:
    st.warning("该项目还没有概念阐释。")
    st.stop()
guideline_id = st.selectbox(
    "概念阐释",
    [row["id"] for row in project_guidelines],
    format_func=lambda guideline_id: next(row["payload"]["name"] for row in project_guidelines if row["id"] == guideline_id),
)
guideline_payload = next(row["payload"] for row in project_guidelines if row["id"] == guideline_id)
default_label = (guideline_payload.get("labels") or ["Term"])[0]

with st.expander("查看当前概念阐释", expanded=False):
    st.write(guideline_payload.get("stable_description", ""))

st.divider()
st.subheader("2. 上传语料")
uploaded_file = st.file_uploader("上传 TXT、JSONL 或 CSV", type=["txt", "jsonl", "csv"])
csv_text_column = st.text_input("CSV 文本列名", value="text")
manual_text = st.text_area("也可以直接粘贴 TXT 内容", height=160, placeholder="粘贴一段原始文本，系统会自动分句。")

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
    st.success(f"已解析出 {len(tasks)} 条标注任务。")
    st.dataframe(preview_tasks(tasks, limit=8), use_container_width=True, hide_index=True)
else:
    st.info("上传或粘贴语料后会在这里预览切分结果。")

st.divider()
st.subheader("3. 提交任务")
col1, col2, col3, col4 = st.columns(4)
sample_count = col1.selectbox("每条采样次数", [1, 3, 5], index=2)
concurrency = col2.number_input("并发数", min_value=1, max_value=32, value=4, step=1)
review_threshold = col3.slider("人工审核阈值", 0.0, 1.0, 0.75, 0.01)
auto_sample_rate = col4.slider("高置信抽检比例", 0.0, 0.5, 0.05, 0.01)

run_mode = st.radio("执行方式", ["只提交队列", "本地模拟", "调用大模型"], horizontal=True)
platform_id = st.selectbox(
    "平台",
    list(PLATFORM_CONFIGS.keys()),
    format_func=lambda key: PLATFORM_CONFIGS[key].name,
    disabled=run_mode != "调用大模型",
)
model = st.text_input("模型", value=PLATFORM_CONFIGS[platform_id].default_model, disabled=run_mode != "调用大模型")
temperature = st.slider("温度", 0.0, 1.0, 0.3, 0.1, disabled=run_mode == "只提交队列")

if st.button("提交批量任务", type="primary", use_container_width=True, disabled=not tasks):
    job = submit_batch_annotation(
        store,
        project_id=project_id,
        guideline_id=guideline_id,
        tasks=tasks,
        sample_count=int(sample_count),
        concurrency=int(concurrency),
        review_threshold=float(review_threshold),
        auto_sample_rate=float(auto_sample_rate),
        metadata={"source_page": "批量标注"},
    )
    st.success(f"任务已提交：{job.id}")
    if run_mode != "只提交队列":
        _start_worker(job.id, run_mode, platform_id, model, float(temperature), default_label)
        st.info("后台执行已启动。可以切到“审核队列”等待低置信样本出现。")
    st.session_state["last_batch_job_id"] = job.id

st.divider()
st.subheader("4. 任务进度")
jobs = store.list_jobs(limit=20)
if not jobs:
    st.info("暂无批量任务。")
else:
    for row in jobs:
        payload: dict[str, Any] = row["payload"]
        total = max(int(payload.get("total_items", 0)), 1)
        completed = int(payload.get("completed_items", 0))
        st.markdown(f"**{payload['id']}**：{payload['status']}")
        st.progress(min(completed / total, 1.0), text=f"{completed}/{payload.get('total_items', 0)} 已完成")
        cols = st.columns(4)
        cols[0].metric("总数", payload.get("total_items", 0))
        cols[1].metric("完成", payload.get("completed_items", 0))
        cols[2].metric("失败", payload.get("failed_items", 0))
        cols[3].metric("待审核", payload.get("review_items", 0))
