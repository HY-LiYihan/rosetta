from __future__ import annotations

import json

import streamlit as st

from app.runtime.store import RuntimeStore

st.title("Export")
st.caption("导出 Rosetta 的 Prodigy-compatible JSONL。")

store = RuntimeStore()
tasks = store.list_tasks(limit=10000)

if not tasks:
    st.info("本地 runtime store 中暂无任务。当前旧页面的 session 数据仍按兼容路径运行。")
else:
    jsonl = "\n".join(json.dumps(row["payload"], ensure_ascii=False) for row in tasks) + "\n"
    st.download_button(
        "下载 tasks.jsonl",
        data=jsonl,
        file_name="rosetta_tasks.jsonl",
        mime="application/jsonl",
        use_container_width=True,
    )
    st.code(jsonl[:4000], language="json")
