"""
Entity extraction for semantic memory.

Extracts entities from memory content using simple pattern matching.
Can be extended to use NER models for more accurate extraction.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from gnosys_backend.config import AppConfig
from gnosys_backend.db import Database, decode_json, encode_json


# Common entity patterns
ENTITY_PATTERNS = {
    "person": r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b",
    "email": r"\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b",
    "url": r"\b(https?://[^\s]+)\b",
    "github": r"\b(github\.com/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)\b",
    "file_path": r"\b([a-zA-Z]:\\[^\s]+|/[^\s]+)\b",
    "version": r"\bv(\d+\.\d+\.\d+(?:-[a-zA-Z0-9]+)?)\b",
}


class EntityStore:
    """Store and retrieve extracted entities from memories."""

    def __init__(self, db: Database, config: AppConfig) -> None:
        self._db = db
        self._config = config
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create entity tables if they don't exist."""
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                memory_id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_value TEXT NOT NULL,
                context TEXT,
                confidence REAL DEFAULT 1.0,
                metadata_json TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        # Index for memory_id lookups
        self._db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_entities_memory_id ON entities(memory_id)
            """
        )
        # Index for entity lookups
        self._db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_entities_type_value ON entities(entity_type, entity_value)
            """
        )

    def extract_entities(self, memory_id: str, content: str) -> list[dict[str, Any]]:
        """Extract entities from memory content."""
        entities = []

        for entity_type, pattern in ENTITY_PATTERNS.items():
            matches = re.finditer(pattern, content)
            for match in matches:
                entity_value = match.group(1) if match.groups() else match.group(0)

                # Get surrounding context (50 chars before and after)
                start = max(0, match.start() - 50)
                end = min(len(content), match.end() + 50)
                context = content[start:end]

                entities.append(
                    {
                        "entity_type": entity_type,
                        "entity_value": entity_value,
                        "context": context,
                        "confidence": 1.0,
                    }
                )

        # Store all extracted entities
        stored_entities = []
        for entity in entities:
            entity_id = self.store_entity(
                memory_id=memory_id,
                entity_type=entity["entity_type"],
                entity_value=entity["entity_value"],
                context=entity.get("context"),
                confidence=entity.get("confidence", 1.0),
            )
            stored_entities.append(entity_id)

        return stored_entities

    def store_entity(
        self,
        memory_id: str,
        entity_type: str,
        entity_value: str,
        context: str | None = None,
        confidence: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store an extracted entity."""
        entity_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        self._db.execute(
            """
            INSERT INTO entities (id, memory_id, entity_type, entity_value, context, confidence, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entity_id,
                memory_id,
                entity_type,
                entity_value,
                context,
                confidence,
                encode_json(metadata) if metadata else None,
                now,
            ),
        )
        return entity_id

    def get_entities_by_memory(self, memory_id: str) -> list[dict[str, Any]]:
        """Get all entities for a specific memory."""
        rows = self._db.fetch_all(
            "SELECT * FROM entities WHERE memory_id = ?",
            (memory_id,),
        )
        return [self._row_to_dict(row) for row in rows]

    def get_entities_by_type(
        self, entity_type: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get entities by type."""
        rows = self._db.fetch_all(
            "SELECT * FROM entities WHERE entity_type = ? ORDER BY created_at DESC LIMIT ?",
            (entity_type, limit),
        )
        return [self._row_to_dict(row) for row in rows]

    def search_entities(
        self, query: str, entity_type: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Search entities by value."""
        if entity_type:
            rows = self._db.fetch_all(
                "SELECT * FROM entities WHERE entity_type = ? AND entity_value LIKE ? LIMIT ?",
                (entity_type, f"%{query}%", limit),
            )
        else:
            rows = self._db.fetch_all(
                "SELECT * FROM entities WHERE entity_value LIKE ? LIMIT ?",
                (f"%{query}%", limit),
            )
        return [self._row_to_dict(row) for row in rows]

    def delete_entities_by_memory(self, memory_id: str) -> int:
        """Delete all entities associated with a memory."""
        cursor = self._db.execute(
            "DELETE FROM entities WHERE memory_id = ?",
            (memory_id,),
        )
        return cursor.rowcount

    def get_entity_stats(self) -> dict[str, Any]:
        """Get entity statistics."""
        from collections import Counter

        rows = self._db.fetch_all("SELECT entity_type FROM entities")
        type_counts = Counter(row["entity_type"] for row in rows)

        total = sum(type_counts.values())
        unique_values = len(
            self._db.fetch_all("SELECT DISTINCT entity_value FROM entities")
        )

        return {
            "total_entities": total,
            "unique_values": unique_values,
            "counts_by_type": dict(type_counts),
        }

    def _row_to_dict(self, row: object) -> dict[str, Any]:
        return {
            "id": row["id"],
            "memory_id": row["memory_id"],
            "entity_type": row["entity_type"],
            "entity_value": row["entity_value"],
            "context": row["context"],
            "confidence": row["confidence"],
            "metadata": decode_json(row["metadata_json"])
            if row["metadata_json"]
            else None,
            "created_at": row["created_at"],
        }

    def close(self) -> None:
        """Close the entity store."""
        pass


class EntityExtractor:
    """Main entity extraction class."""

    def __init__(self, entity_store: EntityStore) -> None:
        self._store = entity_store

    def extract_from_memory(self, memory_id: str, content: str) -> list[dict[str, Any]]:
        """Extract and store entities from memory content."""
        return self._store.extract_entities(memory_id, content)

    def get_memory_entities(self, memory_id: str) -> list[dict[str, Any]]:
        """Get all entities for a memory."""
        return self._store.get_entities_by_memory(memory_id)

    def search(
        self, query: str, entity_type: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Search entities."""
        return self._store.search_entities(query, entity_type, limit)

    def delete_by_memory(self, memory_id: str) -> int:
        """Delete all entities for a memory."""
        return self._store.delete_entities_by_memory(memory_id)

    def get_stats(self) -> dict[str, Any]:
        """Get entity extraction statistics."""
        return self._store.get_entity_stats()
