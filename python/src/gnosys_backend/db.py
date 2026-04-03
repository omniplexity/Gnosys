from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence


SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS memories (
        id TEXT PRIMARY KEY,
        memory_type TEXT NOT NULL,
        tier TEXT NOT NULL,
        content TEXT NOT NULL,
        tags_json TEXT NOT NULL,
        metadata_json TEXT NOT NULL,
        keywords TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        last_accessed_at TEXT,
        expires_at TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_memories_memory_type ON memories(memory_type)",
    "CREATE INDEX IF NOT EXISTS idx_memories_tier ON memories(tier)",
    "CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at DESC)",
    # Trajectories table for learning system
    """
    CREATE TABLE IF NOT EXISTS trajectories (
        id TEXT PRIMARY KEY,
        task TEXT NOT NULL,
        started_at TEXT NOT NULL,
        completed_at TEXT,
        success INTEGER,
        agent_type TEXT NOT NULL,
        query TEXT,
        response_preview TEXT,
        steps_json TEXT NOT NULL,
        metrics_json TEXT NOT NULL,
        error TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_trajectories_started_at ON trajectories(started_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_trajectories_agent_type ON trajectories(agent_type)",
    # Pipeline profiles table
    """
    CREATE TABLE IF NOT EXISTS pipeline_profiles (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        agents_json TEXT NOT NULL,
        coordination TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    # Agents table
    """
    CREATE TABLE IF NOT EXISTS agents (
        id TEXT PRIMARY KEY,
        role TEXT NOT NULL,
        agent_type TEXT NOT NULL,
        context_json TEXT NOT NULL,
        tools_json TEXT NOT NULL,
        status TEXT NOT NULL,
        result TEXT,
        parent_id TEXT,
        created_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_agents_parent_id ON agents(parent_id)",
    # Learning patterns table
    """
    CREATE TABLE IF NOT EXISTS learning_patterns (
        id TEXT PRIMARY KEY,
        pattern_type TEXT NOT NULL,
        description TEXT NOT NULL,
        frequency INTEGER NOT NULL,
        success_rate REAL NOT NULL,
        tools_json TEXT NOT NULL,
        metadata_json TEXT NOT NULL,
        detected_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_learning_patterns_type ON learning_patterns(pattern_type)",
    # Skills table
    """
    CREATE TABLE IF NOT EXISTS skills (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        version TEXT NOT NULL,
        triggers_json TEXT NOT NULL,
        workflow_json TEXT NOT NULL,
        tools_json TEXT NOT NULL,
        parameters_json TEXT NOT NULL,
        description TEXT,
        compounds_from_json TEXT NOT NULL,
        use_count INTEGER NOT NULL DEFAULT 0,
        success_rate REAL NOT NULL DEFAULT 0.0,
        trigger_count INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        last_used_at TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_skills_name ON skills(name)",
    # Scheduled tasks table
    """
    CREATE TABLE IF NOT EXISTS scheduled_tasks (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        schedule TEXT NOT NULL,
        task_type TEXT NOT NULL,
        enabled INTEGER NOT NULL DEFAULT 1,
        description TEXT,
        action_json TEXT NOT NULL,
        delivery_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        last_run_at TEXT,
        next_run_at TEXT,
        run_count INTEGER NOT NULL DEFAULT 0
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_next_run ON scheduled_tasks(next_run_at)",
    "CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_enabled ON scheduled_tasks(enabled)",
    # Scheduled task execution history
    """
    CREATE TABLE IF NOT EXISTS scheduled_task_executions (
        id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL,
        executed_at TEXT NOT NULL,
        success INTEGER NOT NULL,
        result_json TEXT,
        error TEXT,
        duration_ms INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (task_id) REFERENCES scheduled_tasks(id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_task_executions_task_id ON scheduled_task_executions(task_id)",
    "CREATE INDEX IF NOT EXISTS idx_task_executions_executed_at ON scheduled_task_executions(executed_at DESC)",
)


class Database:
    def __init__(self, db_path: Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._configure()
        self.initialize()

    @property
    def db_path(self) -> Path:
        return self._db_path

    def _configure(self) -> None:
        with self._lock:
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA foreign_keys=ON")
            self._connection.execute("PRAGMA synchronous=NORMAL")

    def initialize(self) -> None:
        with self.transaction() as connection:
            for statement in SCHEMA_STATEMENTS:
                connection.execute(statement)

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            try:
                yield self._connection
                self._connection.commit()
            except Exception:
                self._connection.rollback()
                raise

    def execute(
        self, sql: str, parameters: Sequence[Any] | None = None
    ) -> sqlite3.Cursor:
        with self.transaction() as connection:
            return connection.execute(sql, tuple(parameters or ()))

    def fetch_all(
        self, sql: str, parameters: Sequence[Any] | None = None
    ) -> list[sqlite3.Row]:
        with self._lock:
            cursor = self._connection.execute(sql, tuple(parameters or ()))
            return list(cursor.fetchall())

    def fetch_one(
        self, sql: str, parameters: Sequence[Any] | None = None
    ) -> sqlite3.Row | None:
        with self._lock:
            cursor = self._connection.execute(sql, tuple(parameters or ()))
            return cursor.fetchone()

    def ping(self) -> bool:
        row = self.fetch_one("SELECT 1 AS ok")
        return bool(row and row["ok"] == 1)

    def close(self) -> None:
        with self._lock:
            self._connection.close()


def encode_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def decode_json(value: str) -> Any:
    return json.loads(value)
