from __future__ import annotations

import re
import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Iterable

from gnosys_backend.config import AppConfig
from gnosys_backend.db import Database, decode_json, encode_json
from gnosys_backend.models import (
    MemoryCreateRequest,
    MemoryRecord,
    MemorySearchResult,
    SearchResponse,
    StatsResponse,
)


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class MemoryStore:
    def __init__(self, db: Database, config: AppConfig) -> None:
        self._db = db
        self._config = config

    def store_memory(self, request: MemoryCreateRequest) -> MemoryRecord:
        now = datetime.now(UTC)
        created_at = request.created_at or now
        expires_at = request.expires_at or self._default_expiry(
            request.tier, created_at
        )
        memory_id = str(uuid.uuid4())
        keywords = sorted(
            set(
                self._tokenize_parts(
                    [request.content, *request.tags, request.memory_type, request.tier]
                )
            )
        )

        self._db.execute(
            """
            INSERT INTO memories (
                id, memory_type, tier, content, tags_json, metadata_json, keywords,
                created_at, updated_at, last_accessed_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory_id,
                request.memory_type,
                request.tier,
                request.content,
                encode_json(request.tags),
                encode_json(request.metadata),
                " ".join(keywords),
                created_at.isoformat(),
                now.isoformat(),
                now.isoformat(),
                expires_at.isoformat() if expires_at else None,
            ),
        )
        row = self._db.fetch_one("SELECT * FROM memories WHERE id = ?", (memory_id,))
        if row is None:
            raise RuntimeError("Stored memory could not be reloaded")
        return self._row_to_record(row)

    def search_memories(
        self,
        query: str,
        *,
        limit: int | None = None,
        memory_type: str | None = None,
        tier: str | None = None,
    ) -> SearchResponse:
        normalized_query = query.strip()
        tokens = self._tokenize(normalized_query)
        effective_limit = limit or self._config.retention.default_search_limit
        if not normalized_query:
            return SearchResponse(query=query, count=0, results=[])

        rows = self._db.fetch_all("SELECT * FROM memories")
        scored: list[MemorySearchResult] = []
        for row in rows:
            record = self._row_to_record(row)
            if memory_type and record.memory_type != memory_type:
                continue
            if tier and record.tier != tier:
                continue
            score, matched = self._score_record(record, normalized_query, tokens)
            if score <= 0:
                continue
            scored.append(
                MemorySearchResult(memory=record, score=score, matched_keywords=matched)
            )

        scored.sort(
            key=lambda item: (
                -item.score,
                item.memory.created_at,
                item.memory.id,
            ),
        )
        results = scored[:effective_limit]
        self._touch_records(results)
        return SearchResponse(query=query, count=len(results), results=results)

    def get_stats(self) -> StatsResponse:
        rows = self._db.fetch_all("SELECT * FROM memories")
        type_counts = Counter(row["memory_type"] for row in rows)
        tier_counts = Counter(row["tier"] for row in rows)
        created_values = sorted(row["created_at"] for row in rows)
        oldest = datetime.fromisoformat(created_values[0]) if created_values else None
        newest = datetime.fromisoformat(created_values[-1]) if created_values else None
        return StatsResponse(
            total_memories=len(rows),
            counts_by_type=dict(type_counts),
            counts_by_tier=dict(tier_counts),
            oldest_memory_at=oldest,
            newest_memory_at=newest,
            database_path=str(self._config.resolved_db_path()),
        )

    def get_memory(self, memory_id: str) -> MemoryRecord | None:
        row = self._db.fetch_one("SELECT * FROM memories WHERE id = ?", (memory_id,))
        if row is None:
            return None
        return self._row_to_record(row)

    def delete_memory(self, memory_id: str) -> bool:
        cursor = self._db.execute(
            "DELETE FROM memories WHERE id = ?", (memory_id,)
        )
        return cursor.rowcount > 0

    def prune_expired(self) -> int:
        now = datetime.now(UTC).isoformat()
        cursor = self._db.execute(
            "DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at < ?",
            (now,),
        )
        return cursor.rowcount

    def health(self) -> bool:
        return self._db.ping()

    def close(self) -> None:
        self._db.close()

    def _default_expiry(self, tier: str, created_at: datetime) -> datetime | None:
        if tier == "episodic":
            return created_at + timedelta(days=self._config.retention.episodic_days)
        if tier == "archive":
            return created_at + timedelta(days=self._config.retention.archive_days)
        return None

    def _score_record(
        self, record: MemoryRecord, query: str, tokens: list[str]
    ) -> tuple[int, list[str]]:
        content_lower = record.content.lower()
        keywords = set(
            self._tokenize_parts(
                [record.content, *record.tags, record.memory_type, record.tier]
            )
        )
        matched = sorted(token for token in tokens if token in keywords)
        score = 0
        if query.lower() in content_lower:
            score += 50
        if record.content.lower() == query.lower():
            score += 25
        score += 10 * len(matched)
        if (
            record.memory_type.lower() == query.lower()
            or record.tier.lower() == query.lower()
        ):
            score += 5
        return score, matched

    def _touch_records(self, results: Iterable[MemorySearchResult]) -> None:
        now = datetime.now(UTC).isoformat()
        for item in results:
            self._db.execute(
                "UPDATE memories SET last_accessed_at = ?, updated_at = updated_at WHERE id = ?",
                (now, item.memory.id),
            )

    def _row_to_record(self, row: object) -> MemoryRecord:
        return MemoryRecord(
            id=row["id"],
            content=row["content"],
            memory_type=row["memory_type"],
            tier=row["tier"],
            tags=decode_json(row["tags_json"]),
            metadata=decode_json(row["metadata_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            last_accessed_at=datetime.fromisoformat(row["last_accessed_at"])
            if row["last_accessed_at"]
            else None,
            expires_at=datetime.fromisoformat(row["expires_at"])
            if row["expires_at"]
            else None,
        )

    def _tokenize(self, text: str) -> list[str]:
        return self._tokenize_parts([text])

    def _tokenize_parts(self, parts: Iterable[str]) -> list[str]:
        tokens: list[str] = []
        for part in parts:
            tokens.extend(TOKEN_PATTERN.findall(part.lower()))
        return tokens
