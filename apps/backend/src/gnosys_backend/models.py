from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ApprovalPolicyValue = Literal["inherit", "require_approval", "autonomous"]
FailurePolicyValue = Literal["retry_once", "fail_fast", "retry_twice"]


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
    project_id: str | None = None
    project_thread_id: str | None = None
    chat_session_id: str | None = None
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
    workspace_path: str
    created_at: str
    updated_at: str


class SkillListItem(BaseModel):
    id: str
    project_id: str | None = None
    parent_skill_id: str | None = None
    promoted_from_skill_id: str | None = None
    latest_test_run_id: str | None = None
    name: str
    description: str
    scope: str
    version: str
    source_type: str
    status: str
    test_status: str = "untested"
    test_score: float = 0.0
    test_summary: str = ""
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
    approval_policy: ApprovalPolicyValue
    failure_policy: FailurePolicyValue
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
    workspace_path: str
    created_at: str
    updated_at: str


class ProjectThreadRecord(BaseModel):
    id: str
    project_id: str
    title: str
    summary: str
    status: str
    context_path: str
    created_at: str
    updated_at: str


class ProjectThreadCreateRequest(BaseModel):
    project_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(default="")
    status: str = Field(default="Open")


class ProjectThreadUpdateRequest(BaseModel):
    title: str = Field(min_length=1)
    summary: str = Field(default="")
    status: str = Field(default="Open")


class ChatSessionRecord(BaseModel):
    id: str
    title: str
    summary: str
    status: str
    context_path: str
    agent_path: str
    soul_path: str
    identity_path: str
    heartbeat_path: str
    created_at: str
    updated_at: str


class ChatSessionCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    summary: str = Field(default="")
    status: str = Field(default="Active")


class ChatSessionUpdateRequest(BaseModel):
    title: str = Field(min_length=1)
    summary: str = Field(default="")
    status: str = Field(default="Active")


class ChatMessageRecord(BaseModel):
    id: str
    chat_session_id: str
    role: Literal["user", "assistant", "system", "tool"]
    kind: Literal["message", "event", "reflection"]
    content: str
    task_run_id: str | None = None
    agent_run_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class ChatMessageCreateRequest(BaseModel):
    role: Literal["user", "assistant", "system", "tool"] = Field(default="user")
    kind: Literal["message", "event", "reflection"] = Field(default="message")
    content: str = Field(min_length=1)
    task_run_id: str | None = None
    agent_run_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


ChatContextMode = Literal["personal", "project", "project-thread"]


class ChatAttachmentRecord(BaseModel):
    id: str
    chat_session_id: str
    mode: ChatContextMode
    project_id: str | None = None
    project_thread_id: str | None = None
    original_name: str
    stored_name: str
    content_type: str
    size_bytes: int
    storage_path: str
    created_at: str


class ChatSessionSendRequest(BaseModel):
    content: str = Field(min_length=1)
    requested_by: str = Field(default="desktop")
    selected_model: str | None = None
    reasoning_strength: str | None = None
    mode: ChatContextMode = Field(default="personal")
    project_id: str | None = None
    project_thread_id: str | None = None
    attachment_ids: list[str] = Field(default_factory=list)


class OrchestrationStepRecord(BaseModel):
    intent: str
    objective: str
    assigned_agent: str
    approval_note: str
    rationale: str = ""
    spawn_worker: bool = False


class OrchestrationDecisionRecord(BaseModel):
    intent_classification: str
    execution_mode: Literal["answer-only", "task-created"]
    delegated_specialists: list[str] = Field(default_factory=list)
    invoked_skills: list[str] = Field(default_factory=list)
    approvals_triggered: bool = False
    synthesis: str


class ChatSessionSendResponse(BaseModel):
    user_message: ChatMessageRecord
    assistant_message: ChatMessageRecord
    generated_messages: list[ChatMessageRecord] = Field(default_factory=list)
    task_run: TaskRunRecord | None = None
    agent_runs: list[AgentRunRecord] = Field(default_factory=list)
    approval_request: ApprovalRequestRecord | None = None
    decision: OrchestrationDecisionRecord


class SessionReflectionRecord(BaseModel):
    id: str
    chat_session_id: str
    summary: str
    user_preferences: list[str] = Field(default_factory=list)
    working_style: list[str] = Field(default_factory=list)
    recurring_goals: list[str] = Field(default_factory=list)
    personal_context: list[str] = Field(default_factory=list)
    identity_refinements: list[str] = Field(default_factory=list)
    source_message_ids: list[str] = Field(default_factory=list)
    created_at: str


class IdentityProposalRecord(BaseModel):
    id: str
    chat_session_id: str
    target_file: str
    proposal_kind: str
    rationale: str
    proposed_content: str
    status: str
    created_at: str
    updated_at: str


class SessionReflectionResponse(BaseModel):
    reflection: SessionReflectionRecord
    memory_items: list[MemoryItemRecord] = Field(default_factory=list)
    identity_proposals: list[IdentityProposalRecord] = Field(default_factory=list)


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
    parent_skill_id: str | None = None
    promoted_from_skill_id: str | None = None
    latest_test_run_id: str | None = None
    name: str
    description: str
    scope: str
    version: str
    source_type: str
    status: str
    test_status: str = "untested"
    test_score: float = 0.0
    test_summary: str = ""
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
    parent_skill_id: str | None = None
    promoted_from_skill_id: str | None = None
    latest_test_run_id: str | None = None
    test_status: str | None = None
    test_score: float | None = None
    test_summary: str | None = None


class ScheduleRecord(BaseModel):
    id: str
    project_id: str | None = None
    name: str
    target_type: str
    target_ref: str
    schedule_expression: str
    timezone: str
    enabled: bool
    approval_policy: ApprovalPolicyValue
    failure_policy: FailurePolicyValue
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
    project_id: str | None = None
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
    approval_policy: ApprovalPolicyValue = Field(default="inherit")
    failure_policy: FailurePolicyValue = Field(default="retry_once")
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
    approval_policy: ApprovalPolicyValue = Field(default="inherit")
    failure_policy: FailurePolicyValue = Field(default="retry_once")
    project_id: str | None = None
    last_run_at: str | None = None
    next_run_at: str | None = None


class MemoryItemRecord(BaseModel):
    id: str
    layer: str
    scope: str
    project_id: str | None = None
    state: str
    pinned: bool = False
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
    recommended_action: str | None = None
    review_reason: str | None = None
    signature: str | None = None
    conflict_count: int | None = None


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
    contradictions: int = 0


class MemoryContradictionRecord(BaseModel):
    signature: str
    item_count: int
    item_ids: list[str]
    item_titles: list[str]
    item_states: list[str]
    pinned_item_id: str | None = None
    winner_item_id: str | None = None
    recommended_resolution: str
    reason: str


class MemoryReviewResponse(BaseModel):
    candidate_count: int
    pinned_count: int
    contradiction_count: int
    items: list[MemoryItemRecord]
    contradictions: list[MemoryContradictionRecord]


class MemoryBrowseResponse(BaseModel):
    query: str | None = None
    project_id: str | None = None
    total_count: int
    daily_memories: list[MemoryItemRecord]
    long_term_memories: list[MemoryItemRecord]
    pinned_memories: list[MemoryItemRecord]
    candidate_memories: list[MemoryItemRecord]
    contradictions: list[MemoryContradictionRecord]


class SkillTestRunRecord(BaseModel):
    id: str
    skill_id: str
    scenario: str
    expected_outcome: str
    observed_outcome: str
    passed: bool
    score: float
    summary: str
    requested_by: str
    created_at: str


class SkillLifecycleRecord(BaseModel):
    skill: SkillRecord
    parent_skill: SkillRecord | None = None
    related_skills: list[SkillRecord]
    test_runs: list[SkillTestRunRecord]
    lifecycle_state: str
    ready_for_promotion: bool


class SkillTestRequest(BaseModel):
    scenario: str = Field(min_length=1)
    expected_outcome: str = Field(min_length=1)
    requested_by: str = Field(default="ui")


class OrchestrationLaunchRequest(BaseModel):
    objective: str = Field(min_length=1)
    task_title: str | None = None
    task_summary: str | None = None
    task_id: str | None = None
    project_id: str | None = None
    project_thread_id: str | None = None
    chat_session_id: str | None = None
    requested_by: str = Field(default="user")
    mode: str = Field(default="Supervised")
    priority: str = Field(default="High")


class OrchestrationLaunchResponse(BaseModel):
    task: TaskRecord
    task_run: TaskRunRecord
    agent_runs: list[AgentRunRecord]
    steps: list[OrchestrationStepRecord]
    approvals_required: list[str]
    summary: str
    decision: OrchestrationDecisionRecord


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
    timeline: list[ReplayTimelineRecord]
    comparison: ReplayComparisonRecord | None = None
    schedule_runs: list[ScheduleRunRecord]


class ReplayTimelineRecord(BaseModel):
    kind: str
    label: str
    detail: str
    created_at: str
    source_id: str | None = None


class ReplayComparisonRecord(BaseModel):
    previous_task_run_id: str | None = None
    status_changed: bool
    summary_changed: bool
    step_count_delta: int
    approval_required_changed: bool
    task_summary_changed: bool = False
    agent_run_count_delta: int = 0
    schedule_run_count_delta: int = 0
    timeline_entry_count_delta: int = 0


class DiagnosticsMetricsRecord(BaseModel):
    total_task_runs: int
    filtered_task_runs: int
    total_agent_runs: int
    total_schedule_runs: int
    completed_task_runs: int
    failed_task_runs: int
    approval_required_task_runs: int


class DiagnosticsRunListResponse(BaseModel):
    task_runs: list[TaskRunRecord]
    query: str | None = None
    status: str | None = None
    approval_required: bool | None = None
    total_count: int
    filtered_count: int
    metrics: DiagnosticsMetricsRecord


class WorkspaceSnapshotResponse(BaseModel):
    workspace: WorkspaceSummary
    tasks: list[TaskRecord]
    agents: list[AgentRecord]
    projects: list[ProjectListItem]
    project_threads: list[ProjectThreadRecord]
    chat_sessions: list[ChatSessionRecord]
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
