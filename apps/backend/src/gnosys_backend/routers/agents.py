from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..deps import AppServices, get_services
from ..models import AgentCreateRequest, AgentRecord, AgentUpdateRequest


router = APIRouter()


@router.get("/api/agents", response_model=list[AgentRecord])
def agents(services: AppServices = Depends(get_services)) -> list[AgentRecord]:
    return [AgentRecord(**agent) for agent in services.store.list_agents()]


@router.post("/api/agents", response_model=AgentRecord, status_code=201)
def create_agent(payload: AgentCreateRequest, services: AppServices = Depends(get_services)) -> AgentRecord:
    services.gate_mutation(action="agent.create", subject_type="agent", subject_ref=payload.name, payload=payload.model_dump())
    agent = services.store.create_agent(name=payload.name, role=payload.role, status=payload.status)
    services.store.record_event(event_type="agent.created", source="ui", payload={"agent_id": agent["id"], "name": agent["name"]})
    return AgentRecord(**agent)


@router.get("/api/agents/{agent_id}", response_model=AgentRecord)
def get_agent(agent_id: str, services: AppServices = Depends(get_services)) -> AgentRecord:
    agent = services.store.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentRecord(**agent)


@router.patch("/api/agents/{agent_id}", response_model=AgentRecord)
def update_agent(agent_id: str, payload: AgentUpdateRequest, services: AppServices = Depends(get_services)) -> AgentRecord:
    services.gate_mutation(action="agent.update", subject_type="agent", subject_ref=agent_id, payload=payload.model_dump())
    agent = services.store.update_agent(agent_id, name=payload.name, role=payload.role, status=payload.status)
    services.store.record_event(event_type="agent.updated", source="ui", payload={"agent_id": agent_id, "status": agent["status"]})
    return AgentRecord(**agent)


@router.delete("/api/agents/{agent_id}", status_code=204)
def delete_agent(agent_id: str, services: AppServices = Depends(get_services)) -> None:
    services.gate_mutation(action="agent.delete", subject_type="agent", subject_ref=agent_id, payload={"agent_id": agent_id})
    services.store.delete_agent(agent_id)
    services.store.record_event(event_type="agent.deleted", source="ui", payload={"agent_id": agent_id})
