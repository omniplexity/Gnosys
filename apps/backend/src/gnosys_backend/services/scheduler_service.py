from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from threading import Event, Thread
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException

from ..models import ApprovalRequestRecord
from ..runtime import OrchestrationEngine
from ..store import GnosysStore, utc_now


WEEKDAY_INDEX = {
    "MO": 0,
    "TU": 1,
    "WE": 2,
    "TH": 3,
    "FR": 4,
    "SA": 5,
    "SU": 6,
}


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _coerce_datetime(value: datetime | str | None) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = _parse_iso_datetime(value)
        if parsed is None:
            return datetime.now(timezone.utc)
    else:
        return datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _isoformat(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_schedule_expression(expression: str) -> dict[str, str]:
    parts: dict[str, str] = {}
    for chunk in expression.split(";"):
        if "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        key = key.strip().upper()
        value = value.strip()
        if key:
            parts[key] = value
    if "FREQ" not in parts:
        raise ValueError("schedule expression must include FREQ")
    return parts


def _parse_days(value: str | None, fallback: int) -> list[int]:
    if not value:
        return [fallback]
    days: list[int] = []
    for token in value.split(","):
        weekday = WEEKDAY_INDEX.get(token.strip().upper())
        if weekday is not None and weekday not in days:
            days.append(weekday)
    return days or [fallback]


def schedule_execution_objective(store: GnosysStore, schedule: dict[str, Any]) -> tuple[str, str | None, str | None]:
    target_type = str(schedule.get("target_type", ""))
    target_ref = str(schedule.get("target_ref", ""))
    if target_type == "task":
        task = store.get_task(target_ref)
        if task is not None:
            return (f"Scheduled task execution: {task['title']}", task["title"], task["summary"])
    if target_type == "project":
        project = store.get_project(target_ref)
        if project is not None:
            return (f"Scheduled project execution: {project['name']}", project["name"], project["summary"])
    if target_type == "skill":
        skill = store.get_skill(target_ref)
        if skill is not None:
            return (f"Scheduled skill execution: {skill['name']}", skill["name"], skill["description"])
    if target_type == "orchestration":
        return (
            f"Scheduled orchestration: {target_ref or schedule.get('name', 'scheduled run')}",
            str(schedule.get("name", "Scheduled orchestration")),
            f"Recurring execution for {target_ref or schedule.get('name', 'scheduled run')}",
        )
    return (
        f"Scheduled execution: {schedule.get('name', 'scheduled run')}",
        str(schedule.get("name", "Scheduled run")),
        str(schedule.get("name", "Scheduled run")),
    )


@dataclass(slots=True)
class SchedulePolicyDecision:
    requires_approval: bool
    max_attempts: int
    backoff_seconds: int


class SchedulerService:
    def __init__(self, store: GnosysStore, orchestration_engine: OrchestrationEngine) -> None:
        self.store = store
        self.orchestration_engine = orchestration_engine

    def compute_next_run(self, schedule: dict[str, Any], reference: datetime | str | None = None) -> str | None:
        try:
            zone = ZoneInfo(str(schedule.get("timezone", "America/New_York")))
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unknown timezone: {schedule.get('timezone')}") from exc

        expression = parse_schedule_expression(str(schedule.get("schedule_expression", "")))
        frequency = expression["FREQ"].upper()
        reference_dt = _coerce_datetime(reference)
        local_reference = reference_dt.astimezone(zone)
        try:
            interval = max(int(expression.get("INTERVAL", "1")), 1)
        except ValueError as exc:
            raise ValueError("INTERVAL must be an integer") from exc

        hour = local_reference.hour
        minute = local_reference.minute
        if "BYHOUR" in expression:
            hour = max(0, min(int(expression["BYHOUR"]), 23))
        if "BYMINUTE" in expression:
            minute = max(0, min(int(expression["BYMINUTE"]), 59))

        if frequency == "HOURLY":
            candidate = local_reference.replace(minute=minute, second=0, microsecond=0)
            while candidate <= local_reference:
                candidate += timedelta(hours=interval)
            return _isoformat(candidate)
        if frequency == "DAILY":
            candidate = local_reference.replace(hour=hour, minute=minute, second=0, microsecond=0)
            while candidate <= local_reference:
                candidate += timedelta(days=interval)
            return _isoformat(candidate)
        if frequency == "WEEKLY":
            weekdays = _parse_days(expression.get("BYDAY"), local_reference.weekday())
            candidate_date = local_reference.date()
            for _ in range(0, 7 * interval * 8):
                candidate = datetime.combine(candidate_date, time(hour=hour, minute=minute), tzinfo=zone)
                if candidate > local_reference and candidate.weekday() in weekdays:
                    return _isoformat(candidate)
                candidate_date += timedelta(days=1)
            raise ValueError("Unable to compute next weekly occurrence")
        raise ValueError(f"Unsupported schedule frequency: {frequency}")

    def evaluate_schedule_policy(self, schedule: dict[str, Any], *, attempt_number: int = 1) -> SchedulePolicyDecision:
        failure_policy = str(schedule.get("failure_policy", "retry_once")).lower()
        max_attempts = {"fail_fast": 1, "retry_once": 2, "retry_twice": 3}.get(failure_policy, 2)
        approval_policy = str(schedule.get("approval_policy", "inherit")).lower()
        requires_approval = approval_policy in {"require_approval", "manual", "approval_required"}
        return SchedulePolicyDecision(
            requires_approval=requires_approval,
            max_attempts=max_attempts,
            backoff_seconds=max(attempt_number, 1) * 300,
        )

    def latest_pending_run(self, schedule_id: str) -> dict[str, Any] | None:
        for run in self.store.list_schedule_runs(limit=10, schedule_id=schedule_id):
            if run["status"] == "pending_approval":
                return run
        return None

    def latest_active_run(self, schedule_id: str, *, retry_of_run_id: str | None = None) -> dict[str, Any] | None:
        runs = self.store.list_schedule_runs(limit=10, schedule_id=schedule_id, retry_of_run_id=retry_of_run_id)
        for run in runs:
            if run["status"] == "running" and run.get("completed_at") is None:
                return run
        return None

    def latest_run(self, schedule_id: str) -> dict[str, Any] | None:
        runs = self.store.list_schedule_runs(limit=1, schedule_id=schedule_id)
        return runs[0] if runs else None

    def _persist_schedule_window(self, schedule: dict[str, Any], *, last_run_at: str | None, next_run_at: str | None) -> dict[str, Any]:
        return self.store.update_schedule(
            str(schedule["id"]),
            name=str(schedule.get("name", "Untitled schedule")),
            target_type=str(schedule.get("target_type", "skill")),
            target_ref=str(schedule.get("target_ref", "")),
            schedule_expression=str(schedule.get("schedule_expression", "")),
            timezone=str(schedule.get("timezone", "America/New_York")),
            enabled=bool(schedule.get("enabled", True)),
            approval_policy=str(schedule.get("approval_policy", "inherit")),
            failure_policy=str(schedule.get("failure_policy", "retry_once")),
            last_run_at=last_run_at,
            next_run_at=next_run_at,
            project_id=str(schedule["project_id"]) if schedule.get("project_id") else None,
        )

    def advance_schedule_window(
        self,
        schedule: dict[str, Any],
        *,
        reference: datetime | str | None = None,
        last_run_at: str | None = None,
    ) -> dict[str, Any]:
        next_run_at = self.compute_next_run(schedule, reference=reference)
        return self._persist_schedule_window(schedule, last_run_at=last_run_at, next_run_at=next_run_at)

    def queue_schedule_approval(
        self,
        schedule: dict[str, Any],
        *,
        requested_by: str,
        retry_of_run_id: str | None = None,
        attempt_number: int = 1,
    ) -> dict[str, Any]:
        run = self.store.create_schedule_run(
            schedule_id=str(schedule["id"]),
            schedule_name=str(schedule["name"]),
            target_type=str(schedule["target_type"]),
            target_ref=str(schedule["target_ref"]),
            requested_by=requested_by,
            result_summary=f"Schedule {schedule['name']} is waiting for approval.",
            retry_of_run_id=retry_of_run_id,
            attempt_number=attempt_number,
            status="pending_approval",
        )
        approval = self.store.create_approval_request(
            action="schedule.run",
            subject_type="schedule",
            subject_ref=str(schedule["id"]),
            sensitivity="high",
            reason="Schedule approval policy requires manual review.",
            payload={
                "schedule_id": schedule["id"],
                "schedule_name": schedule["name"],
                "target_type": schedule["target_type"],
                "target_ref": schedule["target_ref"],
                "requested_by": requested_by,
                "retry_of_run_id": retry_of_run_id,
                "attempt_number": attempt_number,
                "project_id": schedule.get("project_id"),
                "approval_policy": schedule.get("approval_policy"),
                "failure_policy": schedule.get("failure_policy"),
            },
            requested_by=requested_by,
        )
        self.store.record_event(
            event_type="approval.requested",
            source="policy",
            payload={
                "approval_id": approval["id"],
                "action": "schedule.run",
                "subject_type": "schedule",
                "subject_ref": schedule["id"],
                "reason": "Schedule approval policy requires manual review.",
                "schedule_run_id": run["id"],
            },
        )
        return {"schedule_run": run, "approval_request": approval, "schedule_id": schedule["id"]}

    def build_schedule_approval_exception(
        self,
        schedule: dict[str, Any],
        *,
        requested_by: str,
        retry_of_run_id: str | None = None,
        attempt_number: int = 1,
        policy_snapshot: dict[str, Any],
    ) -> HTTPException:
        result = self.queue_schedule_approval(
            schedule,
            requested_by=requested_by,
            retry_of_run_id=retry_of_run_id,
            attempt_number=attempt_number,
        )
        approval = result["approval_request"]
        return HTTPException(
            status_code=423,
            detail={
                "message": "Approval required",
                "decision": {
                    "allowed": False,
                    "requires_approval": True,
                    "sensitivity": "high",
                    "reason": "Schedule approval policy requires manual review.",
                    "mode": policy_snapshot["autonomy_mode"],
                    "action": "schedule.run",
                    "policy_scope": "entity",
                    "policy_entity_type": "schedule",
                    "policy_entity_id": schedule["id"],
                },
                "approval_request": ApprovalRequestRecord(**approval).model_dump(),
                "policy": policy_snapshot,
            },
        )

    def dispatch_schedule_run(
        self,
        schedule: dict[str, Any],
        *,
        requested_by: str,
        retry_of_run_id: str | None = None,
        attempt_number: int = 1,
        existing_run_id: str | None = None,
        advance_timing: bool = True,
    ) -> dict[str, Any]:
        reference_now = utc_now()
        if existing_run_id is None:
            run = self.store.create_schedule_run(
                schedule_id=str(schedule["id"]),
                schedule_name=str(schedule["name"]),
                target_type=str(schedule["target_type"]),
                target_ref=str(schedule["target_ref"]),
                requested_by=requested_by,
                result_summary=f"Queued schedule {schedule['name']} for execution.",
                retry_of_run_id=retry_of_run_id,
                attempt_number=attempt_number,
                status="running",
            )
        else:
            run = self.store.update_schedule_run(
                existing_run_id,
                status="running",
                result_summary=f"Executing schedule {schedule['name']}.",
                completed=False,
            )
        self.store.record_event(
            event_type="schedule.run_requested",
            source="scheduler",
            payload={
                "schedule_run_id": run["id"],
                "schedule_id": schedule["id"],
                "requested_by": requested_by,
                "attempt_number": attempt_number,
            },
        )
        try:
            objective, task_title, task_summary = schedule_execution_objective(self.store, schedule)
            launch = self.orchestration_engine.launch(
                objective=objective,
                task_title=task_title,
                task_summary=task_summary,
                requested_by=requested_by,
                mode="Autonomous",
                priority="High",
                task_id=str(schedule.get("target_ref")) if str(schedule.get("target_type")) == "task" else None,
                bypass_policy=True,
            )
            updated = self.store.update_schedule_run(
                run["id"],
                status="completed",
                result_summary=launch.summary,
                task_run_id=launch.task_run["id"],
                completed=True,
            )
            self.store.record_event(
                event_type="schedule.run_completed",
                source="scheduler",
                payload={
                    "schedule_run_id": run["id"],
                    "schedule_id": schedule["id"],
                    "task_run_id": launch.task_run["id"],
                    "requested_by": requested_by,
                },
            )
            if advance_timing:
                self.advance_schedule_window(schedule, reference=reference_now, last_run_at=updated["completed_at"] or reference_now)
            return updated
        except Exception as exc:
            failed = self.store.update_schedule_run(
                run["id"],
                status="failed",
                last_error=str(exc),
                completed=True,
            )
            self.store.record_event(
                event_type="schedule.run_failed",
                source="scheduler",
                payload={
                    "schedule_run_id": run["id"],
                    "schedule_id": schedule["id"],
                    "requested_by": requested_by,
                    "error": str(exc),
                },
            )
            policy = self.evaluate_schedule_policy(schedule, attempt_number=attempt_number)
            if attempt_number < policy.max_attempts:
                retry_run_at = _isoformat(_coerce_datetime(reference_now) + timedelta(seconds=policy.backoff_seconds))
                self._persist_schedule_window(schedule, last_run_at=schedule.get("last_run_at"), next_run_at=retry_run_at)
                self.store.record_event(
                    event_type="schedule.run_retry_scheduled",
                    source="scheduler",
                    payload={
                        "schedule_id": schedule["id"],
                        "previous_run_id": run["id"],
                        "requested_by": requested_by,
                        "attempt_number": attempt_number + 1,
                        "next_run_at": retry_run_at,
                    },
                )
                return failed
            if advance_timing:
                self.advance_schedule_window(schedule, reference=reference_now, last_run_at=failed["completed_at"] or reference_now)
            return failed

    def retry_schedule_run(self, original_run: dict[str, Any], schedule: dict[str, Any], *, requested_by: str) -> dict[str, Any]:
        active_retry = self.latest_active_run(str(schedule["id"]), retry_of_run_id=str(original_run["id"]))
        if active_retry is not None:
            return active_retry
        return self.dispatch_schedule_run(
            schedule,
            requested_by=requested_by,
            retry_of_run_id=str(original_run["id"]),
            attempt_number=int(original_run["attempt_number"]) + 1,
        )

    def reject_pending_approval(self, approval: dict[str, Any], *, resolved_by: str) -> None:
        subject_ref = str(approval["subject_ref"])
        pending_run = self.latest_pending_run(subject_ref)
        schedule = self.store.get_schedule(subject_ref)
        if schedule is None:
            return
        completed_at = None
        if pending_run is not None:
            updated_run = self.store.update_schedule_run(
                pending_run["id"],
                status="rejected",
                result_summary="Schedule run rejected during approval review.",
                last_error="Approval rejected",
                completed=True,
            )
            completed_at = updated_run["completed_at"]
            self.store.record_event(
                event_type="schedule.run_rejected",
                source="policy",
                payload={
                    "schedule_run_id": pending_run["id"],
                    "schedule_id": schedule["id"],
                    "approval_id": approval["id"],
                    "resolved_by": resolved_by,
                },
            )
        self.advance_schedule_window(schedule, reference=completed_at or utc_now(), last_run_at=completed_at or utc_now())

    def prime_schedules(self) -> int:
        primed = 0
        for schedule in self.store.list_schedules():
            if not schedule["enabled"] or schedule.get("next_run_at"):
                continue
            try:
                next_run_at = self.compute_next_run(schedule, reference=utc_now())
            except ValueError:
                continue
            self._persist_schedule_window(schedule, last_run_at=schedule.get("last_run_at"), next_run_at=next_run_at)
            primed += 1
        return primed


@dataclass(slots=True)
class ScheduleRunner:
    scheduler_service: SchedulerService
    poll_interval_seconds: float = 5.0
    _stop_event: Event | None = None
    _thread: Thread | None = None

    def __post_init__(self) -> None:
        self._stop_event = Event()
        self._thread = None

    @property
    def store(self) -> GnosysStore:
        return self.scheduler_service.store

    def prime_schedules(self) -> int:
        return self.scheduler_service.prime_schedules()

    def run_once(self) -> list[dict[str, Any]]:
        now = utc_now()
        now_dt = _coerce_datetime(now)
        processed: list[dict[str, Any]] = []
        for schedule in self.store.list_schedules():
            if not schedule["enabled"]:
                continue
            if self.scheduler_service.latest_active_run(str(schedule["id"])) is not None:
                continue
            if self.scheduler_service.latest_pending_run(str(schedule["id"])) is not None:
                continue
            next_run_at = schedule.get("next_run_at")
            if not next_run_at:
                try:
                    next_run_at = self.scheduler_service.compute_next_run(schedule, reference=now_dt)
                except ValueError:
                    continue
                schedule = self.scheduler_service._persist_schedule_window(
                    schedule,
                    last_run_at=schedule.get("last_run_at"),
                    next_run_at=next_run_at,
                )
            due_at = _parse_iso_datetime(str(next_run_at))
            if due_at is None or due_at > now_dt:
                continue
            latest_run = self.scheduler_service.latest_run(str(schedule["id"]))
            retry_of_run_id = None
            attempt_number = 1
            if latest_run is not None and latest_run["status"] == "failed" and latest_run.get("completed_at") is not None:
                retry_of_run_id = str(latest_run["id"])
                attempt_number = int(latest_run["attempt_number"]) + 1
            policy = self.scheduler_service.evaluate_schedule_policy(schedule, attempt_number=attempt_number)
            if policy.requires_approval:
                result = self.scheduler_service.queue_schedule_approval(
                    schedule,
                    requested_by="scheduler",
                    retry_of_run_id=retry_of_run_id,
                    attempt_number=attempt_number,
                )
            else:
                result = {
                    "schedule_run": self.scheduler_service.dispatch_schedule_run(
                        schedule,
                        requested_by="scheduler",
                        retry_of_run_id=retry_of_run_id,
                        attempt_number=attempt_number,
                    ),
                    "schedule_id": schedule["id"],
                }
            processed.append(result)
        return processed

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        assert self._stop_event is not None
        self._stop_event.clear()
        self._thread = Thread(target=self._loop, name="gnosys-schedule-daemon", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        assert self._stop_event is not None
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def _loop(self) -> None:
        assert self._stop_event is not None
        while not self._stop_event.is_set():
            try:
                self.run_once()
            except Exception:
                pass
            self._stop_event.wait(self.poll_interval_seconds)
