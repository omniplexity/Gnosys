from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


MemoryTier = Literal["working", "episodic", "semantic", "archive"]

ContextTier = MemoryTier


class MemoryCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1)
    memory_type: str = Field(default="conversational", min_length=1)
    tier: MemoryTier = "episodic"
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    expires_at: datetime | None = None


class MemoryRecord(BaseModel):
    id: str
    content: str
    memory_type: str
    tier: MemoryTier
    tags: list[str]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    last_accessed_at: datetime | None = None
    expires_at: datetime | None = None


class MemorySearchResult(BaseModel):
    memory: MemoryRecord
    score: int
    matched_keywords: list[str]


class SearchResponse(BaseModel):
    query: str
    count: int
    results: list[MemorySearchResult]


class MemoryCreateResponse(BaseModel):
    memory: MemoryRecord


class StatsResponse(BaseModel):
    total_memories: int
    counts_by_type: dict[str, int]
    counts_by_tier: dict[str, int]
    newest_memory_at: datetime | None = None
    oldest_memory_at: datetime | None = None
    database_path: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    database: str


class SemanticSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    limit: int = Field(default=10, ge=1, le=100)
    memory_type: str | None = None
    tier: MemoryTier | None = None
    semantic_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    include_entities: bool = Field(default=False)


class SemanticSearchResult(BaseModel):
    memory: MemoryRecord
    score: float
    semantic_score: float | None = None
    keyword_score: float | None = None
    matched_keywords: list[str] = []


class SemanticSearchResponse(BaseModel):
    query: str
    count: int
    results: list[SemanticSearchResult]
    used_semantic_search: bool
    truncated: bool = False


# Trajectory Models


class TrajectoryStep(BaseModel):
    step: int
    tool: str
    params: dict[str, Any] = {}
    result: str | None = None
    success: bool = True
    duration_ms: int = 0


class TrajectoryMetrics(BaseModel):
    total_steps: int = 0
    total_duration_ms: int = 0
    tool_calls: int = 0
    errors: int = 0


class TrajectoryCreateRequest(BaseModel):
    task: str
    agent_type: str = "primary"
    query: str | None = None
    response_preview: str | None = None


class TrajectoryCreateResponse(BaseModel):
    trajectory: TrajectoryRecord


class TrajectoryUpdateRequest(BaseModel):
    completed_at: datetime | None = None
    success: bool
    steps: list[TrajectoryStep] = []
    metrics: TrajectoryMetrics | None = None
    error: str | None = None


class TrajectoryUpdateResponse(BaseModel):
    trajectory: TrajectoryRecord


class TrajectoryRecord(BaseModel):
    id: str
    task: str
    started_at: datetime
    completed_at: datetime | None = None
    success: bool | None = None
    agent_type: str
    steps: list[TrajectoryStep] = []
    metrics: TrajectoryMetrics | None = None
    error: str | None = None
    query: str | None = None
    response_preview: str | None = None


class TrajectoryListResponse(BaseModel):
    count: int
    trajectories: list[TrajectoryRecord]


# Learning Models


class LearningStatsResponse(BaseModel):
    total_trajectories: int
    success_rate: float
    avg_duration_ms: float
    tool_usage: dict[str, int]
    agent_stats: dict[str, Any]


class PatternDetectRequest(BaseModel):
    trajectory_limit: int = 100


class PatternRecord(BaseModel):
    id: str
    pattern_type: str
    description: str
    frequency: int
    success_rate: float
    tools: list[str]
    metadata: dict[str, Any]


class PatternDetectResponse(BaseModel):
    patterns: list[PatternRecord]
    total_analyzed: int
    generated_at: datetime


class DatasetGenerateRequest(BaseModel):
    dataset_type: Literal[
        "task_response", "tool_workflow", "context_relevance", "agent_decision"
    ]
    min_success_rate: float = 0.8


class DatasetGenerateResponse(BaseModel):
    dataset_type: str
    records: list[dict[str, Any]]
    total_records: int
    generated_at: datetime


# Pipeline Models


class AgentProfile(BaseModel):
    id: str | None = None
    role: str
    type: str
    weight: float = 1.0
    context: dict[str, Any] = {}


class PipelineProfile(BaseModel):
    id: str
    name: str
    agents: list[AgentProfile]
    coordination: str


class AgentSpawnRequest(BaseModel):
    agent_id: str | None = None
    role: str
    agent_type: str | None = None
    context: dict[str, Any] | None = None
    tools: list[str] | None = None
    parent_id: str | None = None


class AgentSpawnResponse(BaseModel):
    agent_id: str
    role: str
    agent_type: str
    status: str
    created_at: datetime


class PipelineExecuteRequest(BaseModel):
    profile_name: str
    task: str
    coordinator_id: str | None = None


class PipelineExecuteResponse(BaseModel):
    pipeline_id: str
    profile_name: str
    agents_spawned: int
    results: list[dict[str, Any]]
    executed_at: datetime


class TaskDelegateRequest(BaseModel):
    agent_id: str | None = None
    role: str
    agent_type: str | None = None
    context: dict[str, Any]
    tools: list[str] | None = None
    parent_id: str | None = None


class TaskDelegateResponse(BaseModel):
    agent_id: str
    status: str
    delegated_at: datetime


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# Context Retrieval Models


class ContextRetrieveRequest(BaseModel):
    query: str
    max_tokens: int = 4000
    include_tiers: list[ContextTier] = ["working", "episodic", "semantic", "archive"]


class ContextItem(BaseModel):
    rank: int
    memory: MemoryRecord
    score: float
    blended_score: float | None = None
    matched_keywords: list[str] = []
    estimated_tokens: int


class ContextRetrieveResponse(BaseModel):
    query: str
    items: list[ContextItem]
    tiers_included: list[ContextTier]
    token_budget: int
    used_tokens: int
    remaining_tokens: int
    truncated: bool
    dropped_count: int
    assembly_text: str


# Skill Models


class SkillCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    triggers: list[str] = Field(default_factory=list)
    workflow: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    description: str | None = None
    compounds_from: list[str] = Field(default_factory=list)


class SkillRecord(BaseModel):
    id: str
    name: str
    version: str
    triggers: list[str]
    workflow: list[str]
    tools: list[str]
    parameters: dict[str, Any]
    description: str | None = None
    compounds_from: list[str]
    use_count: int = 0
    success_rate: float = 0.0
    trigger_count: int = 0
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None = None


class SkillListResponse(BaseModel):
    count: int
    skills: list[SkillRecord]


class SkillMatchRequest(BaseModel):
    task: str
    context: dict[str, Any] | None = None


class SkillMatchResponse(BaseModel):
    matched: bool
    skill: SkillRecord | None = None
    confidence: float = 0.0


class SkillRefineRequest(BaseModel):
    feedback: str
    success: bool
    improvements: list[str] = Field(default_factory=list)


class SkillRefineResponse(BaseModel):
    skill: SkillRecord
    previous_version: str
    new_version: str


# Scheduler Models


class ScheduledTaskCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    schedule: str = Field(min_length=1)  # cron expression or interval
    task_type: Literal["query", "action", "report", "check"] = "query"
    enabled: bool = True
    description: str | None = None
    action: dict[str, Any] = Field(default_factory=dict)
    delivery: dict[str, Any] = Field(default_factory=dict)


class ScheduledTaskRecord(BaseModel):
    id: str
    name: str
    schedule: str
    task_type: str
    enabled: bool
    description: str | None
    action: dict[str, Any]
    delivery: dict[str, Any]
    created_at: datetime
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    run_count: int = 0


class ScheduledTaskListResponse(BaseModel):
    count: int
    tasks: list[ScheduledTaskRecord]


class ScheduledTaskRunResponse(BaseModel):
    task_id: str
    executed: bool
    result: dict[str, Any] | None = None
    executed_at: datetime


class ScheduledTaskHistoryResponse(BaseModel):
    count: int
    executions: list[dict[str, Any]]


# Monitoring Models


class MetricsResponse(BaseModel):
    memory_stats: dict[str, Any]
    pipeline_stats: dict[str, Any]
    learning_stats: dict[str, Any]
    skills_stats: dict[str, Any]
    scheduler_stats: dict[str, Any]
    uptime_seconds: float
    timestamp: datetime


class HealthDetailResponse(BaseModel):
    status: str
    service: str
    version: str
    components: dict[str, str]
    metrics: dict[str, Any] | None = None
