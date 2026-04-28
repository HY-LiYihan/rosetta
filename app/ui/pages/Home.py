from __future__ import annotations

import streamlit as st

from app.data.exporters import build_dataset_stats
from app.runtime.paths import get_runtime_paths
from app.runtime.store import RuntimeStore

st.title("工作台")
st.caption("从概念阐释、批量标注、人工审核到导出结果的本地工作入口。")

store = RuntimeStore()
paths = get_runtime_paths().ensure()

tasks = store.list_tasks(limit=10000)
predictions = store.list_predictions(limit=10000)
reviews = store.list_reviews(limit=10000)
jobs = store.list_jobs(limit=10000)
guidelines = store.list_guidelines(limit=1000)
stats = build_dataset_stats(tasks, predictions, reviews, jobs)

col1, col2, col3, col4 = st.columns(4)
col1.metric("待标注语料", stats["task_count"])
col2.metric("候选标注", stats["prediction_count"])
col3.metric("待审核", stats["pending_review_count"])
col4.metric("批量任务", stats["job_count"])

st.divider()

st.subheader("主流程")
flow_cols = st.columns(4)
with flow_cols[0]:
    st.markdown("**1. 概念实验室**")
    st.write("写清楚概念阐释，维护 15 条金样例。")
    if st.button("进入概念实验室", use_container_width=True):
        st.switch_page("app/ui/pages/Concept_Lab.py")
with flow_cols[1]:
    st.markdown("**2. 批量标注**")
    st.write("上传文本，切分为任务，提交本地队列。")
    if st.button("进入批量标注", use_container_width=True):
        st.switch_page("app/ui/pages/Batch_Run.py")
with flow_cols[2]:
    st.markdown("**3. 审核队列**")
    st.write("按置信度阈值逐条确认低置信样本。")
    if st.button("进入审核队列", use_container_width=True):
        st.switch_page("app/ui/pages/Review_Queue.py")
with flow_cols[3]:
    st.markdown("**4. 导出与可视化**")
    st.write("查看统计，并导出 JSONL 与报告。")
    if st.button("进入导出页面", use_container_width=True):
        st.switch_page("app/ui/pages/Export_View.py")

st.divider()

left, right = st.columns([1, 1])
with left:
    st.subheader("最近批量任务")
    if jobs:
        for row in jobs[:5]:
            payload = row["payload"]
            st.markdown(
                f"- `{payload['id']}`：{payload['status']}，"
                f"{payload.get('completed_items', 0)}/{payload.get('total_items', 0)} 已完成，"
                f"{payload.get('review_items', 0)} 条待审核"
            )
    else:
        st.info("还没有批量任务。先进入“批量标注”上传一小段文本即可创建。")

with right:
    st.subheader("最近概念")
    if guidelines:
        for row in guidelines[:5]:
            payload = row["payload"]
            label_text = "、".join(payload.get("labels", [])[:4]) or "未设置标签"
            st.markdown(f"- **{payload['name']}**：{payload.get('status', 'draft')}，{label_text}")
    else:
        st.info("还没有概念阐释。先进入“概念实验室”创建一个概念。")

st.divider()

st.subheader("本地运行目录")
st.code(str(paths.root), language="text")
st.caption("SQLite、导出文件、运行日志和临时产物都会写入本地运行目录。")

st.divider()
st.markdown(
    """
<div style='text-align: center; color: var(--color-text); font-size: 0.9rem; margin-top: 2rem;'>
    <p><strong>Rosetta 本地优先标注工具</strong></p>
    <p>版本: v4.1.0 | 最后更新: 2026年4月29日</p>
    <p>项目地址: <a href='https://github.com/HY-LiYihan/rosetta' target='_blank'>GitHub</a></p>
</div>
""",
    unsafe_allow_html=True,
)
