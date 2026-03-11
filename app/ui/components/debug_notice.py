from __future__ import annotations

import time

import streamlit as st

from app.state.keys import DEBUG_NOTICE_ACK


def render_debug_notice(countdown_seconds: int = 5) -> None:
    if st.session_state.get(DEBUG_NOTICE_ACK):
        return

    with st.container(border=True):
        st.error("Debug Maintenance Mode / 调试维护模式")
        st.markdown(
            """
**中文说明**  
当前网站处于调试维护时段。此时段内，您上传和操作产生的数据将被留存，用于问题排查与程序调试。  
如需个人数据保护，请在 1-2 小时后再访问。

**English Notice**  
This website is currently in debug maintenance mode. During this period, uploaded data and operation traces will be retained for troubleshooting and debugging.  
If you need stronger personal data protection, please revisit in 1-2 hours.
"""
        )

        countdown_placeholder = st.empty()
        for remaining in range(countdown_seconds, 0, -1):
            countdown_placeholder.warning(
                f"请等待 {remaining} 秒后关闭 / Please wait {remaining}s before closing"
            )
            time.sleep(1)
        countdown_placeholder.success("可以关闭提示窗口 / You may now close this notice.")

        if st.button("我已知悉 / I Understand", type="primary", key="debug_notice_ack_btn"):
            st.session_state[DEBUG_NOTICE_ACK] = True
            st.rerun()
