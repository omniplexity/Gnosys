"""
Monitoring System - Health checks, metrics, and observability.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from gnosys_backend.config import MonitoringConfig
from gnosys_backend.db import Database


class MonitoringSystem:
    """Monitoring and observability for Gnosys."""

    def __init__(self, db: Database, config: MonitoringConfig) -> None:
        self._db = db
        self._config = config
        self._start_time = time.time()

    @property
    def uptime_seconds(self) -> float:
        """Get uptime in seconds."""
        return time.time() - self._start_time

    async def check_health(self) -> dict[str, Any]:
        """Perform health check."""
        components = {}

        # Database health
        db_health = "healthy"
        try:
            if not self._db.ping():
                db_health = "unhealthy"
        except Exception:
            db_health = "unhealthy"
        components["database"] = db_health

        return {
            "status": "healthy"
            if all(v == "healthy" for v in components.values())
            else "degraded",
            "service": "gnosys",
            "version": "0.8.0",
            "components": components,
        }

    async def get_metrics(self) -> dict[str, Any]:
        """Get system metrics."""
        now = datetime.utcnow()

        # Memory stats
        memory_stats = await self._get_memory_stats()

        # Pipeline stats
        pipeline_stats = await self._get_pipeline_stats()

        # Learning stats
        learning_stats = await self._get_learning_stats()

        # Skills stats
        skills_stats = await self._get_skills_stats()

        # Scheduler stats
        scheduler_stats = await self._get_scheduler_stats()

        return {
            "memory_stats": memory_stats,
            "pipeline_stats": pipeline_stats,
            "learning_stats": learning_stats,
            "skills_stats": skills_stats,
            "scheduler_stats": scheduler_stats,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "timestamp": now.isoformat(),
        }

    async def _get_memory_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        try:
            total = self._db.fetch_one("SELECT COUNT(*) as total FROM memories")
            by_type = self._db.fetch_all(
                "SELECT memory_type, COUNT(*) as count FROM memories GROUP BY memory_type"
            )
            by_tier = self._db.fetch_all(
                "SELECT tier, COUNT(*) as count FROM memories GROUP BY tier"
            )

            return {
                "total_memories": total["total"] if total else 0,
                "by_type": {row["memory_type"]: row["count"] for row in by_type},
                "by_tier": {row["tier"]: row["count"] for row in by_tier},
            }
        except Exception as e:
            return {"error": str(e)}

    async def _get_pipeline_stats(self) -> dict[str, Any]:
        """Get pipeline statistics."""
        try:
            total_agents = self._db.fetch_one("SELECT COUNT(*) as total FROM agents")
            by_status = self._db.fetch_all(
                "SELECT status, COUNT(*) as count FROM agents GROUP BY status"
            )
            by_role = self._db.fetch_all(
                "SELECT role, COUNT(*) as count FROM agents GROUP BY role"
            )

            return {
                "total_agents": total_agents["total"] if total_agents else 0,
                "by_status": {row["status"]: row["count"] for row in by_status},
                "by_role": {row["role"]: row["count"] for row in by_role},
            }
        except Exception as e:
            return {"error": str(e)}

    async def _get_learning_stats(self) -> dict[str, Any]:
        """Get learning system statistics."""
        try:
            total_trajectories = self._db.fetch_one(
                "SELECT COUNT(*) as total FROM trajectories"
            )
            success_row = self._db.fetch_one(
                "SELECT AVG(CAST(success AS REAL)) as rate FROM trajectories WHERE success IS NOT NULL"
            )

            # Recent trajectories
            recent = self._db.fetch_all(
                """
                SELECT COUNT(*) as total, SUM(CAST(success AS INTEGER)) as success_count
                FROM trajectories
                WHERE started_at >= datetime('now', '-24 hours')
                """
            )

            # Tool usage
            tool_usage: dict[str, int] = {}
            trajectories = self._db.fetch_all(
                "SELECT steps_json FROM trajectories ORDER BY started_at DESC LIMIT 100"
            )
            import json

            for row in trajectories:
                try:
                    steps = json.loads(row["steps_json"])
                    for step in steps:
                        tool = step.get("tool", "unknown")
                        tool_usage[tool] = tool_usage.get(tool, 0) + 1
                except (json.JSONDecodeError, KeyError):
                    continue

            return {
                "total_trajectories": total_trajectories["total"]
                if total_trajectories
                else 0,
                "overall_success_rate": round(success_row["rate"], 2)
                if success_row and success_row["rate"]
                else 0.0,
                "recent_24h": {
                    "total": recent[0]["total"] if recent else 0,
                    "succeeded": recent[0]["success_count"]
                    if recent and recent[0]["success_count"]
                    else 0,
                },
                "tool_usage": tool_usage,
            }
        except Exception as e:
            return {"error": str(e)}

    async def _get_skills_stats(self) -> dict[str, Any]:
        """Get skills statistics."""
        try:
            total = self._db.fetch_one("SELECT COUNT(*) as total FROM skills")
            if not total or total["total"] == 0:
                return {
                    "total_skills": 0,
                    "total_uses": 0,
                    "avg_success_rate": 0.0,
                }

            uses = self._db.fetch_one("SELECT SUM(use_count) as total FROM skills")
            rate = self._db.fetch_one(
                "SELECT AVG(success_rate) as rate FROM skills WHERE use_count > 0"
            )

            return {
                "total_skills": total["total"],
                "total_uses": uses["total"] if uses and uses["total"] else 0,
                "avg_success_rate": round(rate["rate"], 2)
                if rate and rate["rate"]
                else 0.0,
            }
        except Exception as e:
            return {"error": str(e)}

    async def _get_scheduler_stats(self) -> dict[str, Any]:
        """Get scheduler statistics."""
        try:
            total = self._db.fetch_one(
                "SELECT COUNT(*) as total, SUM(enabled) as active FROM scheduled_tasks"
            )
            if not total or total["total"] == 0:
                return {
                    "total_tasks": 0,
                    "active_tasks": 0,
                    "due_now": 0,
                }

            # Due now
            now = datetime.utcnow().isoformat()
            due = self._db.fetch_one(
                "SELECT COUNT(*) as due FROM scheduled_tasks WHERE enabled = 1 AND next_run_at <= ?",
                (now,),
            )

            # Recent executions
            recent = self._db.fetch_all(
                """
                SELECT COUNT(*) as total, SUM(success) as succeeded
                FROM scheduled_task_executions
                WHERE executed_at >= datetime('now', '-24 hours')
                """
            )

            return {
                "total_tasks": total["total"],
                "active_tasks": total["active"] if total["active"] else 0,
                "due_now": due["due"] if due else 0,
                "executions_24h": recent[0]["total"] if recent else 0,
                "success_rate_24h": round(
                    recent[0]["succeeded"] / recent[0]["total"], 2
                )
                if recent and recent[0]["total"] and recent[0]["succeeded"]
                else 0.0,
            }
        except Exception as e:
            return {"error": str(e)}
