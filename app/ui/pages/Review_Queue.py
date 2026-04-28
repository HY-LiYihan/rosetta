from __future__ import annotations

import json
from typing import Any

import streamlit as st

from app.runtime.store import RuntimeStore
from app.workflows.review import apply_review_decision, get_next_review_task, list_review_queue

st.title("审核队列")
st.caption("低置信、低自洽和抽检样本会逐条出现，优先用选择题完成专家审核。")

store = RuntimeStore()

st.subheader("筛选条件")
col1, col2, col3 = st.columns([1, 1, 2])
threshold = col1.slider("低于多少需要审核", 0.0, 1.0, 0.75, 0.01)
include_audit = col2.checkbox("包含高置信抽检", value=True)
jobs = store.list_jobs(limit=200)
job_options = ["全部批次"] + [row["id"] for row in jobs]
selected_job = col3.selectbox("批次", job_options)
job_id = None if selected_job == "全部批次" else selected_job

queue = list_review_queue(store, threshold=threshold, include_audit=include_audit, job_id=job_id, limit=200)
st.metric("当前待审核", len(queue))

card = get_next_review_task(store, threshold=threshold, include_audit=include_audit, job_id=job_id)
if card is None:
    st.success("当前没有符合条件的待审核样本。")
    st.stop()

review = card["review"]
task = card["task"]
predictions = card["predictions"]
guideline = card["guideline"]
gold_examples = card["gold_examples"]

if task is None:
    st.error("该审核任务关联的原文不存在。")
    st.stop()

st.divider()
meta = review.get("meta", {})
score_cols = st.columns(4)
score_cols[0].metric("综合置信度", meta.get("score", 0.0))
score_cols[1].metric("自洽性", meta.get("agreement", 0.0))
score_cols[2].metric("模型自评", meta.get("avg_confidence", 0.0))
score_cols[3].metric("路由原因", meta.get("route_reason", "低置信"))

st.subheader("原文")
st.write(task["text"])

if guideline:
    with st.expander("当前概念阐释", expanded=False):
        st.write(guideline.get("stable_description") or guideline.get("brief", ""))

if gold_examples:
    with st.expander("相似金样例参考", expanded=False):
        for example in gold_examples:
            st.markdown(f"**{example['id']}**")
            st.write(example["text"])
            if example.get("spans"):
                st.json(example["spans"], expanded=False)

st.subheader("候选")
option_labels = []
for option in review.get("options", []):
    option_labels.append(f"{option['id']}：{option['text']}")
if not option_labels:
    option_labels = ["manual：以上都不对，我要手动修正"]

selected_label = st.radio("请选择最正确的候选", option_labels, key=f"review_choice_{review['id']}")
selected_option_id = selected_label.split("：", 1)[0]

candidate_preview: list[dict[str, Any]] = []
if selected_option_id != "manual":
    index = ord(selected_option_id.upper()) - ord("A")
    if 0 <= index < len(predictions):
        candidate_preview = predictions[index].get("spans", [])

manual_default = json.dumps(candidate_preview, ensure_ascii=False, indent=2)
manual_spans_text = st.text_area(
    "需要微调时，在这里编辑 span 列表",
    value=manual_default,
    height=180,
    help='格式示例：[{"start":0,"end":12,"text":"heart failure","label":"Term"}]',
)
note = st.text_area("审核备注", height=80)
hard_example = st.checkbox("标记为疑难样例", value=False)

button_cols = st.columns(4)
accept_clicked = button_cols[0].button(
    "保存选择",
    type="primary",
    use_container_width=True,
    disabled=selected_option_id == "manual",
)
manual_clicked = button_cols[1].button("保存手动修正", use_container_width=True)
reject_clicked = button_cols[2].button("全部不对", use_container_width=True)
skip_clicked = button_cols[3].button("跳过", use_container_width=True)

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
        st.success("已保存审核结果。")
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
        st.success("已保存手动修正。")
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
        st.warning("已记录为全部不对。")
        st.rerun()
    if skip_clicked:
        apply_review_decision(store, review_id=review["id"], decision="skip", note=note)
        st.info("已跳过该样本。")
        st.rerun()
except Exception as exc:
    st.error(f"保存失败：{exc}")

with st.expander("调试信息", expanded=False):
    st.json({"review": review, "task": task, "predictions": predictions}, expanded=False)
