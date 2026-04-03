from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Callable

from gnosys_backend.config import PipelineConfig
from gnosys_backend.db import Database, decode_json, encode_json
from gnosys_backend.models import (
    AgentProfile,
    AgentSpawnRequest,
    AgentSpawnResponse,
    AgentStatus,
    PipelineExecuteRequest,
    PipelineExecuteResponse,
    PipelineProfile,
    TaskDelegateRequest,
    TaskDelegateResponse,
)


class AgentType(str, Enum):
    PRIMARY = "primary"
    SPECIALIST = "specialist"
    WORKER = "worker"
    COORDINATOR = "coordinator"


class CoordinationMode(str, Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HIERARCHICAL = "hierarchical"
    DEBATE = "debate"


class PipelineStore:
    """Multi-agent pipeline orchestration system."""

    def __init__(self, db: Database, config: PipelineConfig) -> None:
        self._db = db
        self._config = config
        self._active_agents: dict[str, dict[str, Any]] = {}
        self._spawn_callbacks: list[Callable] = []

    def register_spawn_callback(self, callback: Callable) -> None:
        """Register a callback for spawning sub-agents (for OpenClaw integration)."""
        self._spawn_callbacks.append(callback)

    def define_profile(
        self,
        name: str,
        agents: list[dict[str, Any]],
        coordination: CoordinationMode,
    ) -> PipelineProfile:
        """Define a pipeline profile for coordinated agent execution."""
        profile_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        self._db.execute(
            """INSERT INTO pipeline_profiles (
                id, name, agents_json, coordination, created_at
            ) VALUES (?, ?, ?, ?, ?)""",
            (profile_id, name, encode_json(agents), coordination.value, now),
        )

        return PipelineProfile(
            id=profile_id,
            name=name,
            agents=[AgentProfile(**a) for a in agents],
            coordination=coordination,
        )

    def get_profile(self, profile_name: str) -> PipelineProfile | None:
        """Get a pipeline profile by name."""
        row = self._db.fetch_one(
            "SELECT * FROM pipeline_profiles WHERE name = ?", (profile_name,)
        )
        if not row:
            return None

        return PipelineProfile(
            id=row["id"],
            name=row["name"],
            agents=[AgentProfile(**a) for a in decode_json(row["agents_json"])],
            coordination=CoordinationMode(row["coordination"]),
        )

    def spawn_agent(self, request: AgentSpawnRequest) -> AgentSpawnResponse:
        """Spawn a sub-agent with isolated context."""
        agent_id = request.agent_id or f"agent_{uuid.uuid4().hex[:8]}"
        now = datetime.now(UTC)

        # Store agent state
        self._active_agents[agent_id] = {
            "id": agent_id,
            "role": request.role,
            "agent_type": request.agent_type or AgentType.WORKER,
            "context": request.context or {},
            "tools": request.tools or [],
            "status": AgentStatus.PENDING,
            "created_at": now,
            "parent_id": request.parent_id,
        }

        # Persist to database
        self._db.execute(
            """INSERT INTO agents (
                id, role, agent_type, context_json, tools_json, status,
                parent_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                agent_id,
                request.role,
                request.agent_type or AgentType.WORKER,
                encode_json(request.context or {}),
                encode_json(request.tools or {}),
                AgentStatus.PENDING.value,
                request.parent_id,
                now.isoformat(),
            ),
        )

        # Execute spawn callbacks (for OpenClaw integration)
        for callback in self._spawn_callbacks:
            try:
                callback(agent_id, request)
            except Exception:
                pass  # Best effort

        return AgentSpawnResponse(
            agent_id=agent_id,
            role=request.role,
            agent_type=request.agent_type or AgentType.WORKER,
            status=AgentStatus.PENDING,
            created_at=now,
        )

    def update_agent_status(
        self, agent_id: str, status: AgentStatus, result: str | None = None
    ) -> None:
        """Update agent status and optionally store result."""
        if agent_id in self._active_agents:
            self._active_agents[agent_id]["status"] = status
            if result:
                self._active_agents[agent_id]["result"] = result

        self._db.execute(
            "UPDATE agents SET status = ?, result = ? WHERE id = ?",
            (status.value, result, agent_id),
        )

    def get_agent(self, agent_id: str) -> AgentSpawnResponse | None:
        """Get agent by ID."""
        if agent_id in self._active_agents:
            agent = self._active_agents[agent_id]
            return AgentSpawnResponse(
                agent_id=agent["id"],
                role=agent["role"],
                agent_type=agent["agent_type"],
                status=agent["status"],
                created_at=agent["created_at"],
            )

        row = self._db.fetch_one("SELECT * FROM agents WHERE id = ?", (agent_id,))
        if not row:
            return None

        return AgentSpawnResponse(
            agent_id=row["id"],
            role=row["role"],
            agent_type=AgentType(row["agent_type"]),
            status=AgentStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def delegate_task(self, request: TaskDelegateRequest) -> TaskDelegateResponse:
        """Delegate a task to a sub-agent."""
        # Create spawn request
        spawn_req = AgentSpawnRequest(
            agent_id=request.agent_id,
            role=request.role,
            agent_type=request.agent_type or AgentType.WORKER,
            context=request.context,
            tools=request.tools,
            parent_id=request.parent_id,
        )
        spawn_resp = self.spawn_agent(spawn_req)

        return TaskDelegateResponse(
            agent_id=spawn_resp.agent_id,
            status=spawn_resp.status,
            delegated_at=datetime.now(UTC),
        )

    def execute_pipeline(
        self, request: PipelineExecuteRequest
    ) -> PipelineExecuteResponse:
        """Execute a multi-agent pipeline."""
        profile = self.get_profile(request.profile_name)
        if not profile:
            raise ValueError(f"Profile not found: {request.profile_name}")

        results: list[dict[str, Any]] = []
        start_time = datetime.now(UTC)

        if profile.coordination == CoordinationMode.SEQUENTIAL:
            # Sequential: Agent A → Agent B → Agent C
            for agent_def in profile.agents:
                spawn_req = AgentSpawnRequest(
                    role=agent_def.role,
                    agent_type=AgentType(agent_def.type),
                    context={"task": request.task, **agent_def.context},
                    parent_id=request.coordinator_id,
                )
                result = self.spawn_agent(spawn_req)
                results.append(
                    {
                        "agent": agent_def.role,
                        "result": result.model_dump(),
                    }
                )

        elif profile.coordination == CoordinationMode.PARALLEL:
            # Parallel: All agents execute simultaneously
            spawn_reqs = [
                AgentSpawnRequest(
                    role=agent_def.role,
                    agent_type=AgentType(agent_def.type),
                    context={"task": request.task, **agent_def.context},
                    parent_id=request.coordinator_id,
                )
                for agent_def in profile.agents
            ]
            for spawn_req in spawn_reqs:
                result = self.spawn_agent(spawn_req)
                results.append(
                    {
                        "agent": spawn_req.role,
                        "result": result.model_dump(),
                    }
                )

        elif profile.coordination == CoordinationMode.HIERARCHICAL:
            # Hierarchical: Coordinator manages workers
            coordinator = profile.agents[0]
            workers = profile.agents[1:]

            # Spawn coordinator
            coord_req = AgentSpawnRequest(
                role=coordinator.role,
                agent_type=AgentType(coordinator.type),
                context={"task": request.task, "workers": [w.role for w in workers]},
                parent_id=request.coordinator_id,
            )
            coord_result = self.spawn_agent(coord_req)
            results.append(
                {
                    "agent": coordinator.role,
                    "result": coord_result.model_dump(),
                }
            )

            # Spawn workers
            for worker in workers:
                worker_req = AgentSpawnRequest(
                    role=worker.role,
                    agent_type=AgentType(worker.type),
                    context={"task": request.task, "coordinator": coordinator.role},
                    parent_id=coord_result.agent_id,
                )
                worker_result = self.spawn_agent(worker_req)
                results.append(
                    {
                        "agent": worker.role,
                        "result": worker_result.model_dump(),
                    }
                )

        return PipelineExecuteResponse(
            pipeline_id=str(uuid.uuid4()),
            profile_name=request.profile_name,
            agents_spawned=len(results),
            results=results,
            executed_at=start_time,
        )

    def list_active_agents(
        self, parent_id: str | None = None
    ) -> list[AgentSpawnResponse]:
        """List active agents, optionally filtered by parent."""
        if parent_id:
            rows = self._db.fetch_all(
                "SELECT * FROM agents WHERE parent_id = ?", (parent_id,)
            )
        else:
            rows = self._db.fetch_all("SELECT * FROM agents")

        agents = []
        for row in rows:
            agents.append(
                AgentSpawnResponse(
                    agent_id=row["id"],
                    role=row["role"],
                    agent_type=AgentType(row["agent_type"]),
                    status=AgentStatus(row["status"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
            )
        return agents
