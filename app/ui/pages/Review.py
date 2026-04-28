from __future__ import annotations

import streamlit as st

from app.runtime.store import RuntimeStore

st.title("Review")
st.caption("集中处理低置信、多候选和冲突样本。优先做选择题式复核，减少开放式人工标注成本。")

store = RuntimeStore()
reviews = store.list_reviews()

if not reviews:
    st.info("暂无本地 review task。运行 bootstrap 或 batch annotation 并开启 runtime 记录后会出现在这里。")
else:
    for row in reviews:
        payload = row["payload"]
        with st.expander(f"{payload['id']} · {payload['status']}", expanded=False):
            st.write(payload["question"])
            if payload.get("options"):
                st.radio(
                    "候选",
                    [f"{option['id']}: {option['text']}" for option in payload["options"]],
                    key=f"review_{payload['id']}",
                )
            st.json(payload)
