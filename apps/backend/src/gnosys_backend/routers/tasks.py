from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..deps import AppServices, get_services
from ..models import TaskCreateRequest, TaskRecord, TaskUpdateRequest


router = APIRouter()


@router.get("/api/tasks", response_model=list[TaskRecord])
def tasks(services: AppServices = Depends(get_services)) -> list[TaskRecord]:
    return [TaskRecord(**task) for task in services.store.list_tasks()]


@router.post("/api/tasks", response_model=TaskRecord, status_code=201)
def create_task(payload: TaskCreateRequest, services: AppServices = Depends(get_services)) -> TaskRecord:
    services.gate_mutation(action="task.create", subject_type="task", subject_ref=payload.title, payload=payload.model_dump(), project_id=payload.project_id)
    task = services.store.create_task(title=payload.title, summary=payload.summary, status=payload.status, priority=payload.priority, project_id=payload.project_id)
    services.store.record_event(event_type="task.created", source="ui", payload={"task_id": task["id"], "title": task["title"]})
    return TaskRecord(**task)


@router.get("/api/tasks/{task_id}", response_model=TaskRecord)
def get_task(task_id: str, services: AppServices = Depends(get_services)) -> TaskRecord:
    task = services.store.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskRecord(**task)


@router.patch("/api/tasks/{task_id}", response_model=TaskRecord)
def update_task(task_id: str, payload: TaskUpdateRequest, services: AppServices = Depends(get_services)) -> TaskRecord:
    existing = services.store.get_task(task_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Task not found")
    project_id = services.resolve_optional_project_id(payload, existing)
    services.gate_mutation(action="task.update", subject_type="task", subject_ref=task_id, payload=payload.model_dump(), project_id=project_id)
    task = services.store.update_task(task_id, title=payload.title, summary=payload.summary, status=payload.status, priority=payload.priority, project_id=project_id)
    services.store.record_event(event_type="task.updated", source="ui", payload={"task_id": task_id, "status": task["status"]})
    return TaskRecord(**task)


@router.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(task_id: str, services: AppServices = Depends(get_services)) -> None:
    existing = services.store.get_task(task_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Task not found")
    services.gate_mutation(action="task.delete", subject_type="task", subject_ref=task_id, payload={"task_id": task_id}, project_id=existing.get("project_id"))
    services.store.delete_task(task_id)
    services.store.record_event(event_type="task.deleted", source="ui", payload={"task_id": task_id})
