from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    service: str = "gnosys-backend"
    status: str = "healthy"


class StatusResponse(BaseModel):
    service: str = "gnosys-backend"
    version: str = "0.1.0"
    mode: str = "scaffold"
    workspace: str = "Gnosys"
    note: str = Field(default="Foundational scaffold only")


class WorkspaceSummary(BaseModel):
    name: str
    mode: str
    status: str
    active_project: str
    phase: str


class TaskRecord(BaseModel):
    id: str
    title: str
    summary: str
    status: str
    priority: str


class AgentRecord(BaseModel):
    id: str
    name: str
    role: str
    status: str


class MemoryLayerRecord(BaseModel):
    id: str
    name: str
    description: str
    score: float


class EventRecord(BaseModel):
    id: int
    type: str
    source: str
    payload: dict[str, Any]
    created_at: str


class EventCreateRequest(BaseModel):
    type: str = Field(min_length=3)
    source: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class WorkspaceSnapshotResponse(BaseModel):
    workspace: WorkspaceSummary
    tasks: list[TaskRecord]
    agents: list[AgentRecord]
    memory_layers: list[MemoryLayerRecord]
    recent_events: list[EventRecord]
    counts: dict[str, int]
