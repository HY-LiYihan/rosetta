#!/usr/bin/env python3
"""One-shot migration: convert assets/concepts.json annotation strings to AnnotationDoc (v3.0)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.domain.annotation_doc import make_annotation_doc


def migrate(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    changed = 0
    for concept in payload.get("concepts", []):
        for example in concept.get("examples", []):
            ann = example.get("annotation")
            if isinstance(ann, str):
                example["annotation"] = make_annotation_doc(example["text"], ann)
                changed += 1
    payload["version"] = "3.0"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Migrated {changed} examples → {path}")


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "assets" / "concepts.json"
    migrate(target)
