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
    autonomy_mode: str
    kill_switch: bool
    approval_bias: str
    mode_label: str
    status: str
    active_project: str
    phase: str


class TaskRecord(BaseModel):
    id: str
    project_id: str | None = None
    title: str
    summary: str
    status: str
    priority: str


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    summary: str = Field(default="")
    status: str = Field(default="Inbox")
    priority: str = Field(default="Medium")
    project_id: str | None = None


class TaskUpdateRequest(BaseModel):
    title: str = Field(min_length=1)
    summary: str = Field(default="")
    status: str = Field(default="Inbox")
    priority: str = Field(default="Medium")
    project_id: str | None = None


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


class AgentCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    role: str = Field(default="")
    status: str = Field(default="Idle")


class AgentUpdateRequest(BaseModel):
    name: str = Field(min_length=1)
    role: str = Field(default="")
    status: str = Field(default="Idle")


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


class ProjectListItem(BaseModel):
    id: str
    name: str
    summary: str
    status: str
    owner: str
    created_at: str
    updated_at: str


class SkillListItem(BaseModel):
    id: str
    project_id: str | None = None
    name: str
    description: str
    scope: str
    version: str
    source_type: str
    status: str
    created_at: str
    updated_at: str


class ScheduleListItem(BaseModel):
    id: str
    project_id: str | None = None
    name: str
    target_type: str
    target_ref: str
    schedule_expression: str
    timezone: str
    enabled: bool
    last_run_at: str | None = None
    next_run_at: str | None = None
    created_at: str
    updated_at: str


class ProjectRecord(BaseModel):
    id: str
    name: str
    summary: str
    status: str
    owner: str
    created_at: str
    updated_at: str


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    summary: str = Field(default="")
    status: str = Field(default="Planned")
    owner: str = Field(default="Gnosys")


class ProjectUpdateRequest(BaseModel):
    name: str = Field(min_length=1)
    summary: str = Field(default="")
    status: str = Field(default="Planned")
    owner: str = Field(default="Gnosys")


class SkillRecord(BaseModel):
    id: str
    project_id: str | None = None
    name: str
    description: str
    scope: str
    version: str
    source_type: str
    status: str
    created_at: str
    updated_at: str


class SkillCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str = Field(default="")
    scope: str = Field(default="workspace")
    version: str = Field(default="0.1.0")
    source_type: str = Field(default="authored")
    status: str = Field(default="draft")
    project_id: str | None = None


class SkillUpdateRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str = Field(default="")
    scope: str = Field(default="workspace")
    version: str = Field(default="0.1.0")
    source_type: str = Field(default="authored")
    status: str = Field(default="draft")
    project_id: str | None = None


class ScheduleRecord(BaseModel):
    id: str
    project_id: str | None = None
    name: str
    target_type: str
    target_ref: str
    schedule_expression: str
    timezone: str
    enabled: bool
    last_run_at: str | None = None
    next_run_at: str | None = None
    created_at: str
    updated_at: str


class PolicyRecord(BaseModel):
    autonomy_mode: str
    kill_switch: bool
    approval_bias: str
    mode_label: str


class EntityPolicyRecord(BaseModel):
    entity_type: str
    entity_id: str
    autonomy_mode: str
    kill_switch: bool
    approval_bias: str
    created_at: str
    updated_at: str


class EntityPolicyUpdateRequest(BaseModel):
    autonomy_mode: str | None = None
    kill_switch: bool | None = None
    approval_bias: str | None = None


class PolicyUpdateRequest(BaseModel):
    autonomy_mode: str | None = None
    kill_switch: bool | None = None
    approval_bias: str | None = None


class PolicyDecisionRecord(BaseModel):
    allowed: bool
    requires_approval: bool
    sensitivity: str
    reason: str
    mode: str
    action: str
    policy_scope: str
    policy_entity_type: str | None = None
    policy_entity_id: str | None = None


class ApprovalRequestRecord(BaseModel):
    id: str
    action: str
    subject_type: str
    subject_ref: str
    sensitivity: str
    status: str
    reason: str
    payload: dict[str, Any]
    requested_by: str
    created_at: str
    updated_at: str
    resolved_at: str | None = None
    resolved_by: str | None = None


class ApprovalResolveRequest(BaseModel):
    status: str = Field(default="approved")
    resolved_by: str = Field(default="user")


class ScheduleCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    target_type: str = Field(min_length=1)
    target_ref: str = Field(min_length=1)
    schedule_expression: str = Field(min_length=1)
    timezone: str = Field(default="America/New_York")
    enabled: bool = Field(default=True)
    project_id: str | None = None
    last_run_at: str | None = None
    next_run_at: str | None = None


class ScheduleUpdateRequest(BaseModel):
    name: str = Field(min_length=1)
    target_type: str = Field(min_length=1)
    target_ref: str = Field(min_length=1)
    schedule_expression: str = Field(min_length=1)
    timezone: str = Field(default="America/New_York")
    enabled: bool = Field(default=True)
    project_id: str | None = None
    last_run_at: str | None = None
    next_run_at: str | None = None


class MemoryItemRecord(BaseModel):
    id: str
    layer: str
    scope: str
    project_id: str | None = None
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
    project_id: str | None = None
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


class ScheduleRunRecord(BaseModel):
    id: str
    schedule_id: str
    schedule_name: str
    target_type: str
    target_ref: str
    status: str
    attempt_number: int
    retry_of_run_id: str | None = None
    task_run_id: str | None = None
    requested_by: str
    result_summary: str
    last_error: str | None = None
    created_at: str
    updated_at: str
    completed_at: str | None = None


class ScheduleRunListResponse(BaseModel):
    schedule_runs: list[ScheduleRunRecord]


class ReplayResponse(BaseModel):
    task_run: TaskRunRecord
    agent_runs: list[AgentRunRecord]
    events: list[EventRecord]
    schedule_runs: list[ScheduleRunRecord]


class WorkspaceSnapshotResponse(BaseModel):
    workspace: WorkspaceSummary
    tasks: list[TaskRecord]
    agents: list[AgentRecord]
    projects: list[ProjectListItem]
    skills: list[SkillListItem]
    schedules: list[ScheduleListItem]
    memory_layers: list[MemoryLayerRecord]
    memory_items: list[MemoryItemRecord]
    task_runs: list[TaskRunRecord]
    agent_runs: list[AgentRunRecord]
    approval_requests: list[ApprovalRequestRecord]
    schedule_runs: list[ScheduleRunRecord]
    entity_policies: list[EntityPolicyRecord]
    recent_events: list[EventRecord]
    counts: dict[str, int]
