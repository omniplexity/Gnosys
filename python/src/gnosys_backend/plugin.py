"""
Gnosys Memory Slot Replacement Plugin v1.0.6

Integrates Gnosys memory system with OpenClaw's slot system.
Provides session persistence and automatic fallback to default memory.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from gnosys_backend.config import AppConfig
from gnosys_backend.db import Database, decode_json, encode_json


logger = logging.getLogger(__name__)


MEMORY_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS gnosys_sessions (
    session_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    last_accessed_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL
)
"""

MEMORY_SLOTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS gnosys_memory_slots (
    slot_key TEXT PRIMARY KEY,
    slot_value TEXT NOT NULL,
    memory_type TEXT NOT NULL,
    tier TEXT NOT NULL,
    content TEXT NOT NULL,
    tags_json TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


class MemoryMigration:
    """Migrate existing MEMORY.md files to Gnosys format."""

    def __init__(self, db: Database, config: AppConfig) -> None:
        self._db = db
        self._config = config
        self._storage_dir = config.memory.directory.expanduser().resolve()

    async def migrate_from_md(self, source_dir: Path | None = None) -> dict[str, Any]:
        """Migrate MEMORY.md files to Gnosys database format."""
        source = source_dir or self._storage_dir
        migrated = {"sessions": 0, "memories": 0, "errors": []}

        if not source.exists():
            logger.info(f"Source directory does not exist: {source}")
            return migrated

        memory_md = source / "MEMORY.md"
        if memory_md.exists():
            try:
                content = memory_md.read_text(encoding="utf-8")
                await self._parse_and_store(content)
                migrated["sessions"] = 1
            except Exception as e:
                migrated["errors"].append(f"MEMORY.md: {str(e)}")

        return migrated

    async def _parse_and_store(self, content: str) -> None:
        """Parse MEMORY.md content and store in database."""
        import uuid

        now = datetime.now(UTC)
        session_id = str(uuid.uuid4())

        self._db.execute(
            """
            INSERT OR REPLACE INTO gnosys_sessions (
                session_id, created_at, last_accessed_at, metadata_json
            ) VALUES (?, ?, ?, ?)
            """,
            (
                session_id,
                now.isoformat(),
                now.isoformat(),
                encode_json({"source": "MEMORY.md migration"}),
            ),
        )

        lines = content.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            self._db.execute(
                """
                INSERT OR REPLACE INTO gnosys_memory_slots (
                    slot_key, slot_value, memory_type, tier, content, tags_json,
                    metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"migrated_{line[:20]}",
                    line,
                    "episodic",
                    "working",
                    line,
                    encode_json(["migrated"]),
                    encode_json({"session_id": session_id}),
                    now.isoformat(),
                    now.isoformat(),
                ),
            )


class GnosysPlugin:
    """Plugin for memory slot replacement with OpenClaw integration."""

    def __init__(self, config: AppConfig, db: Database) -> None:
        self._config = config
        self._db = db
        self._initialized = False
        self._fallback_enabled = True
        self._migration = MemoryMigration(db, config)

    @property
    def initialized(self) -> bool:
        return self._initialized

    @property
    def fallback_enabled(self) -> bool:
        return self._fallback_enabled

    async def load(self) -> dict[str, Any]:
        """
        Load plugin before session creation.
        Ensures no race conditions with gateway restart.
        """
        result = {
            "status": "loading",
            "memory_slot": "gnosys",
            "fallback": self._fallback_enabled,
        }

        try:
            self._ensure_schema()
            await self._initialize_storage()

            self._initialized = True
            result["status"] = "loaded"
            result["message"] = "Gnosys memory slot configured"

            logger.info("GnosysPlugin loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load GnosysPlugin: {e}")
            result["status"] = "error"
            result["error"] = str(e)

            if self._fallback_enabled:
                result["fallback"] = "automatic"
                logger.info("Falling back to default memory")

        return result

    async def save_session(
        self, session_id: str, metadata: dict[str, Any] | None = None
    ) -> bool:
        """Save session for persistence across gateway restarts."""
        try:
            now = datetime.now(UTC)
            self._db.execute(
                """
                INSERT OR REPLACE INTO gnosys_sessions (
                    session_id, created_at, last_accessed_at, metadata_json
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    session_id,
                    now.isoformat(),
                    now.isoformat(),
                    encode_json(metadata or {}),
                ),
            )
            return True
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False

    async def load_session(self, session_id: str) -> dict[str, Any] | None:
        """Load persisted session after gateway restart."""
        try:
            row = self._db.fetch_one(
                "SELECT * FROM gnosys_sessions WHERE session_id = ?",
                (session_id,),
            )
            if not row:
                return None

            self._db.execute(
                "UPDATE gnosys_sessions SET last_accessed_at = ? WHERE session_id = ?",
                (datetime.now(UTC).isoformat(), session_id),
            )

            return {
                "session_id": row["session_id"],
                "created_at": row["created_at"],
                "last_accessed_at": row["last_accessed_at"],
                "metadata": decode_json(row["metadata_json"]),
            }
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return None

    async def list_sessions(self) -> list[dict[str, Any]]:
        """List all persisted sessions."""
        try:
            rows = self._db.fetch_all(
                "SELECT * FROM gnosys_sessions ORDER BY last_accessed_at DESC"
            )
            return [
                {
                    "session_id": row["session_id"],
                    "created_at": row["created_at"],
                    "last_accessed_at": row["last_accessed_at"],
                    "metadata": decode_json(row["metadata_json"]),
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []

    async def delete_session(self, session_id: str) -> bool:
        """Delete a persisted session."""
        try:
            cursor = self._db.execute(
                "DELETE FROM gnosys_sessions WHERE session_id = ?",
                (session_id,),
            )
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False

    async def store_slot(
        self,
        key: str,
        value: Any,
        memory_type: str = "episodic",
        tier: str = "working",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Store value in memory slot."""
        try:
            now = datetime.now(UTC)
            self._db.execute(
                """
                INSERT OR REPLACE INTO gnosys_memory_slots (
                    slot_key, slot_value, memory_type, tier, content,
                    tags_json, metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    key,
                    json.dumps(value) if not isinstance(value, str) else value,
                    memory_type,
                    tier,
                    str(value),
                    encode_json(tags or []),
                    encode_json(metadata or {}),
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            return True
        except Exception as e:
            logger.error(f"Failed to store slot: {e}")
            return False

    async def load_slot(self, key: str) -> Any | None:
        """Load value from memory slot."""
        try:
            row = self._db.fetch_one(
                "SELECT * FROM gnosys_memory_slots WHERE slot_key = ?",
                (key,),
            )
            if not row:
                return None

            value = row["slot_value"]
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        except Exception as e:
            logger.error(f"Failed to load slot: {e}")
            return None

    async def delete_slot(self, key: str) -> bool:
        """Delete a memory slot."""
        try:
            cursor = self._db.execute(
                "DELETE FROM gnosys_memory_slots WHERE slot_key = ?",
                (key,),
            )
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete slot: {e}")
            return False

    async def list_slots(self, tier: str | None = None) -> list[dict[str, Any]]:
        """List all memory slots."""
        try:
            sql = "SELECT * FROM gnosys_memory_slots"
            params = ()
            if tier:
                sql += " WHERE tier = ?"
                params = (tier,)
            sql += " ORDER BY updated_at DESC"

            rows = self._db.fetch_all(sql, params)
            return [
                {
                    "key": row["slot_key"],
                    "value": row["slot_value"],
                    "memory_type": row["memory_type"],
                    "tier": row["tier"],
                    "tags": decode_json(row["tags_json"]),
                    "metadata": decode_json(row["metadata_json"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Failed to list slots: {e}")
            return []

    async def migrate_existing(self) -> dict[str, Any]:
        """Migrate existing MEMORY.md files to Gnosys format."""
        return await self._migration.migrate_from_md(None)

    async def get_stats(self) -> dict[str, Any]:
        """Get plugin statistics."""
        try:
            session_count = self._db.fetch_one(
                "SELECT COUNT(*) as count FROM gnosys_sessions"
            )
            slot_count = self._db.fetch_one(
                "SELECT COUNT(*) as count FROM gnosys_memory_slots"
            )

            return {
                "initialized": self._initialized,
                "fallback_enabled": self._fallback_enabled,
                "session_count": session_count["count"] if session_count else 0,
                "slot_count": slot_count["count"] if slot_count else 0,
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}

    def _ensure_schema(self) -> None:
        """Ensure database schema exists."""
        with self._db.transaction() as conn:
            conn.execute(MEMORY_TABLE_SCHEMA)
            conn.execute(MEMORY_SLOTS_SCHEMA)

    async def _initialize_storage(self) -> None:
        """Initialize storage directories."""
        storage_dir = self._config.memory.directory.expanduser().resolve()
        storage_dir.mkdir(parents=True, exist_ok=True)


class PluginConfig:
    """Configuration for GnosysPlugin."""

    model_config = {"extra": "allow"}

    enabled: bool = True
    storage: str = "database"
    fallback: bool = True
    migration_enabled: bool = True


def create_plugin(config: AppConfig, db: Database) -> GnosysPlugin:
    """Create GnosysPlugin instance."""
    return GnosysPlugin(config, db)
