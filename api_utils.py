"""
Compatibility shim.

Canonical module location is:
app.infrastructure.llm.api_utils
"""

from app.infrastructure.llm.api_utils import (  # noqa: F401
    PLATFORM_CONFIG,
    get_chat_response,
    get_client,
    probe_available_platforms,
)
