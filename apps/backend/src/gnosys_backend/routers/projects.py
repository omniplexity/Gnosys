from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..deps import AppServices, get_services
from ..models import (
    ProjectCreateRequest,
    ProjectRecord,
    ProjectThreadCreateRequest,
    ProjectThreadRecord,
    ProjectThreadUpdateRequest,
    ProjectUpdateRequest,
)


router = APIRouter()


@router.get("/api/projects", response_model=list[ProjectRecord])
def projects(services: AppServices = Depends(get_services)) -> list[ProjectRecord]:
    return [ProjectRecord(**project) for project in services.store.list_projects()]


@router.post("/api/projects", response_model=ProjectRecord, status_code=201)
def create_project(payload: ProjectCreateRequest, services: AppServices = Depends(get_services)) -> ProjectRecord:
    services.gate_mutation(action="project.create", subject_type="project", subject_ref=payload.name, payload=payload.model_dump())
    project = services.store.create_project(name=payload.name, summary=payload.summary, status=payload.status, owner=payload.owner)
    services.store.record_event(event_type="project.created", source="ui", payload={"project_id": project["id"], "name": project["name"]})
    return ProjectRecord(**project)


@router.get("/api/projects/{project_id}", response_model=ProjectRecord)
def get_project(project_id: str, services: AppServices = Depends(get_services)) -> ProjectRecord:
    project = services.store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectRecord(**project)


@router.patch("/api/projects/{project_id}", response_model=ProjectRecord)
def update_project(project_id: str, payload: ProjectUpdateRequest, services: AppServices = Depends(get_services)) -> ProjectRecord:
    services.gate_mutation(action="project.update", subject_type="project", subject_ref=project_id, payload=payload.model_dump(), project_id=project_id)
    project = services.store.update_project(project_id, name=payload.name, summary=payload.summary, status=payload.status, owner=payload.owner)
    services.store.record_event(event_type="project.updated", source="ui", payload={"project_id": project_id, "status": project["status"]})
    return ProjectRecord(**project)


@router.delete("/api/projects/{project_id}", status_code=204)
def delete_project(project_id: str, services: AppServices = Depends(get_services)) -> None:
    services.gate_mutation(action="project.delete", subject_type="project", subject_ref=project_id, payload={"project_id": project_id}, project_id=project_id)
    services.store.delete_project(project_id)
    services.store.record_event(event_type="project.deleted", source="ui", payload={"project_id": project_id})


@router.get("/api/project-threads", response_model=list[ProjectThreadRecord])
def project_threads(project_id: str | None = None, services: AppServices = Depends(get_services)) -> list[ProjectThreadRecord]:
    return [ProjectThreadRecord(**thread) for thread in services.store.list_project_threads(project_id=project_id)]


@router.post("/api/project-threads", response_model=ProjectThreadRecord, status_code=201)
def create_project_thread(payload: ProjectThreadCreateRequest, services: AppServices = Depends(get_services)) -> ProjectThreadRecord:
    services.gate_mutation(action="project_thread.create", subject_type="project", subject_ref=payload.project_id, payload=payload.model_dump(), project_id=payload.project_id)
    thread = services.store.create_project_thread(project_id=payload.project_id, title=payload.title, summary=payload.summary, status=payload.status)
    services.store.record_event(event_type="project_thread.created", source="ui", payload={"thread_id": thread["id"], "project_id": thread["project_id"]})
    return ProjectThreadRecord(**thread)


@router.get("/api/project-threads/{thread_id}", response_model=ProjectThreadRecord)
def get_project_thread(thread_id: str, services: AppServices = Depends(get_services)) -> ProjectThreadRecord:
    thread = services.store.get_project_thread(thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Project thread not found")
    return ProjectThreadRecord(**thread)


@router.patch("/api/project-threads/{thread_id}", response_model=ProjectThreadRecord)
def update_project_thread(thread_id: str, payload: ProjectThreadUpdateRequest, services: AppServices = Depends(get_services)) -> ProjectThreadRecord:
    existing = services.store.get_project_thread(thread_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Project thread not found")
    services.gate_mutation(action="project_thread.update", subject_type="project", subject_ref=existing["project_id"], payload=payload.model_dump(), project_id=existing["project_id"])
    thread = services.store.update_project_thread(thread_id, title=payload.title, summary=payload.summary, status=payload.status)
    services.store.record_event(event_type="project_thread.updated", source="ui", payload={"thread_id": thread_id, "project_id": thread["project_id"]})
    return ProjectThreadRecord(**thread)


@router.delete("/api/project-threads/{thread_id}", status_code=204)
def delete_project_thread(thread_id: str, services: AppServices = Depends(get_services)) -> None:
    existing = services.store.get_project_thread(thread_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Project thread not found")
    services.gate_mutation(action="project_thread.delete", subject_type="project", subject_ref=existing["project_id"], payload={"thread_id": thread_id}, project_id=existing["project_id"])
    services.store.delete_project_thread(thread_id)
    services.store.record_event(event_type="project_thread.deleted", source="ui", payload={"thread_id": thread_id, "project_id": existing["project_id"]})
