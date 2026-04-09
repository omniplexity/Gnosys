from __future__ import annotations

import json
import re
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
    "autonomy_mode": "Supervised",
    "kill_switch": "false",
    "approval_bias": "supervised",
    "mode_label": "Global autonomy and approval policy",
    "status": "Bootstrapping",
    "active_project": "Core Console",
    "phase": "Persistence and event log foundation",
}

TASK_SEED = [
    {
        "id": "task-001",
        "project_id": "project-001",
        "title": "Desktop shell scaffold",
        "summary": "Build the main console layout and navigation.",
        "status": "Running",
        "priority": "Critical",
    },
    {
        "id": "task-002",
        "project_id": "project-001",
        "title": "Backend API scaffold",
        "summary": "Expose health, state, and event log endpoints.",
        "status": "Running",
        "priority": "High",
    },
    {
        "id": "task-003",
        "project_id": "project-002",
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
        "workspace_path": "workspaces/core-console",
    },
    {
        "id": "project-002",
        "name": "Phase 4 CRUD",
        "summary": "Implement editable surfaces for tasks, projects, agents, skills, and schedules.",
        "status": "Planned",
        "owner": "Gnosys",
        "workspace_path": "workspaces/phase-4-crud",
    },
]

PROJECT_THREAD_SEED = [
    {
        "id": "thread-001",
        "project_id": "project-001",
        "title": "Core runtime planning",
        "summary": "Track execution design and storage work for the core console.",
        "status": "Open",
        "context_path": "threads/core-runtime-planning",
    }
]

CHAT_SESSION_SEED = [
    {
        "id": "session-001",
        "title": "Main agent thread",
        "summary": "Default non-project orchestration conversation.",
        "status": "Active",
        "context_path": "agent/main-thread",
    }
]

CHAT_MESSAGE_SEED = [
    {
        "id": "chat-message-001",
        "chat_session_id": "session-001",
        "role": "assistant",
        "kind": "message",
        "content": "Persistent session initialized. I will keep continuity here as work and memory deepen over time.",
        "task_run_id": None,
        "agent_run_ids": [],
        "metadata": {"source": "bootstrap"},
    }
]

SKILL_SEED = [
    {
        "id": "skill-001",
        "project_id": "project-001",
        "name": "Persistence Inspector",
        "description": "Inspect SQLite state, event logs, and runtime runs for consistency.",
        "scope": "workspace",
        "version": "0.1.0",
        "source_type": "authored",
        "status": "active",
    },
    {
        "id": "skill-002",
        "project_id": "project-002",
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
        "project_id": "project-001",
        "name": "Daily integrity check",
        "target_type": "skill",
        "target_ref": "skill-001",
        "schedule_expression": "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=9;BYMINUTE=0",
        "timezone": "America/New_York",
        "enabled": 1,
        "approval_policy": "inherit",
        "failure_policy": "retry_once",
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
        "project_id": "project-001",
        "state": "validated",
        "pinned": 1,
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
        "project_id": "project-001",
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
        "project_id": "project-002",
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
    project_id TEXT,
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
    workspace_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS project_threads (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    status TEXT NOT NULL,
    context_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    status TEXT NOT NULL,
    context_path TEXT NOT NULL,
    agent_path TEXT NOT NULL,
    soul_path TEXT NOT NULL,
    identity_path TEXT NOT NULL,
    heartbeat_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    chat_session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    kind TEXT NOT NULL,
    content TEXT NOT NULL,
    task_run_id TEXT,
    agent_run_ids TEXT NOT NULL,
    metadata TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_attachments (
    id TEXT PRIMARY KEY,
    chat_session_id TEXT NOT NULL,
    mode TEXT NOT NULL,
    project_id TEXT,
    project_thread_id TEXT,
    original_name TEXT NOT NULL,
    stored_name TEXT NOT NULL,
    content_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    storage_path TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS session_reflections (
    id TEXT PRIMARY KEY,
    chat_session_id TEXT NOT NULL,
    summary TEXT NOT NULL,
    user_preferences TEXT NOT NULL,
    working_style TEXT NOT NULL,
    recurring_goals TEXT NOT NULL,
    personal_context TEXT NOT NULL,
    identity_refinements TEXT NOT NULL,
    source_message_ids TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS identity_proposals (
    id TEXT PRIMARY KEY,
    chat_session_id TEXT NOT NULL,
    target_file TEXT NOT NULL,
    proposal_kind TEXT NOT NULL,
    rationale TEXT NOT NULL,
    proposed_content TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skills (
    id TEXT PRIMARY KEY,
    project_id TEXT,
    parent_skill_id TEXT,
    promoted_from_skill_id TEXT,
    latest_test_run_id TEXT,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    scope TEXT NOT NULL,
    version TEXT NOT NULL,
    source_type TEXT NOT NULL,
    status TEXT NOT NULL,
    test_status TEXT NOT NULL,
    test_score REAL NOT NULL,
    test_summary TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skill_test_runs (
    id TEXT PRIMARY KEY,
    skill_id TEXT NOT NULL,
    scenario TEXT NOT NULL,
    expected_outcome TEXT NOT NULL,
    observed_outcome TEXT NOT NULL,
    passed INTEGER NOT NULL,
    score REAL NOT NULL,
    summary TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schedules (
    id TEXT PRIMARY KEY,
    project_id TEXT,
    name TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_ref TEXT NOT NULL,
    schedule_expression TEXT NOT NULL,
    timezone TEXT NOT NULL,
    enabled INTEGER NOT NULL,
    approval_policy TEXT NOT NULL,
    failure_policy TEXT NOT NULL,
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
    project_id TEXT,
    state TEXT NOT NULL,
    pinned INTEGER NOT NULL DEFAULT 0,
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
    project_id TEXT,
    project_thread_id TEXT,
    chat_session_id TEXT,
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

CREATE TABLE IF NOT EXISTS approval_requests (
    id TEXT PRIMARY KEY,
    action TEXT NOT NULL,
    subject_type TEXT NOT NULL,
    subject_ref TEXT NOT NULL,
    sensitivity TEXT NOT NULL,
    status TEXT NOT NULL,
    reason TEXT NOT NULL,
    payload TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    resolved_at TEXT,
    resolved_by TEXT
);

CREATE TABLE IF NOT EXISTS entity_policies (
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    project_id TEXT,
    autonomy_mode TEXT NOT NULL,
    kill_switch INTEGER NOT NULL,
    approval_bias TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(entity_type, entity_id)
);

CREATE TABLE IF NOT EXISTS schedule_runs (
    id TEXT PRIMARY KEY,
    schedule_id TEXT NOT NULL,
    schedule_name TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_ref TEXT NOT NULL,
    status TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,
    retry_of_run_id TEXT,
    task_run_id TEXT,
    requested_by TEXT NOT NULL,
    result_summary TEXT NOT NULL,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_task_runs_created_at ON task_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_runs_created_at ON agent_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_approval_requests_created_at ON approval_requests(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_schedule_runs_created_at ON schedule_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_entity_policies_updated_at ON entity_policies(updated_at DESC);
"""


def _encode(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _decode(value: str, default: Any | None = None) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "project"


@dataclass(slots=True)
class GnosysStore:
    path: Path

    @property
    def workspace_root(self) -> Path:
        return self.path.parent / "workspaces"

    @property
    def agent_root(self) -> Path:
        return self.path.parent / "agent"

    def _project_workspace_dir(self, project_id: str, project_name: str) -> Path:
        return self.workspace_root / f"{_slugify(project_name)}-{project_id[-6:]}"

    def _ensure_project_workspace(self, project_id: str, project_name: str) -> str:
        directory = self._project_workspace_dir(project_id, project_name)
        directory.mkdir(parents=True, exist_ok=True)
        return str(directory.resolve())

    def _project_threads_root(self, project_id: str, project_name: str) -> Path:
        return Path(self._ensure_project_workspace(project_id, project_name)) / "threads"

    def _ensure_project_thread_context(self, project_id: str, project_name: str, thread_id: str, title: str) -> str:
        directory = self._project_threads_root(project_id, project_name) / f"{_slugify(title)}-{thread_id[-6:]}"
        directory.mkdir(parents=True, exist_ok=True)
        return str(directory.resolve())

    def _ensure_chat_session_files(self, session_id: str, title: str) -> dict[str, str]:
        directory = self.agent_root / f"{_slugify(title)}-{session_id[-6:]}"
        directory.mkdir(parents=True, exist_ok=True)
        files = {
            "context_path": str(directory.resolve()),
            "agent_path": str((directory / "AGENT.md").resolve()),
            "soul_path": str((directory / "SOUL.md").resolve()),
            "identity_path": str((directory / "IDENTITY.md").resolve()),
            "heartbeat_path": str((directory / "HEARTBEAT.md").resolve()),
        }
        for path in [files["agent_path"], files["soul_path"], files["identity_path"], files["heartbeat_path"]]:
            file_path = Path(path)
            if not file_path.exists():
                file_path.write_text(f"# {file_path.stem}\n", encoding="utf-8")
        return files

    def _chat_session_uploads_root(self, session_id: str, title: str) -> Path:
        return Path(self._ensure_chat_session_files(session_id, title)["context_path"]) / "uploads"

    def resolve_chat_context_directory(
        self,
        *,
        chat_session_id: str,
        mode: str,
        project_id: str | None = None,
        project_thread_id: str | None = None,
    ) -> str:
        session = self.get_chat_session(chat_session_id)
        if session is None:
            raise KeyError(chat_session_id)
        if mode == "personal":
            directory = self._chat_session_uploads_root(chat_session_id, session["title"])
        elif mode == "project":
            if not project_id:
                raise KeyError("project_id")
            project = self.get_project(project_id)
            if project is None:
                raise KeyError(project_id)
            directory = Path(project["workspace_path"]) / "session-inputs" / chat_session_id
        elif mode == "project-thread":
            if not project_thread_id:
                raise KeyError("project_thread_id")
            thread = self.get_project_thread(project_thread_id)
            if thread is None:
                raise KeyError(project_thread_id)
            directory = Path(thread["context_path"]) / "inputs"
        else:
            raise ValueError(f"Unsupported mode: {mode}")
        directory.mkdir(parents=True, exist_ok=True)
        return str(directory.resolve())

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA_SQL)
            self._ensure_columns(
                connection,
                table_name="task_runs",
                columns={
                    "project_id": "TEXT",
                    "project_thread_id": "TEXT",
                    "chat_session_id": "TEXT",
                },
            )
            self._ensure_columns(
                connection,
                table_name="tasks",
                columns={"project_id": "TEXT"},
            )
            self._ensure_columns(
                connection,
                table_name="skills",
                columns={
                    "project_id": "TEXT",
                    "parent_skill_id": "TEXT",
                    "promoted_from_skill_id": "TEXT",
                    "latest_test_run_id": "TEXT",
                    "test_status": "TEXT NOT NULL DEFAULT 'untested'",
                    "test_score": "REAL NOT NULL DEFAULT 0",
                    "test_summary": "TEXT NOT NULL DEFAULT ''",
                },
            )
            self._ensure_columns(
                connection,
                table_name="schedules",
                columns={
                    "project_id": "TEXT",
                    "approval_policy": "TEXT DEFAULT 'inherit'",
                    "failure_policy": "TEXT DEFAULT 'retry_once'",
                },
            )
            self._ensure_columns(
                connection,
                table_name="memory_items",
                columns={"project_id": "TEXT", "pinned": "INTEGER NOT NULL DEFAULT 0"},
            )
            self._ensure_columns(
                connection,
                table_name="entity_policies",
                columns={"project_id": "TEXT"},
            )
            self._ensure_columns(
                connection,
                table_name="projects",
                columns={"workspace_path": "TEXT"},
            )
            self._ensure_columns(
                connection,
                table_name="project_threads",
                columns={"context_path": "TEXT"},
            )
            self._ensure_columns(
                connection,
                table_name="chat_sessions",
                columns={
                    "context_path": "TEXT",
                    "agent_path": "TEXT",
                    "soul_path": "TEXT",
                    "identity_path": "TEXT",
                    "heartbeat_path": "TEXT",
                },
            )
            self._ensure_columns(
                connection,
                table_name="chat_messages",
                columns={
                    "task_run_id": "TEXT",
                    "agent_run_ids": "TEXT NOT NULL DEFAULT '[]'",
                    "metadata": "TEXT NOT NULL DEFAULT '{}'",
                },
            )
            connection.execute(
                "UPDATE schedules SET approval_policy = COALESCE(approval_policy, 'inherit'), failure_policy = COALESCE(failure_policy, 'retry_once')"
            )
            project_rows = connection.execute("SELECT id, name, workspace_path FROM projects").fetchall()
            for row in project_rows:
                workspace_path = row["workspace_path"] if "workspace_path" in row.keys() else None
                if workspace_path:
                    Path(workspace_path).mkdir(parents=True, exist_ok=True)
                    continue
                generated_path = self._ensure_project_workspace(row["id"], row["name"])
                connection.execute(
                    "UPDATE projects SET workspace_path = ? WHERE id = ?",
                    (generated_path, row["id"]),
                )
            thread_rows = connection.execute(
                """
                SELECT project_threads.id, project_threads.project_id, project_threads.title, project_threads.context_path, projects.name AS project_name
                FROM project_threads
                JOIN projects ON projects.id = project_threads.project_id
                """
            ).fetchall()
            for row in thread_rows:
                if row["context_path"]:
                    Path(row["context_path"]).mkdir(parents=True, exist_ok=True)
                    continue
                generated_path = self._ensure_project_thread_context(row["project_id"], row["project_name"], row["id"], row["title"])
                connection.execute(
                    "UPDATE project_threads SET context_path = ? WHERE id = ?",
                    (generated_path, row["id"]),
                )
            session_rows = connection.execute(
                "SELECT id, title, context_path, agent_path, soul_path, identity_path, heartbeat_path FROM chat_sessions"
            ).fetchall()
            for row in session_rows:
                if row["context_path"] and row["agent_path"] and row["soul_path"] and row["identity_path"] and row["heartbeat_path"]:
                    self._ensure_chat_session_files(row["id"], row["title"])
                    continue
                generated_paths = self._ensure_chat_session_files(row["id"], row["title"])
                connection.execute(
                    """
                    UPDATE chat_sessions
                    SET context_path = ?, agent_path = ?, soul_path = ?, identity_path = ?, heartbeat_path = ?
                    WHERE id = ?
                    """,
                    (
                        generated_paths["context_path"],
                        generated_paths["agent_path"],
                        generated_paths["soul_path"],
                        generated_paths["identity_path"],
                        generated_paths["heartbeat_path"],
                        row["id"],
                    ),
                )
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
            if self._is_empty(connection, "entity_policies"):
                timestamp = utc_now()
                connection.execute(
                    """
                    INSERT OR REPLACE INTO entity_policies(
                        entity_type, entity_id, project_id, autonomy_mode, kill_switch, approval_bias, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "project",
                        "project-001",
                        "project-001",
                        WORKSPACE_SEED["autonomy_mode"],
                        int(False),
                        WORKSPACE_SEED["approval_bias"],
                        timestamp,
                        timestamp,
                    ),
                )
                connection.commit()

    def _is_empty(self, connection: sqlite3.Connection, table_name: str) -> bool:
        result = connection.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
        return bool(result is not None and result["count"] == 0)

    def _ensure_columns(self, connection: sqlite3.Connection, *, table_name: str, columns: dict[str, str]) -> None:
        existing = {
            row["name"]
            for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        for column, definition in columns.items():
            if column not in existing:
                connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column} {definition}")

    def _seed(self, connection: sqlite3.Connection) -> None:
        workspace_pairs = WORKSPACE_SEED.items()
        connection.executemany(
            "INSERT OR REPLACE INTO workspace_state(key, value) VALUES (?, ?)",
            [(key, value) for key, value in workspace_pairs],
        )

        timestamp = utc_now()
        connection.executemany(
            """
            INSERT OR REPLACE INTO tasks(id, project_id, title, summary, status, priority, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item["id"],
                    item.get("project_id"),
                    item["title"],
                    item["summary"],
                    item["status"],
                    item["priority"],
                    timestamp,
                )
                for item in TASK_SEED
            ],
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
            INSERT OR REPLACE INTO projects(id, name, summary, status, owner, workspace_path, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item["id"],
                    item["name"],
                    item["summary"],
                    item["status"],
                    item["owner"],
                    str((self.path.parent / item["workspace_path"]).resolve()),
                    timestamp,
                    timestamp,
                )
                for item in PROJECT_SEED
            ],
        )
        connection.executemany(
            """
            INSERT OR REPLACE INTO project_threads(id, project_id, title, summary, status, context_path, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item["id"],
                    item["project_id"],
                    item["title"],
                    item["summary"],
                    item["status"],
                    self._ensure_project_thread_context(
                        item["project_id"],
                        next(project["name"] for project in PROJECT_SEED if project["id"] == item["project_id"]),
                        item["id"],
                        item["title"],
                    ),
                    timestamp,
                    timestamp,
                )
                for item in PROJECT_THREAD_SEED
            ],
        )
        connection.executemany(
            """
            INSERT OR REPLACE INTO chat_sessions(
                id, title, summary, status, context_path, agent_path, soul_path, identity_path, heartbeat_path, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item["id"],
                    item["title"],
                    item["summary"],
                    item["status"],
                    session_paths["context_path"],
                    session_paths["agent_path"],
                    session_paths["soul_path"],
                    session_paths["identity_path"],
                    session_paths["heartbeat_path"],
                    timestamp,
                    timestamp,
                )
                for item in CHAT_SESSION_SEED
                for session_paths in [self._ensure_chat_session_files(item["id"], item["title"])]
            ],
        )
        connection.executemany(
            """
            INSERT OR REPLACE INTO chat_messages(
                id, chat_session_id, role, kind, content, task_run_id, agent_run_ids, metadata, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item["id"],
                    item["chat_session_id"],
                    item["role"],
                    item["kind"],
                    item["content"],
                    item["task_run_id"],
                    _encode(item["agent_run_ids"]),
                    _encode(item["metadata"]),
                    timestamp,
                )
                for item in CHAT_MESSAGE_SEED
            ],
        )
        connection.executemany(
            """
            INSERT OR REPLACE INTO skills(
                id, project_id, parent_skill_id, promoted_from_skill_id, latest_test_run_id, name, description, scope, version,
                source_type, status, test_status, test_score, test_summary, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item["id"],
                    item.get("project_id"),
                    item.get("parent_skill_id"),
                    item.get("promoted_from_skill_id"),
                    item.get("latest_test_run_id"),
                    item["name"],
                    item["description"],
                    item["scope"],
                    item["version"],
                    item["source_type"],
                    item["status"],
                    item.get("test_status", "untested"),
                    item.get("test_score", 0.0),
                    item.get("test_summary", ""),
                    timestamp,
                    timestamp,
                )
                for item in SKILL_SEED
            ],
        )
        connection.executemany(
            """
            INSERT OR REPLACE INTO schedules(
                id, project_id, name, target_type, target_ref, schedule_expression, timezone, enabled, approval_policy, failure_policy, last_run_at, next_run_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item["id"],
                    item.get("project_id"),
                    item["name"],
                    item["target_type"],
                    item["target_ref"],
                    item["schedule_expression"],
                    item["timezone"],
                    item["enabled"],
                    item["approval_policy"],
                    item["failure_policy"],
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
                id, layer, scope, state, pinned, title, summary, content, provenance, source_ref,
                confidence, freshness, tags, created_at, updated_at, last_accessed_at, project_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item["id"],
                    item["layer"],
                    item["scope"],
                    item["state"],
                    int(item.get("pinned", False)),
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
                    item.get("project_id"),
                )
                for item in MEMORY_ITEM_SEED
            ],
        )
        connection.executemany(
            """
            INSERT OR REPLACE INTO entity_policies(
                entity_type, entity_id, project_id, autonomy_mode, kill_switch, approval_bias, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "project",
                    "project-001",
                    "project-001",
                    WORKSPACE_SEED["autonomy_mode"],
                    int(False),
                    WORKSPACE_SEED["approval_bias"],
                    timestamp,
                    timestamp,
                )
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
        project_id: str | None = None,
    ) -> dict[str, Any]:
        timestamp = utc_now()
        task_id = f"task-{uuid4().hex[:12]}"
        title, summary = self._task_seed_defaults(title, summary)
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO tasks(id, project_id, title, summary, status, priority, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (task_id, project_id, title, summary, status, priority, timestamp),
            )
            connection.commit()
        task = self.get_task(task_id)
        if task is None:
            raise KeyError(task_id)
        return task

    def _skill_row(self, row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        data = dict(row)
        data["test_score"] = float(data.get("test_score", 0))
        return data

    def update_task(
        self,
        task_id: str,
        *,
        title: str,
        summary: str,
        status: str,
        priority: str,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        timestamp = utc_now()
        with self.connect() as connection:
            connection.execute(
                "UPDATE tasks SET project_id = ?, title = ?, summary = ?, status = ?, priority = ?, updated_at = ? WHERE id = ?",
                (
                    project_id,
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
                "SELECT id, project_id, title, summary, status, priority FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
            return dict(row) if row is not None else None

    def get_workspace_state(self) -> dict[str, str]:
        with self.connect() as connection:
            rows = connection.execute("SELECT key, value FROM workspace_state").fetchall()
            state = {row["key"]: row["value"] for row in rows}
            for key, value in WORKSPACE_SEED.items():
                state.setdefault(key, value)
            return state

    def update_workspace_state(self, updates: dict[str, str]) -> dict[str, str]:
        if not updates:
            return self.get_workspace_state()
        with self.connect() as connection:
            connection.executemany(
                "INSERT OR REPLACE INTO workspace_state(key, value) VALUES (?, ?)",
                list(updates.items()),
            )
            connection.commit()
        return self.get_workspace_state()

    def list_tasks(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT id, project_id, title, summary, status, priority FROM tasks ORDER BY updated_at DESC, id ASC"
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

    def count_project_threads(self) -> int:
        with self.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM project_threads").fetchone()
            return int(row["count"] if row is not None else 0)

    def count_chat_sessions(self) -> int:
        with self.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM chat_sessions").fetchone()
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
                "SELECT id, name, summary, status, owner, workspace_path, created_at, updated_at FROM projects ORDER BY updated_at DESC, id ASC"
            ).fetchall()
            return [dict(row) for row in rows]

    def list_project_threads(self, project_id: str | None = None) -> list[dict[str, Any]]:
        with self.connect() as connection:
            if project_id:
                rows = connection.execute(
                    """
                    SELECT id, project_id, title, summary, status, context_path, created_at, updated_at
                    FROM project_threads
                    WHERE project_id = ?
                    ORDER BY updated_at DESC, id ASC
                    """,
                    (project_id,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT id, project_id, title, summary, status, context_path, created_at, updated_at
                    FROM project_threads
                    ORDER BY updated_at DESC, id ASC
                    """
                ).fetchall()
            return [dict(row) for row in rows]

    def get_project_thread(self, thread_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT id, project_id, title, summary, status, context_path, created_at, updated_at
                FROM project_threads
                WHERE id = ?
                """,
                (thread_id,),
            ).fetchone()
            return dict(row) if row is not None else None

    def create_project_thread(self, *, project_id: str, title: str, summary: str, status: str = "Open") -> dict[str, Any]:
        timestamp = utc_now()
        thread_id = f"thread-{uuid4().hex[:12]}"
        project = self.get_project(project_id)
        if project is None:
            raise KeyError(project_id)
        normalized_title = title.strip() or "Untitled thread"
        context_path = self._ensure_project_thread_context(project_id, project["name"], thread_id, normalized_title)
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO project_threads(id, project_id, title, summary, status, context_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (thread_id, project_id, normalized_title, summary.strip() or normalized_title, status, context_path, timestamp, timestamp),
            )
            connection.commit()
        return self.get_project_thread(thread_id) or {}

    def update_project_thread(self, thread_id: str, *, title: str, summary: str, status: str) -> dict[str, Any]:
        existing = self.get_project_thread(thread_id)
        if existing is None:
            raise KeyError(thread_id)
        timestamp = utc_now()
        normalized_title = title.strip() or "Untitled thread"
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE project_threads
                SET title = ?, summary = ?, status = ?, updated_at = ?
                WHERE id = ?
                """,
                (normalized_title, summary.strip() or normalized_title, status, timestamp, thread_id),
            )
            connection.commit()
        thread = self.get_project_thread(thread_id)
        if thread is None:
            raise KeyError(thread_id)
        return thread

    def delete_project_thread(self, thread_id: str) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM project_threads WHERE id = ?", (thread_id,))
            connection.commit()

    def list_chat_sessions(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, title, summary, status, context_path, agent_path, soul_path, identity_path, heartbeat_path, created_at, updated_at
                FROM chat_sessions
                ORDER BY updated_at DESC, id ASC
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def _chat_message_row(self, row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        data = dict(row)
        data["agent_run_ids"] = _decode(data.get("agent_run_ids") or "[]", default=[])
        data["metadata"] = _decode(data.get("metadata") or "{}", default={})
        return data

    def _session_reflection_row(self, row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        data = dict(row)
        for key in ("user_preferences", "working_style", "recurring_goals", "personal_context", "identity_refinements", "source_message_ids"):
            data[key] = _decode(data.get(key) or "[]", default=[])
        return data

    def _identity_proposal_row(self, row: sqlite3.Row | None) -> dict[str, Any] | None:
        return dict(row) if row is not None else None

    def _chat_attachment_row(self, row: sqlite3.Row | None) -> dict[str, Any] | None:
        return dict(row) if row is not None else None

    def list_chat_messages(self, chat_session_id: str, *, limit: int = 200) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, chat_session_id, role, kind, content, task_run_id, agent_run_ids, metadata, created_at
                FROM chat_messages
                WHERE chat_session_id = ?
                ORDER BY rowid ASC
                LIMIT ?
                """,
                (chat_session_id, limit),
            ).fetchall()
            messages: list[dict[str, Any]] = []
            for row in rows:
                message = self._chat_message_row(row)
                if message is not None:
                    messages.append(message)
            return messages

    def create_chat_message(
        self,
        *,
        chat_session_id: str,
        role: str,
        kind: str,
        content: str,
        task_run_id: str | None = None,
        agent_run_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        timestamp = utc_now()
        message_id = f"chat-message-{uuid4().hex[:12]}"
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO chat_messages(
                    id, chat_session_id, role, kind, content, task_run_id, agent_run_ids, metadata, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    chat_session_id,
                    role,
                    kind,
                    content.strip(),
                    task_run_id,
                    _encode(agent_run_ids or []),
                    _encode(metadata or {}),
                    timestamp,
                ),
            )
            connection.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
                (timestamp, chat_session_id),
            )
            connection.commit()
        return self.get_chat_message(message_id) or {}

    def get_chat_message(self, message_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT id, chat_session_id, role, kind, content, task_run_id, agent_run_ids, metadata, created_at
                FROM chat_messages
                WHERE id = ?
                """,
                (message_id,),
            ).fetchone()
            return self._chat_message_row(row)

    def list_chat_attachments(self, chat_session_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, chat_session_id, mode, project_id, project_thread_id, original_name, stored_name,
                       content_type, size_bytes, storage_path, created_at
                FROM chat_attachments
                WHERE chat_session_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (chat_session_id, limit),
            ).fetchall()
            return [self._chat_attachment_row(row) for row in rows if row is not None]

    def get_chat_attachment(self, attachment_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT id, chat_session_id, mode, project_id, project_thread_id, original_name, stored_name,
                       content_type, size_bytes, storage_path, created_at
                FROM chat_attachments
                WHERE id = ?
                """,
                (attachment_id,),
            ).fetchone()
            return self._chat_attachment_row(row)

    def create_chat_attachment(
        self,
        *,
        chat_session_id: str,
        mode: str,
        project_id: str | None,
        project_thread_id: str | None,
        original_name: str,
        stored_name: str,
        content_type: str,
        size_bytes: int,
        storage_path: str,
    ) -> dict[str, Any]:
        attachment_id = f"attachment-{uuid4().hex[:12]}"
        timestamp = utc_now()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO chat_attachments(
                    id, chat_session_id, mode, project_id, project_thread_id, original_name, stored_name,
                    content_type, size_bytes, storage_path, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attachment_id,
                    chat_session_id,
                    mode,
                    project_id,
                    project_thread_id,
                    original_name,
                    stored_name,
                    content_type,
                    size_bytes,
                    storage_path,
                    timestamp,
                ),
            )
            connection.commit()
        return self.get_chat_attachment(attachment_id) or {}

    def list_session_reflections(self, chat_session_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, chat_session_id, summary, user_preferences, working_style, recurring_goals,
                       personal_context, identity_refinements, source_message_ids, created_at
                FROM session_reflections
                WHERE chat_session_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (chat_session_id, limit),
            ).fetchall()
            items: list[dict[str, Any]] = []
            for row in rows:
                item = self._session_reflection_row(row)
                if item is not None:
                    items.append(item)
            return items

    def create_session_reflection(
        self,
        *,
        chat_session_id: str,
        summary: str,
        user_preferences: list[str] | None = None,
        working_style: list[str] | None = None,
        recurring_goals: list[str] | None = None,
        personal_context: list[str] | None = None,
        identity_refinements: list[str] | None = None,
        source_message_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        timestamp = utc_now()
        reflection_id = f"reflection-{uuid4().hex[:12]}"
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO session_reflections(
                    id, chat_session_id, summary, user_preferences, working_style, recurring_goals,
                    personal_context, identity_refinements, source_message_ids, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reflection_id,
                    chat_session_id,
                    summary,
                    _encode(user_preferences or []),
                    _encode(working_style or []),
                    _encode(recurring_goals or []),
                    _encode(personal_context or []),
                    _encode(identity_refinements or []),
                    _encode(source_message_ids or []),
                    timestamp,
                ),
            )
            connection.commit()
        return self.list_session_reflections(chat_session_id, limit=1)[0]

    def list_identity_proposals(self, chat_session_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, chat_session_id, target_file, proposal_kind, rationale, proposed_content, status, created_at, updated_at
                FROM identity_proposals
                WHERE chat_session_id = ?
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT ?
                """,
                (chat_session_id, limit),
            ).fetchall()
            return [self._identity_proposal_row(row) for row in rows if row is not None]

    def create_identity_proposal(
        self,
        *,
        chat_session_id: str,
        target_file: str,
        proposal_kind: str,
        rationale: str,
        proposed_content: str,
        status: str = "proposed",
    ) -> dict[str, Any]:
        timestamp = utc_now()
        proposal_id = f"identity-proposal-{uuid4().hex[:12]}"
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO identity_proposals(
                    id, chat_session_id, target_file, proposal_kind, rationale, proposed_content, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal_id,
                    chat_session_id,
                    target_file,
                    proposal_kind,
                    rationale,
                    proposed_content,
                    status,
                    timestamp,
                    timestamp,
                ),
            )
            connection.commit()
        return self.list_identity_proposals(chat_session_id, limit=1)[0]

    def get_chat_session(self, session_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT id, title, summary, status, context_path, agent_path, soul_path, identity_path, heartbeat_path, created_at, updated_at
                FROM chat_sessions
                WHERE id = ?
                """,
                (session_id,),
            ).fetchone()
            return dict(row) if row is not None else None

    def create_chat_session(self, *, title: str, summary: str, status: str = "Active") -> dict[str, Any]:
        timestamp = utc_now()
        session_id = f"session-{uuid4().hex[:12]}"
        normalized_title = title.strip() or "Untitled session"
        paths = self._ensure_chat_session_files(session_id, normalized_title)
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO chat_sessions(
                    id, title, summary, status, context_path, agent_path, soul_path, identity_path, heartbeat_path, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    normalized_title,
                    summary.strip() or normalized_title,
                    status,
                    paths["context_path"],
                    paths["agent_path"],
                    paths["soul_path"],
                    paths["identity_path"],
                    paths["heartbeat_path"],
                    timestamp,
                    timestamp,
                ),
            )
            connection.commit()
        self.create_chat_message(
            chat_session_id=session_id,
            role="assistant",
            kind="message",
            content=f"Persistent session {normalized_title} initialized. I will keep continuity here as we work.",
            metadata={"source": "session.create"},
        )
        return self.get_chat_session(session_id) or {}

    def update_chat_session(self, session_id: str, *, title: str, summary: str, status: str) -> dict[str, Any]:
        existing = self.get_chat_session(session_id)
        if existing is None:
            raise KeyError(session_id)
        timestamp = utc_now()
        normalized_title = title.strip() or "Untitled session"
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE chat_sessions
                SET title = ?, summary = ?, status = ?, updated_at = ?
                WHERE id = ?
                """,
                (normalized_title, summary.strip() or normalized_title, status, timestamp, session_id),
            )
            connection.commit()
        session = self.get_chat_session(session_id)
        if session is None:
            raise KeyError(session_id)
        return session

    def delete_chat_session(self, session_id: str) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            connection.commit()

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT id, name, summary, status, owner, workspace_path, created_at, updated_at FROM projects WHERE id = ?",
                (project_id,),
            ).fetchone()
            return dict(row) if row is not None else None

    def create_project(self, *, name: str, summary: str, status: str = "Planned", owner: str = "Gnosys") -> dict[str, Any]:
        timestamp = utc_now()
        project_id = f"project-{uuid4().hex[:12]}"
        normalized_name = name.strip() or "Untitled project"
        workspace_path = self._ensure_project_workspace(project_id, normalized_name)
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO projects(id, name, summary, status, owner, workspace_path, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    project_id,
                    normalized_name,
                    summary.strip() or normalized_name,
                    status,
                    owner.strip() or "Gnosys",
                    workspace_path,
                    timestamp,
                    timestamp,
                ),
            )
            connection.commit()
        return self.get_project(project_id) or {}

    def update_project(self, project_id: str, *, name: str, summary: str, status: str, owner: str) -> dict[str, Any]:
        timestamp = utc_now()
        normalized_name = name.strip() or "Untitled project"
        project = self.get_project(project_id)
        if project is None:
            raise KeyError(project_id)
        workspace_path = project["workspace_path"] or self._ensure_project_workspace(project_id, normalized_name)
        with self.connect() as connection:
            connection.execute(
                "UPDATE projects SET name = ?, summary = ?, status = ?, owner = ?, workspace_path = ?, updated_at = ? WHERE id = ?",
                (
                    normalized_name,
                    summary.strip() or normalized_name,
                    status,
                    owner.strip() or "Gnosys",
                    workspace_path,
                    timestamp,
                    project_id,
                ),
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
                """
                SELECT id, project_id, parent_skill_id, promoted_from_skill_id, latest_test_run_id, name, description, scope, version,
                       source_type, status, test_status, test_score, test_summary, created_at, updated_at
                FROM skills
                ORDER BY updated_at DESC, id ASC
                """
            ).fetchall()
            return [self._skill_row(row) or {} for row in rows]

    def get_skill(self, skill_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT id, project_id, parent_skill_id, promoted_from_skill_id, latest_test_run_id, name, description, scope, version,
                       source_type, status, test_status, test_score, test_summary, created_at, updated_at
                FROM skills
                WHERE id = ?
                """,
                (skill_id,),
            ).fetchone()
            return self._skill_row(row)

    def create_skill(
        self,
        *,
        name: str,
        description: str,
        scope: str = "workspace",
        version: str = "0.1.0",
        source_type: str = "authored",
        status: str = "draft",
        parent_skill_id: str | None = None,
        promoted_from_skill_id: str | None = None,
        latest_test_run_id: str | None = None,
        test_status: str = "untested",
        test_score: float = 0.0,
        test_summary: str = "",
        project_id: str | None = None,
    ) -> dict[str, Any]:
        timestamp = utc_now()
        skill_id = f"skill-{uuid4().hex[:12]}"
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO skills(
                    id, project_id, parent_skill_id, promoted_from_skill_id, latest_test_run_id, name, description, scope, version,
                    source_type, status, test_status, test_score, test_summary, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    skill_id,
                    project_id,
                    parent_skill_id,
                    promoted_from_skill_id,
                    latest_test_run_id,
                    name.strip() or "Untitled skill",
                    description.strip() or name.strip() or "Untitled skill",
                    scope,
                    version,
                    source_type,
                    status,
                    test_status,
                    test_score,
                    test_summary,
                    timestamp,
                    timestamp,
                ),
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
        parent_skill_id: str | None = None,
        promoted_from_skill_id: str | None = None,
        latest_test_run_id: str | None = None,
        test_status: str | None = None,
        test_score: float | None = None,
        test_summary: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        timestamp = utc_now()
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE skills
                SET project_id = ?,
                    parent_skill_id = COALESCE(?, parent_skill_id),
                    promoted_from_skill_id = COALESCE(?, promoted_from_skill_id),
                    latest_test_run_id = COALESCE(?, latest_test_run_id),
                    name = ?, description = ?, scope = ?, version = ?, source_type = ?, status = ?,
                    test_status = COALESCE(?, test_status),
                    test_score = COALESCE(?, test_score),
                    test_summary = COALESCE(?, test_summary),
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    project_id,
                    parent_skill_id,
                    promoted_from_skill_id,
                    latest_test_run_id,
                    name.strip() or "Untitled skill",
                    description.strip() or name.strip() or "Untitled skill",
                    scope,
                    version,
                    source_type,
                    status,
                    test_status,
                    test_score,
                    test_summary,
                    timestamp,
                    skill_id,
                ),
            )
            connection.commit()
        skill = self.get_skill(skill_id)
        if skill is None:
            raise KeyError(skill_id)
        return skill

    def create_skill_test_run(
        self,
        *,
        skill_id: str,
        scenario: str,
        expected_outcome: str,
        observed_outcome: str,
        passed: bool,
        score: float,
        summary: str,
        requested_by: str,
    ) -> dict[str, Any]:
        timestamp = utc_now()
        test_run_id = f"skill-test-{uuid4().hex[:12]}"
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO skill_test_runs(
                    id, skill_id, scenario, expected_outcome, observed_outcome, passed, score, summary, requested_by, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    test_run_id,
                    skill_id,
                    scenario,
                    expected_outcome,
                    observed_outcome,
                    int(passed),
                    score,
                    summary,
                    requested_by,
                    timestamp,
                ),
            )
            connection.commit()
        return self.get_skill_test_run(test_run_id) or {}

    def get_skill_test_run(self, test_run_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT id, skill_id, scenario, expected_outcome, observed_outcome, passed, score, summary, requested_by, created_at
                FROM skill_test_runs
                WHERE id = ?
                """,
                (test_run_id,),
            ).fetchone()
            if row is None:
                return None
            item = dict(row)
            item["passed"] = bool(item["passed"])
            item["score"] = float(item["score"])
            return item

    def list_skill_test_runs(self, *, skill_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        query = [
            "SELECT id, skill_id, scenario, expected_outcome, observed_outcome, passed, score, summary, requested_by, created_at",
            "FROM skill_test_runs",
        ]
        params: list[Any] = []
        if skill_id:
            query.append("WHERE skill_id = ?")
            params.append(skill_id)
        query.append("ORDER BY created_at DESC, id DESC")
        query.append("LIMIT ?")
        params.append(limit)
        sql = " ".join(query)
        with self.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
            result = []
            for row in rows:
                item = dict(row)
                item["passed"] = bool(item["passed"])
                item["score"] = float(item["score"])
                result.append(item)
            return result

    def count_skill_test_runs(self) -> int:
        with self.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM skill_test_runs").fetchone()
            return int(row["count"] if row is not None else 0)

    def delete_skill(self, skill_id: str) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM skills WHERE id = ?", (skill_id,))
            connection.commit()

    def list_schedules(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, project_id, name, target_type, target_ref, schedule_expression, timezone, enabled, approval_policy, failure_policy, last_run_at, next_run_at, created_at, updated_at
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
                SELECT id, project_id, name, target_type, target_ref, schedule_expression, timezone, enabled, approval_policy, failure_policy, last_run_at, next_run_at, created_at, updated_at
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
        approval_policy: str = "inherit",
        failure_policy: str = "retry_once",
        last_run_at: str | None = None,
        next_run_at: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        timestamp = utc_now()
        schedule_id = f"schedule-{uuid4().hex[:12]}"
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO schedules(
                    id, project_id, name, target_type, target_ref, schedule_expression, timezone, enabled, approval_policy, failure_policy, last_run_at, next_run_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    schedule_id,
                    project_id,
                    name.strip() or "Untitled schedule",
                    target_type,
                    target_ref,
                    schedule_expression,
                    timezone,
                    int(enabled),
                    approval_policy,
                    failure_policy,
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
        approval_policy: str = "inherit",
        failure_policy: str = "retry_once",
        last_run_at: str | None = None,
        next_run_at: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        timestamp = utc_now()
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE schedules
                SET project_id = ?, name = ?, target_type = ?, target_ref = ?, schedule_expression = ?, timezone = ?, enabled = ?, approval_policy = ?, failure_policy = ?, last_run_at = ?, next_run_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    project_id,
                    name.strip() or "Untitled schedule",
                    target_type,
                    target_ref,
                    schedule_expression,
                    timezone,
                    int(enabled),
                    approval_policy,
                    failure_policy,
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
        project_id: str | None = None,
        state: str | None = None,
    ) -> list[dict[str, Any]]:
        query = [
            "SELECT id, layer, scope, project_id, state, pinned, title, summary, content, provenance, source_ref, confidence, freshness, tags, created_at, updated_at, last_accessed_at",
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
        if project_id:
            conditions.append("(project_id = ? OR project_id IS NULL)")
            params.append(project_id)
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
                    "pinned": bool(row["pinned"]),
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
                SELECT id, layer, scope, project_id, state, pinned, title, summary, content, provenance, source_ref,
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
                "pinned": bool(row["pinned"]),
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
                    id, layer, scope, state, pinned, title, summary, content, provenance, source_ref,
                    confidence, freshness, tags, created_at, updated_at, last_accessed_at, project_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["id"],
                    item["layer"],
                    item["scope"],
                    item["state"],
                    int(item.get("pinned", existing["pinned"] if existing is not None else False)),
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
                    item.get("project_id"),
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

    def pin_memory_item(self, item_id: str, pinned: bool = True) -> dict[str, Any]:
        timestamp = utc_now()
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE memory_items
                SET pinned = ?, updated_at = ?
                WHERE id = ?
                """,
                (int(pinned), timestamp, item_id),
            )
            connection.commit()
        item = self.get_memory_item(item_id)
        if item is None:
            raise KeyError(item_id)
        return item

    def forget_memory_item(self, item_id: str) -> dict[str, Any]:
        timestamp = utc_now()
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE memory_items
                SET state = 'archived', pinned = 0, updated_at = ?
                WHERE id = ?
                """,
                (timestamp, item_id),
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
        project_id: str | None = None,
        project_thread_id: str | None = None,
        chat_session_id: str | None = None,
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
                    id, task_id, objective, requested_by, project_id, project_thread_id, chat_session_id, mode, status, summary, step_count,
                    approval_required, created_at, updated_at, completed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    task_id,
                    objective,
                    requested_by,
                    project_id,
                    project_thread_id,
                    chat_session_id,
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
                SELECT id, task_id, objective, requested_by, project_id, project_thread_id, chat_session_id, mode, status, summary, step_count,
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
                SELECT id, task_id, objective, requested_by, project_id, project_thread_id, chat_session_id, mode, status, summary, step_count,
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

    def create_approval_request(
        self,
        *,
        action: str,
        subject_type: str,
        subject_ref: str,
        sensitivity: str,
        reason: str,
        payload: dict[str, Any],
        requested_by: str,
        status: str = "pending",
    ) -> dict[str, Any]:
        approval_id = f"approval-{uuid4().hex[:12]}"
        timestamp = utc_now()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO approval_requests(
                    id, action, subject_type, subject_ref, sensitivity, status, reason,
                    payload, requested_by, created_at, updated_at, resolved_at, resolved_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
                """,
                (
                    approval_id,
                    action,
                    subject_type,
                    subject_ref,
                    sensitivity,
                    status,
                    reason,
                    _encode(payload),
                    requested_by,
                    timestamp,
                    timestamp,
                ),
            )
            connection.commit()
        return self.get_approval_request(approval_id) or {}

    def list_approval_requests(self, limit: int = 25) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, action, subject_type, subject_ref, sensitivity, status, reason,
                       payload, requested_by, created_at, updated_at, resolved_at, resolved_by
                FROM approval_requests
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [self._approval_row(row) for row in rows]

    def get_approval_request(self, approval_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT id, action, subject_type, subject_ref, sensitivity, status, reason,
                       payload, requested_by, created_at, updated_at, resolved_at, resolved_by
                FROM approval_requests
                WHERE id = ?
                """,
                (approval_id,),
            ).fetchone()
            return self._approval_row(row) if row is not None else None

    def update_approval_request(
        self,
        approval_id: str,
        *,
        status: str,
        resolved_by: str | None = None,
    ) -> dict[str, Any]:
        timestamp = utc_now()
        resolved_at = timestamp if status in {"approved", "rejected"} else None
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE approval_requests
                SET status = ?, updated_at = ?, resolved_at = COALESCE(?, resolved_at), resolved_by = COALESCE(?, resolved_by)
                WHERE id = ?
                """,
                (status, timestamp, resolved_at, resolved_by, approval_id),
            )
            connection.commit()
        request = self.get_approval_request(approval_id)
        if request is None:
            raise KeyError(approval_id)
        return request

    def count_approval_requests(self) -> int:
        with self.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM approval_requests").fetchone()
            return int(row["count"] if row is not None else 0)

    def upsert_entity_policy(
        self,
        *,
        entity_type: str,
        entity_id: str,
        project_id: str | None = None,
        autonomy_mode: str,
        kill_switch: bool,
        approval_bias: str,
    ) -> dict[str, Any]:
        timestamp = utc_now()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO entity_policies(
                    entity_type, entity_id, project_id, autonomy_mode, kill_switch, approval_bias, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(entity_type, entity_id) DO UPDATE SET
                    project_id = excluded.project_id,
                    autonomy_mode = excluded.autonomy_mode,
                    kill_switch = excluded.kill_switch,
                    approval_bias = excluded.approval_bias,
                    updated_at = excluded.updated_at
                """,
                (entity_type, entity_id, project_id, autonomy_mode, int(kill_switch), approval_bias, timestamp, timestamp),
            )
            connection.commit()
        policy = self.get_entity_policy(entity_type, entity_id)
        if policy is None:
            raise RuntimeError(f"Unable to persist entity policy {entity_type}:{entity_id}")
        return policy

    def get_entity_policy(self, entity_type: str, entity_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT entity_type, entity_id, project_id, autonomy_mode, kill_switch, approval_bias, created_at, updated_at
                FROM entity_policies
                WHERE entity_type = ? AND entity_id = ?
                """,
                (entity_type, entity_id),
            ).fetchone()
            if row is None:
                return None
            data = dict(row)
            data["kill_switch"] = bool(data["kill_switch"])
            return data

    def list_entity_policies(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT entity_type, entity_id, project_id, autonomy_mode, kill_switch, approval_bias, created_at, updated_at
                FROM entity_policies
                ORDER BY updated_at DESC, entity_type ASC, entity_id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            results = []
            for row in rows:
                item = dict(row)
                item["kill_switch"] = bool(item["kill_switch"])
                results.append(item)
            return results

    def count_entity_policies(self) -> int:
        with self.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM entity_policies").fetchone()
            return int(row["count"] if row is not None else 0)

    def create_schedule_run(
        self,
        *,
        schedule_id: str,
        schedule_name: str,
        target_type: str,
        target_ref: str,
        requested_by: str,
        result_summary: str,
        attempt_number: int = 1,
        retry_of_run_id: str | None = None,
        task_run_id: str | None = None,
        status: str = "running",
        last_error: str | None = None,
    ) -> dict[str, Any]:
        timestamp = utc_now()
        run_id = f"schedule-run-{uuid4().hex[:12]}"
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO schedule_runs(
                    id, schedule_id, schedule_name, target_type, target_ref, status, attempt_number,
                    retry_of_run_id, task_run_id, requested_by, result_summary, last_error,
                    created_at, updated_at, completed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    schedule_id,
                    schedule_name,
                    target_type,
                    target_ref,
                    status,
                    attempt_number,
                    retry_of_run_id,
                    task_run_id,
                    requested_by,
                    result_summary,
                    last_error,
                    timestamp,
                    timestamp,
                    None,
                ),
            )
            connection.commit()
        return self.get_schedule_run(run_id) or {}

    def update_schedule_run(
        self,
        run_id: str,
        *,
        status: str,
        result_summary: str | None = None,
        task_run_id: str | None = None,
        last_error: str | None = None,
        completed: bool = False,
    ) -> dict[str, Any]:
        timestamp = utc_now()
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE schedule_runs
                SET status = ?,
                    result_summary = COALESCE(?, result_summary),
                    task_run_id = COALESCE(?, task_run_id),
                    last_error = COALESCE(?, last_error),
                    updated_at = ?,
                    completed_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    result_summary,
                    task_run_id,
                    last_error,
                    timestamp,
                    timestamp if completed else None,
                    run_id,
                ),
            )
            connection.commit()
        run = self.get_schedule_run(run_id)
        if run is None:
            raise KeyError(run_id)
        return run

    def get_schedule_run(self, run_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT id, schedule_id, schedule_name, target_type, target_ref, status, attempt_number,
                       retry_of_run_id, task_run_id, requested_by, result_summary, last_error,
                       created_at, updated_at, completed_at
                FROM schedule_runs
                WHERE id = ?
                """,
                (run_id,),
            ).fetchone()
            return dict(row) if row is not None else None

    def list_schedule_runs(
        self,
        *,
        limit: int = 50,
        schedule_id: str | None = None,
        task_run_id: str | None = None,
        retry_of_run_id: str | None = None,
    ) -> list[dict[str, Any]]:
        query = [
            "SELECT id, schedule_id, schedule_name, target_type, target_ref, status, attempt_number, retry_of_run_id, task_run_id, requested_by, result_summary, last_error, created_at, updated_at, completed_at",
            "FROM schedule_runs",
        ]
        params: list[Any] = []
        conditions: list[str] = []
        if schedule_id:
            conditions.append("schedule_id = ?")
            params.append(schedule_id)
        if task_run_id:
            conditions.append("task_run_id = ?")
            params.append(task_run_id)
        if retry_of_run_id:
            conditions.append("retry_of_run_id = ?")
            params.append(retry_of_run_id)
        if conditions:
            query.append("WHERE " + " AND ".join(conditions))
        query.append("ORDER BY created_at DESC, id DESC")
        query.append("LIMIT ?")
        params.append(limit)
        sql = " ".join(query)
        with self.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
            return [dict(row) for row in rows]

    def count_schedule_runs(self) -> int:
        with self.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM schedule_runs").fetchone()
            return int(row["count"] if row is not None else 0)

    def list_replay_events(self, *, task_run_id: str, limit: int = 200) -> list[dict[str, Any]]:
        events = self.list_events(limit=limit)
        results: list[dict[str, Any]] = []
        for event in reversed(events):
            payload = event.get("payload", {})
            if not isinstance(payload, dict):
                continue
            if payload.get("task_run_id") == task_run_id or payload.get("run_id") == task_run_id:
                results.append(event)
                continue
            approval_request = payload.get("approval_request")
            if isinstance(approval_request, dict) and approval_request.get("task_run_id") == task_run_id:
                results.append(event)
                continue
            nested_payload = approval_request.get("payload") if isinstance(approval_request, dict) else None
            if isinstance(nested_payload, dict) and nested_payload.get("task_run_id") == task_run_id:
                results.append(event)
        return results

    def _approval_row(self, row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return {
            "id": row["id"],
            "action": row["action"],
            "subject_type": row["subject_type"],
            "subject_ref": row["subject_ref"],
            "sensitivity": row["sensitivity"],
            "status": row["status"],
            "reason": row["reason"],
            "payload": _decode(row["payload"]),
            "requested_by": row["requested_by"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "resolved_at": row["resolved_at"],
            "resolved_by": row["resolved_by"],
        }

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
        project_threads = self.list_project_threads()
        chat_sessions = self.list_chat_sessions()
        skills = self.list_skills()
        schedules = self.list_schedules()
        memory_layers = self.list_memory_layers()
        memory_items = self.list_memory_items(limit=10)
        task_runs = self.list_task_runs(limit=10)
        agent_runs = self.list_agent_runs(limit=25)
        schedule_runs = self.list_schedule_runs(limit=10)
        entity_policies = self.list_entity_policies(limit=10)
        recent_events = self.list_events()
        approvals = self.list_approval_requests(limit=10)

        return {
            "workspace": {
                "name": workspace.get("name", "Gnosys"),
                "mode": workspace.get("mode", "Supervised"),
                "autonomy_mode": workspace.get("autonomy_mode", "Supervised"),
                "kill_switch": workspace.get("kill_switch", "false").lower() == "true",
                "approval_bias": workspace.get("approval_bias", "supervised"),
                "mode_label": workspace.get("mode_label", "Global autonomy and approval policy"),
                "status": workspace.get("status", "Bootstrapping"),
                "active_project": workspace.get("active_project", "Core Console"),
                "phase": workspace.get("phase", "Persistence and event log foundation"),
            },
            "tasks": tasks,
            "agents": agents,
            "projects": projects,
            "project_threads": project_threads,
            "chat_sessions": chat_sessions,
            "skills": skills,
            "schedules": schedules,
            "memory_layers": memory_layers,
            "memory_items": memory_items,
            "task_runs": task_runs,
            "agent_runs": agent_runs,
            "schedule_runs": schedule_runs,
            "entity_policies": entity_policies,
            "approval_requests": approvals,
            "recent_events": recent_events,
            "counts": {
                "tasks": len(tasks),
                "agents": len(agents),
                "projects": self.count_projects(),
                "project_threads": self.count_project_threads(),
                "chat_sessions": self.count_chat_sessions(),
                "skills": self.count_skills(),
                "skill_test_runs": self.count_skill_test_runs(),
                "schedules": self.count_schedules(),
                "memory_layers": len(memory_layers),
                "memory_items": self.count_memory_items(),
                "task_runs": self.count_task_runs(),
                "agent_runs": self.count_agent_runs(),
                "schedule_runs": self.count_schedule_runs(),
                "entity_policies": self.count_entity_policies(),
                "approval_requests": self.count_approval_requests(),
                "events": self.count_events(),
            },
        }
