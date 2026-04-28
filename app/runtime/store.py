from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.core.models import AgentStep, AnnotationTask, Prediction, Project, ReviewTask, WorkflowRun
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

    def upsert_task(self, task: AnnotationTask, project_id: str | None = None) -> None:
        payload = json.dumps(task_to_dict(task), ensure_ascii=False)
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO tasks (id, project_id, payload) VALUES (?, ?, ?)",
                (task.id, project_id, payload),
            )

    def list_tasks(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as conn:
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

    def upsert_review(self, review: ReviewTask) -> None:
        review.validate()
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO reviews (id, task_id, payload, created_at) VALUES (?, ?, ?, ?)",
                (review.id, review.task_id, _json(review), review.created_at),
            )

    def list_reviews(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT id, task_id, payload, created_at FROM reviews ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) | {"payload": json.loads(row["payload"])} for row in rows]

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


def _json(value: Any) -> str:
    return json.dumps(to_plain_dict(value), ensure_ascii=False)
