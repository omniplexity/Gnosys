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


class TaskRunRecord(BaseModel):
    id: str
    task_id: str
    objective: str
    requested_by: str
    mode: str
    status: str
    summary: str
    step_count: int
    approval_required: bool
    created_at: str
    updated_at: str
    completed_at: str | None = None


class AgentRecord(BaseModel):
    id: str
    name: str
    role: str
    status: str


class AgentRunRecord(BaseModel):
    id: str
    agent_id: str
    agent_name: str
    agent_role: str
    run_kind: str
    status: str
    objective: str
    summary: str
    parent_run_id: str | None = None
    task_run_id: str
    recursion_depth: int
    child_count: int
    budget_units: int
    approval_required: bool
    created_at: str
    updated_at: str
    completed_at: str | None = None


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


class OrchestrationLaunchRequest(BaseModel):
    objective: str = Field(min_length=1)
    task_title: str | None = None
    task_summary: str | None = None
    requested_by: str = Field(default="user")
    mode: str = Field(default="Supervised")
    priority: str = Field(default="High")


class OrchestrationLaunchResponse(BaseModel):
    task: TaskRecord
    task_run: TaskRunRecord
    agent_runs: list[AgentRunRecord]
    steps: list[dict[str, str]]
    approvals_required: list[str]
    summary: str


class OrchestrationRunResponse(BaseModel):
    task: TaskRecord
    task_run: TaskRunRecord
    agent_runs: list[AgentRunRecord]


class OrchestrationRunListResponse(BaseModel):
    task_runs: list[TaskRunRecord]


class WorkspaceSnapshotResponse(BaseModel):
    workspace: WorkspaceSummary
    tasks: list[TaskRecord]
    agents: list[AgentRecord]
    memory_layers: list[MemoryLayerRecord]
    memory_items: list[MemoryItemRecord]
    task_runs: list[TaskRunRecord]
    agent_runs: list[AgentRunRecord]
    recent_events: list[EventRecord]
    counts: dict[str, int]
