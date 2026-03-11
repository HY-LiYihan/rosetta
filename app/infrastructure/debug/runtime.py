from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

_STATE = {
    "enabled": False,
    "runtime_dir": Path(".runtime"),
    "log_file": None,
}


def _safe_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in {"-", "_", "."} else "_" for c in name)


def configure_debug(enabled: bool, runtime_dir: str | None = None) -> None:
    _STATE["enabled"] = bool(enabled)
    if not _STATE["enabled"]:
        return

    base_dir = Path(runtime_dir or os.environ.get("ROSETTA_DEBUG_RUNTIME_DIR", ".runtime"))
    logs_dir = base_dir / "logs" / "debug"
    uploads_dir = base_dir / "data" / "debug_uploads"
    logs_dir.mkdir(parents=True, exist_ok=True)
    uploads_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"session_{now}_{os.getpid()}.jsonl"
    _STATE["runtime_dir"] = base_dir
    _STATE["log_file"] = log_file

    log_debug_event("debug_mode_enabled", {"runtime_dir": str(base_dir)})


def is_debug_mode() -> bool:
    return bool(_STATE["enabled"])


def get_runtime_dir() -> Path:
    return _STATE["runtime_dir"]


def log_debug_event(event: str, payload: dict | None = None) -> None:
    if not _STATE["enabled"] or _STATE["log_file"] is None:
        return
    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "event": event,
        "payload": payload or {},
    }
    with Path(_STATE["log_file"]).open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def persist_debug_upload(filename: str, content: str) -> str | None:
    if not _STATE["enabled"]:
        return None
    uploads_dir = get_runtime_dir() / "data" / "debug_uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = _safe_name(filename or "upload.json")
    output = uploads_dir / f"{now}_{safe_filename}"
    output.write_text(content, encoding="utf-8")
    log_debug_event("debug_upload_persisted", {"path": str(output), "bytes": len(content.encode('utf-8'))})
    return str(output)
