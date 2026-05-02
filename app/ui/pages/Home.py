from __future__ import annotations

import streamlit as st

from app.data.exporters import build_dataset_stats
from app.runtime.paths import get_runtime_paths
from app.runtime.store import RuntimeStore
from app.ui.i18n import t

VERSION = "v4.2.2"
UPDATED_AT = "2026-05-01"

st.title(t("home.title"))
st.caption(t("home.caption"))

store = RuntimeStore()
paths = get_runtime_paths().ensure()

tasks = store.list_tasks(limit=10000)
predictions = store.list_predictions(limit=10000)
reviews = store.list_reviews(limit=10000)
jobs = store.list_jobs(limit=10000)
guidelines = store.list_guidelines(limit=1000)
stats = build_dataset_stats(tasks, predictions, reviews, jobs)
pending_reviews = [row for row in reviews if row["payload"].get("status") == "pending"]

col1, col2, col3, col4 = st.columns(4)
col1.metric(t("home.metric_tasks"), stats["task_count"])
col2.metric(t("home.metric_predictions"), stats["prediction_count"])
col3.metric(t("home.metric_pending_reviews"), stats["pending_review_count"])
col4.metric(t("home.metric_jobs"), stats["job_count"])

st.divider()

if not guidelines:
    next_label = t("home.next_concept")
    next_page = "app/ui/pages/Concept_Lab.py"
elif pending_reviews:
    next_label = t("home.next_review")
    next_page = "app/ui/pages/Review_Queue.py"
elif not jobs:
    next_label = t("home.next_batch")
    next_page = "app/ui/pages/Batch_Run.py"
else:
    next_label = t("home.next_export")
    next_page = "app/ui/pages/Export_View.py"

st.subheader(t("home.next_title"))
if st.button(next_label, type="primary", use_container_width=True):
    st.switch_page(next_page)

st.divider()

left, right = st.columns([1, 1])
with left:
    st.subheader(t("home.recent_jobs"))
    if jobs:
        for row in jobs[:3]:
            payload = row["payload"]
            st.markdown(
                f"- `{payload['id']}`: {payload['status']}, "
                f"{payload.get('completed_items', 0)}/{payload.get('total_items', 0)}, "
                f"{payload.get('review_items', 0)} {t('common.pending_review')}"
            )
    else:
        st.info(t("home.no_jobs"))

with right:
    st.subheader(t("home.recent_reviews"))
    if reviews:
        for row in reviews[:3]:
            payload = row["payload"]
            score = payload.get("meta", {}).get("score", 0.0)
            st.markdown(f"- `{payload['id']}`: {payload.get('status', 'pending')}, {score}")
    else:
        st.info(t("home.no_reviews"))

with st.expander(t("home.flow_expander"), expanded=False):
    st.write(t("home.flow_text"))

with st.expander(t("home.runtime"), expanded=False):
    st.code(str(paths.root), language="text")
    st.caption(t("home.runtime_caption"))

st.divider()
st.markdown(
    f"""
<div style='text-align: center; color: var(--color-text); font-size: 0.9rem; margin-top: 2rem;'>
    <p><strong>{t("home.footer_name")}</strong></p>
    <p>{t("common.version_line", version=VERSION, date=UPDATED_AT)}</p>
    <p>{t("common.github")}: <a href='https://github.com/HY-LiYihan/rosetta' target='_blank'>GitHub</a></p>
</div>
""",
    unsafe_allow_html=True,
)
