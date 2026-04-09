from __future__ import annotations

from pathlib import Path

from gnosys_backend.runtime import OrchestrationEngine
from gnosys_backend.services.scheduler_service import ScheduleRunner, SchedulerService
from gnosys_backend.store import GnosysStore


class FailingOrchestrationEngine:
    def launch(self, **_: object) -> object:
        raise RuntimeError("Synthetic scheduler failure")


def build_store(tmp_path: Path) -> GnosysStore:
    store = GnosysStore(path=tmp_path / "gnosys.sqlite3")
    store.initialize()
    return store


def test_scheduler_service_dispatch_advances_window_after_success(tmp_path: Path) -> None:
    store = build_store(tmp_path)
    service = SchedulerService(store, OrchestrationEngine(store))
    schedule = store.create_schedule(
        name="Service dispatch schedule",
        target_type="skill",
        target_ref="skill-001",
        schedule_expression="FREQ=DAILY;BYHOUR=9;BYMINUTE=0",
        timezone="America/New_York",
        enabled=True,
        approval_policy="autonomous",
        failure_policy="retry_once",
        last_run_at="2026-04-05T13:00:00Z",
        next_run_at="2026-04-06T13:00:00Z",
    )

    run = service.dispatch_schedule_run(schedule, requested_by="scheduler")
    updated = store.get_schedule(schedule["id"])

    assert run["status"] == "completed"
    assert run["task_run_id"] is not None
    assert updated is not None
    assert updated["last_run_at"] is not None
    assert updated["next_run_at"] is not None
    assert updated["next_run_at"] > run["created_at"]


def test_scheduler_service_retry_policy_matrix(tmp_path: Path) -> None:
    store = build_store(tmp_path)
    service = SchedulerService(store, OrchestrationEngine(store))

    fail_fast = service.evaluate_schedule_policy({"failure_policy": "fail_fast"}, attempt_number=1)
    retry_once = service.evaluate_schedule_policy({"failure_policy": "retry_once"}, attempt_number=1)
    retry_twice = service.evaluate_schedule_policy({"failure_policy": "retry_twice"}, attempt_number=2)

    assert fail_fast.max_attempts == 1
    assert retry_once.max_attempts == 2
    assert retry_twice.max_attempts == 3
    assert retry_twice.backoff_seconds == 600


def test_scheduler_service_reject_pending_approval_marks_run_and_advances_window(tmp_path: Path) -> None:
    store = build_store(tmp_path)
    service = SchedulerService(store, OrchestrationEngine(store))
    schedule = store.create_schedule(
        name="Approval rejection schedule",
        target_type="skill",
        target_ref="skill-001",
        schedule_expression="FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0",
        timezone="America/New_York",
        enabled=True,
        approval_policy="require_approval",
        failure_policy="retry_once",
        last_run_at="2026-04-05T13:00:00Z",
        next_run_at="2026-04-06T13:00:00Z",
    )
    queued = service.queue_schedule_approval(schedule, requested_by="scheduler")
    approval = queued["approval_request"]

    service.reject_pending_approval(approval, resolved_by="tester")

    rejected = store.get_schedule_run(queued["schedule_run"]["id"])
    updated_schedule = store.get_schedule(schedule["id"])
    assert rejected is not None
    assert rejected["status"] == "rejected"
    assert updated_schedule is not None
    assert updated_schedule["next_run_at"] is not None
    assert updated_schedule["last_run_at"] is not None


def test_schedule_runner_queues_approval_for_due_schedule(tmp_path: Path) -> None:
    store = build_store(tmp_path)
    service = SchedulerService(store, OrchestrationEngine(store))
    runner = ScheduleRunner(service, poll_interval_seconds=0.01)
    schedule = store.create_schedule(
        name="Runner approval schedule",
        target_type="skill",
        target_ref="skill-001",
        schedule_expression="FREQ=DAILY;BYHOUR=9;BYMINUTE=0",
        timezone="America/New_York",
        enabled=True,
        approval_policy="require_approval",
        failure_policy="retry_once",
        last_run_at="2026-04-05T13:00:00Z",
        next_run_at="2026-04-06T13:00:00Z",
    )

    processed = runner.run_once()

    assert any(item["schedule_id"] == schedule["id"] for item in processed)
    pending = store.list_schedule_runs(limit=5, schedule_id=schedule["id"])[0]
    assert pending["status"] == "pending_approval"


def test_scheduler_service_failure_schedules_retry_window(tmp_path: Path) -> None:
    store = build_store(tmp_path)
    service = SchedulerService(store, FailingOrchestrationEngine())
    schedule = store.create_schedule(
        name="Failure retry schedule",
        target_type="skill",
        target_ref="skill-001",
        schedule_expression="FREQ=DAILY;BYHOUR=9;BYMINUTE=0",
        timezone="America/New_York",
        enabled=True,
        approval_policy="autonomous",
        failure_policy="retry_once",
        last_run_at="2026-04-05T13:00:00Z",
        next_run_at="2026-04-06T13:00:00Z",
    )

    failed = service.dispatch_schedule_run(schedule, requested_by="scheduler")
    updated = store.get_schedule(schedule["id"])

    assert failed["status"] == "failed"
    assert updated is not None
    assert updated["next_run_at"] is not None
    assert updated["last_run_at"] == schedule["last_run_at"]
