from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
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
    {"id": "agent-003", "name": "Memory Steward", "role": "Memory policies and write-back", "status": "Idle"},
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

CREATE TABLE IF NOT EXISTS memory_layers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    score REAL NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    source TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at DESC);
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
            INSERT OR REPLACE INTO memory_layers(id, name, description, score, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(item["id"], item["name"], item["description"], item["score"], timestamp) for item in MEMORY_SEED],
        )

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

    def list_memory_layers(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT id, name, description, score FROM memory_layers ORDER BY score DESC, id ASC"
            ).fetchall()
            return [dict(row) for row in rows]

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
        memory_layers = self.list_memory_layers()
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
            "memory_layers": memory_layers,
            "recent_events": recent_events,
            "counts": {
                "tasks": len(tasks),
                "agents": len(agents),
                "memory_layers": len(memory_layers),
                "events": self.count_events(),
            },
        }
