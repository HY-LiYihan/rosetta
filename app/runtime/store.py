from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.core.models import (
    AgentStep,
    AnnotationTask,
    BatchJob,
    BatchJobItem,
    ConceptGuideline,
    ConceptVersion,
    GoldExampleSet,
    Prediction,
    Project,
    ReviewTask,
    WorkflowRun,
)
from app.core.serialization import to_plain_dict
from app.data.prodigy_jsonl import prediction_to_dict, task_to_dict
from app.runtime.paths import get_runtime_paths


class RuntimeStore:
    def __init__(self, database_path: str | Path | None = None):
        if database_path is None:
            paths = get_runtime_paths().ensure()
            self.database_path = paths.database
        else:
            self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    payload TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS predictions (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reviews (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    workflow TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    started_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    path TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS agent_steps (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS concept_guidelines (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS gold_example_sets (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    guideline_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS concept_versions (
                    id TEXT PRIMARY KEY,
                    guideline_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    guideline_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS job_items (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS job_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def upsert_project(self, project: Project) -> None:
        project.validate()
        payload = _json(project)
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO projects (id, payload, created_at) VALUES (?, ?, ?)",
                (project.id, payload, project.created_at),
            )

    def list_projects(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT id, payload, created_at FROM projects ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) | {"payload": json.loads(row["payload"])} for row in rows]

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT id, payload, created_at FROM projects WHERE id = ?", (project_id,)).fetchone()
        return dict(row) | {"payload": json.loads(row["payload"])} if row else None

    def upsert_task(self, task: AnnotationTask, project_id: str | None = None) -> None:
        payload = json.dumps(task_to_dict(task), ensure_ascii=False)
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO tasks (id, project_id, payload) VALUES (?, ?, ?)",
                (task.id, project_id, payload),
            )

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT id, project_id, payload, created_at FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
        return dict(row) | {"payload": json.loads(row["payload"])} if row else None

    def list_tasks(self, limit: int = 100, project_id: str | None = None) -> list[dict[str, Any]]:
        with self.connect() as conn:
            if project_id:
                rows = conn.execute(
                    "SELECT id, project_id, payload, created_at FROM tasks WHERE project_id = ? ORDER BY created_at DESC LIMIT ?",
                    (project_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, project_id, payload, created_at FROM tasks ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [dict(row) | {"payload": json.loads(row["payload"])} for row in rows]

    def upsert_prediction(self, prediction: Prediction) -> None:
        payload = json.dumps(prediction_to_dict(prediction), ensure_ascii=False)
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO predictions (id, task_id, payload, created_at) VALUES (?, ?, ?, ?)",
                (prediction.id, prediction.task_id, payload, prediction.created_at),
            )

    def list_predictions(self, task_id: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
        with self.connect() as conn:
            if task_id:
                rows = conn.execute(
                    "SELECT id, task_id, payload, created_at FROM predictions WHERE task_id = ? ORDER BY created_at DESC LIMIT ?",
                    (task_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, task_id, payload, created_at FROM predictions ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [dict(row) | {"payload": json.loads(row["payload"])} for row in rows]

    def get_prediction(self, prediction_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT id, task_id, payload, created_at FROM predictions WHERE id = ?",
                (prediction_id,),
            ).fetchone()
        return dict(row) | {"payload": json.loads(row["payload"])} if row else None

    def upsert_review(self, review: ReviewTask) -> None:
        review.validate()
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO reviews (id, task_id, payload, created_at) VALUES (?, ?, ?, ?)",
                (review.id, review.task_id, _json(review), review.created_at),
            )

    def get_review(self, review_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT id, task_id, payload, created_at FROM reviews WHERE id = ?",
                (review_id,),
            ).fetchone()
        return dict(row) | {"payload": json.loads(row["payload"])} if row else None

    def list_reviews(
        self,
        limit: int = 100,
        status: str | None = None,
        max_score: float | None = None,
    ) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT id, task_id, payload, created_at FROM reviews ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        reviews = [dict(row) | {"payload": json.loads(row["payload"])} for row in rows]
        if status is not None:
            reviews = [row for row in reviews if row["payload"].get("status") == status]
        if max_score is not None:
            reviews = [row for row in reviews if float(row["payload"].get("meta", {}).get("score", 0.0)) <= max_score]
        return reviews

    def upsert_run(self, run: WorkflowRun) -> None:
        run.validate()
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO runs (id, workflow, status, payload, started_at) VALUES (?, ?, ?, ?, ?)",
                (run.id, run.workflow, run.status, _json(run), run.started_at),
            )

    def add_artifact(self, run_id: str, path: str | Path, kind: str, metadata: dict[str, Any] | None = None) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO artifacts (run_id, path, kind, metadata) VALUES (?, ?, ?, ?)",
                (run_id, str(path), kind, json.dumps(metadata or {}, ensure_ascii=False)),
            )

    def add_agent_step(self, step: AgentStep) -> None:
        step.validate()
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO agent_steps (id, run_id, payload, created_at) VALUES (?, ?, ?, ?)",
                (step.id, step.run_id, _json(step), step.created_at),
            )

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT id, workflow, status, payload, started_at FROM runs ORDER BY started_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) | {"payload": json.loads(row["payload"])} for row in rows]

    def upsert_guideline(self, guideline: ConceptGuideline) -> None:
        guideline.validate()
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO concept_guidelines (id, project_id, payload, created_at) VALUES (?, ?, ?, ?)",
                (guideline.id, guideline.project_id, _json(guideline), guideline.created_at),
            )

    def list_guidelines(self, project_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as conn:
            if project_id:
                rows = conn.execute(
                    "SELECT id, project_id, payload, created_at FROM concept_guidelines WHERE project_id = ? ORDER BY created_at DESC LIMIT ?",
                    (project_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, project_id, payload, created_at FROM concept_guidelines ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [dict(row) | {"payload": json.loads(row["payload"])} for row in rows]

    def get_guideline(self, guideline_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT id, project_id, payload, created_at FROM concept_guidelines WHERE id = ?",
                (guideline_id,),
            ).fetchone()
        return dict(row) | {"payload": json.loads(row["payload"])} if row else None

    def upsert_gold_example_set(self, gold_set: GoldExampleSet) -> None:
        gold_set.validate()
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO gold_example_sets (id, project_id, guideline_id, payload, created_at) VALUES (?, ?, ?, ?, ?)",
                (gold_set.id, gold_set.project_id, gold_set.guideline_id, _json(gold_set), gold_set.created_at),
            )

    def list_gold_example_sets(self, guideline_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as conn:
            if guideline_id:
                rows = conn.execute(
                    "SELECT id, project_id, guideline_id, payload, created_at FROM gold_example_sets WHERE guideline_id = ? ORDER BY created_at DESC LIMIT ?",
                    (guideline_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, project_id, guideline_id, payload, created_at FROM gold_example_sets ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [dict(row) | {"payload": json.loads(row["payload"])} for row in rows]

    def upsert_concept_version(self, version: ConceptVersion) -> None:
        version.validate()
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO concept_versions (id, guideline_id, payload, created_at) VALUES (?, ?, ?, ?)",
                (version.id, version.guideline_id, _json(version), version.created_at),
            )

    def list_concept_versions(self, guideline_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as conn:
            if guideline_id:
                rows = conn.execute(
                    "SELECT id, guideline_id, payload, created_at FROM concept_versions WHERE guideline_id = ? ORDER BY created_at DESC LIMIT ?",
                    (guideline_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, guideline_id, payload, created_at FROM concept_versions ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [dict(row) | {"payload": json.loads(row["payload"])} for row in rows]

    def upsert_job(self, job: BatchJob) -> None:
        job.validate()
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO jobs (id, project_id, guideline_id, status, payload, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (job.id, job.project_id, job.guideline_id, job.status, _json(job), job.created_at, job.updated_at),
            )

    def list_jobs(self, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as conn:
            if status:
                rows = conn.execute(
                    "SELECT id, project_id, guideline_id, status, payload, created_at, updated_at FROM jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, project_id, guideline_id, status, payload, created_at, updated_at FROM jobs ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [dict(row) | {"payload": json.loads(row["payload"])} for row in rows]

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT id, project_id, guideline_id, status, payload, created_at, updated_at FROM jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
        return dict(row) | {"payload": json.loads(row["payload"])} if row else None

    def upsert_job_item(self, item: BatchJobItem) -> None:
        item.validate()
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO job_items (id, job_id, task_id, status, payload, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (item.id, item.job_id, item.task_id, item.status, _json(item), item.created_at, item.updated_at),
            )

    def list_job_items(
        self,
        job_id: str | None = None,
        status: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        query = "SELECT id, job_id, task_id, status, payload, created_at, updated_at FROM job_items"
        clauses: list[str] = []
        params: list[Any] = []
        if job_id:
            clauses.append("job_id = ?")
            params.append(job_id)
        if status:
            clauses.append("status = ?")
            params.append(status)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at ASC LIMIT ?"
        params.append(limit)
        with self.connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(row) | {"payload": json.loads(row["payload"])} for row in rows]

    def add_job_event(self, job_id: str, event_type: str, payload: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO job_events (job_id, event_type, payload) VALUES (?, ?, ?)",
                (job_id, event_type, json.dumps(payload, ensure_ascii=False)),
            )


def _json(value: Any) -> str:
    return json.dumps(to_plain_dict(value), ensure_ascii=False)
