from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import (
    AgentRecord,
    EventCreateRequest,
    EventRecord,
    HealthResponse,
    MemoryLayerRecord,
    StatusResponse,
    TaskRecord,
    WorkspaceSnapshotResponse,
    WorkspaceSummary,
)
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

    @app.get("/api/agents", response_model=list[AgentRecord])
    def agents() -> list[AgentRecord]:
        return [AgentRecord(**agent) for agent in active_store.list_agents()]

    @app.get("/api/memory", response_model=list[MemoryLayerRecord])
    def memory_layers() -> list[MemoryLayerRecord]:
        return [MemoryLayerRecord(**layer) for layer in active_store.list_memory_layers()]

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
