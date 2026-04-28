from __future__ import annotations

import json
from typing import Any

import streamlit as st

from app.runtime.store import RuntimeStore
from app.ui.i18n import t
from app.workflows.review import apply_review_decision, get_next_review_task, list_review_queue

st.title(t("review_queue.title"))
st.caption(t("review_queue.caption"))

store = RuntimeStore()

st.subheader(t("review_queue.filters"))
col1, col2, col3 = st.columns([1, 1, 2])
threshold = col1.slider(t("review_queue.threshold"), 0.0, 1.0, 0.75, 0.01)
include_audit = col2.checkbox(t("review_queue.include_audit"), value=True)
jobs = store.list_jobs(limit=200)
job_options = ["__all__", *[row["id"] for row in jobs]]
selected_job = col3.selectbox(
    t("review_queue.batch"),
    job_options,
    format_func=lambda option: t("review_queue.all_batches") if option == "__all__" else option,
)
job_id = None if selected_job == "__all__" else selected_job

queue = list_review_queue(store, threshold=threshold, include_audit=include_audit, job_id=job_id, limit=200)
st.metric(t("review_queue.current_pending"), len(queue))

card = get_next_review_task(store, threshold=threshold, include_audit=include_audit, job_id=job_id)
if card is None:
    st.success(t("review_queue.empty"))
    st.stop()

review = card["review"]
task = card["task"]
predictions = card["predictions"]
guideline = card["guideline"]
gold_examples = card["gold_examples"]

if task is None:
    st.error(t("review_queue.missing_task"))
    st.stop()

st.divider()
meta = review.get("meta", {})
score_cols = st.columns(4)
score_cols[0].metric(t("review_queue.score"), meta.get("score", 0.0))
score_cols[1].metric(t("review_queue.agreement"), meta.get("agreement", 0.0))
score_cols[2].metric(t("review_queue.model_confidence"), meta.get("avg_confidence", 0.0))
score_cols[3].metric(t("review_queue.route_reason"), meta.get("route_reason", t("review_queue.low_confidence")))

st.subheader(t("review_queue.source_text"))
st.write(task["text"])

if guideline:
    with st.expander(t("review_queue.guideline"), expanded=False):
        st.write(guideline.get("stable_description") or guideline.get("brief", ""))

if gold_examples:
    with st.expander(t("review_queue.gold_reference"), expanded=False):
        for example in gold_examples:
            st.markdown(f"**{example['id']}**")
            st.write(example["text"])
            if example.get("spans"):
                st.json(example["spans"], expanded=False)

st.subheader(t("review_queue.candidates"))
option_map: dict[str, str] = {}
for option in review.get("options", []):
    option_text = t("review_queue.manual_option") if option["id"] == "manual" else option["text"]
    option_map[option["id"]] = option_text
if not option_map:
    option_map["manual"] = t("review_queue.manual_option")

selected_option_id = st.radio(
    t("review_queue.choose"),
    list(option_map.keys()),
    key=f"review_choice_{review['id']}",
    format_func=lambda option_id: f"{option_id}: {option_map[option_id]}",
)

candidate_preview: list[dict[str, Any]] = []
if selected_option_id != "manual":
    index = ord(selected_option_id.upper()) - ord("A")
    if 0 <= index < len(predictions):
        candidate_preview = predictions[index].get("spans", [])

manual_default = json.dumps(candidate_preview, ensure_ascii=False, indent=2)
manual_spans_text = st.text_area(
    t("review_queue.edit_spans"),
    value=manual_default,
    height=180,
    help=t("review_queue.edit_help"),
)
note = st.text_area(t("review_queue.note"), height=80)
hard_example = st.checkbox(t("review_queue.hard"), value=False)

button_cols = st.columns(4)
accept_clicked = button_cols[0].button(
    t("review_queue.accept"),
    type="primary",
    use_container_width=True,
    disabled=selected_option_id == "manual",
)
manual_clicked = button_cols[1].button(t("review_queue.save_manual"), use_container_width=True)
reject_clicked = button_cols[2].button(t("review_queue.reject"), use_container_width=True)
skip_clicked = button_cols[3].button(t("review_queue.skip"), use_container_width=True)

try:
    if accept_clicked:
        apply_review_decision(
            store,
            review_id=review["id"],
            decision="accept",
            selected_option_id=selected_option_id,
            note=note,
            hard_example=hard_example,
        )
        st.success(t("review_queue.accepted"))
        st.rerun()
    if manual_clicked:
        manual_spans = json.loads(manual_spans_text) if manual_spans_text.strip() else []
        apply_review_decision(
            store,
            review_id=review["id"],
            decision="manual",
            selected_option_id="manual",
            manual_spans=manual_spans,
            note=note,
            hard_example=hard_example,
        )
        st.success(t("review_queue.manual_saved"))
        st.rerun()
    if reject_clicked:
        apply_review_decision(
            store,
            review_id=review["id"],
            decision="reject",
            selected_option_id="reject",
            note=note,
            hard_example=True,
        )
        st.warning(t("review_queue.rejected"))
        st.rerun()
    if skip_clicked:
        apply_review_decision(store, review_id=review["id"], decision="skip", note=note)
        st.info(t("review_queue.skipped"))
        st.rerun()
except Exception as exc:
    st.error(t("review_queue.save_failed", error=exc))

with st.expander(t("review_queue.debug"), expanded=False):
    st.json({"review": review, "task": task, "predictions": predictions}, expanded=False)
