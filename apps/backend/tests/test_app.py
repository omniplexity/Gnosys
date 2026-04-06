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


def test_state_includes_entity_collections(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.get("/api/state")

    assert response.status_code == 200
    payload = response.json()
    assert payload["counts"]["projects"] >= 2
    assert payload["counts"]["skills"] >= 2
    assert payload["counts"]["schedules"] >= 1
    assert payload["counts"]["memory_items"] >= 3
    assert payload["counts"]["task_runs"] == 0
    assert payload["counts"]["agent_runs"] == 0


def test_memory_retrieval_returns_trace_and_relevant_item(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.get("/api/memory/retrieve", params={"query": "persistence event log", "role": "orchestrator"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "orchestrator"
    assert payload["trace"][0]["stage"] == "normalize"
    assert payload["items"][0]["title"] == "Phase 1 completed"
    assert payload["items"][0]["score"] > 0


def test_orchestration_launch_creates_task_runs_and_workers(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.post(
        "/api/orchestration/launch",
        json={
            "objective": "Research the local persistence layer and build a bounded execution plan",
            "task_title": "Phase 3 orchestration",
            "task_summary": "Launch an inspectable agent run with bounded workers",
            "requested_by": "desktop",
            "mode": "Supervised",
            "priority": "High",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["task_run"]["status"] == "Running"
    assert payload["task_run"]["approval_required"] is False
    assert len(payload["agent_runs"]) >= 4
    assert any(run["run_kind"] == "worker" for run in payload["agent_runs"])

    state_response = client.get("/api/state")
    assert state_response.status_code == 200
    state_payload = state_response.json()
    assert state_payload["counts"]["task_runs"] == 1
    assert state_payload["counts"]["agent_runs"] >= len(payload["agent_runs"])


def test_orchestration_rejects_sensitive_objectives_with_approval_gate(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.post(
        "/api/orchestration/launch",
        json={
            "objective": "Delete the old runtime artifacts and publish the result",
            "task_title": "Sensitive operation",
            "task_summary": "Exercise the approval gate",
            "requested_by": "desktop",
            "mode": "Supervised",
            "priority": "Critical",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["task_run"]["approval_required"] is True
    assert payload["task_run"]["status"] == "Needs Approval"
    assert payload["approvals_required"]


def test_task_crud_workflow(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    create_response = client.post(
        "/api/tasks",
        json={"title": "CRUD task", "summary": "Task lifecycle", "status": "Inbox", "priority": "High"},
    )
    assert create_response.status_code == 201
    task = create_response.json()

    update_response = client.patch(
        f"/api/tasks/{task['id']}",
        json={"title": "CRUD task updated", "summary": "Task lifecycle updated", "status": "Running", "priority": "Critical"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "Running"

    delete_response = client.delete(f"/api/tasks/{task['id']}")
    assert delete_response.status_code == 204
    assert client.get(f"/api/tasks/{task['id']}").status_code == 404


def test_project_skill_schedule_crud_workflows(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    project = client.post(
        "/api/projects",
        json={"name": "CRUD project", "summary": "Project lifecycle", "status": "Planned", "owner": "Gnosys"},
    ).json()
    assert client.patch(
        f"/api/projects/{project['id']}",
        json={"name": "CRUD project updated", "summary": "Updated", "status": "Active", "owner": "Gnosys"},
    ).status_code == 200
    assert client.delete(f"/api/projects/{project['id']}").status_code == 204

    skill = client.post(
        "/api/skills",
        json={
            "name": "CRUD skill",
            "description": "Skill lifecycle",
            "scope": "workspace",
            "version": "1.0.0",
            "source_type": "authored",
            "status": "draft",
        },
    ).json()
    assert client.patch(
        f"/api/skills/{skill['id']}",
        json={
            "name": "CRUD skill updated",
            "description": "Updated skill",
            "scope": "project",
            "version": "1.0.1",
            "source_type": "learned",
            "status": "active",
        },
    ).status_code == 200
    assert client.delete(f"/api/skills/{skill['id']}").status_code == 204

    schedule = client.post(
        "/api/schedules",
        json={
            "name": "CRUD schedule",
            "target_type": "skill",
            "target_ref": "skill-001",
            "schedule_expression": "FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0",
            "timezone": "America/New_York",
            "enabled": True,
        },
    ).json()
    assert client.patch(
        f"/api/schedules/{schedule['id']}",
        json={
            "name": "CRUD schedule updated",
            "target_type": "task",
            "target_ref": "task-001",
            "schedule_expression": "FREQ=WEEKLY;BYDAY=TU;BYHOUR=10;BYMINUTE=0",
            "timezone": "America/New_York",
            "enabled": False,
        },
    ).status_code == 200
    assert client.delete(f"/api/schedules/{schedule['id']}").status_code == 204


def test_agent_crud_workflow(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    agent = client.post(
        "/api/agents",
        json={"name": "CRUD agent", "role": "Lifecycle", "status": "Idle"},
    ).json()
    assert client.patch(
        f"/api/agents/{agent['id']}",
        json={"name": "CRUD agent updated", "role": "Lifecycle updated", "status": "Working"},
    ).status_code == 200
    assert client.delete(f"/api/agents/{agent['id']}").status_code == 204
