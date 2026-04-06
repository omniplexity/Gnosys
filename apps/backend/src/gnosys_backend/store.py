from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


WORKSPACE_SEED = {
    "name": "Gnosys",
    "mode": "Supervised",
    "status": "Bootstrapping",
    "active_project": "Core Console",
    "phase": "Persistence and event log foundation",
}

TASK_SEED = [
    {
        "id": "task-001",
        "title": "Desktop shell scaffold",
        "summary": "Build the main console layout and navigation.",
        "status": "Running",
        "priority": "Critical",
    },
    {
        "id": "task-002",
        "title": "Backend API scaffold",
        "summary": "Expose health, state, and event log endpoints.",
        "status": "Running",
        "priority": "High",
    },
    {
        "id": "task-003",
        "title": "Local persistence layer",
        "summary": "Store workspace state and append-only execution events.",
        "status": "Planned",
        "priority": "Critical",
    },
]

AGENT_SEED = [
    {"id": "agent-001", "name": "Orchestrator", "role": "Control loop and task routing", "status": "Working"},
    {"id": "agent-002", "name": "Planner", "role": "Task decomposition and sequencing", "status": "Reviewing"},
    {"id": "agent-003", "name": "Research Specialist", "role": "Research and retrieval", "status": "Idle"},
    {"id": "agent-004", "name": "Builder Specialist", "role": "Coding and implementation", "status": "Idle"},
    {"id": "agent-005", "name": "Memory Steward", "role": "Memory policies and write-back", "status": "Idle"},
    {"id": "agent-006", "name": "Critic / Evaluator", "role": "Review and validation", "status": "Idle"},
    {"id": "agent-007", "name": "Operations / Scheduler", "role": "Scheduling and control", "status": "Idle"},
]

PROJECT_SEED = [
    {
        "id": "project-001",
        "name": "Core Console",
        "summary": "Foundation workspace for the desktop, backend, memory, and orchestration layers.",
        "status": "Active",
        "owner": "Gnosys",
    },
    {
        "id": "project-002",
        "name": "Phase 4 CRUD",
        "summary": "Implement editable surfaces for tasks, projects, agents, skills, and schedules.",
        "status": "Planned",
        "owner": "Gnosys",
    },
]

SKILL_SEED = [
    {
        "id": "skill-001",
        "name": "Persistence Inspector",
        "description": "Inspect SQLite state, event logs, and runtime runs for consistency.",
        "scope": "workspace",
        "version": "0.1.0",
        "source_type": "authored",
        "status": "active",
    },
    {
        "id": "skill-002",
        "name": "Run Planner",
        "description": "Decompose objectives into bounded steps and specialist responsibilities.",
        "scope": "workspace",
        "version": "0.1.0",
        "source_type": "authored",
        "status": "active",
    },
]

SCHEDULE_SEED = [
    {
        "id": "schedule-001",
        "name": "Daily integrity check",
        "target_type": "skill",
        "target_ref": "skill-001",
        "schedule_expression": "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=9;BYMINUTE=0",
        "timezone": "America/New_York",
        "enabled": 1,
        "last_run_at": None,
        "next_run_at": None,
    }
]

MEMORY_SEED = [
    {
        "id": "memory-active",
        "name": "Active Context",
        "description": "In-flight session context and immediate working state.",
        "score": 0.95,
    },
    {
        "id": "memory-episodic",
        "name": "Episodic",
        "description": "Task episodes, decisions, and prior runs.",
        "score": 0.88,
    },
    {
        "id": "memory-semantic",
        "name": "Semantic",
        "description": "Normalized facts and stable workspace knowledge.",
        "score": 0.91,
    },
]

MEMORY_ITEM_SEED = [
    {
        "id": "memory-item-001",
        "layer": "Active Context",
        "scope": "session",
        "state": "validated",
        "title": "Phase 1 completed",
        "summary": "SQLite persistence and append-only event logging are live in the backend.",
        "content": "Phase 1 finished with a persistent SQLite store, append-only events, and live desktop refreshes.",
        "provenance": "phase-1-commit",
        "source_ref": "commit:069ba04",
        "confidence": 0.99,
        "freshness": 0.96,
        "tags": ["persistence", "events", "backend"],
    },
    {
        "id": "memory-item-002",
        "layer": "Semantic",
        "scope": "workspace",
        "state": "validated",
        "title": "Phase 2 target",
        "summary": "Build the memory engine with scoped retrieval and explanation traces.",
        "content": "Phase 2 focuses on durable memory records, retrieval traceability, and consolidation rules.",
        "provenance": "roadmap",
        "source_ref": "docs/ROADMAP.md",
        "confidence": 0.94,
        "freshness": 0.9,
        "tags": ["memory", "retrieval", "trace"],
    },
    {
        "id": "memory-item-003",
        "layer": "Episodic",
        "scope": "project",
        "state": "candidate",
        "title": "Retrieval audit note",
        "summary": "Inspect why a memory item was surfaced before it becomes durable.",
        "content": "A surfaced memory should explain scope, layer bias, and score so the user can validate it.",
        "provenance": "design-note",
        "source_ref": "notes/session-2",
        "confidence": 0.78,
        "freshness": 0.84,
        "tags": ["inspectability", "candidate", "retrieval"],
    },
]

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS workspace_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    status TEXT NOT NULL,
    priority TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    status TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    summary TEXT NOT NULL,
    status TEXT NOT NULL,
    owner TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skills (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    scope TEXT NOT NULL,
    version TEXT NOT NULL,
    source_type TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schedules (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_ref TEXT NOT NULL,
    schedule_expression TEXT NOT NULL,
    timezone TEXT NOT NULL,
    enabled INTEGER NOT NULL,
    last_run_at TEXT,
    next_run_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memory_layers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    score REAL NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memory_items (
    id TEXT PRIMARY KEY,
    layer TEXT NOT NULL,
    scope TEXT NOT NULL,
    state TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    content TEXT NOT NULL,
    provenance TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    confidence REAL NOT NULL,
    freshness REAL NOT NULL,
    tags TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_accessed_at TEXT
);

CREATE TABLE IF NOT EXISTS task_runs (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    objective TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    mode TEXT NOT NULL,
    status TEXT NOT NULL,
    summary TEXT NOT NULL,
    step_count INTEGER NOT NULL,
    approval_required INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    agent_role TEXT NOT NULL,
    run_kind TEXT NOT NULL,
    status TEXT NOT NULL,
    objective TEXT NOT NULL,
    summary TEXT NOT NULL,
    parent_run_id TEXT,
    task_run_id TEXT NOT NULL,
    recursion_depth INTEGER NOT NULL,
    child_count INTEGER NOT NULL,
    budget_units INTEGER NOT NULL,
    approval_required INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    source TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_task_runs_created_at ON task_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_runs_created_at ON agent_runs(created_at DESC);
"""


def _encode(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _decode(value: str) -> Any:
    return json.loads(value)


@dataclass(slots=True)
class GnosysStore:
    path: Path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA_SQL)
            if self._is_empty(connection, "workspace_state"):
                self._seed(connection)
                self.record_event(
                    connection,
                    event_type="system.bootstrap",
                    source="gnosys_backend",
                    payload={
                        "message": "Persistent workspace initialized",
                        "mode": WORKSPACE_SEED["mode"],
                    },
                )

    def _is_empty(self, connection: sqlite3.Connection, table_name: str) -> bool:
        result = connection.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
        return bool(result is not None and result["count"] == 0)

    def _seed(self, connection: sqlite3.Connection) -> None:
        workspace_pairs = WORKSPACE_SEED.items()
        connection.executemany(
            "INSERT OR REPLACE INTO workspace_state(key, value) VALUES (?, ?)",
            [(key, value) for key, value in workspace_pairs],
        )

        timestamp = utc_now()
        connection.executemany(
            """
            INSERT OR REPLACE INTO tasks(id, title, summary, status, priority, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [(item["id"], item["title"], item["summary"], item["status"], item["priority"], timestamp) for item in TASK_SEED],
        )
        connection.executemany(
            """
            INSERT OR REPLACE INTO agents(id, name, role, status, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(item["id"], item["name"], item["role"], item["status"], timestamp) for item in AGENT_SEED],
        )
        connection.executemany(
            """
            INSERT OR REPLACE INTO projects(id, name, summary, status, owner, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (item["id"], item["name"], item["summary"], item["status"], item["owner"], timestamp, timestamp)
                for item in PROJECT_SEED
            ],
        )
        connection.executemany(
            """
            INSERT OR REPLACE INTO skills(id, name, description, scope, version, source_type, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item["id"],
                    item["name"],
                    item["description"],
                    item["scope"],
                    item["version"],
                    item["source_type"],
                    item["status"],
                    timestamp,
                    timestamp,
                )
                for item in SKILL_SEED
            ],
        )
        connection.executemany(
            """
            INSERT OR REPLACE INTO schedules(
                id, name, target_type, target_ref, schedule_expression, timezone, enabled, last_run_at, next_run_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item["id"],
                    item["name"],
                    item["target_type"],
                    item["target_ref"],
                    item["schedule_expression"],
                    item["timezone"],
                    item["enabled"],
                    item["last_run_at"],
                    item["next_run_at"],
                    timestamp,
                    timestamp,
                )
                for item in SCHEDULE_SEED
            ],
        )
        connection.executemany(
            """
            INSERT OR REPLACE INTO memory_layers(id, name, description, score, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(item["id"], item["name"], item["description"], item["score"], timestamp) for item in MEMORY_SEED],
        )
        connection.executemany(
            """
            INSERT OR REPLACE INTO memory_items(
                id, layer, scope, state, title, summary, content, provenance, source_ref,
                confidence, freshness, tags, created_at, updated_at, last_accessed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item["id"],
                    item["layer"],
                    item["scope"],
                    item["state"],
                    item["title"],
                    item["summary"],
                    item["content"],
                    item["provenance"],
                    item["source_ref"],
                    item["confidence"],
                    item["freshness"],
                    _encode(item["tags"]),
                    timestamp,
                    timestamp,
                    None,
                )
                for item in MEMORY_ITEM_SEED
            ],
        )

    def _task_seed_defaults(self, title: str, summary: str) -> tuple[str, str]:
        safe_title = title.strip() or "Untitled task"
        safe_summary = summary.strip() or safe_title
        return safe_title, safe_summary

    def create_task(
        self,
        *,
        title: str,
        summary: str,
        status: str = "Inbox",
        priority: str = "Medium",
    ) -> dict[str, Any]:
        timestamp = utc_now()
        task_id = f"task-{uuid4().hex[:12]}"
        title, summary = self._task_seed_defaults(title, summary)
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO tasks(id, title, summary, status, priority, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (task_id, title, summary, status, priority, timestamp),
            )
            connection.commit()
        return {
            "id": task_id,
            "title": title,
            "summary": summary,
            "status": status,
            "priority": priority,
        }

    def update_task(
        self,
        task_id: str,
        *,
        title: str,
        summary: str,
        status: str,
        priority: str,
    ) -> dict[str, Any]:
        timestamp = utc_now()
        with self.connect() as connection:
            connection.execute(
                "UPDATE tasks SET title = ?, summary = ?, status = ?, priority = ?, updated_at = ? WHERE id = ?",
                (
                    title.strip() or "Untitled task",
                    summary.strip() or title.strip() or "Untitled task",
                    status,
                    priority,
                    timestamp,
                    task_id,
                ),
            )
            connection.commit()
        task = self.get_task(task_id)
        if task is None:
            raise KeyError(task_id)
        return task

    def delete_task(self, task_id: str) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            connection.commit()

    def update_task_status(self, task_id: str, status: str) -> dict[str, Any]:
        timestamp = utc_now()
        with self.connect() as connection:
            connection.execute(
                "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
                (status, timestamp, task_id),
            )
            connection.commit()
        task = self.get_task(task_id)
        if task is None:
            raise KeyError(task_id)
        return task

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT id, title, summary, status, priority FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
            return dict(row) if row is not None else None

    def get_workspace_state(self) -> dict[str, str]:
        with self.connect() as connection:
            rows = connection.execute("SELECT key, value FROM workspace_state").fetchall()
            return {row["key"]: row["value"] for row in rows}

    def list_tasks(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT id, title, summary, status, priority FROM tasks ORDER BY updated_at DESC, id ASC"
            ).fetchall()
            return [dict(row) for row in rows]

    def list_agents(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT id, name, role, status FROM agents ORDER BY updated_at DESC, id ASC"
            ).fetchall()
            return [dict(row) for row in rows]

    def get_agent(self, agent_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT id, name, role, status FROM agents WHERE id = ?",
                (agent_id,),
            ).fetchone()
            return dict(row) if row is not None else None

    def create_agent(self, *, name: str, role: str, status: str = "Idle") -> dict[str, Any]:
        timestamp = utc_now()
        agent_id = f"agent-{uuid4().hex[:12]}"
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO agents(id, name, role, status, updated_at) VALUES (?, ?, ?, ?, ?)",
                (agent_id, name.strip() or "Untitled agent", role.strip() or "Unassigned", status, timestamp),
            )
            connection.commit()
        return self.get_agent(agent_id) or {}

    def update_agent(self, agent_id: str, *, name: str, role: str, status: str) -> dict[str, Any]:
        timestamp = utc_now()
        with self.connect() as connection:
            connection.execute(
                "UPDATE agents SET name = ?, role = ?, status = ?, updated_at = ? WHERE id = ?",
                (name.strip() or "Untitled agent", role.strip() or "Unassigned", status, timestamp, agent_id),
            )
            connection.commit()
        agent = self.get_agent(agent_id)
        if agent is None:
            raise KeyError(agent_id)
        return agent

    def delete_agent(self, agent_id: str) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
            connection.commit()

    def list_memory_layers(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT id, name, description, score FROM memory_layers ORDER BY score DESC, id ASC"
            ).fetchall()
            return [dict(row) for row in rows]

    def count_projects(self) -> int:
        with self.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM projects").fetchone()
            return int(row["count"] if row is not None else 0)

    def count_skills(self) -> int:
        with self.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM skills").fetchone()
            return int(row["count"] if row is not None else 0)

    def count_schedules(self) -> int:
        with self.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM schedules").fetchone()
            return int(row["count"] if row is not None else 0)

    def list_projects(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT id, name, summary, status, owner, created_at, updated_at FROM projects ORDER BY updated_at DESC, id ASC"
            ).fetchall()
            return [dict(row) for row in rows]

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT id, name, summary, status, owner, created_at, updated_at FROM projects WHERE id = ?",
                (project_id,),
            ).fetchone()
            return dict(row) if row is not None else None

    def create_project(self, *, name: str, summary: str, status: str = "Planned", owner: str = "Gnosys") -> dict[str, Any]:
        timestamp = utc_now()
        project_id = f"project-{uuid4().hex[:12]}"
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO projects(id, name, summary, status, owner, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (project_id, name.strip() or "Untitled project", summary.strip() or name.strip() or "Untitled project", status, owner.strip() or "Gnosys", timestamp, timestamp),
            )
            connection.commit()
        return self.get_project(project_id) or {}

    def update_project(self, project_id: str, *, name: str, summary: str, status: str, owner: str) -> dict[str, Any]:
        timestamp = utc_now()
        with self.connect() as connection:
            connection.execute(
                "UPDATE projects SET name = ?, summary = ?, status = ?, owner = ?, updated_at = ? WHERE id = ?",
                (name.strip() or "Untitled project", summary.strip() or name.strip() or "Untitled project", status, owner.strip() or "Gnosys", timestamp, project_id),
            )
            connection.commit()
        project = self.get_project(project_id)
        if project is None:
            raise KeyError(project_id)
        return project

    def delete_project(self, project_id: str) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            connection.commit()

    def list_skills(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT id, name, description, scope, version, source_type, status, created_at, updated_at FROM skills ORDER BY updated_at DESC, id ASC"
            ).fetchall()
            return [dict(row) for row in rows]

    def get_skill(self, skill_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT id, name, description, scope, version, source_type, status, created_at, updated_at FROM skills WHERE id = ?",
                (skill_id,),
            ).fetchone()
            return dict(row) if row is not None else None

    def create_skill(
        self,
        *,
        name: str,
        description: str,
        scope: str = "workspace",
        version: str = "0.1.0",
        source_type: str = "authored",
        status: str = "draft",
    ) -> dict[str, Any]:
        timestamp = utc_now()
        skill_id = f"skill-{uuid4().hex[:12]}"
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO skills(id, name, description, scope, version, source_type, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (skill_id, name.strip() or "Untitled skill", description.strip() or name.strip() or "Untitled skill", scope, version, source_type, status, timestamp, timestamp),
            )
            connection.commit()
        return self.get_skill(skill_id) or {}

    def update_skill(
        self,
        skill_id: str,
        *,
        name: str,
        description: str,
        scope: str,
        version: str,
        source_type: str,
        status: str,
    ) -> dict[str, Any]:
        timestamp = utc_now()
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE skills
                SET name = ?, description = ?, scope = ?, version = ?, source_type = ?, status = ?, updated_at = ?
                WHERE id = ?
                """,
                (name.strip() or "Untitled skill", description.strip() or name.strip() or "Untitled skill", scope, version, source_type, status, timestamp, skill_id),
            )
            connection.commit()
        skill = self.get_skill(skill_id)
        if skill is None:
            raise KeyError(skill_id)
        return skill

    def delete_skill(self, skill_id: str) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM skills WHERE id = ?", (skill_id,))
            connection.commit()

    def list_schedules(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, name, target_type, target_ref, schedule_expression, timezone, enabled, last_run_at, next_run_at, created_at, updated_at
                FROM schedules
                ORDER BY updated_at DESC, id ASC
                """
            ).fetchall()
            results = []
            for row in rows:
                item = dict(row)
                item["enabled"] = bool(item["enabled"])
                results.append(item)
            return results

    def get_schedule(self, schedule_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT id, name, target_type, target_ref, schedule_expression, timezone, enabled, last_run_at, next_run_at, created_at, updated_at
                FROM schedules
                WHERE id = ?
                """,
                (schedule_id,),
            ).fetchone()
            if row is None:
                return None
            item = dict(row)
            item["enabled"] = bool(item["enabled"])
            return item

    def create_schedule(
        self,
        *,
        name: str,
        target_type: str,
        target_ref: str,
        schedule_expression: str,
        timezone: str,
        enabled: bool = True,
        last_run_at: str | None = None,
        next_run_at: str | None = None,
    ) -> dict[str, Any]:
        timestamp = utc_now()
        schedule_id = f"schedule-{uuid4().hex[:12]}"
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO schedules(
                    id, name, target_type, target_ref, schedule_expression, timezone, enabled, last_run_at, next_run_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    schedule_id,
                    name.strip() or "Untitled schedule",
                    target_type,
                    target_ref,
                    schedule_expression,
                    timezone,
                    int(enabled),
                    last_run_at,
                    next_run_at,
                    timestamp,
                    timestamp,
                ),
            )
            connection.commit()
        return self.get_schedule(schedule_id) or {}

    def update_schedule(
        self,
        schedule_id: str,
        *,
        name: str,
        target_type: str,
        target_ref: str,
        schedule_expression: str,
        timezone: str,
        enabled: bool,
        last_run_at: str | None = None,
        next_run_at: str | None = None,
    ) -> dict[str, Any]:
        timestamp = utc_now()
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE schedules
                SET name = ?, target_type = ?, target_ref = ?, schedule_expression = ?, timezone = ?, enabled = ?, last_run_at = ?, next_run_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    name.strip() or "Untitled schedule",
                    target_type,
                    target_ref,
                    schedule_expression,
                    timezone,
                    int(enabled),
                    last_run_at,
                    next_run_at,
                    timestamp,
                    schedule_id,
                ),
            )
            connection.commit()
        schedule = self.get_schedule(schedule_id)
        if schedule is None:
            raise KeyError(schedule_id)
        return schedule

    def delete_schedule(self, schedule_id: str) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
            connection.commit()

    def list_memory_items(
        self,
        *,
        limit: int = 50,
        layer: str | None = None,
        scope: str | None = None,
        state: str | None = None,
    ) -> list[dict[str, Any]]:
        query = [
            "SELECT id, layer, scope, state, title, summary, content, provenance, source_ref, confidence, freshness, tags, created_at, updated_at, last_accessed_at",
            "FROM memory_items",
        ]
        params: list[Any] = []
        conditions: list[str] = []
        if layer:
            conditions.append("layer = ?")
            params.append(layer)
        if scope:
            conditions.append("scope = ?")
            params.append(scope)
        if state:
            conditions.append("state = ?")
            params.append(state)
        if conditions:
            query.append("WHERE " + " AND ".join(conditions))
        query.append("ORDER BY updated_at DESC, created_at DESC, id ASC")
        query.append("LIMIT ?")
        params.append(limit)
        sql = " ".join(query)

        with self.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
            return [
                {
                    **dict(row),
                    "tags": _decode(row["tags"]),
                }
                for row in rows
            ]

    def count_memory_items(self) -> int:
        with self.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM memory_items").fetchone()
            return int(row["count"] if row is not None else 0)

    def get_memory_item(self, item_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT id, layer, scope, state, title, summary, content, provenance, source_ref,
                       confidence, freshness, tags, created_at, updated_at, last_accessed_at
                FROM memory_items
                WHERE id = ?
                """,
                (item_id,),
            ).fetchone()
            if row is None:
                return None
            return {
                **dict(row),
                "tags": _decode(row["tags"]),
            }

    def upsert_memory_item(self, item: dict[str, Any]) -> dict[str, Any]:
        timestamp = utc_now()
        tags = item.get("tags", [])
        with self.connect() as connection:
            existing = self.get_memory_item(item["id"])
            created_at = existing["created_at"] if existing is not None else timestamp
            last_accessed_at = item.get("last_accessed_at", existing["last_accessed_at"] if existing else None)
            connection.execute(
                """
                INSERT OR REPLACE INTO memory_items(
                    id, layer, scope, state, title, summary, content, provenance, source_ref,
                    confidence, freshness, tags, created_at, updated_at, last_accessed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["id"],
                    item["layer"],
                    item["scope"],
                    item["state"],
                    item["title"],
                    item["summary"],
                    item.get("content", item["summary"]),
                    item["provenance"],
                    item["source_ref"],
                    item["confidence"],
                    item["freshness"],
                    _encode(tags),
                    created_at,
                    timestamp,
                    last_accessed_at,
                ),
            )
            connection.commit()
        saved = self.get_memory_item(item["id"])
        if saved is None:
            raise RuntimeError(f"Unable to persist memory item {item['id']}")
        return saved

    def update_memory_item_state(self, item_id: str, state: str) -> dict[str, Any]:
        timestamp = utc_now()
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE memory_items
                SET state = ?, updated_at = ?
                WHERE id = ?
                """,
                (state, timestamp, item_id),
            )
            connection.commit()
        item = self.get_memory_item(item_id)
        if item is None:
            raise KeyError(item_id)
        return item

    def touch_memory_item(self, item_id: str) -> None:
        timestamp = utc_now()
        with self.connect() as connection:
            connection.execute(
                "UPDATE memory_items SET last_accessed_at = ?, updated_at = ? WHERE id = ?",
                (timestamp, timestamp, item_id),
            )
            connection.commit()

    def create_task_run(
        self,
        *,
        task_id: str,
        objective: str,
        requested_by: str,
        mode: str,
        status: str,
        summary: str,
        step_count: int,
        approval_required: bool,
    ) -> dict[str, Any]:
        timestamp = utc_now()
        run_id = f"run-{uuid4().hex[:12]}"
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO task_runs(
                    id, task_id, objective, requested_by, mode, status, summary, step_count,
                    approval_required, created_at, updated_at, completed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    task_id,
                    objective,
                    requested_by,
                    mode,
                    status,
                    summary,
                    step_count,
                    int(approval_required),
                    timestamp,
                    timestamp,
                    None,
                ),
            )
            connection.commit()
        return self.get_task_run(run_id) or {}

    def update_task_run(
        self,
        run_id: str,
        *,
        status: str,
        summary: str | None = None,
        completed: bool = False,
        step_count: int | None = None,
        approval_required: bool | None = None,
    ) -> dict[str, Any]:
        timestamp = utc_now()
        current = self.get_task_run(run_id)
        if current is None:
            raise KeyError(run_id)
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE task_runs
                SET status = ?,
                    summary = COALESCE(?, summary),
                    step_count = COALESCE(?, step_count),
                    approval_required = COALESCE(?, approval_required),
                    updated_at = ?,
                    completed_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    summary,
                    step_count,
                    None if approval_required is None else int(approval_required),
                    timestamp,
                    timestamp if completed else current["completed_at"],
                    run_id,
                ),
            )
            connection.commit()
        updated = self.get_task_run(run_id)
        if updated is None:
            raise KeyError(run_id)
        return updated

    def get_task_run(self, run_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT id, task_id, objective, requested_by, mode, status, summary, step_count,
                       approval_required, created_at, updated_at, completed_at
                FROM task_runs
                WHERE id = ?
                """,
                (run_id,),
            ).fetchone()
            if row is None:
                return None
            data = dict(row)
            data["approval_required"] = bool(data["approval_required"])
            return data

    def list_task_runs(self, *, limit: int = 20) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, task_id, objective, requested_by, mode, status, summary, step_count,
                       approval_required, created_at, updated_at, completed_at
                FROM task_runs
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            results = []
            for row in rows:
                item = dict(row)
                item["approval_required"] = bool(item["approval_required"])
                results.append(item)
            return results

    def create_agent_run(
        self,
        *,
        agent_id: str,
        agent_name: str,
        agent_role: str,
        run_kind: str,
        status: str,
        objective: str,
        summary: str,
        task_run_id: str,
        parent_run_id: str | None,
        recursion_depth: int,
        child_count: int,
        budget_units: int,
        approval_required: bool,
    ) -> dict[str, Any]:
        timestamp = utc_now()
        run_id = f"agent-run-{uuid4().hex[:12]}"
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_runs(
                    id, agent_id, agent_name, agent_role, run_kind, status, objective, summary,
                    parent_run_id, task_run_id, recursion_depth, child_count, budget_units,
                    approval_required, created_at, updated_at, completed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    agent_id,
                    agent_name,
                    agent_role,
                    run_kind,
                    status,
                    objective,
                    summary,
                    parent_run_id,
                    task_run_id,
                    recursion_depth,
                    child_count,
                    budget_units,
                    int(approval_required),
                    timestamp,
                    timestamp,
                    None,
                ),
            )
            connection.commit()
        return self.get_agent_run(run_id) or {}

    def update_agent_run(
        self,
        run_id: str,
        *,
        status: str,
        summary: str | None = None,
        completed: bool = False,
        child_count: int | None = None,
        budget_units: int | None = None,
        approval_required: bool | None = None,
    ) -> dict[str, Any]:
        timestamp = utc_now()
        current = self.get_agent_run(run_id)
        if current is None:
            raise KeyError(run_id)
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE agent_runs
                SET status = ?,
                    summary = COALESCE(?, summary),
                    child_count = COALESCE(?, child_count),
                    budget_units = COALESCE(?, budget_units),
                    approval_required = COALESCE(?, approval_required),
                    updated_at = ?,
                    completed_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    summary,
                    child_count,
                    budget_units,
                    None if approval_required is None else int(approval_required),
                    timestamp,
                    timestamp if completed else current["completed_at"],
                    run_id,
                ),
            )
            connection.commit()
        updated = self.get_agent_run(run_id)
        if updated is None:
            raise KeyError(run_id)
        return updated

    def get_agent_run(self, run_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT id, agent_id, agent_name, agent_role, run_kind, status, objective, summary,
                       parent_run_id, task_run_id, recursion_depth, child_count, budget_units,
                       approval_required, created_at, updated_at, completed_at
                FROM agent_runs
                WHERE id = ?
                """,
                (run_id,),
            ).fetchone()
            if row is None:
                return None
            data = dict(row)
            data["approval_required"] = bool(data["approval_required"])
            return data

    def list_agent_runs(
        self,
        *,
        limit: int = 50,
        task_run_id: str | None = None,
        parent_run_id: str | None = None,
    ) -> list[dict[str, Any]]:
        query = [
            "SELECT id, agent_id, agent_name, agent_role, run_kind, status, objective, summary, parent_run_id, task_run_id, recursion_depth, child_count, budget_units, approval_required, created_at, updated_at, completed_at",
            "FROM agent_runs",
        ]
        params: list[Any] = []
        conditions: list[str] = []
        if task_run_id:
            conditions.append("task_run_id = ?")
            params.append(task_run_id)
        if parent_run_id is not None:
            conditions.append("parent_run_id = ?")
            params.append(parent_run_id)
        if conditions:
            query.append("WHERE " + " AND ".join(conditions))
        query.append("ORDER BY created_at ASC, id ASC")
        query.append("LIMIT ?")
        params.append(limit)
        sql = " ".join(query)
        with self.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
            results = []
            for row in rows:
                item = dict(row)
                item["approval_required"] = bool(item["approval_required"])
                results.append(item)
            return results

    def list_runtime_roots(self, limit: int = 10) -> list[dict[str, Any]]:
        task_runs = self.list_task_runs(limit=limit)
        for run in task_runs:
            run["agent_runs"] = self.list_agent_runs(task_run_id=run["id"], limit=100)
        return task_runs

    def count_task_runs(self) -> int:
        with self.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM task_runs").fetchone()
            return int(row["count"] if row is not None else 0)

    def count_agent_runs(self) -> int:
        with self.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM agent_runs").fetchone()
            return int(row["count"] if row is not None else 0)

    def list_events(self, limit: int = 25) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, type, source, payload, created_at
                FROM events
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [
                {
                    "id": row["id"],
                    "type": row["type"],
                    "source": row["source"],
                    "payload": _decode(row["payload"]),
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

    def count_events(self) -> int:
        with self.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM events").fetchone()
            return int(row["count"] if row is not None else 0)

    def record_event(
        self,
        connection: sqlite3.Connection | None = None,
        *,
        event_type: str,
        source: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        owns_connection = connection is None
        active_connection = connection or self.connect()
        try:
            created_at = utc_now()
            cursor = active_connection.execute(
                """
                INSERT INTO events(type, source, payload, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (event_type, source, _encode(payload), created_at),
            )
            if owns_connection:
                active_connection.commit()
            return {
                "id": cursor.lastrowid,
                "type": event_type,
                "source": source,
                "payload": payload,
                "created_at": created_at,
            }
        finally:
            if owns_connection:
                active_connection.close()

    def workspace_snapshot(self) -> dict[str, Any]:
        workspace = self.get_workspace_state()
        tasks = self.list_tasks()
        agents = self.list_agents()
        projects = self.list_projects()
        skills = self.list_skills()
        schedules = self.list_schedules()
        memory_layers = self.list_memory_layers()
        memory_items = self.list_memory_items(limit=10)
        task_runs = self.list_task_runs(limit=10)
        agent_runs = self.list_agent_runs(limit=25)
        recent_events = self.list_events()

        return {
            "workspace": {
                "name": workspace.get("name", "Gnosys"),
                "mode": workspace.get("mode", "Supervised"),
                "status": workspace.get("status", "Bootstrapping"),
                "active_project": workspace.get("active_project", "Core Console"),
                "phase": workspace.get("phase", "Persistence and event log foundation"),
            },
            "tasks": tasks,
            "agents": agents,
            "projects": projects,
            "skills": skills,
            "schedules": schedules,
            "memory_layers": memory_layers,
            "memory_items": memory_items,
            "task_runs": task_runs,
            "agent_runs": agent_runs,
            "recent_events": recent_events,
            "counts": {
                "tasks": len(tasks),
                "agents": len(agents),
                "projects": self.count_projects(),
                "skills": self.count_skills(),
                "schedules": self.count_schedules(),
                "memory_layers": len(memory_layers),
                "memory_items": self.count_memory_items(),
                "task_runs": self.count_task_runs(),
                "agent_runs": self.count_agent_runs(),
                "events": self.count_events(),
            },
        }
