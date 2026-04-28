from __future__ import annotations

import streamlit as st

st.title("Guideline Studio")
st.caption("用一句话概念描述和少量金样例，迭代出稳定的标注 guideline。")

st.markdown(
    """
当前版本先保留原有概念管理能力，并把它作为 Guideline Studio 的兼容入口。

后续 workflow 将把以下步骤收敛到本页：

1. 输入概念描述。
2. 导入 15 个左右金样例。
3. 让 agent 对金样例试标。
4. 抽出失败样例，改写 guideline。
5. 生成可复核的 review queue。
"""
)

if st.button("打开旧概念管理兼容页", use_container_width=True):
    st.switch_page("app/ui/pages/Concept_Management.py")
