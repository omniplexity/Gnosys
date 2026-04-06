from __future__ import annotations

from fastapi import FastAPI

from .models import HealthResponse, StatusResponse


def create_app() -> FastAPI:
    app = FastAPI(title="Gnosys Backend", version="0.1.0")

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    @app.get("/status", response_model=StatusResponse)
    def status() -> StatusResponse:
        return StatusResponse()

    @app.get("/workspace")
    def workspace() -> dict[str, str]:
        return {
            "name": "Gnosys",
            "mode": "scaffold",
            "surface": "desktop console",
        }

    return app


app = create_app()
