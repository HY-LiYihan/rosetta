from __future__ import annotations

import streamlit as st

from app.runtime.store import RuntimeStore

st.title("Runs")
st.caption("查看 workflow run、输出目录和 agent trace。")

limit = st.slider("显示数量", min_value=10, max_value=200, value=50, step=10)
store = RuntimeStore()
runs = store.list_runs(limit=limit)

if not runs:
    st.info("暂无记录。CLI 使用 `--record` 或后续页面 workflow 运行后会写入本地 SQLite store。")
else:
    for row in runs:
        payload = row["payload"]
        with st.expander(f"{payload['workflow']} · {payload['status']} · {payload['id']}", expanded=False):
            st.write(payload.get("summary", ""))
            st.json(payload)
