from __future__ import annotations
import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime

from gnosys_backend.config import AppConfig
from gnosys_backend.db import Database, decode_json, encode_json
from gnosys_backend.models import (
    LearningStatsResponse,
    TrajectoryCreateRequest,
    TrajectoryCreateResponse,
    TrajectoryListResponse,
    TrajectoryRecord,
    TrajectoryStep,
    TrajectoryMetrics,
    TrajectoryUpdateRequest,
    TrajectoryUpdateResponse,
)

class TrajectoryStore:
    def __init__(self, db: Database, config: AppConfig) -> None:
        self._db = db
        self._config = config

    def create(self, request: TrajectoryCreateRequest) -> TrajectoryRecord:
        now = datetime.now(UTC)
        trajectory_id = str(uuid.uuid4())
        
        self._db.execute(
            """INSERT INTO trajectories (
                id, task, started_at, agent_type, query, response_preview,
                completed_at, success, steps_json, metrics_json, error
            ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, '[]', '{}', NULL)""",
            (trajectory_id, request.task, now.isoformat(), request.agent_type, 
             request.query, request.response_preview)
        )
        
        row = self._db.fetch_one("SELECT * FROM trajectories WHERE id = ?", (trajectory_id,))
        if row is None:
            raise RuntimeError("Created trajectory not found")
        return self._row_to_record(row)

    def update(self, trajectory_id: str, request: TrajectoryUpdateRequest) -> TrajectoryRecord | None:
        now = datetime.now(UTC)
        completed_at = request.completed_at or now
        
        self._db.execute(
            """UPDATE trajectories SET 
                completed_at = ?, success = ?, steps_json = ?, metrics_json = ?, error = ?
            WHERE id = ?""",
            (completed_at.isoformat(), request.success,
             encode_json([s.model_dump() for s in request.steps]),
             encode_json(request.metrics.model_dump() if request.metrics else {}),
             request.error, trajectory_id)
        )
        
        row = self._db.fetch_one("SELECT * FROM trajectories WHERE id = ?", (trajectory_id,))
        return self._row_to_record(row) if row else None

    def get(self, trajectory_id: str) -> TrajectoryRecord | None:
        row = self._db.fetch_one("SELECT * FROM trajectories WHERE id = ?", (trajectory_id,))
        return self._row_to_record(row) if row else None

    def list_recent(self, limit: int = 50, agent_type: str | None = None) -> TrajectoryListResponse:
        if agent_type:
            rows = self._db.fetch_all(
                "SELECT * FROM trajectories WHERE agent_type = ? ORDER BY started_at DESC LIMIT ?",
                (agent_type, limit)
            )
        else:
            rows = self._db.fetch_all(
                "SELECT * FROM trajectories ORDER BY started_at DESC LIMIT ?",
                (limit,)
            )
        return TrajectoryListResponse(
            count=len(rows),
            trajectories=[self._row_to_record(row) for row in rows]
        )

    def get_stats(self) -> LearningStatsResponse:
        rows = self._db.fetch_all("SELECT * FROM trajectories")
        
        if not rows:
            return LearningStatsResponse(
                total_trajectories=0, success_rate=0.0, avg_duration_ms=0.0,
                tool_usage={}, agent_stats={}
            )
        
        success_count = sum(1 for r in rows if r["success"])
        success_rate = success_count / len(rows)
        
        total_duration = 0
        tool_counter = Counter()
        agent_stats = defaultdict(lambda: {"count": 0, "success": 0, "durations": []})
        
        for row in rows:
            metrics = decode_json(row["metrics_json"]) or {}
            duration = metrics.get("total_duration_ms", 0)
            total_duration += duration
            
            steps = decode_json(row["steps_json"]) or []
            for step in steps:
                tool_counter[step.get("tool", "unknown")] += 1
            
            agent_type = row["agent_type"]
            agent_stats[agent_type]["count"] += 1
            if row["success"]:
                agent_stats[agent_type]["success"] += 1
            if duration > 0:
                agent_stats[agent_type]["durations"].append(duration)
        
        formatted_agent_stats = {}
        for at, data in agent_stats.items():
            durations = data.get("durations", [])
            formatted_agent_stats[at] = {
                "count": data["count"],
                "success_rate": data["success"] / data["count"] if data["count"] > 0 else 0.0,
                "avg_duration_ms": sum(durations) / len(durations) if durations else 0.0
            }
        
        return LearningStatsResponse(
            total_trajectories=len(rows),
            success_rate=success_rate,
            avg_duration_ms=total_duration / len(rows) if rows else 0.0,
            tool_usage=dict(tool_counter),
            agent_stats=formatted_agent_stats
        )

    def _row_to_record(self, row: object) -> TrajectoryRecord:
        return TrajectoryRecord(
            id=row["id"],
            task=row["task"],
            started_at=datetime.fromisoformat(row["started_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            success=bool(row["success"]) if row["success"] is not None else None,
            agent_type=row["agent_type"],
            steps=[TrajectoryStep(**s) for s in (decode_json(row["steps_json"]) or [])],
            metrics=TrajectoryMetrics(**decode_json(row["metrics_json"])) if row["metrics_json"] and row["metrics_json"] != '{}' else None,
            error=row["error"] or None,
            query=row["query"] or None,
            response_preview=row["response_preview"] or None
        )
