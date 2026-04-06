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


class MemoryItemRecord(BaseModel):
    id: str
    layer: str
    scope: str
    state: str
    title: str
    summary: str
    content: str
    provenance: str
    source_ref: str
    confidence: float
    freshness: float
    tags: list[str]
    created_at: str
    updated_at: str
    last_accessed_at: str | None = None
    score: float | None = None
    reason: str | None = None


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


class MemorySearchRequest(BaseModel):
    query: str = Field(min_length=1)
    role: str = Field(default="orchestrator")
    scope: str | None = None
    limit: int = Field(default=5, ge=1, le=20)


class MemoryIngestRequest(BaseModel):
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    content: str = Field(min_length=1)
    provenance: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    layer: str = Field(default="Semantic")
    scope: str = Field(default="workspace")
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    freshness: float = Field(default=0.7, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    state: str = Field(default="candidate")


class MemoryRetrievalTraceStep(BaseModel):
    stage: str
    detail: str


class MemoryRetrievalResponse(BaseModel):
    query: str
    scope: str | None
    role: str
    items: list[MemoryItemRecord]
    trace: list[MemoryRetrievalTraceStep]


class MemoryConsolidationResponse(BaseModel):
    reviewed: int
    promoted: int
    archived: int


class WorkspaceSnapshotResponse(BaseModel):
    workspace: WorkspaceSummary
    tasks: list[TaskRecord]
    agents: list[AgentRecord]
    memory_layers: list[MemoryLayerRecord]
    memory_items: list[MemoryItemRecord]
    recent_events: list[EventRecord]
    counts: dict[str, int]
