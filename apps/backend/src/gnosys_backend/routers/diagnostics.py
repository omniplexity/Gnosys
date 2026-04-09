from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..deps import AppServices, get_services
from ..models import AgentRunRecord, DiagnosticsMetricsRecord, DiagnosticsRunListResponse, EventRecord, ReplayComparisonRecord, ReplayResponse, ReplayTimelineRecord, ScheduleRunRecord, TaskRunRecord


router = APIRouter()


@router.get("/api/diagnostics/runs", response_model=DiagnosticsRunListResponse)
def diagnostics_runs(
    limit: int = 20,
    query: str | None = None,
    status: str | None = None,
    approval_required: bool | None = None,
    project_id: str | None = None,
    project_thread_id: str | None = None,
    chat_session_id: str | None = None,
    services: AppServices = Depends(get_services),
) -> DiagnosticsRunListResponse:
    if limit < 1 or limit > 50:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 50")
    runs = services.store.list_task_runs(limit=200)
    filtered = []
    for run in runs:
        if status is not None and run["status"] != status:
            continue
        if approval_required is not None and bool(run["approval_required"]) != approval_required:
            continue
        if project_id is not None and run.get("project_id") != project_id:
            continue
        if project_thread_id is not None and run.get("project_thread_id") != project_thread_id:
            continue
        if chat_session_id is not None and run.get("chat_session_id") != chat_session_id:
            continue
        if query and not services.replay_service.run_matches_query(run, query):
            continue
        filtered.append(run)
    filtered = filtered[:limit]
    metrics = services.replay_service.diagnostics_metrics(filtered, filtered_count=len(filtered))
    return DiagnosticsRunListResponse(
        task_runs=[TaskRunRecord(**run) for run in filtered],
        query=query,
        status=status,
        approval_required=approval_required,
        total_count=len(runs),
        filtered_count=len(filtered),
        metrics=DiagnosticsMetricsRecord(**metrics),
    )


@router.get("/api/diagnostics/replay/{task_run_id}", response_model=ReplayResponse)
def replay_run(task_run_id: str, services: AppServices = Depends(get_services)) -> ReplayResponse:
    result = services.orchestration_engine.get_run(task_run_id)
    comparison = services.replay_service.compare_runs(task_run_id)
    return ReplayResponse(
        task_run=TaskRunRecord(**result["task_run"]),
        agent_runs=[AgentRunRecord(**run) for run in result["agent_runs"]],
        events=[EventRecord(**event) for event in services.store.list_replay_events(task_run_id=task_run_id)],
        timeline=[ReplayTimelineRecord(**item) for item in services.replay_service.build_replay_timeline(task_run_id)],
        comparison=ReplayComparisonRecord(**comparison) if comparison is not None else None,
        schedule_runs=[ScheduleRunRecord(**run) for run in services.store.list_schedule_runs(limit=100, task_run_id=task_run_id)],
    )
