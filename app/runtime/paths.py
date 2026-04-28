from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimePaths:
    root: Path
    data: Path
    logs: Path
    artifacts: Path
    exports: Path
    indexes: Path
    database: Path

    def ensure(self) -> "RuntimePaths":
        for path in [self.root, self.data, self.logs, self.artifacts, self.exports, self.indexes]:
            path.mkdir(parents=True, exist_ok=True)
        return self


def get_runtime_paths(root: str | Path | None = None) -> RuntimePaths:
    runtime_root = Path(root or os.getenv("ROSETTA_RUNTIME_DIR", ".runtime")).expanduser()
    return RuntimePaths(
        root=runtime_root,
        data=Path(os.getenv("ROSETTA_DATA_DIR", runtime_root / "data")),
        logs=Path(os.getenv("ROSETTA_LOG_DIR", runtime_root / "logs")),
        artifacts=runtime_root / "artifacts",
        exports=runtime_root / "exports",
        indexes=runtime_root / "indexes",
        database=runtime_root / "rosetta.sqlite3",
    )
