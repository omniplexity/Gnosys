from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..deps import AppServices, get_services
from ..models import EntityPolicyRecord, EntityPolicyUpdateRequest, PolicyRecord, PolicyUpdateRequest


router = APIRouter()


@router.get("/api/policy", response_model=PolicyRecord)
def get_policy(services: AppServices = Depends(get_services)) -> PolicyRecord:
    return PolicyRecord(**services.policy_engine.snapshot())


@router.patch("/api/policy", response_model=PolicyRecord)
def update_policy(payload: PolicyUpdateRequest, services: AppServices = Depends(get_services)) -> PolicyRecord:
    policy = services.policy_engine.update(
        autonomy_mode=payload.autonomy_mode,
        kill_switch=payload.kill_switch,
        approval_bias=payload.approval_bias,
    )
    services.store.record_event(event_type="policy.updated", source="ui", payload=policy)
    return PolicyRecord(**policy)


@router.get("/api/policies/entities", response_model=list[EntityPolicyRecord])
def list_entity_policies(limit: int = 25, services: AppServices = Depends(get_services)) -> list[EntityPolicyRecord]:
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    return [EntityPolicyRecord(**policy) for policy in services.store.list_entity_policies(limit=limit)]


@router.get("/api/policies/entities/{entity_type}/{entity_id}", response_model=EntityPolicyRecord)
def get_entity_policy(entity_type: str, entity_id: str, services: AppServices = Depends(get_services)) -> EntityPolicyRecord:
    policy = services.store.get_entity_policy(entity_type, entity_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Entity policy not found")
    return EntityPolicyRecord(**policy)


@router.patch("/api/policies/entities/{entity_type}/{entity_id}", response_model=EntityPolicyRecord)
def update_entity_policy(
    entity_type: str,
    entity_id: str,
    payload: EntityPolicyUpdateRequest,
    services: AppServices = Depends(get_services),
) -> EntityPolicyRecord:
    existing = services.store.get_entity_policy(entity_type, entity_id)
    project_id = existing.get("project_id") if existing is not None else None
    if entity_type == "project":
        project_id = entity_id
    policy = services.store.upsert_entity_policy(
        entity_type=entity_type,
        entity_id=entity_id,
        project_id=project_id,
        autonomy_mode=payload.autonomy_mode,
        kill_switch=payload.kill_switch,
        approval_bias=payload.approval_bias,
    )
    services.store.record_event(
        event_type="policy.entity.updated",
        source="ui",
        payload={"entity_type": entity_type, "entity_id": entity_id, "policy": policy},
    )
    return EntityPolicyRecord(**policy)
