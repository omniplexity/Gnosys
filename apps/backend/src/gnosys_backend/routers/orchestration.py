from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..deps import AppServices, get_services
from ..models import AgentRunRecord, OrchestrationDecisionRecord, OrchestrationLaunchRequest, OrchestrationLaunchResponse, OrchestrationRunListResponse, OrchestrationRunResponse, OrchestrationStepRecord, TaskRecord, TaskRunRecord


router = APIRouter()


@router.get("/api/orchestration/runs", response_model=OrchestrationRunListResponse)
def orchestration_runs(limit: int = 10, services: AppServices = Depends(get_services)) -> OrchestrationRunListResponse:
    if limit < 1 or limit > 20:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 20")
    return OrchestrationRunListResponse(task_runs=[TaskRunRecord(**run) for run in services.orchestration_engine.list_runs(limit=limit)])


@router.get("/api/orchestration/runs/{task_run_id}", response_model=OrchestrationRunResponse)
def orchestration_run(task_run_id: str, services: AppServices = Depends(get_services)) -> OrchestrationRunResponse:
    result = services.orchestration_engine.get_run(task_run_id)
    return OrchestrationRunResponse(task=TaskRecord(**result["task"]), task_run=TaskRunRecord(**result["task_run"]), agent_runs=[AgentRunRecord(**run) for run in result["agent_runs"]])


@router.post("/api/orchestration/launch", response_model=OrchestrationLaunchResponse, status_code=201)
def launch_orchestration(payload: OrchestrationLaunchRequest, services: AppServices = Depends(get_services)) -> OrchestrationLaunchResponse:
    services.gate_mutation(action="orchestration.launch", subject_type="task_run", subject_ref=payload.task_title or payload.objective[:48], payload=payload.model_dump())
    result = services.orchestration_engine.launch(
        objective=payload.objective,
        task_title=payload.task_title,
        task_summary=payload.task_summary,
        requested_by=payload.requested_by,
        mode=payload.mode,
        priority=payload.priority,
        task_id=payload.task_id,
        project_id=payload.project_id,
        project_thread_id=payload.project_thread_id,
        chat_session_id=payload.chat_session_id,
    )
    return OrchestrationLaunchResponse(
        task=TaskRecord(**result.task),
        task_run=TaskRunRecord(**result.task_run),
        agent_runs=[AgentRunRecord(**run) for run in result.agent_runs],
        steps=[OrchestrationStepRecord(**step) for step in result.steps],
        approvals_required=result.approvals_required,
        summary=result.summary,
        decision=OrchestrationDecisionRecord(**result.decision),
    )
