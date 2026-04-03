"""
Vector store for storing and searching embeddings.

Uses SQLite with a simple implementation supporting cosine similarity search.
"""

from __future__ import annotations

import json
import math
import uuid
from datetime import UTC, datetime
from typing import Any, Iterable

import numpy as np

from gnosys_backend.config import AppConfig
from gnosys_backend.db import Database


class VectorStore:
    """SQLite-backed vector store with cosine similarity search."""

    def __init__(self, db: Database, config: AppConfig) -> None:
        self._db = db
        self._config = config
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create vector store tables if they don't exist."""
        # Vectors table for storing embeddings
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS vectors (
                id TEXT PRIMARY KEY,
                memory_id TEXT NOT NULL,
                content TEXT NOT NULL,
                vector_json TEXT NOT NULL,
                metadata_json TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        # Index for memory_id lookups
        self._db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_vectors_memory_id ON vectors(memory_id)
            """
        )

    def store_vector(
        self,
        memory_id: str,
        content: str,
        vector: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store a vector embedding for a memory."""
        vector_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        self._db.execute(
            """
            INSERT INTO vectors (id, memory_id, content, vector_json, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                vector_id,
                memory_id,
                content,
                json.dumps(vector),
                json.dumps(metadata) if metadata else None,
                now,
            ),
        )
        return vector_id

    def get_vector(self, memory_id: str) -> tuple[list[float], str] | None:
        """Retrieve vector by memory_id."""
        row = self._db.fetch_one(
            "SELECT vector_json, content FROM vectors WHERE memory_id = ?",
            (memory_id,),
        )
        if row is None:
            return None
        return (json.loads(row["vector_json"]), row["content"])

    def delete_vector(self, memory_id: str) -> bool:
        """Delete vector by memory_id."""
        cursor = self._db.execute(
            "DELETE FROM vectors WHERE memory_id = ?", (memory_id,)
        )
        return cursor.rowcount > 0

    def search_similar(
        self,
        query_vector: list[float],
        limit: int = 10,
        memory_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for similar vectors using cosine similarity.

        Returns list of {memory_id, content, similarity, metadata}
        """
        # Normalize query vector
        query_norm = math.sqrt(sum(x * x for x in query_vector))
        if query_norm == 0:
            return []

        # Fetch all vectors
        if memory_ids:
            placeholders = ",".join("?" * len(memory_ids))
            query = f"SELECT memory_id, content, vector_json, metadata_json FROM vectors WHERE memory_id IN ({placeholders})"
            rows = self._db.fetch_all(query, tuple(memory_ids))
        else:
            rows = self._db.fetch_all(
                "SELECT memory_id, content, vector_json, metadata_json FROM vectors"
            )

        results = []
        for row in rows:
            vector = json.loads(row["vector_json"])
            similarity = self._cosine_similarity(query_vector, vector, query_norm)
            if similarity > 0:  # Only include positive similarities
                results.append(
                    {
                        "memory_id": row["memory_id"],
                        "content": row["content"],
                        "similarity": similarity,
                        "metadata": json.loads(row["metadata_json"])
                        if row["metadata_json"]
                        else None,
                    }
                )

        # Sort by similarity descending
        results.sort(key=lambda x: (-x["similarity"], x["memory_id"]))
        return results[:limit]

    def _cosine_similarity(
        self, vec1: list[float], vec2: list[float], vec1_norm: float
    ) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        vec2_norm = math.sqrt(sum(x * x for x in vec2))

        if vec2_norm == 0:
            return 0.0

        return dot_product / (vec1_norm * vec2_norm)

    def count_vectors(self) -> int:
        """Count total vectors stored."""
        row = self._db.fetch_one("SELECT COUNT(*) as count FROM vectors")
        return row["count"] if row else 0

    def health(self) -> bool:
        """Check if vector store is healthy."""
        try:
            self._db.fetch_one("SELECT 1")
            return True
        except Exception:
            return False

    def close(self) -> None:
        """Close the vector store."""
        # Database is closed by the main db module
        pass
