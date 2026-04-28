from __future__ import annotations

from typing import Any

import streamlit as st

_BUSY_SUFFIX = "__rosetta_busy"


def busy_state_key(key: str) -> str:
    return f"{key}{_BUSY_SUFFIX}"


def is_busy(key: str) -> bool:
    return bool(st.session_state.get(busy_state_key(key), False))


def any_busy(keys: list[str] | tuple[str, ...]) -> bool:
    return any(is_busy(key) for key in keys)


def clear_busy(key: str) -> None:
    st.session_state.pop(busy_state_key(key), None)


def busy_button(
    label: str,
    *,
    key: str,
    pending_label: str,
    container: Any | None = None,
    disabled: bool = False,
    type: str = "secondary",
    use_container_width: bool = False,
    help: str | None = None,
) -> bool:
    """Render a button that disables itself before the long action runs.

    Streamlit cannot mutate a button after it has already been drawn in the
    same script pass. This helper therefore uses a two-pass flow: first click
    records a busy flag and reruns; the next pass renders a disabled pending
    button, then the page code performs the expensive action.
    """

    host = container or st
    busy = is_busy(key)
    clicked = host.button(
        pending_label if busy else label,
        key=key,
        type=type,
        disabled=disabled or busy,
        use_container_width=use_container_width,
        help=help,
    )
    if busy:
        return True
    if clicked:
        st.session_state[busy_state_key(key)] = True
        st.rerun()
    return False
