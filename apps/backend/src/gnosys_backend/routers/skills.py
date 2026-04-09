from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..deps import AppServices, get_services
from ..models import SkillCreateRequest, SkillLifecycleRecord, SkillRecord, SkillTestRequest, SkillTestRunRecord, SkillUpdateRequest


router = APIRouter()


@router.get("/api/skills", response_model=list[SkillRecord])
def skills(services: AppServices = Depends(get_services)) -> list[SkillRecord]:
    return [SkillRecord(**skill) for skill in services.store.list_skills()]


@router.post("/api/skills", response_model=SkillRecord, status_code=201)
def create_skill(payload: SkillCreateRequest, services: AppServices = Depends(get_services)) -> SkillRecord:
    services.gate_mutation(action="skill.create", subject_type="skill", subject_ref=payload.name, payload=payload.model_dump(), project_id=payload.project_id)
    skill = services.store.create_skill(name=payload.name, description=payload.description, scope=payload.scope, version=payload.version, source_type=payload.source_type, status=payload.status, project_id=payload.project_id)
    services.store.record_event(event_type="skill.created", source="ui", payload={"skill_id": skill["id"], "name": skill["name"]})
    return SkillRecord(**skill)


@router.get("/api/skills/{skill_id}", response_model=SkillRecord)
def get_skill(skill_id: str, services: AppServices = Depends(get_services)) -> SkillRecord:
    skill = services.store.get_skill(skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return SkillRecord(**skill)


@router.patch("/api/skills/{skill_id}", response_model=SkillRecord)
def update_skill(skill_id: str, payload: SkillUpdateRequest, services: AppServices = Depends(get_services)) -> SkillRecord:
    existing = services.store.get_skill(skill_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    project_id = services.resolve_optional_project_id(payload, existing)
    services.gate_mutation(action="skill.update", subject_type="skill", subject_ref=skill_id, payload=payload.model_dump(), project_id=project_id)
    skill = services.store.update_skill(skill_id, name=payload.name, description=payload.description, scope=payload.scope, version=payload.version, source_type=payload.source_type, status=payload.status, project_id=project_id)
    services.store.record_event(event_type="skill.updated", source="ui", payload={"skill_id": skill_id, "status": skill["status"]})
    return SkillRecord(**skill)


@router.delete("/api/skills/{skill_id}", status_code=204)
def delete_skill(skill_id: str, services: AppServices = Depends(get_services)) -> None:
    existing = services.store.get_skill(skill_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    services.gate_mutation(action="skill.delete", subject_type="skill", subject_ref=skill_id, payload={"skill_id": skill_id}, project_id=existing.get("project_id"))
    services.store.delete_skill(skill_id)
    services.store.record_event(event_type="skill.deleted", source="ui", payload={"skill_id": skill_id})


@router.post("/api/skills/{skill_id}/draft", response_model=SkillRecord, status_code=201)
def draft_skill(skill_id: str, requested_by: str = "ui", services: AppServices = Depends(get_services)) -> SkillRecord:
    existing = services.store.get_skill(skill_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    services.gate_mutation(action="skill.draft", subject_type="skill", subject_ref=skill_id, payload={"skill_id": skill_id, "requested_by": requested_by}, project_id=existing.get("project_id"))
    return SkillRecord(**services.skill_engine.create_learned_draft(skill_id, requested_by=requested_by))


@router.post("/api/chat-sessions/{session_id}/skills/propose", response_model=SkillRecord, status_code=201)
def propose_skill_from_session(session_id: str, requested_by: str = "ui", services: AppServices = Depends(get_services)) -> SkillRecord:
    session = services.store.get_chat_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    services.gate_mutation(action="skill.draft", subject_type="chat_session", subject_ref=session_id, payload={"chat_session_id": session_id, "requested_by": requested_by})
    try:
        draft = services.skill_engine.propose_from_session(session_id, requested_by=requested_by)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return SkillRecord(**draft)


@router.post("/api/skills/{skill_id}/improve", response_model=SkillRecord, status_code=201)
def improve_skill(skill_id: str, requested_by: str = "ui", services: AppServices = Depends(get_services)) -> SkillRecord:
    existing = services.store.get_skill(skill_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    services.gate_mutation(action="skill.draft", subject_type="skill", subject_ref=skill_id, payload={"skill_id": skill_id, "requested_by": requested_by, "mode": "improve"}, project_id=existing.get("project_id"))
    return SkillRecord(**services.skill_engine.improve_skill(skill_id, requested_by=requested_by))


@router.post("/api/skills/{skill_id}/test", response_model=SkillTestRunRecord, status_code=201)
def test_skill(skill_id: str, payload: SkillTestRequest, services: AppServices = Depends(get_services)) -> SkillTestRunRecord:
    existing = services.store.get_skill(skill_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    services.gate_mutation(action="skill.test", subject_type="skill", subject_ref=skill_id, payload=payload.model_dump(), project_id=existing.get("project_id"))
    return SkillTestRunRecord(**services.skill_engine.test_skill(skill_id, scenario=payload.scenario, expected_outcome=payload.expected_outcome, requested_by=payload.requested_by))


@router.post("/api/skills/{skill_id}/promote", response_model=SkillRecord)
def promote_skill(skill_id: str, requested_by: str = "ui", services: AppServices = Depends(get_services)) -> SkillRecord:
    existing = services.store.get_skill(skill_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    services.gate_mutation(action="skill.promote", subject_type="skill", subject_ref=skill_id, payload={"skill_id": skill_id, "requested_by": requested_by}, project_id=existing.get("project_id"))
    return SkillRecord(**services.skill_engine.promote_skill(skill_id, requested_by=requested_by))


@router.post("/api/skills/{skill_id}/rollback", response_model=SkillRecord)
def rollback_skill(skill_id: str, requested_by: str = "ui", services: AppServices = Depends(get_services)) -> SkillRecord:
    existing = services.store.get_skill(skill_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    services.gate_mutation(action="skill.rollback", subject_type="skill", subject_ref=skill_id, payload={"skill_id": skill_id, "requested_by": requested_by}, project_id=existing.get("project_id"))
    return SkillRecord(**services.skill_engine.rollback_skill(skill_id, requested_by=requested_by))


@router.get("/api/skills/{skill_id}/lifecycle", response_model=SkillLifecycleRecord)
def skill_lifecycle(skill_id: str, services: AppServices = Depends(get_services)) -> SkillLifecycleRecord:
    lifecycle = services.skill_engine.get_lifecycle(skill_id)
    return SkillLifecycleRecord(
        skill=SkillRecord(**lifecycle.skill),
        parent_skill=SkillRecord(**lifecycle.parent_skill) if lifecycle.parent_skill is not None else None,
        related_skills=[SkillRecord(**skill) for skill in lifecycle.related_skills],
        test_runs=[SkillTestRunRecord(**test_run) for test_run in lifecycle.test_runs],
        lifecycle_state=lifecycle.lifecycle_state,
        ready_for_promotion=lifecycle.ready_for_promotion,
    )
