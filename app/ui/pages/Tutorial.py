from pathlib import Path

import streamlit as st


st.title("📘 使用教程")
st.markdown(
    """
<p style='color: var(--color-text); line-height: 1.6;'>
    本教程面向直接使用网站功能的用户，仅包含功能操作说明，不包含部署、运维和密钥配置。
</p>
""",
    unsafe_allow_html=True,
)

doc_path = Path("docs/user/TUTORIAL.md")
if not doc_path.exists():
    st.error("未找到用户教程文档：docs/user/TUTORIAL.md")
else:
    st.markdown(doc_path.read_text(encoding="utf-8"))
