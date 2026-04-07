from __future__ import annotations

from dataclasses import asdict
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import (
    AgentRecord,
    AgentCreateRequest,
    AgentUpdateRequest,
    AgentRunRecord,
    ApprovalRequestRecord,
    ApprovalResolveRequest,
    EntityPolicyRecord,
    EntityPolicyUpdateRequest,
    EventCreateRequest,
    EventRecord,
    HealthResponse,
    MemoryConsolidationResponse,
    MemoryIngestRequest,
    MemoryItemRecord,
    MemoryLayerRecord,
    MemoryRetrievalResponse,
    MemoryReviewResponse,
    OrchestrationLaunchRequest,
    OrchestrationLaunchResponse,
    OrchestrationRunListResponse,
    OrchestrationRunResponse,
    ReplayComparisonRecord,
    ReplayResponse,
    ReplayTimelineRecord,
    PolicyDecisionRecord,
    PolicyRecord,
    PolicyUpdateRequest,
    ProjectCreateRequest,
    ProjectRecord,
    ProjectUpdateRequest,
    ScheduleCreateRequest,
    ScheduleRecord,
    ScheduleRunListResponse,
    ScheduleRunRecord,
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
from .policy import PolicyEngine
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
    policy_engine = PolicyEngine(active_store)

    def _gate_mutation(
        *,
        action: str,
        subject_type: str,
        subject_ref: str,
        payload: dict[str, object],
        project_id: str | None = None,
        requested_by: str = "ui",
    ) -> None:
        decision = policy_engine.evaluate(
            action=action,
            payload=payload,
            entity_type=subject_type,
            entity_id=subject_ref,
            project_id=project_id,
            mutating=True,
        )
        if decision.allowed:
            return
        approval = active_store.create_approval_request(
            action=action,
            subject_type=subject_type,
            subject_ref=subject_ref,
            sensitivity=decision.sensitivity,
            reason=decision.reason,
            payload={
                "action": action,
                "subject_type": subject_type,
                "subject_ref": subject_ref,
                "requested_by": requested_by,
                "payload": payload,
                "policy": policy_engine.snapshot(),
            },
            requested_by=requested_by,
        )
        active_store.record_event(
            event_type="approval.requested",
            source="policy",
            payload={
                "approval_id": approval["id"],
                "action": action,
                "subject_type": subject_type,
                "subject_ref": subject_ref,
                "sensitivity": decision.sensitivity,
                "mode": decision.mode,
                "reason": decision.reason,
            },
        )
        raise HTTPException(
            status_code=423,
            detail={
                "message": "Approval required",
                "decision": PolicyDecisionRecord(**asdict(decision)).model_dump(),
                "approval_request": ApprovalRequestRecord(**approval).model_dump(),
                "policy": policy_engine.snapshot(),
            },
        )

    def _approved_request_payload(approval: dict[str, object]) -> dict[str, object]:
        payload = approval.get("payload", {})
        if isinstance(payload, dict):
            nested = payload.get("payload", {})
            if isinstance(nested, dict):
                return nested
        return {}

    def _payload_project_id(payload: dict[str, object]) -> str | None:
        project_id = payload.get("project_id")
        return project_id if isinstance(project_id, str) and project_id else None

    def _schedule_requires_approval(schedule: dict[str, object]) -> bool:
        policy = str(schedule.get("approval_policy", "inherit")).lower()
        return policy in {"require_approval", "manual", "approval_required"}

    def _schedule_execution_objective(schedule: dict[str, object]) -> tuple[str, str | None, str | None]:
        target_type = str(schedule.get("target_type", ""))
        target_ref = str(schedule.get("target_ref", ""))

        if target_type == "task":
            task = active_store.get_task(target_ref)
            if task is not None:
                return (
                    f"Scheduled task execution: {task['title']}",
                    task["title"],
                    task["summary"],
                )
        if target_type == "project":
            project = active_store.get_project(target_ref)
            if project is not None:
                return (
                    f"Scheduled project execution: {project['name']}",
                    project["name"],
                    project["summary"],
                )
        if target_type == "skill":
            skill = active_store.get_skill(target_ref)
            if skill is not None:
                return (
                    f"Scheduled skill execution: {skill['name']}",
                    skill["name"],
                    skill["description"],
                )
        if target_type == "orchestration":
            return (
                f"Scheduled orchestration: {target_ref or schedule.get('name', 'scheduled run')}",
                str(schedule.get("name", "Scheduled orchestration")),
                f"Recurring execution for {target_ref or schedule.get('name', 'scheduled run')}",
            )
        return (
            f"Scheduled execution: {schedule.get('name', 'scheduled run')}",
            str(schedule.get("name", "Scheduled run")),
            str(schedule.get("name", "Scheduled run")),
        )

    def _build_replay_timeline(task_run_id: str) -> list[dict[str, object]]:
        task_run = active_store.get_task_run(task_run_id)
        if task_run is None:
            raise HTTPException(status_code=404, detail="Task run not found")

        timeline: list[dict[str, object]] = [
            {
                "kind": "task_run",
                "label": task_run["status"],
                "detail": task_run["summary"],
                "created_at": task_run["created_at"],
                "source_id": task_run["id"],
            }
        ]
        for agent_run in active_store.list_agent_runs(task_run_id=task_run_id, limit=100):
            timeline.append(
                {
                    "kind": f"agent:{agent_run['run_kind']}",
                    "label": agent_run["agent_name"],
                    "detail": agent_run["summary"],
                    "created_at": agent_run["created_at"],
                    "source_id": agent_run["id"],
                }
            )
        for schedule_run in active_store.list_schedule_runs(limit=100, task_run_id=task_run_id):
            timeline.append(
                {
                    "kind": "schedule_run",
                    "label": schedule_run["schedule_name"],
                    "detail": schedule_run["result_summary"],
                    "created_at": schedule_run["created_at"],
                    "source_id": schedule_run["id"],
                }
            )
        for event in active_store.list_replay_events(task_run_id=task_run_id):
            timeline.append(
                {
                    "kind": "event",
                    "label": event["type"],
                    "detail": event["source"],
                    "created_at": event["created_at"],
                    "source_id": str(event["id"]),
                }
            )
        timeline.sort(key=lambda item: str(item["created_at"]))
        return timeline

    def _compare_runs(task_run_id: str) -> dict[str, object] | None:
        task_run = active_store.get_task_run(task_run_id)
        if task_run is None:
            return None
        history = [run for run in active_store.list_task_runs(limit=50) if run["task_id"] == task_run["task_id"]]
        previous = next((run for run in history if run["id"] != task_run_id), None)
        if previous is None:
            return {
                "previous_task_run_id": None,
                "status_changed": False,
                "summary_changed": False,
                "step_count_delta": 0,
                "approval_required_changed": False,
            }
        return {
            "previous_task_run_id": previous["id"],
            "status_changed": previous["status"] != task_run["status"],
            "summary_changed": previous["summary"] != task_run["summary"],
            "step_count_delta": int(task_run["step_count"]) - int(previous["step_count"]),
            "approval_required_changed": bool(previous["approval_required"]) != bool(task_run["approval_required"]),
        }

    def _dispatch_schedule_run(
        *,
        schedule: dict[str, object],
        requested_by: str,
        retry_of_run_id: str | None = None,
        attempt_number: int = 1,
    ) -> dict[str, object]:
        run = active_store.create_schedule_run(
            schedule_id=str(schedule["id"]),
            schedule_name=str(schedule["name"]),
            target_type=str(schedule["target_type"]),
            target_ref=str(schedule["target_ref"]),
            requested_by=requested_by,
            result_summary=f"Queued schedule {schedule['name']} for execution.",
            retry_of_run_id=retry_of_run_id,
            attempt_number=attempt_number,
            status="running",
        )
        active_store.record_event(
            event_type="schedule.run_requested",
            source="scheduler",
            payload={
                "schedule_run_id": run["id"],
                "schedule_id": schedule["id"],
                "requested_by": requested_by,
                "attempt_number": attempt_number,
            },
        )

        try:
            objective, task_title, task_summary = _schedule_execution_objective(schedule)
            launch = orchestration_engine.launch(
                objective=objective,
                task_title=task_title,
                task_summary=task_summary,
                requested_by=requested_by,
                mode="Autonomous",
                priority="High",
                task_id=str(schedule.get("target_ref")) if str(schedule.get("target_type")) == "task" else None,
                bypass_policy=True,
            )
            updated = active_store.update_schedule_run(
                run["id"],
                status="completed",
                result_summary=launch.summary,
                task_run_id=launch.task_run["id"],
                completed=True,
            )
            active_store.record_event(
                event_type="schedule.run_completed",
                source="scheduler",
                payload={
                    "schedule_run_id": run["id"],
                    "schedule_id": schedule["id"],
                    "task_run_id": launch.task_run["id"],
                    "requested_by": requested_by,
                },
            )
            return updated
        except Exception as exc:  # pragma: no cover - defensive guard for live execution
            failed = active_store.update_schedule_run(
                run["id"],
                status="failed",
                last_error=str(exc),
                completed=True,
            )
            active_store.record_event(
                event_type="schedule.run_failed",
                source="scheduler",
                payload={
                    "schedule_run_id": run["id"],
                    "schedule_id": schedule["id"],
                    "requested_by": requested_by,
                    "error": str(exc),
                },
            )
            if str(schedule.get("failure_policy", "retry_once")).lower() == "retry_once" and attempt_number == 1:
                active_store.record_event(
                    event_type="schedule.run_retry_scheduled",
                    source="scheduler",
                    payload={
                        "schedule_id": schedule["id"],
                        "previous_run_id": run["id"],
                        "requested_by": requested_by,
                    },
                )
                return _dispatch_schedule_run(
                    schedule=schedule,
                    requested_by=requested_by,
                    retry_of_run_id=run["id"],
                    attempt_number=2,
                )
            return failed

    def _execute_approved_request(approval: dict[str, object]) -> dict[str, object]:
        action = str(approval.get("action", ""))
        subject_ref = str(approval.get("subject_ref", ""))
        requested_by = str(approval.get("requested_by", "ui"))
        payload = _approved_request_payload(approval)

        if action == "task.create":
            task = active_store.create_task(
                title=str(payload.get("title", "Untitled task")),
                summary=str(payload.get("summary", "")),
                status=str(payload.get("status", "Inbox")),
                priority=str(payload.get("priority", "Medium")),
                project_id=_payload_project_id(payload),
            )
            active_store.record_event(
                event_type="task.created",
                source="approval",
                payload={"task_id": task["id"], "title": task["title"], "requested_by": requested_by},
            )
            return {"task": task}

        if action == "task.update":
            task = active_store.update_task(
                subject_ref,
                title=str(payload.get("title", "Untitled task")),
                summary=str(payload.get("summary", "")),
                status=str(payload.get("status", "Inbox")),
                priority=str(payload.get("priority", "Medium")),
                project_id=_payload_project_id(payload),
            )
            active_store.record_event(
                event_type="task.updated",
                source="approval",
                payload={"task_id": subject_ref, "status": task["status"], "requested_by": requested_by},
            )
            return {"task": task}

        if action == "task.delete":
            active_store.delete_task(subject_ref)
            active_store.record_event(
                event_type="task.deleted",
                source="approval",
                payload={"task_id": subject_ref, "requested_by": requested_by},
            )
            return {"task_id": subject_ref}

        if action == "agent.create":
            agent = active_store.create_agent(
                name=str(payload.get("name", "Untitled agent")),
                role=str(payload.get("role", "Unassigned")),
                status=str(payload.get("status", "Idle")),
            )
            active_store.record_event(
                event_type="agent.created",
                source="approval",
                payload={"agent_id": agent["id"], "name": agent["name"], "requested_by": requested_by},
            )
            return {"agent": agent}

        if action == "agent.update":
            agent = active_store.update_agent(
                subject_ref,
                name=str(payload.get("name", "Untitled agent")),
                role=str(payload.get("role", "Unassigned")),
                status=str(payload.get("status", "Idle")),
            )
            active_store.record_event(
                event_type="agent.updated",
                source="approval",
                payload={"agent_id": subject_ref, "status": agent["status"], "requested_by": requested_by},
            )
            return {"agent": agent}

        if action == "agent.delete":
            active_store.delete_agent(subject_ref)
            active_store.record_event(
                event_type="agent.deleted",
                source="approval",
                payload={"agent_id": subject_ref, "requested_by": requested_by},
            )
            return {"agent_id": subject_ref}

        if action == "project.create":
            project = active_store.create_project(
                name=str(payload.get("name", "Untitled project")),
                summary=str(payload.get("summary", "")),
                status=str(payload.get("status", "Planned")),
                owner=str(payload.get("owner", "Gnosys")),
            )
            active_store.record_event(
                event_type="project.created",
                source="approval",
                payload={"project_id": project["id"], "name": project["name"], "requested_by": requested_by},
            )
            return {"project": project}

        if action == "project.update":
            project = active_store.update_project(
                subject_ref,
                name=str(payload.get("name", "Untitled project")),
                summary=str(payload.get("summary", "")),
                status=str(payload.get("status", "Planned")),
                owner=str(payload.get("owner", "Gnosys")),
            )
            active_store.record_event(
                event_type="project.updated",
                source="approval",
                payload={"project_id": subject_ref, "status": project["status"], "requested_by": requested_by},
            )
            return {"project": project}

        if action == "project.delete":
            active_store.delete_project(subject_ref)
            active_store.record_event(
                event_type="project.deleted",
                source="approval",
                payload={"project_id": subject_ref, "requested_by": requested_by},
            )
            return {"project_id": subject_ref}

        if action == "skill.create":
            skill = active_store.create_skill(
                name=str(payload.get("name", "Untitled skill")),
                description=str(payload.get("description", "")),
                scope=str(payload.get("scope", "workspace")),
                version=str(payload.get("version", "0.1.0")),
                source_type=str(payload.get("source_type", "authored")),
                status=str(payload.get("status", "draft")),
                project_id=_payload_project_id(payload),
            )
            active_store.record_event(
                event_type="skill.created",
                source="approval",
                payload={"skill_id": skill["id"], "name": skill["name"], "requested_by": requested_by},
            )
            return {"skill": skill}

        if action == "skill.update":
            skill = active_store.update_skill(
                subject_ref,
                name=str(payload.get("name", "Untitled skill")),
                description=str(payload.get("description", "")),
                scope=str(payload.get("scope", "workspace")),
                version=str(payload.get("version", "0.1.0")),
                source_type=str(payload.get("source_type", "authored")),
                status=str(payload.get("status", "draft")),
                project_id=_payload_project_id(payload),
            )
            active_store.record_event(
                event_type="skill.updated",
                source="approval",
                payload={"skill_id": subject_ref, "status": skill["status"], "requested_by": requested_by},
            )
            return {"skill": skill}

        if action == "skill.delete":
            active_store.delete_skill(subject_ref)
            active_store.record_event(
                event_type="skill.deleted",
                source="approval",
                payload={"skill_id": subject_ref, "requested_by": requested_by},
            )
            return {"skill_id": subject_ref}

        if action == "schedule.create":
            schedule = active_store.create_schedule(
                name=str(payload.get("name", "Untitled schedule")),
                target_type=str(payload.get("target_type", "skill")),
                target_ref=str(payload.get("target_ref", "")),
                schedule_expression=str(payload.get("schedule_expression", "")),
                timezone=str(payload.get("timezone", "America/New_York")),
                enabled=bool(payload.get("enabled", True)),
                approval_policy=str(payload.get("approval_policy", "inherit")),
                failure_policy=str(payload.get("failure_policy", "retry_once")),
                last_run_at=payload.get("last_run_at"),
                next_run_at=payload.get("next_run_at"),
                project_id=_payload_project_id(payload),
            )
            active_store.record_event(
                event_type="schedule.created",
                source="approval",
                payload={"schedule_id": schedule["id"], "name": schedule["name"], "requested_by": requested_by},
            )
            return {"schedule": schedule}

        if action == "schedule.update":
            schedule = active_store.update_schedule(
                subject_ref,
                name=str(payload.get("name", "Untitled schedule")),
                target_type=str(payload.get("target_type", "skill")),
                target_ref=str(payload.get("target_ref", "")),
                schedule_expression=str(payload.get("schedule_expression", "")),
                timezone=str(payload.get("timezone", "America/New_York")),
                enabled=bool(payload.get("enabled", True)),
                approval_policy=str(payload.get("approval_policy", "inherit")),
                failure_policy=str(payload.get("failure_policy", "retry_once")),
                last_run_at=payload.get("last_run_at"),
                next_run_at=payload.get("next_run_at"),
                project_id=_payload_project_id(payload),
            )
            active_store.record_event(
                event_type="schedule.updated",
                source="approval",
                payload={"schedule_id": subject_ref, "enabled": schedule["enabled"], "requested_by": requested_by},
            )
            return {"schedule": schedule}

        if action == "schedule.delete":
            active_store.delete_schedule(subject_ref)
            active_store.record_event(
                event_type="schedule.deleted",
                source="approval",
                payload={"schedule_id": subject_ref, "requested_by": requested_by},
            )
            return {"schedule_id": subject_ref}

        if action == "schedule.run":
            schedule = active_store.get_schedule(subject_ref)
            if schedule is None:
                raise HTTPException(status_code=404, detail="Schedule not found")
            run = _dispatch_schedule_run(schedule=schedule, requested_by=requested_by)
            return {"schedule_run": run, "schedule_id": subject_ref}

        if action == "memory.ingest":
            item = memory_engine.ingest(
                title=str(payload.get("title", "Untitled memory")),
                summary=str(payload.get("summary", "")),
                content=str(payload.get("content", "")),
                provenance=str(payload.get("provenance", "approval")),
                source_ref=str(payload.get("source_ref", "")),
                layer=str(payload.get("layer", "Semantic")),
                scope=str(payload.get("scope", "workspace")),
                confidence=float(payload.get("confidence", 0.7)),
                freshness=float(payload.get("freshness", 0.7)),
                tags=list(payload.get("tags", [])) if isinstance(payload.get("tags", []), list) else [],
                state=str(payload.get("state", "candidate")),
                project_id=_payload_project_id(payload),
            )
            return {"memory_item": item}

        if action == "orchestration.launch":
            result = orchestration_engine.launch(
                objective=str(payload.get("objective", "")),
                task_title=payload.get("task_title") if isinstance(payload.get("task_title"), str) else None,
                task_summary=payload.get("task_summary") if isinstance(payload.get("task_summary"), str) else None,
                requested_by=requested_by,
                mode=str(payload.get("mode", "Supervised")),
                priority=str(payload.get("priority", "High")),
                task_id=payload.get("task_id") if isinstance(payload.get("task_id"), str) else None,
                bypass_policy=True,
            )
            return {
                "task": result.task,
                "task_run": result.task_run,
                "agent_runs": result.agent_runs,
            }

        raise HTTPException(status_code=422, detail=f"Unsupported approval action: {action}")

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    @app.get("/status", response_model=StatusResponse)
    def status() -> StatusResponse:
        return StatusResponse(
            mode="operational",
            note="Local persistence, event log, and autonomy policy are active",
        )

    @app.get("/api/policy", response_model=PolicyRecord)
    def get_policy() -> PolicyRecord:
        return PolicyRecord(**policy_engine.snapshot())

    @app.patch("/api/policy", response_model=PolicyRecord)
    def update_policy(payload: PolicyUpdateRequest) -> PolicyRecord:
        policy = policy_engine.update(
            autonomy_mode=payload.autonomy_mode,
            kill_switch=payload.kill_switch,
            approval_bias=payload.approval_bias,
        )
        active_store.record_event(
            event_type="policy.updated",
            source="ui",
            payload=policy,
        )
        return PolicyRecord(**policy)

    @app.get("/api/approvals", response_model=list[ApprovalRequestRecord])
    def list_approvals(limit: int = 25) -> list[ApprovalRequestRecord]:
        if limit < 1 or limit > 100:
            raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
        return [ApprovalRequestRecord(**request) for request in active_store.list_approval_requests(limit=limit)]

    @app.post("/api/approvals/{approval_id}/resolve", response_model=ApprovalRequestRecord)
    def resolve_approval(approval_id: str, payload: ApprovalResolveRequest) -> ApprovalRequestRecord:
        updated = active_store.update_approval_request(
            approval_id,
            status=payload.status,
            resolved_by=payload.resolved_by,
        )
        if payload.status == "approved":
            approval = active_store.get_approval_request(approval_id)
            if approval is None:
                raise HTTPException(status_code=404, detail="Approval request not found")
            _execute_approved_request(approval)
        active_store.record_event(
            event_type="approval.resolved",
            source="ui",
            payload={"approval_id": approval_id, "status": payload.status, "resolved_by": payload.resolved_by},
        )
        return ApprovalRequestRecord(**updated)

    @app.get("/api/policies/entities", response_model=list[EntityPolicyRecord])
    def list_entity_policies(limit: int = 25) -> list[EntityPolicyRecord]:
        if limit < 1 or limit > 100:
            raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
        return [EntityPolicyRecord(**policy) for policy in active_store.list_entity_policies(limit=limit)]

    @app.get("/api/policies/entities/{entity_type}/{entity_id}", response_model=EntityPolicyRecord)
    def get_entity_policy(entity_type: str, entity_id: str) -> EntityPolicyRecord:
        policy = active_store.get_entity_policy(entity_type, entity_id)
        if policy is None:
            raise HTTPException(status_code=404, detail="Entity policy not found")
        return EntityPolicyRecord(**policy)

    @app.patch("/api/policies/entities/{entity_type}/{entity_id}", response_model=EntityPolicyRecord)
    def update_entity_policy(entity_type: str, entity_id: str, payload: EntityPolicyUpdateRequest) -> EntityPolicyRecord:
        current = active_store.get_entity_policy(entity_type, entity_id) or {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "project_id": entity_id if entity_type == "project" else None,
            "autonomy_mode": policy_engine.snapshot()["autonomy_mode"],
            "kill_switch": False,
            "approval_bias": policy_engine.snapshot()["approval_bias"],
            "created_at": None,
            "updated_at": None,
        }
        policy = active_store.upsert_entity_policy(
            entity_type=entity_type,
            entity_id=entity_id,
            project_id=entity_id if entity_type == "project" else current.get("project_id"),
            autonomy_mode=payload.autonomy_mode or current["autonomy_mode"],
            kill_switch=current["kill_switch"] if payload.kill_switch is None else payload.kill_switch,
            approval_bias=payload.approval_bias or current["approval_bias"],
        )
        active_store.record_event(
            event_type="policy.entity.updated",
            source="ui",
            payload={"entity_type": entity_type, "entity_id": entity_id, "policy": policy},
        )
        return EntityPolicyRecord(**policy)

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
        _gate_mutation(
            action="task.create",
            subject_type="task",
            subject_ref=payload.title,
            payload=payload.model_dump(),
            project_id=payload.project_id,
        )
        task = active_store.create_task(
            title=payload.title,
            summary=payload.summary,
            status=payload.status,
            priority=payload.priority,
            project_id=payload.project_id,
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
        existing = active_store.get_task(task_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Task not found")
        _gate_mutation(
            action="task.update",
            subject_type="task",
            subject_ref=task_id,
            payload=payload.model_dump(),
            project_id=payload.project_id or existing.get("project_id"),
        )
        task = active_store.update_task(
            task_id,
            title=payload.title,
            summary=payload.summary,
            status=payload.status,
            priority=payload.priority,
            project_id=payload.project_id,
        )
        active_store.record_event(
            event_type="task.updated",
            source="ui",
            payload={"task_id": task_id, "status": task["status"]},
        )
        return TaskRecord(**task)

    @app.delete("/api/tasks/{task_id}", status_code=204)
    def delete_task(task_id: str) -> None:
        existing = active_store.get_task(task_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Task not found")
        _gate_mutation(
            action="task.delete",
            subject_type="task",
            subject_ref=task_id,
            payload={"task_id": task_id},
            project_id=existing.get("project_id"),
        )
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
        _gate_mutation(
            action="agent.create",
            subject_type="agent",
            subject_ref=payload.name,
            payload=payload.model_dump(),
        )
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
        _gate_mutation(
            action="agent.update",
            subject_type="agent",
            subject_ref=agent_id,
            payload=payload.model_dump(),
        )
        agent = active_store.update_agent(agent_id, name=payload.name, role=payload.role, status=payload.status)
        active_store.record_event(
            event_type="agent.updated",
            source="ui",
            payload={"agent_id": agent_id, "status": agent["status"]},
        )
        return AgentRecord(**agent)

    @app.delete("/api/agents/{agent_id}", status_code=204)
    def delete_agent(agent_id: str) -> None:
        _gate_mutation(
            action="agent.delete",
            subject_type="agent",
            subject_ref=agent_id,
            payload={"agent_id": agent_id},
        )
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
        _gate_mutation(
            action="project.create",
            subject_type="project",
            subject_ref=payload.name,
            payload=payload.model_dump(),
        )
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
        _gate_mutation(
            action="project.update",
            subject_type="project",
            subject_ref=project_id,
            payload=payload.model_dump(),
            project_id=project_id,
        )
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
        _gate_mutation(
            action="project.delete",
            subject_type="project",
            subject_ref=project_id,
            payload={"project_id": project_id},
            project_id=project_id,
        )
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
        _gate_mutation(
            action="skill.create",
            subject_type="skill",
            subject_ref=payload.name,
            payload=payload.model_dump(),
            project_id=payload.project_id,
        )
        skill = active_store.create_skill(
            name=payload.name,
            description=payload.description,
            scope=payload.scope,
            version=payload.version,
            source_type=payload.source_type,
            status=payload.status,
            project_id=payload.project_id,
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
        existing = active_store.get_skill(skill_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Skill not found")
        _gate_mutation(
            action="skill.update",
            subject_type="skill",
            subject_ref=skill_id,
            payload=payload.model_dump(),
            project_id=payload.project_id or existing.get("project_id"),
        )
        skill = active_store.update_skill(
            skill_id,
            name=payload.name,
            description=payload.description,
            scope=payload.scope,
            version=payload.version,
            source_type=payload.source_type,
            status=payload.status,
            project_id=payload.project_id,
        )
        active_store.record_event(
            event_type="skill.updated",
            source="ui",
            payload={"skill_id": skill_id, "status": skill["status"]},
        )
        return SkillRecord(**skill)

    @app.delete("/api/skills/{skill_id}", status_code=204)
    def delete_skill(skill_id: str) -> None:
        existing = active_store.get_skill(skill_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Skill not found")
        _gate_mutation(
            action="skill.delete",
            subject_type="skill",
            subject_ref=skill_id,
            payload={"skill_id": skill_id},
            project_id=existing.get("project_id"),
        )
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
        _gate_mutation(
            action="schedule.create",
            subject_type="schedule",
            subject_ref=payload.name,
            payload=payload.model_dump(),
            project_id=payload.project_id,
        )
        schedule = active_store.create_schedule(
            name=payload.name,
            target_type=payload.target_type,
            target_ref=payload.target_ref,
            schedule_expression=payload.schedule_expression,
            timezone=payload.timezone,
            enabled=payload.enabled,
            approval_policy=payload.approval_policy,
            failure_policy=payload.failure_policy,
            last_run_at=payload.last_run_at,
            next_run_at=payload.next_run_at,
            project_id=payload.project_id,
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
        existing = active_store.get_schedule(schedule_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Schedule not found")
        _gate_mutation(
            action="schedule.update",
            subject_type="schedule",
            subject_ref=schedule_id,
            payload=payload.model_dump(),
            project_id=payload.project_id or existing.get("project_id"),
        )
        schedule = active_store.update_schedule(
            schedule_id,
            name=payload.name,
            target_type=payload.target_type,
            target_ref=payload.target_ref,
            schedule_expression=payload.schedule_expression,
            timezone=payload.timezone,
            enabled=payload.enabled,
            approval_policy=payload.approval_policy,
            failure_policy=payload.failure_policy,
            last_run_at=payload.last_run_at,
            next_run_at=payload.next_run_at,
            project_id=payload.project_id,
        )
        active_store.record_event(
            event_type="schedule.updated",
            source="ui",
            payload={"schedule_id": schedule_id, "enabled": schedule["enabled"]},
        )
        return ScheduleRecord(**schedule)

    @app.delete("/api/schedules/{schedule_id}", status_code=204)
    def delete_schedule(schedule_id: str) -> None:
        existing = active_store.get_schedule(schedule_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Schedule not found")
        _gate_mutation(
            action="schedule.delete",
            subject_type="schedule",
            subject_ref=schedule_id,
            payload={"schedule_id": schedule_id},
            project_id=existing.get("project_id"),
        )
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
    def memory_items(limit: int = 25, project_id: str | None = None) -> list[MemoryItemRecord]:
        if limit < 1 or limit > 100:
            raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
        return [MemoryItemRecord(**item) for item in active_store.list_memory_items(limit=limit, project_id=project_id)]

    @app.get("/api/memory/review", response_model=MemoryReviewResponse)
    def review_memory(limit: int = 25) -> MemoryReviewResponse:
        if limit < 1 or limit > 100:
            raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
        candidates = active_store.list_memory_items(limit=limit, state="candidate")
        return MemoryReviewResponse(
            candidate_count=len(active_store.list_memory_items(limit=1000, state="candidate")),
            items=[MemoryItemRecord(**item) for item in candidates],
        )

    @app.post("/api/memory/items", response_model=MemoryItemRecord, status_code=201)
    def ingest_memory(payload: MemoryIngestRequest) -> MemoryItemRecord:
        _gate_mutation(
            action="memory.ingest",
            subject_type="memory_item",
            subject_ref=payload.title,
            payload=payload.model_dump(),
            project_id=payload.project_id,
        )
        item = memory_engine.ingest(
            title=payload.title,
            summary=payload.summary,
            content=payload.content,
            provenance=payload.provenance,
            source_ref=payload.source_ref,
            layer=payload.layer,
            scope=payload.scope,
            project_id=payload.project_id,
            confidence=payload.confidence,
            freshness=payload.freshness,
            tags=payload.tags,
            state=payload.state,
        )
        return MemoryItemRecord(**item)

    @app.post("/api/memory/items/{item_id}/promote", response_model=MemoryItemRecord)
    def promote_memory_item(item_id: str) -> MemoryItemRecord:
        item = active_store.update_memory_item_state(item_id, "validated")
        active_store.record_event(
            event_type="memory.promoted",
            source="ui",
            payload={"memory_item_id": item_id, "state": item["state"]},
        )
        return MemoryItemRecord(**item)

    @app.post("/api/memory/items/{item_id}/archive", response_model=MemoryItemRecord)
    def archive_memory_item(item_id: str) -> MemoryItemRecord:
        item = active_store.update_memory_item_state(item_id, "archived")
        active_store.record_event(
            event_type="memory.archived",
            source="ui",
            payload={"memory_item_id": item_id, "state": item["state"]},
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
        project_id: str | None = None,
        limit: int = 5,
    ) -> MemoryRetrievalResponse:
        if limit < 1 or limit > 20:
            raise HTTPException(status_code=400, detail="limit must be between 1 and 20")
        result = memory_engine.retrieve(query=query, role=role, scope=scope, project_id=project_id, limit=limit)
        return MemoryRetrievalResponse(
            query=result.query,
            scope=result.scope,
            role=result.role,
            items=[MemoryItemRecord(**item) for item in result.items],
            trace=result.trace,
        )

    @app.get("/api/schedule-runs", response_model=ScheduleRunListResponse)
    def schedule_runs(limit: int = 25) -> ScheduleRunListResponse:
        if limit < 1 or limit > 100:
            raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
        return ScheduleRunListResponse(
            schedule_runs=[ScheduleRunRecord(**run) for run in active_store.list_schedule_runs(limit=limit)]
        )

    @app.post("/api/schedules/{schedule_id}/run", response_model=ScheduleRunRecord, status_code=201)
    def run_schedule(schedule_id: str, requested_by: str = "ui") -> ScheduleRunRecord:
        schedule = active_store.get_schedule(schedule_id)
        if schedule is None:
            raise HTTPException(status_code=404, detail="Schedule not found")
        if _schedule_requires_approval(schedule):
            approval = active_store.create_approval_request(
                action="schedule.run",
                subject_type="schedule",
                subject_ref=schedule_id,
                sensitivity="high",
                reason="Schedule approval policy requires manual review.",
                payload={
                    "schedule_id": schedule_id,
                    "schedule_name": schedule["name"],
                    "target_type": schedule["target_type"],
                    "target_ref": schedule["target_ref"],
                    "requested_by": requested_by,
                    "project_id": schedule.get("project_id"),
                    "approval_policy": schedule.get("approval_policy"),
                    "failure_policy": schedule.get("failure_policy"),
                },
                requested_by=requested_by,
            )
            active_store.record_event(
                event_type="approval.requested",
                source="policy",
                payload={
                    "approval_id": approval["id"],
                    "action": "schedule.run",
                    "subject_type": "schedule",
                    "subject_ref": schedule_id,
                    "reason": "Schedule approval policy requires manual review.",
                },
            )
            raise HTTPException(
                status_code=423,
                detail={
                    "message": "Approval required",
                    "decision": {
                        "allowed": False,
                        "requires_approval": True,
                        "sensitivity": "high",
                        "reason": "Schedule approval policy requires manual review.",
                        "mode": policy_engine.snapshot()["autonomy_mode"],
                        "action": "schedule.run",
                        "policy_scope": "entity",
                        "policy_entity_type": "schedule",
                        "policy_entity_id": schedule_id,
                    },
                    "approval_request": ApprovalRequestRecord(**approval).model_dump(),
                    "policy": policy_engine.snapshot(),
                },
            )
        _gate_mutation(
            action="schedule.run",
            subject_type="schedule",
            subject_ref=schedule_id,
            payload={
                "schedule_id": schedule_id,
                "schedule_name": schedule["name"],
                "target_type": schedule["target_type"],
                "target_ref": schedule["target_ref"],
                "requested_by": requested_by,
                "project_id": schedule.get("project_id"),
                "approval_policy": schedule.get("approval_policy"),
                "failure_policy": schedule.get("failure_policy"),
            },
            project_id=schedule.get("project_id"),
        )
        return ScheduleRunRecord(**_dispatch_schedule_run(schedule=schedule, requested_by=requested_by))

    @app.post("/api/schedule-runs/{run_id}/retry", response_model=ScheduleRunRecord, status_code=201)
    def retry_schedule_run(run_id: str, requested_by: str = "ui") -> ScheduleRunRecord:
        original = active_store.get_schedule_run(run_id)
        if original is None:
            raise HTTPException(status_code=404, detail="Schedule run not found")
        schedule = active_store.get_schedule(original["schedule_id"])
        if schedule is None:
            raise HTTPException(status_code=404, detail="Schedule not found")
        if _schedule_requires_approval(schedule):
            approval = active_store.create_approval_request(
                action="schedule.run",
                subject_type="schedule",
                subject_ref=schedule["id"],
                sensitivity="high",
                reason="Schedule approval policy requires manual review.",
                payload={
                    "schedule_id": schedule["id"],
                    "schedule_name": schedule["name"],
                    "target_type": schedule["target_type"],
                    "target_ref": schedule["target_ref"],
                    "requested_by": requested_by,
                    "retry_of_run_id": run_id,
                    "project_id": schedule.get("project_id"),
                    "approval_policy": schedule.get("approval_policy"),
                    "failure_policy": schedule.get("failure_policy"),
                },
                requested_by=requested_by,
            )
            active_store.record_event(
                event_type="approval.requested",
                source="policy",
                payload={
                    "approval_id": approval["id"],
                    "action": "schedule.run",
                    "subject_type": "schedule",
                    "subject_ref": schedule["id"],
                    "reason": "Schedule approval policy requires manual review.",
                },
            )
            raise HTTPException(
                status_code=423,
                detail={
                    "message": "Approval required",
                    "decision": {
                        "allowed": False,
                        "requires_approval": True,
                        "sensitivity": "high",
                        "reason": "Schedule approval policy requires manual review.",
                        "mode": policy_engine.snapshot()["autonomy_mode"],
                        "action": "schedule.run",
                        "policy_scope": "entity",
                        "policy_entity_type": "schedule",
                        "policy_entity_id": schedule["id"],
                    },
                    "approval_request": ApprovalRequestRecord(**approval).model_dump(),
                    "policy": policy_engine.snapshot(),
                },
            )
        _gate_mutation(
            action="schedule.run",
            subject_type="schedule",
            subject_ref=schedule["id"],
            payload={
                "schedule_id": schedule["id"],
                "schedule_name": schedule["name"],
                "target_type": schedule["target_type"],
                "target_ref": schedule["target_ref"],
                "requested_by": requested_by,
                "retry_of_run_id": run_id,
                "project_id": schedule.get("project_id"),
                "approval_policy": schedule.get("approval_policy"),
                "failure_policy": schedule.get("failure_policy"),
            },
            project_id=schedule.get("project_id"),
        )
        return ScheduleRunRecord(
            **_dispatch_schedule_run(
                schedule=schedule,
                requested_by=requested_by,
                retry_of_run_id=run_id,
                attempt_number=int(original["attempt_number"]) + 1,
            )
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

    @app.get("/api/diagnostics/replay/{task_run_id}", response_model=ReplayResponse)
    def replay_run(task_run_id: str) -> ReplayResponse:
        result = orchestration_engine.get_run(task_run_id)
        comparison = _compare_runs(task_run_id)
        return ReplayResponse(
            task_run=TaskRunRecord(**result["task_run"]),
            agent_runs=[AgentRunRecord(**run) for run in result["agent_runs"]],
            events=[EventRecord(**event) for event in active_store.list_replay_events(task_run_id=task_run_id)],
            timeline=[ReplayTimelineRecord(**item) for item in _build_replay_timeline(task_run_id)],
            comparison=ReplayComparisonRecord(**comparison) if comparison is not None else None,
            schedule_runs=[
                ScheduleRunRecord(**run)
                for run in active_store.list_schedule_runs(limit=100, task_run_id=task_run_id)
            ],
        )

    @app.post("/api/orchestration/launch", response_model=OrchestrationLaunchResponse, status_code=201)
    def launch_orchestration(payload: OrchestrationLaunchRequest) -> OrchestrationLaunchResponse:
        _gate_mutation(
            action="orchestration.launch",
            subject_type="task_run",
            subject_ref=payload.task_title or payload.objective[:48],
            payload=payload.model_dump(),
        )
        result = orchestration_engine.launch(
            objective=payload.objective,
            task_title=payload.task_title,
            task_summary=payload.task_summary,
            requested_by=payload.requested_by,
            mode=payload.mode,
            priority=payload.priority,
            task_id=payload.task_id,
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
