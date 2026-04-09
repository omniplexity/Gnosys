from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..deps import AppServices, get_services
from ..models import ScheduleCreateRequest, ScheduleRecord, ScheduleRunListResponse, ScheduleRunRecord, ScheduleUpdateRequest


router = APIRouter()


@router.get("/api/schedules", response_model=list[ScheduleRecord])
def schedules(services: AppServices = Depends(get_services)) -> list[ScheduleRecord]:
    return [ScheduleRecord(**schedule) for schedule in services.store.list_schedules()]


@router.post("/api/schedules", response_model=ScheduleRecord, status_code=201)
def create_schedule(payload: ScheduleCreateRequest, services: AppServices = Depends(get_services)) -> ScheduleRecord:
    services.gate_mutation(action="schedule.create", subject_type="schedule", subject_ref=payload.name, payload=payload.model_dump(), project_id=payload.project_id)
    schedule = services.store.create_schedule(
        name=payload.name,
        target_type=payload.target_type,
        target_ref=payload.target_ref,
        schedule_expression=payload.schedule_expression,
        timezone=payload.timezone,
        enabled=payload.enabled,
        approval_policy=payload.approval_policy,
        failure_policy=payload.failure_policy,
        last_run_at=payload.last_run_at,
        next_run_at=payload.next_run_at,
        project_id=payload.project_id,
    )
    services.store.record_event(event_type="schedule.created", source="ui", payload={"schedule_id": schedule["id"], "name": schedule["name"]})
    return ScheduleRecord(**schedule)


@router.get("/api/schedules/{schedule_id}", response_model=ScheduleRecord)
def get_schedule(schedule_id: str, services: AppServices = Depends(get_services)) -> ScheduleRecord:
    schedule = services.store.get_schedule(schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return ScheduleRecord(**schedule)


@router.patch("/api/schedules/{schedule_id}", response_model=ScheduleRecord)
def update_schedule(schedule_id: str, payload: ScheduleUpdateRequest, services: AppServices = Depends(get_services)) -> ScheduleRecord:
    existing = services.store.get_schedule(schedule_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    project_id = services.resolve_optional_project_id(payload, existing)
    services.gate_mutation(action="schedule.update", subject_type="schedule", subject_ref=schedule_id, payload=payload.model_dump(), project_id=project_id)
    schedule = services.store.update_schedule(
        schedule_id,
        name=payload.name,
        target_type=payload.target_type,
        target_ref=payload.target_ref,
        schedule_expression=payload.schedule_expression,
        timezone=payload.timezone,
        enabled=payload.enabled,
        approval_policy=payload.approval_policy,
        failure_policy=payload.failure_policy,
        last_run_at=payload.last_run_at,
        next_run_at=payload.next_run_at,
        project_id=project_id,
    )
    services.store.record_event(event_type="schedule.updated", source="ui", payload={"schedule_id": schedule_id, "enabled": schedule["enabled"]})
    return ScheduleRecord(**schedule)


@router.delete("/api/schedules/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: str, services: AppServices = Depends(get_services)) -> None:
    existing = services.store.get_schedule(schedule_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    services.gate_mutation(action="schedule.delete", subject_type="schedule", subject_ref=schedule_id, payload={"schedule_id": schedule_id}, project_id=existing.get("project_id"))
    services.store.delete_schedule(schedule_id)
    services.store.record_event(event_type="schedule.deleted", source="ui", payload={"schedule_id": schedule_id})


@router.get("/api/schedule-runs", response_model=ScheduleRunListResponse)
def schedule_runs(limit: int = 25, services: AppServices = Depends(get_services)) -> ScheduleRunListResponse:
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    return ScheduleRunListResponse(schedule_runs=[ScheduleRunRecord(**run) for run in services.store.list_schedule_runs(limit=limit)])


@router.post("/api/schedules/{schedule_id}/run", response_model=ScheduleRunRecord, status_code=201)
def run_schedule(schedule_id: str, requested_by: str = "ui", services: AppServices = Depends(get_services)) -> ScheduleRunRecord:
    schedule = services.store.get_schedule(schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    active_run = services.scheduler_service.latest_active_run(schedule_id)
    if active_run is not None:
        return ScheduleRunRecord(**active_run)
    policy = services.scheduler_service.evaluate_schedule_policy(schedule)
    if policy.requires_approval:
        raise services.scheduler_service.build_schedule_approval_exception(schedule, requested_by=requested_by, policy_snapshot=services.policy_engine.snapshot())
    services.gate_mutation(
        action="schedule.run",
        subject_type="schedule",
        subject_ref=schedule_id,
        payload={
            "schedule_id": schedule_id,
            "schedule_name": schedule["name"],
            "target_type": schedule["target_type"],
            "target_ref": schedule["target_ref"],
            "requested_by": requested_by,
            "project_id": schedule.get("project_id"),
            "approval_policy": schedule.get("approval_policy"),
            "failure_policy": schedule.get("failure_policy"),
        },
        project_id=schedule.get("project_id"),
    )
    return ScheduleRunRecord(**services.scheduler_service.dispatch_schedule_run(schedule, requested_by=requested_by))


@router.post("/api/schedule-runs/{run_id}/retry", response_model=ScheduleRunRecord, status_code=201)
def retry_schedule_run(run_id: str, requested_by: str = "ui", services: AppServices = Depends(get_services)) -> ScheduleRunRecord:
    original = services.store.get_schedule_run(run_id)
    if original is None:
        raise HTTPException(status_code=404, detail="Schedule run not found")
    schedule = services.store.get_schedule(original["schedule_id"])
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    active_retry = services.scheduler_service.latest_active_run(str(schedule["id"]), retry_of_run_id=run_id)
    if active_retry is not None:
        return ScheduleRunRecord(**active_retry)
    policy = services.scheduler_service.evaluate_schedule_policy(schedule, attempt_number=int(original["attempt_number"]) + 1)
    if policy.requires_approval:
        raise services.scheduler_service.build_schedule_approval_exception(
            schedule,
            requested_by=requested_by,
            retry_of_run_id=run_id,
            attempt_number=int(original["attempt_number"]) + 1,
            policy_snapshot=services.policy_engine.snapshot(),
        )
    services.gate_mutation(
        action="schedule.run",
        subject_type="schedule",
        subject_ref=schedule["id"],
        payload={
            "schedule_id": schedule["id"],
            "schedule_name": schedule["name"],
            "target_type": schedule["target_type"],
            "target_ref": schedule["target_ref"],
            "requested_by": requested_by,
            "retry_of_run_id": run_id,
            "project_id": schedule.get("project_id"),
            "approval_policy": schedule.get("approval_policy"),
            "failure_policy": schedule.get("failure_policy"),
        },
        project_id=schedule.get("project_id"),
    )
    return ScheduleRunRecord(**services.scheduler_service.retry_schedule_run(original, schedule, requested_by=requested_by))
