"""
Scheduler System - Cron-like task scheduling and autonomous execution.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Callable

import croniter

from gnosys_backend.config import SchedulerConfig
from gnosys_backend.db import Database, decode_json, encode_json
from gnosys_backend.models import (
    ScheduledTaskCreateRequest,
    ScheduledTaskHistoryResponse,
    ScheduledTaskListResponse,
    ScheduledTaskRecord,
    ScheduledTaskRunResponse,
)


class Scheduler:
    """Cron-like scheduler for autonomous task execution."""

    def __init__(
        self,
        db: Database,
        config: SchedulerConfig,
        execute_callback: Callable[[dict[str, Any]], Any] | None = None,
    ) -> None:
        self._db = db
        self._config = config
        self._execute_callback = execute_callback
        self._running = False
        self._task_cache: dict[str, ScheduledTaskRecord] = {}

    def _validate_cron(self, schedule: str) -> bool:
        """Validate cron expression."""
        if schedule.startswith("@every"):
            # Interval format like @every 30m, @every 1h
            match = re.match(r"@every\s+(\d+)([mh])", schedule)
            return match is not None
        else:
            # Standard cron format
            try:
                croniter.croniter(schedule)
                return True
            except (KeyError, ValueError):
                return False

    def _calculate_next_run(self, schedule: str, last_run: datetime | None) -> datetime:
        """Calculate next run time from cron expression."""
        now = datetime.now(UTC)

        if schedule.startswith("@every"):
            # Handle interval format
            match = re.match(r"@every\s+(\d+)([mh])", schedule)
            if match:
                value, unit = int(match.group(1)), match.group(2)
                delta = (
                    timedelta(minutes=value) if unit == "m" else timedelta(hours=value)
                )
                return (last_run or now) + delta

        # Standard cron
        try:
            cron = croniter.croniter(schedule, now)
            return cron.get_next(datetime)
        except (KeyError, ValueError):
            return now + timedelta(hours=1)  # Default to 1 hour

    async def create_task(
        self, request: ScheduledTaskCreateRequest
    ) -> ScheduledTaskRecord:
        """Create a new scheduled task."""
        now = datetime.now(UTC)
        next_run = self._calculate_next_run(request.schedule, None)
        task_id = str(uuid.uuid4())

        self._db.execute(
            """
            INSERT INTO scheduled_tasks (
                id, name, schedule, task_type, enabled, description,
                action_json, delivery_json, created_at, last_run_at,
                next_run_at, run_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                request.name,
                request.schedule,
                request.task_type,
                1 if request.enabled else 0,
                request.description,
                encode_json(request.action),
                encode_json(request.delivery),
                now.isoformat(),
                None,
                next_run.isoformat(),
                0,
            ),
        )

        record = ScheduledTaskRecord(
            id=task_id,
            name=request.name,
            schedule=request.schedule,
            task_type=request.task_type,
            enabled=request.enabled,
            description=request.description,
            action=request.action,
            delivery=request.delivery,
            created_at=now,
            last_run_at=None,
            next_run_at=next_run,
            run_count=0,
        )
        self._task_cache[task_id] = record
        return record

    async def list_tasks(self, enabled_only: bool = False) -> ScheduledTaskListResponse:
        """List all scheduled tasks."""
        sql = "SELECT * FROM scheduled_tasks"
        if enabled_only:
            sql += " WHERE enabled = 1"
        sql += " ORDER BY next_run_at ASC"

        rows = self._db.fetch_all(sql)

        tasks = []
        for row in rows:
            task = ScheduledTaskRecord(
                id=row["id"],
                name=row["name"],
                schedule=row["schedule"],
                task_type=row["task_type"],
                enabled=bool(row["enabled"]),
                description=row["description"],
                action=decode_json(row["action_json"]),
                delivery=decode_json(row["delivery_json"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                last_run_at=datetime.fromisoformat(row["last_run_at"])
                if row["last_run_at"]
                else None,
                next_run_at=datetime.fromisoformat(row["next_run_at"])
                if row["next_run_at"]
                else None,
                run_count=row["run_count"],
            )
            tasks.append(task)
            self._task_cache[task.id] = task

        return ScheduledTaskListResponse(count=len(tasks), tasks=tasks)

    async def get_task(self, task_id: str) -> ScheduledTaskRecord | None:
        """Get a task by ID."""
        if task_id in self._task_cache:
            return self._task_cache[task_id]

        row = self._db.fetch_one(
            "SELECT * FROM scheduled_tasks WHERE id = ?", (task_id,)
        )
        if not row:
            return None

        task = ScheduledTaskRecord(
            id=row["id"],
            name=row["name"],
            schedule=row["schedule"],
            task_type=row["task_type"],
            enabled=bool(row["enabled"]),
            description=row["description"],
            action=decode_json(row["action_json"]),
            delivery=decode_json(row["delivery_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            last_run_at=datetime.fromisoformat(row["last_run_at"])
            if row["last_run_at"]
            else None,
            next_run_at=datetime.fromisoformat(row["next_run_at"])
            if row["next_run_at"]
            else None,
            run_count=row["run_count"],
        )
        self._task_cache[task_id] = task
        return task

    async def update_task(
        self, task_id: str, enabled: bool | None = None
    ) -> ScheduledTaskRecord | None:
        """Update a scheduled task."""
        task = await self.get_task(task_id)
        if not task:
            return None

        updates = []
        params = []

        if enabled is not None:
            updates.append("enabled = ?")
            params.append(1 if enabled else 0)

        if not updates:
            return task

        params.append(task_id)
        self._db.execute(
            f"UPDATE scheduled_tasks SET {', '.join(updates)} WHERE id = ?",
            tuple(params),
        )

        # Clear cache to force refresh
        self._task_cache.pop(task_id, None)
        return await self.get_task(task_id)

    async def delete_task(self, task_id: str) -> bool:
        """Delete a scheduled task."""
        task = await self.get_task(task_id)
        if not task:
            return False

        self._db.execute("DELETE FROM scheduled_tasks WHERE id = ?", (task_id,))
        self._task_cache.pop(task_id, None)
        return True

    async def run_task(self, task_id: str) -> ScheduledTaskRunResponse:
        """Run a task immediately."""
        task = await self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        now = datetime.now(UTC)
        start_time = datetime.now(UTC)

        result: dict[str, Any] = {}
        success = True
        error_msg: str | None = None

        try:
            if self._execute_callback:
                result = await self._execute_callback(task.action) or {}
            else:
                # Default: just record execution
                result = {"status": "executed", "action": task.action}
        except Exception as e:
            success = False
            error_msg = str(e)
            result = {"error": error_msg}

        duration_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)

        # Record execution
        execution_id = str(uuid.uuid4())
        self._db.execute(
            """
            INSERT INTO scheduled_task_executions (
                id, task_id, executed_at, success, result_json, error, duration_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                execution_id,
                task_id,
                now.isoformat(),
                1 if success else 0,
                encode_json(result),
                error_msg,
                duration_ms,
            ),
        )

        # Update task
        next_run = self._calculate_next_run(task.schedule, now)
        new_run_count = task.run_count + 1

        self._db.execute(
            """
            UPDATE scheduled_tasks 
            SET last_run_at = ?, next_run_at = ?, run_count = ?
            WHERE id = ?
            """,
            (now.isoformat(), next_run.isoformat(), new_run_count, task_id),
        )

        # Clear cache
        self._task_cache.pop(task_id, None)

        return ScheduledTaskRunResponse(
            task_id=task_id,
            executed=success,
            result=result if success else None,
            executed_at=now,
        )

    async def get_task_history(
        self, task_id: str, limit: int = 50
    ) -> ScheduledTaskHistoryResponse:
        """Get execution history for a task."""
        rows = self._db.fetch_all(
            """
            SELECT * FROM scheduled_task_executions 
            WHERE task_id = ?
            ORDER BY executed_at DESC
            LIMIT ?
            """,
            (task_id, limit),
        )

        executions = []
        for row in rows:
            executions.append(
                {
                    "id": row["id"],
                    "task_id": row["task_id"],
                    "executed_at": row["executed_at"],
                    "success": bool(row["success"]),
                    "result": decode_json(row["result_json"])
                    if row["result_json"]
                    else None,
                    "error": row["error"],
                    "duration_ms": row["duration_ms"],
                }
            )

        return ScheduledTaskHistoryResponse(
            count=len(executions), executions=executions
        )

    async def get_due_tasks(self) -> list[ScheduledTaskRecord]:
        """Get tasks that are due to run."""
        now = datetime.now(UTC).isoformat()
        rows = self._db.fetch_all(
            """
            SELECT * FROM scheduled_tasks 
            WHERE enabled = 1 AND next_run_at <= ?
            ORDER BY next_run_at ASC
            """,
            (now,),
        )

        tasks = []
        for row in rows:
            task = ScheduledTaskRecord(
                id=row["id"],
                name=row["name"],
                schedule=row["schedule"],
                task_type=row["task_type"],
                enabled=bool(row["enabled"]),
                description=row["description"],
                action=decode_json(row["action_json"]),
                delivery=decode_json(row["delivery_json"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                last_run_at=datetime.fromisoformat(row["last_run_at"])
                if row["last_run_at"]
                else None,
                next_run_at=datetime.fromisoformat(row["next_run_at"])
                if row["next_run_at"]
                else None,
                run_count=row["run_count"],
            )
            tasks.append(task)

        return tasks

    async def process_due_tasks(self) -> dict[str, Any]:
        """Process all due tasks."""
        due_tasks = await self.get_due_tasks()
        results = {
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "errors": [],
        }

        for task in due_tasks:
            try:
                response = await self.run_task(task.id)
                results["processed"] += 1
                if response.executed:
                    results["succeeded"] += 1
                else:
                    results["failed"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({"task_id": task.id, "error": str(e)})

        return results

    async def get_scheduler_stats(self) -> dict[str, Any]:
        """Get scheduler statistics."""
        # Total tasks
        total_row = self._db.fetch_one(
            "SELECT COUNT(*) as total, SUM(enabled) as active FROM scheduled_tasks"
        )
        total = total_row["total"] if total_row else 0
        active = total_row["active"] if total_row else 0

        # Due now
        now = datetime.now(UTC).isoformat()
        due_row = self._db.fetch_one(
            "SELECT COUNT(*) as due FROM scheduled_tasks WHERE enabled = 1 AND next_run_at <= ?",
            (now,),
        )
        due = due_row["due"] if due_row else 0

        # Recent executions
        recent_executions = self._db.fetch_all(
            """
            SELECT COUNT(*) as total, SUM(success) as success_count
            FROM scheduled_task_executions
            WHERE executed_at >= datetime('now', '-24 hours')
            """
        )
        exec_row = recent_executions[0] if recent_executions else None
        exec_24h = exec_row["total"] if exec_row else 0
        success_24h = (
            exec_row["success_count"] if exec_row and exec_row["success_count"] else 0
        )

        return {
            "total_tasks": total,
            "active_tasks": active,
            "due_now": due,
            "executions_24h": exec_24h,
            "success_rate_24h": round(success_24h / exec_24h, 2)
            if exec_24h > 0
            else 0.0,
        }
