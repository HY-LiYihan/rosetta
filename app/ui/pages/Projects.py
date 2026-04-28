from __future__ import annotations

import re

import streamlit as st

from app.core.models import Project
from app.runtime.store import RuntimeStore


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower()).strip("-")
    return slug or "project"


st.title("Projects")
st.caption("本地优先的标注项目入口：schema、guideline、dataset、runs 都挂在 project 下。")

store = RuntimeStore()

with st.form("create_project"):
    name = st.text_input("项目名称", placeholder="ACTER term annotation")
    description = st.text_area("项目说明", placeholder="这个项目要标注什么、服务哪个数据集或任务")
    task_schema = st.selectbox("任务类型", ["span", "relation", "classification", "choice", "document"])
    labels = st.text_input("标签集合", placeholder="Specific_Term, Common_Term")
    submitted = st.form_submit_button("保存项目", use_container_width=True)

if submitted:
    project = Project(
        id=_slug(name),
        name=name.strip(),
        description=description.strip(),
        task_schema=task_schema,
        labels=tuple(label.strip() for label in labels.split(",") if label.strip()),
    )
    try:
        store.upsert_project(project)
        st.success(f"项目已保存：{project.name}")
    except Exception as exc:
        st.error(str(exc))

st.subheader("已有项目")
projects = store.list_projects()
if not projects:
    st.info("暂无项目。先创建一个 project，再导入任务或运行 workflow。")
else:
    for row in projects:
        payload = row["payload"]
        with st.expander(payload["name"], expanded=False):
            st.write(payload.get("description") or "无说明")
            st.json(
                {
                    "id": payload["id"],
                    "task_schema": payload["task_schema"],
                    "labels": payload.get("labels", []),
                    "created_at": payload.get("created_at"),
                }
            )
