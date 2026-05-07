from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from app.infrastructure.debug import list_debug_log_files, read_debug_events

st.title("调试追踪")
st.caption("像日志流一样实时查看 debug 模式下 Rosetta 与 LLM 之间的 prompt / response 对话。")
st.warning(
    "Debug 日志会完整保存提示词、模型回复和部分运行上下文，可能包含语料、金样例或 API 调试信息。"
    "仅建议在本机排障时开启。"
)

st.info("该页面不会出现在主导航中；需要时直接访问 `http://localhost:8501/debug`。")


def _event_matches(event: dict[str, Any], event_type_filter: str, search_text: str) -> bool:
    event_type = str(event.get("event", ""))
    if event_type_filter != "all" and event_type != event_type_filter:
        return False
    blob = json.dumps(event, ensure_ascii=False)
    return not search_text or search_text.lower() in blob.lower()


def _render_event(index: int, event: dict[str, Any]) -> None:
    event_type = str(event.get("event", ""))
    payload = event.get("payload", {})
    timestamp = event.get("timestamp", "")
    title = f"[{index}] {timestamp} · {event_type}"
    with st.container(border=True):
        st.markdown(f"**{title}**")
        left, right = st.columns([1, 1])
        with left:
            st.write("**事件摘要**")
            st.json({"timestamp": timestamp, "event": event_type, "payload_keys": list(payload.keys())})
        with right:
            st.write("**原始记录**")
            st.json(event)
        if event_type == "llm_chat":
            st.write("**子对话窗**")
            messages = list(payload.get("messages", []))
            for message in messages:
                role = str(message.get("role", "user"))
                content = str(message.get("content", ""))
                if role == "system":
                    with st.container(border=True):
                        st.markdown("**system prompt**")
                        st.code(content, language="markdown")
                    continue
                with st.chat_message(role if role in {"user", "assistant"} else "assistant"):
                    st.code(content, language="markdown")
            with st.chat_message("assistant"):
                st.code(str(payload.get("response", "")) or "[empty response]", language="markdown")
            meta_cols = st.columns(5)
            meta_cols[0].metric("provider", payload.get("provider", ""))
            meta_cols[1].metric("model", payload.get("model", ""))
            meta_cols[2].metric("temperature", payload.get("temperature", ""))
            meta_cols[3].metric("elapsed", payload.get("elapsed_seconds", ""))
            meta_cols[4].metric("response source", payload.get("metadata", {}).get("response_source", "content"))
        else:
            st.write("**Payload**")
            st.json(payload)


@st.fragment(run_every="2s")
def _render_live_log() -> None:
    log_files = list_debug_log_files()
    if not log_files:
        st.info("还没有调试日志。请先用 debug 模式启动程序并触发一次大模型调用。")
        return

    latest_file = log_files[0]
    options = ["最新日志", *[Path(path).name for path in log_files]]
    selected_label = st.selectbox("调试日志文件", options, index=0)
    selected_log = latest_file
    if selected_label != "最新日志":
        selected_log = next((path for path in log_files if Path(path).name == selected_label), latest_file)

    events = read_debug_events(selected_log, limit=2000)
    llm_events = [event for event in events if event.get("event") == "llm_chat"]

    top_cols = st.columns(5)
    top_cols[0].metric("日志文件", len(log_files))
    top_cols[1].metric("事件总数", len(events))
    top_cols[2].metric("LLM 对话", len(llm_events))
    top_cols[3].metric("当前文件", Path(selected_log).name)
    top_cols[4].metric("刷新", "2s")

    event_types = sorted({str(event.get("event", "")) for event in events if event.get("event")})
    event_type_options = ["all", *event_types]
    default_event_index = event_type_options.index("llm_chat") if "llm_chat" in event_type_options else 0
    event_type_filter = st.selectbox("事件类型", event_type_options, index=default_event_index)
    search_text = st.text_input("搜索 prompt / response")
    max_events = st.slider("最多显示事件数", min_value=10, max_value=200, value=50, step=10)

    filtered = [event for event in events if _event_matches(event, event_type_filter, search_text)]
    visible_events = list(reversed(filtered))[:max_events]
    st.caption(f"当前显示 {len(visible_events)} / {len(filtered)} 条匹配事件，页面每 2 秒自动刷新。")

    for index, event in enumerate(visible_events, start=1):
        _render_event(index, event)


_render_live_log()
