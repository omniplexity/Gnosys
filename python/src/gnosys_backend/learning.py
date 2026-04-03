from __future__ import annotations

import re
import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any

from gnosys_backend.config import LearningConfig
from gnosys_backend.db import Database, decode_json, encode_json
from gnosys_backend.models import (
    DatasetGenerateRequest,
    DatasetGenerateResponse,
    PatternDetectRequest,
    PatternDetectResponse,
    PatternRecord,
)


class LearningStore:
    """Self-learning system that analyzes trajectories and detects patterns."""

    def __init__(self, db: Database, config: LearningConfig) -> None:
        self._db = db
        self._config = config

    def detect_patterns(self, request: PatternDetectRequest) -> PatternDetectResponse:
        """Detect patterns from recent trajectories."""
        # Fetch recent trajectories
        rows = self._db.fetch_all(
            "SELECT * FROM trajectories ORDER BY started_at DESC LIMIT ?",
            (self._config.pattern_detection.trajectory_limit,),
        )

        if not rows:
            return PatternDetectResponse(
                patterns=[], total_analyzed=0, generated_at=datetime.now(UTC)
            )

        # Analyze tool sequences
        tool_sequences: list[list[str]] = []
        for row in rows:
            steps = decode_json(row["steps_json"]) or []
            sequence = [step.get("tool", "unknown") for step in steps]
            if sequence:
                tool_sequences.append(sequence)

        # Find repeated patterns
        patterns = self._find_repeated_patterns(tool_sequences)

        # Analyze success patterns
        success_patterns = self._analyze_success_patterns(rows)

        # Detect tool effectiveness
        tool_effectiveness = self._analyze_tool_effectiveness(rows)

        all_patterns = []
        for pattern in patterns + success_patterns:
            pattern_id = str(uuid.uuid4())
            self._store_pattern(pattern_id, pattern)
            all_patterns.append(
                PatternRecord(
                    id=pattern_id,
                    pattern_type=pattern.get("type", "tool_sequence"),
                    description=pattern.get("description", ""),
                    frequency=pattern.get("frequency", 1),
                    success_rate=pattern.get("success_rate", 0.0),
                    tools=pattern.get("tools", []),
                    metadata=pattern,
                )
            )

        return PatternDetectResponse(
            patterns=all_patterns,
            total_analyzed=len(rows),
            generated_at=datetime.now(UTC),
        )

    def generate_dataset(
        self, request: DatasetGenerateRequest
    ) -> DatasetGenerateResponse:
        """Generate training datasets from successful trajectories."""
        min_success = self._config.dataset_generation.success_threshold

        # Fetch successful trajectories
        rows = self._db.fetch_all(
            f"SELECT * FROM trajectories WHERE success = 1 ORDER BY started_at DESC LIMIT ?",
            (self._config.dataset_generation.min_trajectories,),
        )

        if not rows:
            return DatasetGenerateResponse(
                dataset_type=request.dataset_type,
                records=[],  # type: ignore
                total_records=0,
                generated_at=datetime.now(UTC),
            )

        records: list[dict[str, Any]] = []

        if request.dataset_type == "task_response":
            for row in rows:
                if row["query"] and row["response_preview"]:
                    records.append(
                        {
                            "task": row["task"],
                            "query": row["query"],
                            "response": row["response_preview"],
                            "agent_type": row["agent_type"],
                        }
                    )

        elif request.dataset_type == "tool_workflow":
            for row in rows:
                steps = decode_json(row["steps_json"]) or []
                if steps:
                    records.append(
                        {
                            "task": row["task"],
                            "tool_sequence": [s.get("tool") for s in steps],
                            "parameters": [s.get("params", {}) for s in steps],
                            "success": row["success"],
                        }
                    )

        elif request.dataset_type == "context_relevance":
            # Get memories related to trajectory queries
            for row in rows:
                if row["query"]:
                    memories = self._db.fetch_all(
                        "SELECT * FROM memories WHERE keywords LIKE ? LIMIT 5",
                        (f"%{row['query'].lower()}%",),
                    )
                    if memories:
                        records.append(
                            {
                                "query": row["query"],
                                "relevant_memories": [
                                    {"content": m["content"], "tier": m["tier"]}
                                    for m in memories
                                ],
                            }
                        )

        elif request.dataset_type == "agent_decision":
            for row in rows:
                metrics = decode_json(row["metrics_json"]) or {}
                records.append(
                    {
                        "task": row["task"],
                        "agent_type": row["agent_type"],
                        "success": row["success"],
                        "duration_ms": metrics.get("total_duration_ms", 0),
                        "tool_count": metrics.get("tool_calls", 0),
                    }
                )

        return DatasetGenerateResponse(
            dataset_type=request.dataset_type,
            records=records,
            total_records=len(records),
            generated_at=datetime.now(UTC),
        )

    def _find_repeated_patterns(
        self, sequences: list[list[str]]
    ) -> list[dict[str, Any]]:
        """Find repeated tool sequences."""
        if not sequences:
            return []

        # Find sequences of length 2+
        pattern_counts: dict[tuple[str, ...], int] = defaultdict(int)
        min_length = self._config.pattern_detection.min_sequence_length

        for sequence in sequences:
            for length in range(min_length, len(sequence) + 1):
                for i in range(len(sequence) - length + 1):
                    pattern = tuple(sequence[i : i + length])
                    if len(pattern) >= min_length:
                        pattern_counts[pattern] += 1

        # Filter by frequency threshold
        threshold = self._config.pattern_detection.min_frequency
        repeated = [
            {
                "type": "repeated_tool_sequence",
                "description": f"Tool sequence: {' -> '.join(pattern)}",
                "tools": list(pattern),
                "frequency": count,
                "success_rate": 0.0,  # Would need trajectory success data
            }
            for pattern, count in pattern_counts.items()
            if count >= threshold
        ]

        return repeated[:10]  # Top 10 patterns

    def _analyze_success_patterns(self, rows: list[object]) -> list[dict[str, Any]]:
        """Analyze patterns in successful vs failed trajectories."""
        success_tools: Counter = Counter()
        failure_tools: Counter = Counter()

        for row in rows:
            steps = decode_json(row["steps_json"]) or []
            tools = [s.get("tool", "unknown") for s in steps]
            if row["success"]:
                success_tools.update(tools)
            else:
                failure_tools.update(tools)

        patterns = []
        all_tools = set(success_tools.keys()) | set(failure_tools.keys())
        for tool in all_tools:
            success_count = success_tools.get(tool, 0)
            total = success_count + failure_tools.get(tool, 0)
            if total >= self._config.pattern_detection.min_frequency:
                rate = success_count / total if total > 0 else 0.0
                if rate >= 0.8:  # High success rate
                    patterns.append(
                        {
                            "type": "high_success_tool",
                            "description": f"Tool '{tool}' has {rate:.1%} success rate",
                            "tools": [tool],
                            "frequency": total,
                            "success_rate": rate,
                        }
                    )

        return patterns[:5]

    def _analyze_tool_effectiveness(
        self, rows: list[object]
    ) -> dict[str, dict[str, Any]]:
        """Analyze tool effectiveness metrics."""
        tool_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"total": 0, "success": 0, "durations": []}
        )

        for row in rows:
            steps = decode_json(row["steps_json"]) or []
            for step in steps:
                tool = step.get("tool", "unknown")
                tool_stats[tool]["total"] += 1
                if step.get("success"):
                    tool_stats[tool]["success"] += 1
                tool_stats[tool]["durations"].append(step.get("duration_ms", 0))

        effectiveness = {}
        for tool, stats in tool_stats.items():
            if stats["total"] >= 3:
                effectiveness[tool] = {
                    "success_rate": stats["success"] / stats["total"],
                    "avg_duration_ms": (
                        sum(stats["durations"]) / len(stats["durations"])
                        if stats["durations"]
                        else 0
                    ),
                    "usage_count": stats["total"],
                }

        return effectiveness

    def _store_pattern(self, pattern_id: str, pattern: dict[str, Any]) -> None:
        """Store detected pattern in database."""
        self._db.execute(
            """INSERT OR REPLACE INTO learning_patterns (
                id, pattern_type, description, frequency, success_rate,
                tools_json, metadata_json, detected_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                pattern_id,
                pattern.get("type", "unknown"),
                pattern.get("description", ""),
                pattern.get("frequency", 0),
                pattern.get("success_rate", 0.0),
                encode_json(pattern.get("tools", [])),
                encode_json(pattern),
                datetime.now(UTC).isoformat(),
            ),
        )

    def get_learning_stats(self) -> dict[str, Any]:
        """Get learning system statistics."""
        pattern_rows = self._db.fetch_all(
            "SELECT COUNT(*) as count FROM learning_patterns"
        )
        pattern_count = pattern_rows[0]["count"] if pattern_rows else 0

        trajectory_rows = self._db.fetch_all(
            "SELECT COUNT(*) as count FROM trajectories"
        )
        trajectory_count = trajectory_rows[0]["count"] if trajectory_rows else 0

        return {
            "patterns_detected": pattern_count,
            "total_trajectories": trajectory_count,
            "learning_enabled": self._config.enabled,
        }
