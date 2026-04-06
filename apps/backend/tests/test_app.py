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


def test_state_includes_seeded_memory_items_and_runs(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.get("/api/state")

    assert response.status_code == 200
    payload = response.json()
    assert payload["counts"]["memory_items"] >= 3
    assert payload["counts"]["task_runs"] == 0
    assert payload["counts"]["agent_runs"] == 0
    assert any(item["state"] == "candidate" for item in payload["memory_items"])


def test_memory_retrieval_returns_trace_and_relevant_item(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.get("/api/memory/retrieve", params={"query": "persistence event log", "role": "orchestrator"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "orchestrator"
    assert payload["trace"][0]["stage"] == "normalize"
    assert payload["items"][0]["title"] == "Phase 1 completed"
    assert payload["items"][0]["score"] > 0


def test_memory_ingest_and_consolidate_flow(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    ingest_response = client.post(
        "/api/memory/items",
        json={
            "title": "Consolidation candidate",
            "summary": "A candidate memory that should be promoted.",
            "content": "A candidate memory that should be promoted once confidence is high enough.",
            "provenance": "test-suite",
            "source_ref": "tests/test_app.py",
            "layer": "Semantic",
            "scope": "workspace",
            "confidence": 0.95,
            "freshness": 0.91,
            "tags": ["memory", "candidate"],
            "state": "candidate",
        },
    )

    assert ingest_response.status_code == 201

    consolidate_response = client.post("/api/memory/consolidate")
    assert consolidate_response.status_code == 200
    consolidate_payload = consolidate_response.json()
    assert consolidate_payload["reviewed"] >= 4
    assert consolidate_payload["promoted"] >= 1

    items_response = client.get("/api/memory/items", params={"limit": 10})
    assert items_response.status_code == 200
    items = items_response.json()
    assert any(item["title"] == "Consolidation candidate" and item["state"] == "validated" for item in items)


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
