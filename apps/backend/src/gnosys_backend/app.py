from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .deps import AppServices
from .memory import MemoryEngine
from .policy import PolicyEngine
from .routers import agents, approvals, chat, diagnostics, events, memory, orchestration, policy, projects, schedules, skills, tasks, workspace
from .runtime import OrchestrationEngine
from .services.approval_service import ApprovalService
from .services.replay_service import ReplayService
from .services.scheduler_service import ScheduleRunner, SchedulerService
from .services.skill_learning_service import SkillLearningService
from .session_learning import SessionLearningEngine
from .skills import SkillEngine
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
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    active_store = store or _build_store()
    active_store.initialize()
    memory_engine = MemoryEngine(active_store)
    session_learning = SessionLearningEngine(active_store, memory_engine)
    policy_engine = PolicyEngine(active_store)
    skill_engine = SkillEngine(active_store)
    orchestration_engine = OrchestrationEngine(active_store, skill_engine=skill_engine)
    skill_learning_service = SkillLearningService(active_store)

    scheduler_service = SchedulerService(active_store, orchestration_engine)
    replay_service = ReplayService(active_store)
    services = AppServices(
        store=active_store,
        memory_engine=memory_engine,
        session_learning=session_learning,
        orchestration_engine=orchestration_engine,
        policy_engine=policy_engine,
        skill_engine=skill_engine,
        skill_learning_service=skill_learning_service,
    )
    approval_service = ApprovalService(services)
    schedule_runner = ScheduleRunner(
        scheduler_service=scheduler_service,
        poll_interval_seconds=float(os.environ.get("GNOSYS_SCHEDULER_POLL_SECONDS", "5")),
    )
    services.scheduler_service = scheduler_service
    services.approval_service = approval_service
    services.replay_service = replay_service
    services.schedule_runner = schedule_runner
    app.state.services = services
    app.state.schedule_daemon = schedule_runner

    @app.on_event("startup")
    def _start_schedule_daemon() -> None:
        schedule_runner.prime_schedules()
        schedule_runner.start()

    @app.on_event("shutdown")
    def _stop_schedule_daemon() -> None:
        schedule_runner.stop()

    app.include_router(workspace.router)
    app.include_router(policy.router)
    app.include_router(approvals.router)
    app.include_router(tasks.router)
    app.include_router(agents.router)
    app.include_router(projects.router)
    app.include_router(chat.router)
    app.include_router(skills.router)
    app.include_router(schedules.router)
    app.include_router(memory.router)
    app.include_router(orchestration.router)
    app.include_router(diagnostics.router)
    app.include_router(events.router)
    return app


app = create_app()
