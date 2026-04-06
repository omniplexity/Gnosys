from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from gnosys_backend.app import create_app
from gnosys_backend.store import GnosysStore


def build_client(tmp_path: Path) -> TestClient:
    store = GnosysStore(path=tmp_path / "gnosys.sqlite3")
    app = create_app(store=store)
    return TestClient(app)


def test_health_endpoint(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_workspace_snapshot_has_seeded_state(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.get("/api/state")

    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace"]["name"] == "Gnosys"
    assert payload["counts"]["tasks"] >= 3
    assert payload["counts"]["events"] >= 1


def test_event_append_persists_to_log(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    post_response = client.post(
        "/api/events",
        json={
            "type": "task.updated",
            "source": "planner",
            "payload": {"task_id": "task-001", "status": "Running"},
        },
    )

    assert post_response.status_code == 201

    get_response = client.get("/api/events?limit=5")
    assert get_response.status_code == 200
    events = get_response.json()
    assert events[0]["type"] == "task.updated"
    assert events[0]["payload"]["task_id"] == "task-001"
