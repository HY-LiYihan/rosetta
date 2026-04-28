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
from app.workflows.bootstrap import gold_task_from_markup, revise_guideline, save_guideline_package, validate_gold_examples

st.title("概念实验室")
st.caption("把一句话概念描述迭代成稳定概念阐释，并维护可导出的金样例库。")

store = RuntimeStore()


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
        raise RuntimeError("平台不可用")
    api_key = resolve_api_key(platform_id)

    def predictor(system_prompt: str, messages: list[dict], temperature: float) -> str:
        full_messages = [{"role": "system", "content": system_prompt}, *messages]
        return provider.chat(api_key=api_key, model=model, messages=full_messages, temperature=temperature)

    return predictor


projects = _project_options()
st.subheader("1. 标注项目")
project_mode = st.radio("项目来源", ["使用已有项目", "创建新项目"], horizontal=True)

selected_project_id = ""
if project_mode == "创建新项目" or not projects:
    with st.form("create_project_form"):
        project_name = st.text_input("项目名称", value="术语标注项目")
        project_description = st.text_area("项目说明", value="用于概念阐释、金样例和批量标注。", height=80)
        create_project = st.form_submit_button("保存项目", type="primary", use_container_width=True)
    if create_project:
        project = Project(
            id=f"project-{uuid.uuid4().hex[:10]}",
            name=project_name,
            description=project_description,
            task_schema="span",
        )
        store.upsert_project(project)
        st.success("项目已保存。")
        st.rerun()
else:
    selected_project_id = st.selectbox(
        "选择项目",
        [row["id"] for row in projects],
        format_func=lambda project_id: next(row["payload"]["name"] for row in projects if row["id"] == project_id),
    )

if not selected_project_id and projects and project_mode != "创建新项目":
    selected_project_id = projects[0]["id"]

st.divider()
st.subheader("2. 概念阐释")
with st.form("guideline_form"):
    concept_name = st.text_input("概念名称", value="硬科学术语")
    brief = st.text_area(
        "一句话概念描述",
        value="标出英文科普新闻中与硬科学概念、技术、物理过程或实验对象直接相关的术语。",
        height=100,
    )
    labels_text = st.text_input("标签集合，用逗号分隔", value="Term")
    boundary_text = st.text_area(
        "边界说明，每行一条",
        value="优先标注最小完整术语\n包含必要修饰词，但不要扩大到整个句子",
        height=90,
    )
    negative_text = st.text_area(
        "负例规则，每行一条",
        value="不标注泛泛的普通名词\n不标注没有科学含义的修辞表达",
        height=90,
    )
    output_format = st.text_input("模型运行时标注格式", value="[原文]{标签}")

    st.markdown("**金样例**")
    manual_text = st.text_area("新增样例原文", height=90, placeholder="粘贴一条需要作为金样例的原文")
    manual_markup = st.text_area("新增样例标注", height=90, placeholder="例如：[quantum dots]{Term} can emit light.")
    pasted_jsonl = st.text_area(
        "批量粘贴 JSONL",
        height=140,
        placeholder='{"text":"quantum dots emit light","annotation":"[quantum dots]{Term} emit light"}',
    )
    upload = st.file_uploader("上传金样例文件", type=["jsonl", "csv"])
    csv_text_column = st.text_input("CSV 文本列名", value="text")
    save_clicked = st.form_submit_button("保存概念与金样例", type="primary", use_container_width=True)

if save_clicked:
    if not selected_project_id:
        st.error("请先创建或选择项目。")
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
        st.error("至少需要提供 1 条金样例。目标是 15 条，第一版允许逐步补充。")
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
    st.success(f"已保存概念阐释和 {len(gold_tasks)} 条金样例。")
    st.session_state["selected_guideline_id"] = package["guideline"].id

st.divider()
st.subheader("3. 验证与修订")
guidelines = store.list_guidelines(project_id=selected_project_id or None, limit=100)
if not guidelines:
    st.info("保存概念后可以在这里验证 15 条金样例。")
else:
    selected_guideline = st.selectbox(
        "选择概念",
        [row["id"] for row in guidelines],
        index=0,
        format_func=lambda guideline_id: next(row["payload"]["name"] for row in guidelines if row["id"] == guideline_id),
        key="concept_lab_guideline_selector",
    )
    guideline_payload = next(row["payload"] for row in guidelines if row["id"] == selected_guideline)
    st.text_area("当前稳定阐释", value=guideline_payload.get("stable_description", ""), height=180)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        validation_mode = st.selectbox("验证方式", ["本地结构验证", "调用大模型"], key="concept_validation_mode")
    with col2:
        platform_id = st.selectbox(
            "平台",
            list(PLATFORM_CONFIGS.keys()),
            format_func=lambda key: PLATFORM_CONFIGS[key].name,
            disabled=validation_mode == "本地结构验证",
        )
    with col3:
        model_name = st.text_input(
            "模型",
            value=PLATFORM_CONFIGS[platform_id].default_model,
            disabled=validation_mode == "本地结构验证",
        )

    if st.button("验证概念", type="primary", use_container_width=True):
        predictor = None
        if validation_mode == "调用大模型":
            predictor = _make_predictor(platform_id, model_name)
        result = validate_gold_examples(store, selected_guideline, predictor=predictor)
        st.session_state["concept_lab_validation_result"] = result
        st.success(result["summary"])

    result = st.session_state.get("concept_lab_validation_result")
    if result:
        metrics = st.columns(3)
        metrics[0].metric("通过", len(result["passed"]))
        metrics[1].metric("失败", len(result["failed"]))
        metrics[2].metric("边界不稳定", len(result["unstable"]))
        st.json(result)
        if st.button("修订概念阐释草案", use_container_width=True):
            revised = revise_guideline(guideline_payload, result)
            st.session_state["concept_lab_revised_text"] = revised

    revised_text = st.session_state.get("concept_lab_revised_text")
    if revised_text:
        revised_text = st.text_area("修订草案", value=revised_text, height=220)
        if st.button("保存修订草案", use_container_width=True):
            updated = ConceptGuideline(
                id=guideline_payload["id"],
                project_id=guideline_payload["project_id"],
                name=guideline_payload["name"],
                brief=guideline_payload["brief"],
                labels=tuple(guideline_payload.get("labels", [])),
                boundary_rules=tuple(guideline_payload.get("boundary_rules", [])),
                negative_rules=tuple(guideline_payload.get("negative_rules", [])),
                output_format=guideline_payload.get("output_format", "[原文]{标签}"),
                stable_description=revised_text,
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
                    description=revised_text,
                    notes="人工保存修订草案。",
                )
            )
            st.success("修订草案已保存为新的概念版本。")
            st.rerun()

    st.divider()
    st.subheader("4. 导出产物")
    gold_sets = store.list_gold_example_sets(guideline_id=selected_guideline, limit=1)
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
    c1.download_button("下载概念阐释", guideline_md, file_name="concept_guideline.md", use_container_width=True)
    c2.download_button("下载金样例", gold_jsonl, file_name="gold_examples.jsonl", use_container_width=True)
    c3.download_button("下载修订记录", versions_jsonl, file_name="concept_versions.jsonl", use_container_width=True)
