from __future__ import annotations

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
