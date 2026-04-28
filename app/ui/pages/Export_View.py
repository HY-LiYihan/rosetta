from __future__ import annotations

import json
from collections import Counter
from typing import Any

import streamlit as st

from app.data.exporters import build_dataset_stats, build_markdown_report, filter_tasks_for_export, rows_to_jsonl
from app.runtime.store import RuntimeStore

st.title("导出与可视化")
st.caption("导出确认后的 JSONL 数据，并查看自动通过、人工审核、标签分布和自洽性概况。")

store = RuntimeStore()
tasks = store.list_tasks(limit=50000)
predictions = store.list_predictions(limit=50000)
reviews = store.list_reviews(limit=50000)
jobs = store.list_jobs(limit=50000)
stats = build_dataset_stats(tasks, predictions, reviews, jobs)


def _chart_rows(counter: Counter[str]) -> list[dict[str, Any]]:
    return [{"类别": key, "数量": value} for key, value in counter.items()]

st.subheader("总览")
cols = st.columns(5)
cols[0].metric("任务总数", stats["task_count"])
cols[1].metric("自动通过率", f"{stats['auto_accept_rate']:.0%}")
cols[2].metric("人工审核率", f"{stats['review_rate']:.0%}")
cols[3].metric("待审核", stats["pending_review_count"])
cols[4].metric("平均片段长度", stats["avg_span_length"])

st.divider()
st.subheader("筛选")
project_options = ["全部项目"] + sorted({row.get("project_id") or "未归属" for row in tasks})
selected_project = st.selectbox("项目", project_options)
score_min, score_max = st.slider("置信度区间", 0.0, 1.0, (0.0, 1.0), 0.01)

filtered_tasks = []
for row in tasks:
    payload = row["payload"]
    if selected_project != "全部项目" and (row.get("project_id") or "未归属") != selected_project:
        continue
    score = float(payload.get("meta", {}).get("score", 0.0))
    if score_min <= score <= score_max:
        filtered_tasks.append(row)

st.write(f"当前筛选后共有 {len(filtered_tasks)} 条任务。")

st.divider()
st.subheader("可视化")
left, right = st.columns(2)
with left:
    route_counter = Counter(row["payload"].get("meta", {}).get("route", "未路由") for row in filtered_tasks)
    st.markdown("**路由分布**")
    if route_counter:
        st.bar_chart(_chart_rows(route_counter), x="类别", y="数量")
    else:
        st.info("暂无可视化数据。")
with right:
    label_counter: Counter[str] = Counter()
    for row in filtered_tasks:
        for span in row["payload"].get("spans", []):
            label_counter[span.get("label", "未知")] += 1
    st.markdown("**标签分布**")
    if label_counter:
        st.bar_chart(_chart_rows(label_counter), x="类别", y="数量")
    else:
        st.info("暂无标签数据。")

agreement_values = [
    float(row["payload"].get("meta", {}).get("agreement", 0.0))
    for row in filtered_tasks
    if "agreement" in row["payload"].get("meta", {})
]
if agreement_values:
    st.markdown("**候选一致性分布**")
    bucket_counter = Counter(f"{int(value * 10) / 10:.1f}" for value in agreement_values)
    st.bar_chart(_chart_rows(bucket_counter), x="类别", y="数量")

st.divider()
st.subheader("导出")
export_labels = {
    "all": "全部样本",
    "confirmed": "全部已确认样本",
    "auto": "自动通过样本",
    "reviewed": "人工审核样本",
    "hard": "疑难样例",
    "low_confidence": "低置信样本",
}
export_kind = st.selectbox("导出范围", list(export_labels.keys()), format_func=lambda key: export_labels[key])
export_rows = filter_tasks_for_export(filtered_tasks, export_kind)
jsonl = rows_to_jsonl(export_rows)
report = build_markdown_report(build_dataset_stats(filtered_tasks, predictions, reviews, jobs))

download_cols = st.columns(3)
download_cols[0].download_button(
    "下载 JSONL",
    data=jsonl,
    file_name="annotations.jsonl",
    mime="application/jsonl",
    use_container_width=True,
)
download_cols[1].download_button(
    "下载报告",
    data=report,
    file_name="report.md",
    mime="text/markdown",
    use_container_width=True,
)
manifest = {
    "export_kind": export_kind,
    "task_count": len(export_rows),
    "stats": stats,
}
download_cols[2].download_button(
    "下载运行清单",
    data=json.dumps(manifest, ensure_ascii=False, indent=2),
    file_name="manifest.json",
    mime="application/json",
    use_container_width=True,
)

with st.expander("预览 JSONL", expanded=False):
    st.code(jsonl[:6000], language="json")

st.divider()
st.subheader("概念版本")
versions = store.list_concept_versions(limit=100)
if versions:
    version_rows: list[dict[str, Any]] = []
    for row in versions:
        payload = row["payload"]
        version_rows.append(
            {
                "概念": payload["guideline_id"],
                "版本": payload["version"],
                "失败样例数": len(payload.get("failed_task_ids", [])),
                "边界不稳定数": len(payload.get("unstable_task_ids", [])),
                "创建时间": payload.get("created_at", ""),
            }
        )
    st.dataframe(version_rows, use_container_width=True, hide_index=True)
else:
    st.info("暂无概念修订记录。")
