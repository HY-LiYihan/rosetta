from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.core.models import ConceptGuideline, ConceptVersion, GoldExampleSet, Project, utc_timestamp
from app.core.serialization import to_plain_dict
from app.data.official_sample import (
    OFFICIAL_CONCEPT_VERSION_ID,
    OFFICIAL_GOLD_SET_ID,
    OFFICIAL_GUIDELINE_ID,
    OFFICIAL_LABEL,
    OFFICIAL_PROJECT_ID,
    OFFICIAL_SAMPLE_KEY,
    PROFESSIONAL_NER_EXAMPLE,
    professional_ner_description,
    professional_ner_gold_tasks,
)
from app.data.prodigy_jsonl import task_to_dict
from app.runtime.store import RuntimeStore

_PROCESS_SEEDED_DATABASES: set[str] = set()

_RUNTIME_TABLES = (
    "run_progress_events",
    "job_events",
    "job_items",
    "jobs",
    "artifacts",
    "agent_steps",
    "runs",
    "reviews",
    "predictions",
    "concept_versions",
    "gold_example_sets",
    "concept_guidelines",
    "tasks",
    "projects",
)


def should_reset_runtime_on_start() -> bool:
    value = os.getenv("ROSETTA_RESET_RUNTIME_ON_START", "true").strip().lower()
    return value not in {"0", "false", "no", "off"}


def ensure_official_sample_on_process_start(database_path: str | Path | None = None) -> dict[str, Any]:
    store = RuntimeStore(database_path)
    database_key = str(store.database_path.resolve())
    if database_key in _PROCESS_SEEDED_DATABASES:
        return {"status": "already_seeded", "database_path": database_key}
    if not should_reset_runtime_on_start():
        _PROCESS_SEEDED_DATABASES.add(database_key)
        return {"status": "disabled", "database_path": database_key}
    result = reset_runtime_to_official_sample(store)
    _PROCESS_SEEDED_DATABASES.add(database_key)
    return result | {"database_path": database_key}


def reset_runtime_to_official_sample(store: RuntimeStore) -> dict[str, Any]:
    now = utc_timestamp()
    description = professional_ner_description()
    tasks = professional_ner_gold_tasks()
    project = Project(
        id=OFFICIAL_PROJECT_ID,
        name=PROFESSIONAL_NER_EXAMPLE["project_name"],
        description=PROFESSIONAL_NER_EXAMPLE["project_description"],
        task_schema="span",
        labels=(OFFICIAL_LABEL,),
        metadata={
            "official_sample": True,
            "sample_key": OFFICIAL_SAMPLE_KEY,
            "reset_on_start": True,
        },
        created_at=now,
    )
    guideline = ConceptGuideline(
        id=OFFICIAL_GUIDELINE_ID,
        project_id=project.id,
        name=PROFESSIONAL_NER_EXAMPLE["concept_name"],
        brief=PROFESSIONAL_NER_EXAMPLE["brief"],
        labels=(OFFICIAL_LABEL,),
        boundary_rules=tuple(PROFESSIONAL_NER_EXAMPLE["boundary_rules"].splitlines()),
        negative_rules=tuple(PROFESSIONAL_NER_EXAMPLE["negative_rules"].splitlines()),
        output_format=PROFESSIONAL_NER_EXAMPLE["output_format"],
        stable_description=description,
        status="draft",
        metadata={
            "official_sample": True,
            "sample_key": OFFICIAL_SAMPLE_KEY,
            "operational_prompt_has_gold_terms": False,
        },
        created_at=now,
    )
    gold_set = GoldExampleSet(
        id=OFFICIAL_GOLD_SET_ID,
        project_id=project.id,
        guideline_id=guideline.id,
        task_ids=tuple(task.id for task in tasks),
        target_count=15,
        status="validating",
        metadata={
            "official_sample": True,
            "sample_key": OFFICIAL_SAMPLE_KEY,
            "label_policy": OFFICIAL_LABEL,
        },
        created_at=now,
    )
    version = ConceptVersion(
        id=OFFICIAL_CONCEPT_VERSION_ID,
        guideline_id=guideline.id,
        version=1,
        description=description,
        notes="官方样例初始提示词。",
        metadata={
            "official_sample": True,
            "sample_key": OFFICIAL_SAMPLE_KEY,
            "revision_source": "official_seed",
            "operational_prompt_has_gold_terms": False,
        },
        created_at=now,
    )

    with store.connect() as conn:
        for table in _RUNTIME_TABLES:
            conn.execute(f"DELETE FROM {table}")
        conn.execute(
            "INSERT INTO projects (id, payload, created_at) VALUES (?, ?, ?)",
            (project.id, _dumps(project), project.created_at),
        )
        conn.execute(
            "INSERT INTO concept_guidelines (id, project_id, payload, created_at) VALUES (?, ?, ?, ?)",
            (guideline.id, guideline.project_id, _dumps(guideline), guideline.created_at),
        )
        for task in tasks:
            conn.execute(
                "INSERT INTO tasks (id, project_id, payload) VALUES (?, ?, ?)",
                (task.id, project.id, json.dumps(task_to_dict(task), ensure_ascii=False)),
            )
        conn.execute(
            "INSERT INTO gold_example_sets (id, project_id, guideline_id, payload, created_at) VALUES (?, ?, ?, ?, ?)",
            (gold_set.id, gold_set.project_id, gold_set.guideline_id, _dumps(gold_set), gold_set.created_at),
        )
        conn.execute(
            "INSERT INTO concept_versions (id, guideline_id, payload, created_at) VALUES (?, ?, ?, ?)",
            (version.id, version.guideline_id, _dumps(version), version.created_at),
        )

    return {
        "status": "seeded",
        "sample_key": OFFICIAL_SAMPLE_KEY,
        "project_id": project.id,
        "guideline_id": guideline.id,
        "gold_count": len(tasks),
        "cleared_tables": list(_RUNTIME_TABLES),
    }


def _dumps(value: Any) -> str:
    return json.dumps(to_plain_dict(value), ensure_ascii=False)
