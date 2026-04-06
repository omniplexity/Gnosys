from __future__ import annotations

from fastapi.testclient import TestClient

from gnosys_backend.app import create_app


def test_health_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_status_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "gnosys-backend"
    assert payload["mode"] == "scaffold"
