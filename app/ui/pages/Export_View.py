from __future__ import annotations

import json
from collections import Counter
from typing import Any

import streamlit as st

from app.data.exporters import build_dataset_stats, build_markdown_report, filter_tasks_for_export, rows_to_jsonl
from app.runtime.store import RuntimeStore
from app.ui.i18n import t

st.title(t("export_view.title"))
st.caption(t("export_view.caption"))

store = RuntimeStore()
tasks = store.list_tasks(limit=50000)
predictions = store.list_predictions(limit=50000)
reviews = store.list_reviews(limit=50000)
jobs = store.list_jobs(limit=50000)
stats = build_dataset_stats(tasks, predictions, reviews, jobs)


def _chart_rows(counter: Counter[str]) -> list[dict[str, Any]]:
    return [{t("common.category"): key, t("common.count"): value} for key, value in counter.items()]


category_key = t("common.category")
count_key = t("common.count")

st.subheader(t("export_view.overview"))
cols = st.columns(5)
cols[0].metric(t("export_view.task_count"), stats["task_count"])
cols[1].metric(t("export_view.auto_rate"), f"{stats['auto_accept_rate']:.0%}")
cols[2].metric(t("export_view.review_rate"), f"{stats['review_rate']:.0%}")
cols[3].metric(t("common.pending_review"), stats["pending_review_count"])
cols[4].metric(t("export_view.avg_span_length"), stats["avg_span_length"])

st.divider()
st.subheader(t("export_view.filters"))
project_ids = sorted({row.get("project_id") or "__unassigned__" for row in tasks})
project_options = ["__all__", *project_ids]
selected_project = st.selectbox(
    t("common.project"),
    project_options,
    format_func=lambda option: t("common.all_projects")
    if option == "__all__"
    else t("common.unassigned")
    if option == "__unassigned__"
    else option,
)
score_min, score_max = st.slider(t("export_view.confidence_range"), 0.0, 1.0, (0.0, 1.0), 0.01)

filtered_tasks = []
for row in tasks:
    payload = row["payload"]
    row_project = row.get("project_id") or "__unassigned__"
    if selected_project != "__all__" and row_project != selected_project:
        continue
    score = float(payload.get("meta", {}).get("score", 0.0))
    if score_min <= score <= score_max:
        filtered_tasks.append(row)

st.write(t("export_view.filtered_count", count=len(filtered_tasks)))

st.divider()
st.subheader(t("export_view.visualization"))
left, right = st.columns(2)
with left:
    route_counter = Counter(row["payload"].get("meta", {}).get("route", t("common.unassigned")) for row in filtered_tasks)
    st.markdown(f"**{t('export_view.route_distribution')}**")
    if route_counter:
        st.bar_chart(_chart_rows(route_counter), x=category_key, y=count_key)
    else:
        st.info(t("export_view.no_visual"))
with right:
    label_counter: Counter[str] = Counter()
    for row in filtered_tasks:
        for span in row["payload"].get("spans", []):
            label_counter[span.get("label", t("common.unassigned"))] += 1
    st.markdown(f"**{t('export_view.label_distribution')}**")
    if label_counter:
        st.bar_chart(_chart_rows(label_counter), x=category_key, y=count_key)
    else:
        st.info(t("export_view.no_labels"))

agreement_values = [
    float(row["payload"].get("meta", {}).get("agreement", 0.0))
    for row in filtered_tasks
    if "agreement" in row["payload"].get("meta", {})
]
if agreement_values:
    st.markdown(f"**{t('export_view.agreement_distribution')}**")
    bucket_counter = Counter(f"{int(value * 10) / 10:.1f}" for value in agreement_values)
    st.bar_chart(_chart_rows(bucket_counter), x=category_key, y=count_key)

st.divider()
st.subheader(t("export_view.export"))
export_labels = {
    "all": t("export_view.export_all"),
    "confirmed": t("export_view.export_confirmed"),
    "auto": t("export_view.export_auto"),
    "reviewed": t("export_view.export_reviewed"),
    "hard": t("export_view.export_hard"),
    "low_confidence": t("export_view.export_low"),
}
export_kind = st.selectbox(t("export_view.export_scope"), list(export_labels.keys()), format_func=lambda key: export_labels[key])
export_rows = filter_tasks_for_export(filtered_tasks, export_kind)
jsonl = rows_to_jsonl(export_rows)
report = build_markdown_report(build_dataset_stats(filtered_tasks, predictions, reviews, jobs))

download_cols = st.columns(3)
download_cols[0].download_button(
    t("export_view.download_jsonl"),
    data=jsonl,
    file_name="annotations.jsonl",
    mime="application/jsonl",
    use_container_width=True,
)
download_cols[1].download_button(
    t("export_view.download_report"),
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
    t("export_view.download_manifest"),
    data=json.dumps(manifest, ensure_ascii=False, indent=2),
    file_name="manifest.json",
    mime="application/json",
    use_container_width=True,
)

with st.expander(t("export_view.preview_jsonl"), expanded=False):
    st.code(jsonl[:6000], language="json")

st.divider()
st.subheader(t("export_view.concept_versions"))
versions = store.list_concept_versions(limit=100)
if versions:
    version_rows: list[dict[str, Any]] = []
    for row in versions:
        payload = row["payload"]
        version_rows.append(
            {
                t("export_view.version_concept"): payload["guideline_id"],
                t("export_view.version"): payload["version"],
                t("export_view.failed_examples"): len(payload.get("failed_task_ids", [])),
                t("export_view.unstable_examples"): len(payload.get("unstable_task_ids", [])),
                t("export_view.created_at"): payload.get("created_at", ""),
            }
        )
    st.dataframe(version_rows, use_container_width=True, hide_index=True)
else:
    st.info(t("export_view.no_versions"))
