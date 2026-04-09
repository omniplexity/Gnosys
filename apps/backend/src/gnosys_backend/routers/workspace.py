from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import AppServices, get_services
from ..models import HealthResponse, StatusResponse, WorkspaceSnapshotResponse, WorkspaceSummary


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@router.get("/status", response_model=StatusResponse)
def status() -> StatusResponse:
    return StatusResponse(mode="operational", note="Local persistence, event log, and autonomy policy are active")


@router.get("/workspace", response_model=WorkspaceSummary)
@router.get("/api/workspace", response_model=WorkspaceSummary)
def workspace(services: AppServices = Depends(get_services)) -> WorkspaceSummary:
    return WorkspaceSummary(**services.store.workspace_snapshot()["workspace"])


@router.get("/api/state", response_model=WorkspaceSnapshotResponse)
def state(services: AppServices = Depends(get_services)) -> WorkspaceSnapshotResponse:
    return WorkspaceSnapshotResponse(**services.store.workspace_snapshot())
