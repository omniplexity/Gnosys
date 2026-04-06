from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import (
    AgentRecord,
    AgentCreateRequest,
    AgentUpdateRequest,
    AgentRunRecord,
    EventCreateRequest,
    EventRecord,
    HealthResponse,
    MemoryConsolidationResponse,
    MemoryIngestRequest,
    MemoryItemRecord,
    MemoryLayerRecord,
    MemoryRetrievalResponse,
    OrchestrationLaunchRequest,
    OrchestrationLaunchResponse,
    OrchestrationRunListResponse,
    OrchestrationRunResponse,
    ProjectCreateRequest,
    ProjectRecord,
    ProjectUpdateRequest,
    ScheduleCreateRequest,
    ScheduleRecord,
    ScheduleUpdateRequest,
    SkillCreateRequest,
    SkillRecord,
    SkillUpdateRequest,
    StatusResponse,
    TaskCreateRequest,
    TaskRecord,
    TaskRunRecord,
    TaskUpdateRequest,
    WorkspaceSnapshotResponse,
    WorkspaceSummary,
)
from .memory import MemoryEngine
from .runtime import OrchestrationEngine
from .store import GnosysStore


def _default_db_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "gnosys.sqlite3"


def _build_store() -> GnosysStore:
    raw_path = os.environ.get("GNOSYS_DB_PATH")
    path = Path(raw_path) if raw_path else _default_db_path()
    store = GnosysStore(path=path)
    store.initialize()
    return store


def create_app(store: GnosysStore | None = None) -> FastAPI:
    app = FastAPI(title="Gnosys Backend", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    active_store = store or _build_store()
    active_store.initialize()
    memory_engine = MemoryEngine(active_store)
    orchestration_engine = OrchestrationEngine(active_store)

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    @app.get("/status", response_model=StatusResponse)
    def status() -> StatusResponse:
        return StatusResponse(
            mode="operational",
            note="Local persistence and event log are active",
        )

    @app.get("/workspace", response_model=WorkspaceSummary)
    @app.get("/api/workspace", response_model=WorkspaceSummary)
    def workspace() -> WorkspaceSummary:
        return WorkspaceSummary(**active_store.workspace_snapshot()["workspace"])

    @app.get("/api/state", response_model=WorkspaceSnapshotResponse)
    def state() -> WorkspaceSnapshotResponse:
        return WorkspaceSnapshotResponse(**active_store.workspace_snapshot())

    @app.get("/api/tasks", response_model=list[TaskRecord])
    def tasks() -> list[TaskRecord]:
        return [TaskRecord(**task) for task in active_store.list_tasks()]

    @app.post("/api/tasks", response_model=TaskRecord, status_code=201)
    def create_task(payload: TaskCreateRequest) -> TaskRecord:
        task = active_store.create_task(
            title=payload.title,
            summary=payload.summary,
            status=payload.status,
            priority=payload.priority,
        )
        active_store.record_event(
            event_type="task.created",
            source="ui",
            payload={"task_id": task["id"], "title": task["title"]},
        )
        return TaskRecord(**task)

    @app.get("/api/tasks/{task_id}", response_model=TaskRecord)
    def get_task(task_id: str) -> TaskRecord:
        task = active_store.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return TaskRecord(**task)

    @app.patch("/api/tasks/{task_id}", response_model=TaskRecord)
    def update_task(task_id: str, payload: TaskUpdateRequest) -> TaskRecord:
        task = active_store.update_task(
            task_id,
            title=payload.title,
            summary=payload.summary,
            status=payload.status,
            priority=payload.priority,
        )
        active_store.record_event(
            event_type="task.updated",
            source="ui",
            payload={"task_id": task_id, "status": task["status"]},
        )
        return TaskRecord(**task)

    @app.delete("/api/tasks/{task_id}", status_code=204)
    def delete_task(task_id: str) -> None:
        active_store.delete_task(task_id)
        active_store.record_event(
            event_type="task.deleted",
            source="ui",
            payload={"task_id": task_id},
        )

    @app.get("/api/agents", response_model=list[AgentRecord])
    def agents() -> list[AgentRecord]:
        return [AgentRecord(**agent) for agent in active_store.list_agents()]

    @app.post("/api/agents", response_model=AgentRecord, status_code=201)
    def create_agent(payload: AgentCreateRequest) -> AgentRecord:
        agent = active_store.create_agent(name=payload.name, role=payload.role, status=payload.status)
        active_store.record_event(
            event_type="agent.created",
            source="ui",
            payload={"agent_id": agent["id"], "name": agent["name"]},
        )
        return AgentRecord(**agent)

    @app.get("/api/agents/{agent_id}", response_model=AgentRecord)
    def get_agent(agent_id: str) -> AgentRecord:
        agent = active_store.get_agent(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        return AgentRecord(**agent)

    @app.patch("/api/agents/{agent_id}", response_model=AgentRecord)
    def update_agent(agent_id: str, payload: AgentUpdateRequest) -> AgentRecord:
        agent = active_store.update_agent(agent_id, name=payload.name, role=payload.role, status=payload.status)
        active_store.record_event(
            event_type="agent.updated",
            source="ui",
            payload={"agent_id": agent_id, "status": agent["status"]},
        )
        return AgentRecord(**agent)

    @app.delete("/api/agents/{agent_id}", status_code=204)
    def delete_agent(agent_id: str) -> None:
        active_store.delete_agent(agent_id)
        active_store.record_event(
            event_type="agent.deleted",
            source="ui",
            payload={"agent_id": agent_id},
        )

    @app.get("/api/projects", response_model=list[ProjectRecord])
    def projects() -> list[ProjectRecord]:
        return [ProjectRecord(**project) for project in active_store.list_projects()]

    @app.post("/api/projects", response_model=ProjectRecord, status_code=201)
    def create_project(payload: ProjectCreateRequest) -> ProjectRecord:
        project = active_store.create_project(name=payload.name, summary=payload.summary, status=payload.status, owner=payload.owner)
        active_store.record_event(
            event_type="project.created",
            source="ui",
            payload={"project_id": project["id"], "name": project["name"]},
        )
        return ProjectRecord(**project)

    @app.get("/api/projects/{project_id}", response_model=ProjectRecord)
    def get_project(project_id: str) -> ProjectRecord:
        project = active_store.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return ProjectRecord(**project)

    @app.patch("/api/projects/{project_id}", response_model=ProjectRecord)
    def update_project(project_id: str, payload: ProjectUpdateRequest) -> ProjectRecord:
        project = active_store.update_project(
            project_id,
            name=payload.name,
            summary=payload.summary,
            status=payload.status,
            owner=payload.owner,
        )
        active_store.record_event(
            event_type="project.updated",
            source="ui",
            payload={"project_id": project_id, "status": project["status"]},
        )
        return ProjectRecord(**project)

    @app.delete("/api/projects/{project_id}", status_code=204)
    def delete_project(project_id: str) -> None:
        active_store.delete_project(project_id)
        active_store.record_event(
            event_type="project.deleted",
            source="ui",
            payload={"project_id": project_id},
        )

    @app.get("/api/skills", response_model=list[SkillRecord])
    def skills() -> list[SkillRecord]:
        return [SkillRecord(**skill) for skill in active_store.list_skills()]

    @app.post("/api/skills", response_model=SkillRecord, status_code=201)
    def create_skill(payload: SkillCreateRequest) -> SkillRecord:
        skill = active_store.create_skill(
            name=payload.name,
            description=payload.description,
            scope=payload.scope,
            version=payload.version,
            source_type=payload.source_type,
            status=payload.status,
        )
        active_store.record_event(
            event_type="skill.created",
            source="ui",
            payload={"skill_id": skill["id"], "name": skill["name"]},
        )
        return SkillRecord(**skill)

    @app.get("/api/skills/{skill_id}", response_model=SkillRecord)
    def get_skill(skill_id: str) -> SkillRecord:
        skill = active_store.get_skill(skill_id)
        if skill is None:
            raise HTTPException(status_code=404, detail="Skill not found")
        return SkillRecord(**skill)

    @app.patch("/api/skills/{skill_id}", response_model=SkillRecord)
    def update_skill(skill_id: str, payload: SkillUpdateRequest) -> SkillRecord:
        skill = active_store.update_skill(
            skill_id,
            name=payload.name,
            description=payload.description,
            scope=payload.scope,
            version=payload.version,
            source_type=payload.source_type,
            status=payload.status,
        )
        active_store.record_event(
            event_type="skill.updated",
            source="ui",
            payload={"skill_id": skill_id, "status": skill["status"]},
        )
        return SkillRecord(**skill)

    @app.delete("/api/skills/{skill_id}", status_code=204)
    def delete_skill(skill_id: str) -> None:
        active_store.delete_skill(skill_id)
        active_store.record_event(
            event_type="skill.deleted",
            source="ui",
            payload={"skill_id": skill_id},
        )

    @app.get("/api/schedules", response_model=list[ScheduleRecord])
    def schedules() -> list[ScheduleRecord]:
        return [ScheduleRecord(**schedule) for schedule in active_store.list_schedules()]

    @app.post("/api/schedules", response_model=ScheduleRecord, status_code=201)
    def create_schedule(payload: ScheduleCreateRequest) -> ScheduleRecord:
        schedule = active_store.create_schedule(
            name=payload.name,
            target_type=payload.target_type,
            target_ref=payload.target_ref,
            schedule_expression=payload.schedule_expression,
            timezone=payload.timezone,
            enabled=payload.enabled,
            last_run_at=payload.last_run_at,
            next_run_at=payload.next_run_at,
        )
        active_store.record_event(
            event_type="schedule.created",
            source="ui",
            payload={"schedule_id": schedule["id"], "name": schedule["name"]},
        )
        return ScheduleRecord(**schedule)

    @app.get("/api/schedules/{schedule_id}", response_model=ScheduleRecord)
    def get_schedule(schedule_id: str) -> ScheduleRecord:
        schedule = active_store.get_schedule(schedule_id)
        if schedule is None:
            raise HTTPException(status_code=404, detail="Schedule not found")
        return ScheduleRecord(**schedule)

    @app.patch("/api/schedules/{schedule_id}", response_model=ScheduleRecord)
    def update_schedule(schedule_id: str, payload: ScheduleUpdateRequest) -> ScheduleRecord:
        schedule = active_store.update_schedule(
            schedule_id,
            name=payload.name,
            target_type=payload.target_type,
            target_ref=payload.target_ref,
            schedule_expression=payload.schedule_expression,
            timezone=payload.timezone,
            enabled=payload.enabled,
            last_run_at=payload.last_run_at,
            next_run_at=payload.next_run_at,
        )
        active_store.record_event(
            event_type="schedule.updated",
            source="ui",
            payload={"schedule_id": schedule_id, "enabled": schedule["enabled"]},
        )
        return ScheduleRecord(**schedule)

    @app.delete("/api/schedules/{schedule_id}", status_code=204)
    def delete_schedule(schedule_id: str) -> None:
        active_store.delete_schedule(schedule_id)
        active_store.record_event(
            event_type="schedule.deleted",
            source="ui",
            payload={"schedule_id": schedule_id},
        )

    @app.get("/api/memory", response_model=list[MemoryLayerRecord])
    def memory_layers() -> list[MemoryLayerRecord]:
        return [MemoryLayerRecord(**layer) for layer in active_store.list_memory_layers()]

    @app.get("/api/memory/items", response_model=list[MemoryItemRecord])
    def memory_items(limit: int = 25) -> list[MemoryItemRecord]:
        if limit < 1 or limit > 100:
            raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
        return [MemoryItemRecord(**item) for item in active_store.list_memory_items(limit=limit)]

    @app.post("/api/memory/items", response_model=MemoryItemRecord, status_code=201)
    def ingest_memory(payload: MemoryIngestRequest) -> MemoryItemRecord:
        item = memory_engine.ingest(
            title=payload.title,
            summary=payload.summary,
            content=payload.content,
            provenance=payload.provenance,
            source_ref=payload.source_ref,
            layer=payload.layer,
            scope=payload.scope,
            confidence=payload.confidence,
            freshness=payload.freshness,
            tags=payload.tags,
            state=payload.state,
        )
        return MemoryItemRecord(**item)

    @app.post("/api/memory/consolidate", response_model=MemoryConsolidationResponse)
    def consolidate_memory() -> MemoryConsolidationResponse:
        return MemoryConsolidationResponse(**memory_engine.consolidate())

    @app.get("/api/memory/retrieve", response_model=MemoryRetrievalResponse)
    def retrieve_memory(
        query: str,
        role: str = "orchestrator",
        scope: str | None = None,
        limit: int = 5,
    ) -> MemoryRetrievalResponse:
        if limit < 1 or limit > 20:
            raise HTTPException(status_code=400, detail="limit must be between 1 and 20")
        result = memory_engine.retrieve(query=query, role=role, scope=scope, limit=limit)
        return MemoryRetrievalResponse(
            query=result.query,
            scope=result.scope,
            role=result.role,
            items=[MemoryItemRecord(**item) for item in result.items],
            trace=result.trace,
        )

    @app.get("/api/orchestration/runs", response_model=OrchestrationRunListResponse)
    def orchestration_runs(limit: int = 10) -> OrchestrationRunListResponse:
        if limit < 1 or limit > 20:
            raise HTTPException(status_code=400, detail="limit must be between 1 and 20")
        return OrchestrationRunListResponse(
            task_runs=[TaskRunRecord(**run) for run in orchestration_engine.list_runs(limit=limit)]
        )

    @app.get("/api/orchestration/runs/{task_run_id}", response_model=OrchestrationRunResponse)
    def orchestration_run(task_run_id: str) -> OrchestrationRunResponse:
        result = orchestration_engine.get_run(task_run_id)
        return OrchestrationRunResponse(
            task=TaskRecord(**result["task"]),
            task_run=TaskRunRecord(**result["task_run"]),
            agent_runs=[AgentRunRecord(**run) for run in result["agent_runs"]],
        )

    @app.post("/api/orchestration/launch", response_model=OrchestrationLaunchResponse, status_code=201)
    def launch_orchestration(payload: OrchestrationLaunchRequest) -> OrchestrationLaunchResponse:
        result = orchestration_engine.launch(
            objective=payload.objective,
            task_title=payload.task_title,
            task_summary=payload.task_summary,
            requested_by=payload.requested_by,
            mode=payload.mode,
            priority=payload.priority,
        )
        return OrchestrationLaunchResponse(
            task=TaskRecord(**result.task),
            task_run=TaskRunRecord(**result.task_run),
            agent_runs=[AgentRunRecord(**run) for run in result.agent_runs],
            steps=result.steps,
            approvals_required=result.approvals_required,
            summary=result.summary,
        )

    @app.get("/api/events", response_model=list[EventRecord])
    def events(limit: int = 25) -> list[EventRecord]:
        if limit < 1 or limit > 100:
            raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
        return [EventRecord(**event) for event in active_store.list_events(limit=limit)]

    @app.post("/api/events", response_model=EventRecord, status_code=201)
    def create_event(payload: EventCreateRequest) -> EventRecord:
        event = active_store.record_event(
            event_type=payload.type,
            source=payload.source,
            payload=payload.payload,
        )
        return EventRecord(**event)

    return app


app = create_app()
