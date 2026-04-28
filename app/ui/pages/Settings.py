from __future__ import annotations

import streamlit as st

from app.infrastructure.llm.providers import PLATFORM_CONFIGS
from app.runtime.paths import get_runtime_paths

st.title("Settings")
st.caption("本地运行目录、模型平台和部署约束。")

paths = get_runtime_paths().ensure()
st.subheader("Runtime")
st.json(
    {
        "root": str(paths.root),
        "data": str(paths.data),
        "logs": str(paths.logs),
        "artifacts": str(paths.artifacts),
        "exports": str(paths.exports),
        "indexes": str(paths.indexes),
        "database": str(paths.database),
    }
)

st.subheader("Model Platforms")
for platform_id, config in PLATFORM_CONFIGS.items():
    with st.expander(f"{config.name} ({platform_id})", expanded=False):
        st.json(
            {
                "base_url": config.base_url,
                "key_name": config.key_name,
                "default_model": config.default_model,
                "has_extra_body": bool(config.chat_extra_body),
            }
        )
