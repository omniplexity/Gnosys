from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from gnosys_backend.app import create_app
from gnosys_backend.memory import MemoryEngine
from gnosys_backend.runtime import OrchestrationEngine
from gnosys_backend.scheduler import ScheduleDaemon
from gnosys_backend.store import GnosysStore


class FailingOrchestrationEngine:
    def launch(self, **_: object) -> object:
        raise RuntimeError("Synthetic scheduler failure")


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
    assert payload["workspace"]["autonomy_mode"] == "Supervised"
    assert payload["workspace"]["kill_switch"] is False
    assert payload["counts"]["projects"] >= 2
    assert payload["counts"]["project_threads"] >= 1
    assert payload["counts"]["chat_sessions"] >= 1
    assert payload["counts"]["skills"] >= 2
    assert payload["counts"]["schedules"] >= 1
    assert payload["counts"]["memory_items"] >= 3
    assert payload["counts"]["task_runs"] == 0
    assert payload["counts"]["agent_runs"] == 0
    assert payload["counts"]["approval_requests"] == 0


def test_project_threads_and_chat_sessions_are_real_entities(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    project = client.get("/api/projects").json()[0]
    thread_response = client.post(
        "/api/project-threads",
        json={
            "project_id": project["id"],
            "title": "Docs workflow",
            "summary": "Track project documentation and file outputs.",
            "status": "Open",
        },
    )
    assert thread_response.status_code == 201
    thread = thread_response.json()
    assert Path(thread["context_path"]).exists()

    update_thread_response = client.patch(
        f"/api/project-threads/{thread['id']}",
        json={"title": "Docs workflow updated", "summary": "Updated summary", "status": "Paused"},
    )
    assert update_thread_response.status_code == 200
    assert update_thread_response.json()["status"] == "Paused"

    session_response = client.post(
        "/api/chat-sessions",
        json={"title": "Personal agent", "summary": "Main self-learning thread", "status": "Active"},
    )
    assert session_response.status_code == 201
    session = session_response.json()
    assert Path(session["context_path"]).exists()
    assert Path(session["agent_path"]).exists()
    assert Path(session["soul_path"]).exists()
    assert Path(session["identity_path"]).exists()
    assert Path(session["heartbeat_path"]).exists()

    update_session_response = client.patch(
        f"/api/chat-sessions/{session['id']}",
        json={"title": "Personal agent updated", "summary": "Updated summary", "status": "Paused"},
    )
    assert update_session_response.status_code == 200
    assert update_session_response.json()["status"] == "Paused"


def test_chat_session_messages_are_persistent_entities(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    session_response = client.post(
        "/api/chat-sessions",
        json={"title": "Persistent operator", "summary": "Main thread", "status": "Active"},
    )
    assert session_response.status_code == 201
    session = session_response.json()

    initial_messages = client.get(f"/api/chat-sessions/{session['id']}/messages")
    assert initial_messages.status_code == 200
    initial_payload = initial_messages.json()
    assert len(initial_payload) == 1
    assert initial_payload[0]["role"] == "assistant"
    assert initial_payload[0]["kind"] == "message"

    create_message = client.post(
        f"/api/chat-sessions/{session['id']}/messages",
        json={
            "role": "system",
            "kind": "event",
            "content": "A local test event was recorded for this session.",
            "metadata": {"event": "test.appended"},
        },
    )
    assert create_message.status_code == 201
    assert create_message.json()["metadata"]["event"] == "test.appended"

    updated_messages = client.get(f"/api/chat-sessions/{session['id']}/messages")
    assert updated_messages.status_code == 200
    updated_payload = updated_messages.json()
    assert len(updated_payload) == 2
    assert updated_payload[-1]["role"] == "system"
    assert updated_payload[-1]["kind"] == "event"


def test_chat_send_returns_direct_reply_for_conversational_prompts(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    session = client.post(
        "/api/chat-sessions",
        json={"title": "Master session", "summary": "Primary chat", "status": "Active"},
    ).json()

    send_response = client.post(
        f"/api/chat-sessions/{session['id']}/send",
        json={
            "content": "What do you already know about this session?",
            "selected_model": "GPT-5.4",
            "reasoning_strength": "medium",
            "requested_by": "tester",
        },
    )
    assert send_response.status_code == 201
    payload = send_response.json()
    assert payload["task_run"] is None
    assert payload["approval_request"] is None
    assert payload["decision"]["execution_mode"] == "answer-only"
    assert payload["decision"]["delegated_specialists"] == []
    assert payload["user_message"]["role"] == "user"
    assert payload["assistant_message"]["role"] == "assistant"
    assert "Master session" in payload["assistant_message"]["content"]

    messages = client.get(f"/api/chat-sessions/{session['id']}/messages").json()
    assert len(messages) == 3
    assert messages[1]["role"] == "user"
    assert messages[2]["role"] == "assistant"

    heartbeat = Path(session["heartbeat_path"]).read_text(encoding="utf-8")
    assert "What do you already know about this session?" in heartbeat


def test_chat_send_can_launch_bounded_work_from_session(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    session = client.post(
        "/api/chat-sessions",
        json={"title": "Execution session", "summary": "Primary chat", "status": "Active"},
    ).json()

    send_response = client.post(
        f"/api/chat-sessions/{session['id']}/send",
        json={
            "content": "Research the runtime and build a bounded plan for the next milestone",
            "selected_model": "GPT-5.4",
            "reasoning_strength": "high",
            "requested_by": "tester",
        },
    )
    assert send_response.status_code == 201
    payload = send_response.json()
    assert payload["task_run"] is not None
    assert payload["task_run"]["chat_session_id"] == session["id"]
    assert payload["decision"]["execution_mode"] == "task-created"
    assert "invoked_skills" in payload["decision"]
    assert isinstance(payload["decision"]["invoked_skills"], list)
    assert len(payload["decision"]["delegated_specialists"]) >= 1
    assert len(payload["agent_runs"]) >= 1
    assert len(payload["generated_messages"]) >= 2
    assert payload["generated_messages"][0]["kind"] == "event"
    assert payload["generated_messages"][1]["metadata"]["event"] == "orchestration.route"
    assert payload["assistant_message"]["task_run_id"] == payload["task_run"]["id"]

    state = client.get("/api/state").json()
    assert state["counts"]["task_runs"] == 1

    messages = client.get(f"/api/chat-sessions/{session['id']}/messages").json()
    assert any(message["role"] == "system" and message["kind"] == "event" for message in messages)
    assert any(message["task_run_id"] == payload["task_run"]["id"] for message in messages)


def test_chat_session_reflection_generates_memory_candidates_and_identity_proposals(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    session = client.post(
        "/api/chat-sessions",
        json={"title": "Learning session", "summary": "Primary chat", "status": "Active"},
    ).json()

    client.post(
        f"/api/chat-sessions/{session['id']}/messages",
        json={"role": "user", "kind": "message", "content": "I want Gnosys to stay clean, minimal, and organized."},
    )
    client.post(
        f"/api/chat-sessions/{session['id']}/messages",
        json={"role": "assistant", "kind": "message", "content": "I will keep the thread focused."},
    )

    reflect = client.post(f"/api/chat-sessions/{session['id']}/reflect")
    assert reflect.status_code == 201
    payload = reflect.json()
    assert payload["reflection"]["chat_session_id"] == session["id"]
    assert any("clean" in item.lower() for item in payload["reflection"]["working_style"])
    assert len(payload["memory_items"]) >= 1
    assert len(payload["identity_proposals"]) >= 1

    reflections = client.get(f"/api/chat-sessions/{session['id']}/reflections")
    assert reflections.status_code == 200
    assert len(reflections.json()) >= 1

    proposals = client.get(f"/api/chat-sessions/{session['id']}/identity-proposals")
    assert proposals.status_code == 200
    assert any(proposal["target_file"] == "IDENTITY.md" for proposal in proposals.json())


def test_chat_session_daily_memory_rollup_creates_candidate_memory(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    session = client.post(
        "/api/chat-sessions",
        json={"title": "Daily memory session", "summary": "Primary chat", "status": "Active"},
    ).json()

    client.post(
        f"/api/chat-sessions/{session['id']}/messages",
        json={"role": "user", "kind": "message", "content": "Implement the next milestone for persistent memory."},
    )
    client.post(
        f"/api/chat-sessions/{session['id']}/messages",
        json={"role": "assistant", "kind": "message", "content": "I will keep the execution bounded and persistent."},
    )

    daily_memory = client.post(f"/api/chat-sessions/{session['id']}/daily-memory")
    assert daily_memory.status_code == 201
    payload = daily_memory.json()
    assert payload["scope"] == "session"
    assert payload["layer"] == "Episodic"
    assert payload["state"] == "candidate"
    assert "Daily memory" in payload["title"]


def test_chat_send_auto_reflection_appends_reflection_message(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    session = client.post(
        "/api/chat-sessions",
        json={"title": "Auto reflection", "summary": "Primary chat", "status": "Active"},
    ).json()

    first = client.post(
        f"/api/chat-sessions/{session['id']}/send",
        json={"content": "I want the product to stay professional and minimal.", "requested_by": "tester"},
    )
    assert first.status_code == 201

    second = client.post(
        f"/api/chat-sessions/{session['id']}/send",
        json={"content": "Please keep the workflow organized and focused.", "requested_by": "tester"},
    )
    assert second.status_code == 201
    payload = second.json()
    assert any(message["kind"] == "reflection" for message in payload["generated_messages"])

    reflections = client.get(f"/api/chat-sessions/{session['id']}/reflections").json()
    assert len(reflections) >= 1


def test_chat_attachment_upload_routes_file_to_thread_context_and_send_uses_thread_mode(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    state = client.get("/api/state").json()
    project = state["projects"][0]
    thread = state["project_threads"][0]
    session = state["chat_sessions"][0]

    upload_response = client.post(
        f"/api/chat-sessions/{session['id']}/attachments",
        data={"mode": "project-thread", "project_id": project["id"], "project_thread_id": thread["id"]},
        files={"file": ("brief.txt", b"Project thread attachment", "text/plain")},
    )
    assert upload_response.status_code == 201
    attachment = upload_response.json()
    assert attachment["mode"] == "project-thread"
    assert attachment["project_thread_id"] == thread["id"]
    assert Path(attachment["storage_path"]).exists()
    assert thread["context_path"] in attachment["storage_path"]

    send_response = client.post(
        f"/api/chat-sessions/{session['id']}/send",
        json={
            "content": "Build the next milestone from the attached project brief",
            "requested_by": "tester",
            "mode": "project-thread",
            "project_id": project["id"],
            "project_thread_id": thread["id"],
            "attachment_ids": [attachment["id"]],
        },
    )
    assert send_response.status_code == 201
    payload = send_response.json()
    assert payload["task_run"]["project_id"] == project["id"]
    assert payload["task_run"]["project_thread_id"] == thread["id"]
    assert attachment["id"] in payload["assistant_message"]["metadata"]["attachment_ids"]


def test_orchestration_launch_persists_explicit_context_fields(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    state = client.get("/api/state").json()
    project = state["projects"][0]
    thread = state["project_threads"][0]
    session = state["chat_sessions"][0]

    project_run = client.post(
        "/api/orchestration/launch",
        json={
            "objective": "Plan project work",
            "task_title": "Project contextual run",
            "task_summary": "Run tied to project thread",
            "project_id": project["id"],
            "project_thread_id": thread["id"],
            "requested_by": "desktop",
            "mode": "Supervised",
            "priority": "High",
        },
    )
    assert project_run.status_code == 201
    project_payload = project_run.json()
    assert project_payload["task_run"]["project_id"] == project["id"]
    assert project_payload["task_run"]["project_thread_id"] == thread["id"]
    assert project_payload["task_run"]["chat_session_id"] is None

    chat_run = client.post(
        "/api/orchestration/launch",
        json={
            "objective": "Continue main conversation",
            "task_title": "Chat contextual run",
            "task_summary": "Run tied to chat session",
            "chat_session_id": session["id"],
            "requested_by": "desktop",
            "mode": "Supervised",
            "priority": "High",
        },
    )
    assert chat_run.status_code == 201
    chat_payload = chat_run.json()
    assert chat_payload["task_run"]["chat_session_id"] == session["id"]
    assert chat_payload["task_run"]["project_thread_id"] is None

    diagnostics_project = client.get(f"/api/diagnostics/runs?project_id={project['id']}")
    assert diagnostics_project.status_code == 200
    assert any(run["project_id"] == project["id"] for run in diagnostics_project.json()["task_runs"])

    diagnostics_thread = client.get(f"/api/diagnostics/runs?project_thread_id={thread['id']}")
    assert diagnostics_thread.status_code == 200
    assert all(run["project_thread_id"] == thread["id"] for run in diagnostics_thread.json()["task_runs"])

    diagnostics_session = client.get(f"/api/diagnostics/runs?chat_session_id={session['id']}")
    assert diagnostics_session.status_code == 200
    assert all(run["chat_session_id"] == session["id"] for run in diagnostics_session.json()["task_runs"])


def test_policy_endpoint_updates_autonomy_controls(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.get("/api/policy")
    assert response.status_code == 200
    assert response.json()["autonomy_mode"] == "Supervised"

    update_response = client.patch(
        "/api/policy",
        json={"autonomy_mode": "Manual", "kill_switch": True, "approval_bias": "manual"},
    )
    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["autonomy_mode"] == "Manual"
    assert payload["kill_switch"] is True

    state_response = client.get("/api/state")
    assert state_response.json()["workspace"]["autonomy_mode"] == "Manual"
    assert state_response.json()["workspace"]["kill_switch"] is True


def test_full_access_mode_bypasses_gates(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    client.patch("/api/policy", json={"autonomy_mode": "Full Access", "kill_switch": False})

    response = client.post(
        "/api/orchestration/launch",
        json={
            "objective": "Delete the old runtime artifacts and publish the result",
            "task_title": "Full access run",
            "task_summary": "Should bypass approvals in full access mode",
            "requested_by": "desktop",
            "mode": "Full Access",
            "priority": "Critical",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["task_run"]["approval_required"] is False
    assert client.get("/api/state").json()["workspace"]["autonomy_mode"] == "Full Access"


def test_manual_mode_gates_launch_requests(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    client.patch("/api/policy", json={"autonomy_mode": "Manual", "kill_switch": False})

    response = client.post(
        "/api/orchestration/launch",
        json={
            "objective": "Draft a small status note",
            "task_title": "Manual gated run",
            "task_summary": "Should be blocked by manual mode",
            "requested_by": "desktop",
            "mode": "Manual",
            "priority": "High",
        },
    )

    assert response.status_code == 423
    payload = response.json()
    assert payload["detail"]["message"] == "Approval required"
    assert payload["detail"]["decision"]["requires_approval"] is True
    assert payload["detail"]["approval_request"]["status"] == "pending"
    assert client.get("/api/state").json()["counts"]["approval_requests"] == 1


def test_memory_retrieval_returns_trace_and_relevant_item(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.get("/api/memory/retrieve", params={"query": "persistence event log", "role": "orchestrator"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "orchestrator"
    assert payload["trace"][0]["stage"] == "normalize"
    assert payload["items"][0]["title"] == "Phase 1 completed"
    assert payload["items"][0]["score"] > 0


def test_memory_browser_groups_daily_long_term_pinned_and_candidates(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    session = client.post(
        "/api/chat-sessions",
        json={"title": "Browser session", "summary": "Daily memory source", "status": "Active"},
    ).json()
    client.post(
        f"/api/chat-sessions/{session['id']}/messages",
        json={"role": "user", "kind": "message", "content": "Keep a daily record of my planning and preferences."},
    )
    daily_response = client.post(f"/api/chat-sessions/{session['id']}/daily-memory")
    assert daily_response.status_code == 201
    daily_item = daily_response.json()

    validated_response = client.post(
        "/api/memory/items",
        json={
            "title": "Long-term preference",
            "summary": "User prefers minimal and organized interfaces.",
            "content": "Validated preference for clean and organized interfaces.",
            "provenance": "reflection",
            "source_ref": "pref-001",
            "layer": "Semantic",
            "scope": "user",
            "confidence": 0.97,
            "freshness": 0.91,
            "tags": ["preference", "long-term"],
            "state": "validated",
        },
    )
    assert validated_response.status_code == 201
    validated_item = validated_response.json()
    assert client.post(f"/api/memory/items/{validated_item['id']}/pin").status_code == 200

    browser_response = client.get("/api/memory/browser", params={"limit": 50})
    assert browser_response.status_code == 200
    payload = browser_response.json()
    assert payload["total_count"] >= 2
    assert any(item["id"] == daily_item["id"] for item in payload["daily_memories"])
    assert any(item["id"] == validated_item["id"] for item in payload["long_term_memories"])
    assert any(item["id"] == validated_item["id"] for item in payload["pinned_memories"])
    assert any(item["id"] == daily_item["id"] for item in payload["candidate_memories"])


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
    assert payload["decision"]["execution_mode"] == "task-created"
    assert "invoked_skills" in payload["decision"]
    assert len(payload["decision"]["delegated_specialists"]) >= 2
    assert all("spawn_worker" in step for step in payload["steps"])
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

    assert response.status_code == 423
    payload = response.json()
    assert payload["detail"]["decision"]["requires_approval"] is True
    assert payload["detail"]["approval_request"]["action"] == "orchestration.launch"
    assert payload["detail"]["approval_request"]["status"] == "pending"


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
    assert delete_response.status_code == 423
    assert delete_response.json()["detail"]["approval_request"]["action"] == "task.delete"
    assert client.get(f"/api/tasks/{task['id']}").status_code == 200


def test_supervised_mode_gates_delete_workflows(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    task = client.post(
        "/api/tasks",
        json={"title": "Approval gate task", "summary": "Task lifecycle", "status": "Inbox", "priority": "High"},
    ).json()

    delete_response = client.delete(f"/api/tasks/{task['id']}")
    assert delete_response.status_code == 423
    payload = delete_response.json()
    assert payload["detail"]["decision"]["sensitivity"] == "critical"
    assert payload["detail"]["approval_request"]["action"] == "task.delete"
    assert client.get("/api/state").json()["counts"]["approval_requests"] == 1


def test_approving_request_replays_blocked_action(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    client.patch("/api/policy", json={"autonomy_mode": "Manual", "kill_switch": False})

    launch_response = client.post(
        "/api/orchestration/launch",
        json={
            "objective": "Delete the old runtime artifacts and publish the result",
            "task_title": "Approval replay run",
            "task_summary": "Should be replayed after approval",
            "requested_by": "desktop",
            "mode": "Manual",
            "priority": "Critical",
        },
    )
    assert launch_response.status_code == 423
    approval = launch_response.json()["detail"]["approval_request"]

    resolve_response = client.post(
        f"/api/approvals/{approval['id']}/resolve",
        json={"status": "approved", "resolved_by": "tester"},
    )
    assert resolve_response.status_code == 200
    assert resolve_response.json()["status"] == "approved"

    state = client.get("/api/state").json()
    assert state["counts"]["task_runs"] == 1
    assert state["counts"]["approval_requests"] == 1


def test_project_skill_schedule_crud_workflows(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    project = client.post(
        "/api/projects",
        json={"name": "CRUD project", "summary": "Project lifecycle", "status": "Planned", "owner": "Gnosys"},
    ).json()
    assert project["workspace_path"]
    assert Path(project["workspace_path"]).exists()
    assert client.patch(
        f"/api/projects/{project['id']}",
        json={"name": "CRUD project updated", "summary": "Updated", "status": "Active", "owner": "Gnosys"},
    ).status_code == 200
    assert client.delete(f"/api/projects/{project['id']}").status_code == 423

    skill = client.post(
        "/api/skills",
        json={
            "name": "CRUD skill",
            "description": "Skill lifecycle",
            "scope": "workspace",
            "version": "1.0.0",
            "source_type": "authored",
            "status": "draft",
            "project_id": project["id"],
        },
    ).json()
    assert skill["project_id"] == project["id"]
    assert client.patch(
        f"/api/skills/{skill['id']}",
        json={
            "name": "CRUD skill updated",
            "description": "Updated skill",
            "scope": "project",
            "version": "1.0.1",
            "source_type": "learned",
            "status": "active",
            "project_id": project["id"],
        },
    ).status_code == 200
    assert client.delete(f"/api/skills/{skill['id']}").status_code == 423

    schedule = client.post(
        "/api/schedules",
        json={
            "name": "CRUD schedule",
            "target_type": "skill",
            "target_ref": "skill-001",
            "schedule_expression": "FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0",
            "timezone": "America/New_York",
            "enabled": True,
            "project_id": project["id"],
        },
    ).json()
    assert schedule["project_id"] == project["id"]
    assert client.patch(
        f"/api/schedules/{schedule['id']}",
        json={
            "name": "CRUD schedule updated",
            "target_type": "task",
            "target_ref": "task-001",
            "schedule_expression": "FREQ=WEEKLY;BYDAY=TU;BYHOUR=10;BYMINUTE=0",
            "timezone": "America/New_York",
            "enabled": False,
            "project_id": project["id"],
        },
    ).status_code == 423
    assert client.delete(f"/api/schedules/{schedule['id']}").status_code == 423


def test_schedule_rejects_invalid_policy_values(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    failure_policy_response = client.post(
        "/api/schedules",
        json={
            "name": "Invalid failure policy",
            "target_type": "skill",
            "target_ref": "skill-001",
            "schedule_expression": "FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0",
            "timezone": "America/New_York",
            "enabled": True,
            "failure_policy": "retry_forever",
        },
    )
    assert failure_policy_response.status_code == 422

    approval_policy_response = client.post(
        "/api/schedules",
        json={
            "name": "Invalid approval policy",
            "target_type": "skill",
            "target_ref": "skill-001",
            "schedule_expression": "FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0",
            "timezone": "America/New_York",
            "enabled": True,
            "approval_policy": "always_prompt",
        },
    )
    assert approval_policy_response.status_code == 422


def test_updates_preserve_project_assignment_when_project_id_is_omitted(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    client.patch("/api/policy", json={"autonomy_mode": "Full Access", "kill_switch": False})

    task = client.post(
        "/api/tasks",
        json={
            "title": "Scoped task",
            "summary": "Assigned to a project",
            "status": "Inbox",
            "priority": "High",
            "project_id": "project-001",
        },
    ).json()

    task_response = client.patch(
        f"/api/tasks/{task['id']}",
        json={
            "title": "Scoped task updated",
            "summary": "Still assigned",
            "status": "Running",
            "priority": "Critical",
        },
    )
    assert task_response.status_code == 200
    assert task_response.json()["project_id"] == "project-001"

    skill = client.post(
        "/api/skills",
        json={
            "name": "Scoped skill",
            "description": "Assigned to a project",
            "scope": "workspace",
            "version": "1.0.0",
            "source_type": "authored",
            "status": "draft",
            "project_id": "project-001",
        },
    ).json()

    skill_response = client.patch(
        f"/api/skills/{skill['id']}",
        json={
            "name": "Scoped skill updated",
            "description": "Still assigned",
            "scope": "project",
            "version": "1.0.1",
            "source_type": "authored",
            "status": "active",
        },
    )
    assert skill_response.status_code == 200
    assert skill_response.json()["project_id"] == "project-001"

    schedule = client.post(
        "/api/schedules",
        json={
            "name": "Scoped schedule",
            "target_type": "skill",
            "target_ref": "skill-001",
            "schedule_expression": "FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0",
            "timezone": "America/New_York",
            "enabled": True,
            "project_id": "project-001",
        },
    ).json()

    schedule_response = client.patch(
        f"/api/schedules/{schedule['id']}",
        json={
            "name": "Scoped schedule updated",
            "target_type": "skill",
            "target_ref": "skill-001",
            "schedule_expression": "FREQ=WEEKLY;BYDAY=TU;BYHOUR=10;BYMINUTE=0",
            "timezone": "America/New_York",
            "enabled": True,
            "approval_policy": "inherit",
            "failure_policy": "retry_once",
            "last_run_at": None,
            "next_run_at": None,
        },
    )
    assert schedule_response.status_code == 200
    assert schedule_response.json()["project_id"] == "project-001"


def test_updates_can_clear_project_assignment_with_explicit_null(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    client.patch("/api/policy", json={"autonomy_mode": "Full Access", "kill_switch": False})

    task = client.post(
        "/api/tasks",
        json={
            "title": "Clearable task",
            "summary": "Assigned to a project",
            "status": "Inbox",
            "priority": "High",
            "project_id": "project-001",
        },
    ).json()

    task_response = client.patch(
        f"/api/tasks/{task['id']}",
        json={
            "title": "Clearable task updated",
            "summary": "Project removed",
            "status": "Running",
            "priority": "Critical",
            "project_id": None,
        },
    )
    assert task_response.status_code == 200
    assert task_response.json()["project_id"] is None

    skill = client.post(
        "/api/skills",
        json={
            "name": "Clearable skill",
            "description": "Assigned to a project",
            "scope": "workspace",
            "version": "1.0.0",
            "source_type": "authored",
            "status": "draft",
            "project_id": "project-001",
        },
    ).json()

    skill_response = client.patch(
        f"/api/skills/{skill['id']}",
        json={
            "name": "Clearable skill updated",
            "description": "Project removed",
            "scope": "workspace",
            "version": "1.0.1",
            "source_type": "authored",
            "status": "active",
            "project_id": None,
        },
    )
    assert skill_response.status_code == 200
    assert skill_response.json()["project_id"] is None

    schedule = client.post(
        "/api/schedules",
        json={
            "name": "Clearable schedule",
            "target_type": "skill",
            "target_ref": "skill-001",
            "schedule_expression": "FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0",
            "timezone": "America/New_York",
            "enabled": True,
            "project_id": "project-001",
        },
    ).json()

    schedule_response = client.patch(
        f"/api/schedules/{schedule['id']}",
        json={
            "name": "Clearable schedule updated",
            "target_type": "skill",
            "target_ref": "skill-001",
            "schedule_expression": "FREQ=WEEKLY;BYDAY=TU;BYHOUR=10;BYMINUTE=0",
            "timezone": "America/New_York",
            "enabled": False,
            "approval_policy": "inherit",
            "failure_policy": "retry_once",
            "last_run_at": None,
            "next_run_at": None,
            "project_id": None,
        },
    )
    assert schedule_response.status_code == 200
    assert schedule_response.json()["project_id"] is None


def test_skill_lifecycle_draft_test_promote_and_rollback(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    source_skill = client.get("/api/skills/skill-001").json()

    draft_response = client.post("/api/skills/skill-001/draft", params={"requested_by": "tester"})
    assert draft_response.status_code == 201
    draft = draft_response.json()
    assert draft["source_type"] == "learned"
    assert draft["status"] == "draft"
    assert draft["parent_skill_id"] == source_skill["id"]
    assert draft["version"] != source_skill["version"]

    test_response = client.post(
        f"/api/skills/{draft['id']}/test",
        json={
            "scenario": "Inspect SQLite state and event logs for consistency",
            "expected_outcome": "Provide a clear inspection summary with actionable results",
            "requested_by": "tester",
        },
    )
    assert test_response.status_code == 201
    test_run = test_response.json()
    assert test_run["skill_id"] == draft["id"]
    assert test_run["passed"] is True

    lifecycle_response = client.get(f"/api/skills/{draft['id']}/lifecycle")
    assert lifecycle_response.status_code == 200
    lifecycle = lifecycle_response.json()
    assert lifecycle["skill"]["id"] == draft["id"]
    assert lifecycle["lifecycle_state"] == "candidate"
    assert lifecycle["ready_for_promotion"] is True
    assert lifecycle["test_runs"][0]["id"] == test_run["id"]
    assert lifecycle["evidence"] == []

    promote_response = client.post(f"/api/skills/{draft['id']}/promote", params={"requested_by": "tester"})
    assert promote_response.status_code == 200
    promoted = promote_response.json()
    assert promoted["status"] == "active"
    assert promoted["promoted_from_skill_id"] == source_skill["id"]
    assert promoted["promotion_summary"]
    assert promoted["last_promoted_at"] is not None

    rollback_response = client.post(f"/api/skills/{draft['id']}/rollback", params={"requested_by": "tester"})
    assert rollback_response.status_code == 200
    restored = rollback_response.json()
    assert restored["id"] == source_skill["id"]
    assert restored["status"] == "active"
    assert restored["rollback_summary"]
    assert restored["last_rolled_back_at"] is not None

    archived_draft = client.get(f"/api/skills/{draft['id']}").json()
    assert archived_draft["status"] == "archived"
    assert archived_draft["rollback_summary"]


def test_skill_can_be_proposed_from_session_reflections(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    session = client.post(
        "/api/chat-sessions",
        json={"title": "Personal operator", "summary": "Persistent thread", "status": "Active"},
    ).json()

    client.post(
        f"/api/chat-sessions/{session['id']}/messages",
        json={"role": "user", "kind": "message", "content": "I want compact weekly planning and clear status summaries."},
    )
    reflect_response = client.post(f"/api/chat-sessions/{session['id']}/reflect")
    assert reflect_response.status_code == 201

    propose_response = client.post(
        f"/api/chat-sessions/{session['id']}/skills/propose",
        params={"requested_by": "tester"},
    )
    assert propose_response.status_code == 201
    skill = propose_response.json()
    assert skill["source_type"] == "learned"
    assert skill["status"] == "candidate"
    assert "Learned from Personal operator" in skill["description"]
    assert skill["provenance_summary"]
    assert skill["evidence_count"] >= 1


def test_skill_improve_creates_recursive_draft(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    source_skill = client.get("/api/skills/skill-001").json()
    test_response = client.post(
        "/api/skills/skill-001/test",
        json={
            "scenario": "Inspect SQLite state and event logs for consistency",
            "expected_outcome": "Provide a clear inspection summary with actionable results",
            "requested_by": "tester",
        },
    )
    assert test_response.status_code == 201

    improve_response = client.post("/api/skills/skill-001/improve", params={"requested_by": "tester"})
    assert improve_response.status_code == 201
    improved = improve_response.json()
    assert improved["source_type"] == "learned"
    assert improved["status"] == "draft"
    assert improved["parent_skill_id"] == source_skill["id"]
    assert improved["version"] != source_skill["version"]


def test_orchestration_invokes_matching_active_skills(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    skill_response = client.post(
        "/api/skills",
        json={
            "name": "Runtime Research Skill",
            "description": "Guide runtime research, milestone planning, and execution summaries.",
            "scope": "workspace",
            "version": "1.0.0",
            "source_type": "manual",
            "status": "active",
            "project_id": None,
        },
    )
    assert skill_response.status_code == 201

    response = client.post(
        "/api/orchestration/launch",
        json={
            "objective": "Research runtime planning and summarize the execution path for this milestone",
            "task_title": "Skill invocation run",
            "task_summary": "Should pick up an active matching skill",
            "requested_by": "desktop",
            "mode": "Supervised",
            "priority": "High",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert "Runtime Research Skill" in payload["decision"]["invoked_skills"]

    events = client.get("/api/events").json()
    assert any(
        event["type"] == "skill.invoked"
        and event["payload"].get("skill_name") == "Runtime Research Skill"
        and event["payload"].get("task_run_id") == payload["task_run"]["id"]
        for event in events
    )


def test_skill_learning_creates_candidate_skills_with_evidence(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    store = client.app.state.services.store

    for index in range(2):
        task = store.create_task(
            title=f"Research plan {index}",
            summary="Repeated research planning workflow",
            status="Completed",
            priority="High",
            project_id=None,
        )
        task_run = store.create_task_run(
            task_id=task["id"],
            objective="Research implementation planning and summarize the rollout path",
            requested_by="tester",
            mode="Full Access",
            status="Completed",
            summary="Completed repeated workflow",
            step_count=3,
            approval_required=False,
        )
        store.update_task_run(task_run["id"], status="Completed", completed=True, summary="Completed repeated workflow")
        planner = store.create_agent_run(
            agent_id=f"planner-{index}",
            agent_name="Planner",
            agent_role="Planner",
            run_kind="specialist",
            status="Completed",
            objective="Plan the work",
            summary="Planner completed",
            task_run_id=task_run["id"],
            parent_run_id=None,
            recursion_depth=0,
            child_count=0,
            budget_units=20,
            approval_required=False,
        )
        store.create_agent_run(
            agent_id=f"research-{index}",
            agent_name="Research Specialist",
            agent_role="Research",
            run_kind="specialist",
            status="Completed",
            objective="Research the implementation path",
            summary="Research completed",
            task_run_id=task_run["id"],
            parent_run_id=planner["id"],
            recursion_depth=1,
            child_count=0,
            budget_units=20,
            approval_required=False,
        )
        store.create_agent_run(
            agent_id=f"builder-{index}",
            agent_name="Builder Specialist",
            agent_role="Builder",
            run_kind="specialist",
            status="Completed",
            objective="Summarize the rollout path",
            summary="Builder completed",
            task_run_id=task_run["id"],
            parent_run_id=planner["id"],
            recursion_depth=1,
            child_count=0,
            budget_units=20,
            approval_required=False,
        )

    learn_response = client.post("/api/skills/learn", json={"limit": 10, "requested_by": "tester"})
    assert learn_response.status_code == 201
    payload = learn_response.json()
    assert payload["analyzed_runs"] >= 2
    assert payload["repeated_patterns"] >= 1
    assert len(payload["created_skills"]) >= 1

    learned_skill = payload["created_skills"][0]
    assert learned_skill["source_type"] == "learned"
    assert learned_skill["status"] == "candidate"
    assert learned_skill["evidence_count"] >= 2
    assert learned_skill["provenance_summary"]
    assert learned_skill["promotion_summary"]
    assert learned_skill["invocation_hints"]

    lifecycle = client.get(f"/api/skills/{learned_skill['id']}/lifecycle").json()
    assert len(lifecycle["evidence"]) >= 2
    assert lifecycle["evidence"][0]["pattern_signature"]
    assert lifecycle["evidence"][0]["task_run_id"] is not None


def test_orchestration_surfaces_candidate_skills_as_routing_hints(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    skill_response = client.post(
        "/api/skills",
        json={
            "name": "Research Planning Procedure",
            "description": "Candidate for research and planning summaries.",
            "scope": "workspace",
            "version": "0.1.0",
            "source_type": "learned",
            "status": "candidate",
            "project_id": None,
            "provenance_summary": "Derived from repeated research planning runs.",
            "invocation_hints": ["research", "planning", "Research Specialist"],
        },
    )
    assert skill_response.status_code == 201

    response = client.post(
        "/api/orchestration/launch",
        json={
            "objective": "Research the planning flow and summarize the next milestone",
            "task_title": "Candidate skill routing run",
            "task_summary": "Should surface candidate skills without activating them",
            "requested_by": "desktop",
            "mode": "Supervised",
            "priority": "High",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert "Research Planning Procedure" in payload["decision"]["candidate_skills"]
    assert payload["decision"]["routing_notes"]


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
    assert client.delete(f"/api/agents/{agent['id']}").status_code == 423


def test_project_scoped_memory_retrieval_uses_project_bias(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    client.post(
        "/api/memory/items",
        json={
            "title": "Workspace note",
            "summary": "Generic workspace memory",
            "content": "This item should not outrank the project scoped item for the same query.",
            "provenance": "test",
            "source_ref": "workspace-note",
            "layer": "Semantic",
            "scope": "workspace",
            "confidence": 0.8,
            "freshness": 0.8,
            "tags": ["workspace"],
        },
    )
    client.post(
        "/api/memory/items",
        json={
            "title": "Project note",
            "summary": "Scoped project memory",
            "content": "This item belongs to project-002 and should surface for that project query.",
            "provenance": "test",
            "source_ref": "project-note",
            "layer": "Semantic",
            "scope": "project",
            "project_id": "project-002",
            "confidence": 0.9,
            "freshness": 0.95,
            "tags": ["project"],
        },
    )

    response = client.get(
        "/api/memory/retrieve",
        params={"query": "project note", "role": "planner", "scope": "project", "project_id": "project-002"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["title"] == "Project note"
    assert payload["trace"][2]["stage"] == "project"


def test_entity_policy_overrides_workspace_policy(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    client.patch("/api/policy", json={"autonomy_mode": "Manual", "kill_switch": False})

    policy_response = client.patch(
        "/api/policies/entities/project/project-001",
        json={"autonomy_mode": "Full Access", "kill_switch": False, "approval_bias": "autonomous"},
    )
    assert policy_response.status_code == 200
    assert policy_response.json()["autonomy_mode"] == "Full Access"

    allowed = client.post(
        "/api/tasks",
        json={
            "title": "Project scoped task",
            "summary": "Allowed because the project policy is Full Access",
            "status": "Inbox",
            "priority": "High",
            "project_id": "project-001",
        },
    )
    assert allowed.status_code == 201

    blocked = client.post(
        "/api/tasks",
        json={
            "title": "Workspace gated task",
            "summary": "Blocked because it has no entity override",
            "status": "Inbox",
            "priority": "High",
            "project_id": "project-002",
        },
    )
    assert blocked.status_code == 423
    assert blocked.json()["detail"]["decision"]["policy_scope"] == "workspace"


def test_schedule_run_retry_and_replay(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    client.patch("/api/policy", json={"autonomy_mode": "Full Access", "kill_switch": False})

    run_response = client.post("/api/schedules/schedule-001/run", params={"requested_by": "scheduler"})
    assert run_response.status_code == 201
    first_run = run_response.json()
    assert first_run["status"] == "completed"
    assert first_run["task_run_id"] is not None

    retry_response = client.post(f"/api/schedule-runs/{first_run['id']}/retry", params={"requested_by": "scheduler"})
    assert retry_response.status_code == 201
    retry_run = retry_response.json()
    assert retry_run["attempt_number"] == first_run["attempt_number"] + 1
    assert retry_run["retry_of_run_id"] == first_run["id"]

    replay_response = client.get(f"/api/diagnostics/replay/{first_run['task_run_id']}")
    assert replay_response.status_code == 200
    replay = replay_response.json()
    assert replay["task_run"]["id"] == first_run["task_run_id"]
    assert len(replay["timeline"]) >= len(replay["events"])
    assert len(replay["schedule_runs"]) >= 1
    assert len(replay["events"]) >= 1


def test_schedule_approval_policy_requires_review(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    schedule = client.post(
        "/api/schedules",
        json={
            "name": "Approval-gated schedule",
            "target_type": "skill",
            "target_ref": "skill-001",
            "schedule_expression": "FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0",
            "timezone": "America/New_York",
            "enabled": True,
            "approval_policy": "require_approval",
            "failure_policy": "fail_fast",
        },
    ).json()

    run_response = client.post(f"/api/schedules/{schedule['id']}/run", params={"requested_by": "scheduler"})
    assert run_response.status_code == 423
    approval = run_response.json()["detail"]["approval_request"]

    resolve_response = client.post(
        f"/api/approvals/{approval['id']}/resolve",
        json={"status": "approved", "resolved_by": "tester"},
    )
    assert resolve_response.status_code == 200

    schedule_runs = client.get("/api/schedule-runs").json()["schedule_runs"]
    assert any(run["schedule_id"] == schedule["id"] for run in schedule_runs)


def test_memory_review_promotion_workflow(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    review_response = client.get("/api/memory/review")
    assert review_response.status_code == 200
    review = review_response.json()
    assert review["candidate_count"] >= 1
    candidate = review["items"][0]

    promote_response = client.post(f"/api/memory/items/{candidate['id']}/promote")
    assert promote_response.status_code == 200
    assert promote_response.json()["state"] == "validated"


def test_memory_governance_pin_and_forget_controls(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    item = client.post(
        "/api/memory/items",
        json={
            "title": "Governance candidate",
            "summary": "Memory control test",
            "content": "This item is used to validate pin and forget actions.",
            "provenance": "test",
            "source_ref": "governance-candidate",
            "layer": "Semantic",
            "scope": "workspace",
            "confidence": 0.72,
            "freshness": 0.74,
            "tags": ["governance"],
        },
    ).json()

    pinned = client.post(f"/api/memory/items/{item['id']}/pin")
    assert pinned.status_code == 200
    assert pinned.json()["pinned"] is True

    review = client.get("/api/memory/review").json()
    assert review["pinned_count"] >= 1

    forgotten = client.post(f"/api/memory/items/{item['id']}/forget")
    assert forgotten.status_code == 200
    assert forgotten.json()["state"] == "archived"
    assert forgotten.json()["pinned"] is False


def test_memory_consolidation_respects_pinned_items(tmp_path: Path) -> None:
    store = GnosysStore(path=tmp_path / "gnosys.sqlite3")
    store.initialize()
    engine = MemoryEngine(store)

    winner = store.upsert_memory_item(
        {
            "id": "memory-item-winner",
            "layer": "Semantic",
            "scope": "workspace",
            "state": "candidate",
            "pinned": True,
            "title": "Shared fact",
            "summary": "Pinned source of truth",
            "content": "Pinned source of truth for the same signature.",
            "provenance": "test",
            "source_ref": "winner",
            "confidence": 0.88,
            "freshness": 0.82,
            "tags": ["governance"],
            "project_id": None,
        }
    )
    loser = store.upsert_memory_item(
        {
            "id": "memory-item-loser",
            "layer": "Semantic",
            "scope": "workspace",
            "state": "candidate",
            "pinned": False,
            "title": "Shared fact",
            "summary": "Pinned source of truth",
            "content": "Competing copy with the same signature.",
            "provenance": "test",
            "source_ref": "loser",
            "confidence": 0.65,
            "freshness": 0.7,
            "tags": ["governance"],
            "project_id": None,
        }
    )

    result = engine.consolidate()

    assert result["contradictions"] >= 1
    assert store.get_memory_item(winner["id"]) is not None
    assert store.get_memory_item(winner["id"])["pinned"] is True
    assert store.get_memory_item(loser["id"]) is not None
    assert store.get_memory_item(loser["id"])["state"] == "archived"


def test_replay_includes_timeline_and_comparison(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    first = client.post(
        "/api/orchestration/launch",
        json={
            "objective": "Repeatable task for replay comparison",
            "task_title": "Replay task",
            "task_summary": "Replay task summary",
            "task_id": "task-001",
            "requested_by": "desktop",
            "mode": "Supervised",
            "priority": "High",
        },
    )
    assert first.status_code == 201

    second = client.post(
        "/api/orchestration/launch",
        json={
            "objective": "Repeatable task for replay comparison",
            "task_title": "Replay task",
            "task_summary": "Replay task summary updated",
            "task_id": "task-001",
            "requested_by": "desktop",
            "mode": "Supervised",
            "priority": "High",
        },
    )
    assert second.status_code == 201

    task_run_id = second.json()["task_run"]["id"]
    replay = client.get(f"/api/diagnostics/replay/{task_run_id}").json()
    assert replay["comparison"]["previous_task_run_id"] is not None
    assert replay["comparison"]["agent_run_count_delta"] >= 0
    assert replay["comparison"]["schedule_run_count_delta"] >= 0
    assert replay["comparison"]["timeline_entry_count_delta"] >= 0
    assert len(replay["timeline"]) >= 1


def test_diagnostics_run_search_filters_by_query_and_status(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    completed = client.post(
        "/api/orchestration/launch",
        json={
            "objective": "Diagnostics replay search alpha",
            "task_title": "Search alpha",
            "task_summary": "Search alpha summary",
            "requested_by": "desktop",
            "mode": "Full Access",
            "priority": "High",
        },
    )
    assert completed.status_code == 201

    client.post(
        "/api/orchestration/launch",
        json={
            "objective": "Diagnostics replay search beta",
            "task_title": "Search beta",
            "task_summary": "Search beta summary",
            "requested_by": "desktop",
            "mode": "Full Access",
            "priority": "High",
        },
    )

    diagnostics = client.get(
        "/api/diagnostics/runs",
        params={"query": "alpha", "status": "Running", "approval_required": False, "limit": 5},
    )
    assert diagnostics.status_code == 200
    payload = diagnostics.json()
    assert payload["filtered_count"] >= 1
    assert payload["metrics"]["total_task_runs"] >= payload["filtered_count"]
    assert all("alpha" in run["objective"].lower() for run in payload["task_runs"])


def test_schedule_daemon_executes_due_autonomous_schedule(tmp_path: Path) -> None:
    store = GnosysStore(path=tmp_path / "gnosys.sqlite3")
    store.initialize()
    schedule = store.create_schedule(
        name="Autonomous due schedule",
        target_type="skill",
        target_ref="skill-001",
        schedule_expression="FREQ=DAILY;BYHOUR=9;BYMINUTE=0",
        timezone="America/New_York",
        enabled=True,
        approval_policy="autonomous",
        failure_policy="retry_once",
        last_run_at="2026-04-05T13:00:00Z",
        next_run_at="2026-04-06T13:00:00Z",
    )

    daemon = ScheduleDaemon(store, OrchestrationEngine(store), poll_interval_seconds=0.01)
    processed = daemon.run_once()

    assert any(item["schedule_id"] == schedule["id"] for item in processed)
    run = store.list_schedule_runs(limit=5, schedule_id=schedule["id"])[0]
    updated = store.get_schedule(schedule["id"])
    assert run["status"] == "completed"
    assert updated is not None
    assert updated["last_run_at"] is not None
    assert updated["next_run_at"] is not None
    assert updated["next_run_at"] > run["created_at"]


def test_schedule_daemon_queues_approval_required_schedule(tmp_path: Path) -> None:
    store = GnosysStore(path=tmp_path / "gnosys.sqlite3")
    store.initialize()
    schedule = store.create_schedule(
        name="Approval-gated due schedule",
        target_type="skill",
        target_ref="skill-001",
        schedule_expression="FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0",
        timezone="America/New_York",
        enabled=True,
        approval_policy="require_approval",
        failure_policy="retry_once",
        last_run_at="2026-04-05T13:00:00Z",
        next_run_at="2026-04-06T13:00:00Z",
    )

    daemon = ScheduleDaemon(store, OrchestrationEngine(store), poll_interval_seconds=0.01)
    processed = daemon.run_once()

    assert any(item["schedule_id"] == schedule["id"] for item in processed)
    pending = store.list_schedule_runs(limit=5, schedule_id=schedule["id"])[0]
    approvals = store.list_approval_requests(limit=5)
    assert pending["status"] == "pending_approval"
    assert any(request["action"] == "schedule.run" and request["subject_ref"] == schedule["id"] for request in approvals)


def test_schedule_daemon_skips_due_schedule_with_active_run(tmp_path: Path) -> None:
    store = GnosysStore(path=tmp_path / "gnosys.sqlite3")
    store.initialize()
    schedule = store.create_schedule(
        name="Already running schedule",
        target_type="skill",
        target_ref="skill-001",
        schedule_expression="FREQ=DAILY;BYHOUR=9;BYMINUTE=0",
        timezone="America/New_York",
        enabled=True,
        approval_policy="autonomous",
        failure_policy="retry_once",
        last_run_at="2026-04-05T13:00:00Z",
        next_run_at="2026-04-06T13:00:00Z",
    )
    active_run = store.create_schedule_run(
        schedule_id=schedule["id"],
        schedule_name=schedule["name"],
        target_type=schedule["target_type"],
        target_ref=schedule["target_ref"],
        requested_by="scheduler",
        result_summary="Still executing the current due window.",
        status="running",
    )

    daemon = ScheduleDaemon(store, OrchestrationEngine(store), poll_interval_seconds=0.01)
    processed = daemon.run_once()

    assert processed == []
    schedule_runs = store.list_schedule_runs(limit=10, schedule_id=schedule["id"])
    assert len(schedule_runs) == 1
    assert schedule_runs[0]["id"] == active_run["id"]


def test_schedule_daemon_schedules_retry_backoff_instead_of_inline_retry(tmp_path: Path) -> None:
    store = GnosysStore(path=tmp_path / "gnosys.sqlite3")
    store.initialize()
    schedule = store.create_schedule(
        name="Failing retry-once schedule",
        target_type="skill",
        target_ref="skill-001",
        schedule_expression="FREQ=DAILY;BYHOUR=9;BYMINUTE=0",
        timezone="America/New_York",
        enabled=True,
        approval_policy="autonomous",
        failure_policy="retry_once",
        last_run_at="2026-04-05T13:00:00Z",
        next_run_at="2026-04-06T13:00:00Z",
    )

    daemon = ScheduleDaemon(store, FailingOrchestrationEngine(), poll_interval_seconds=0.01)
    processed = daemon.run_once()

    assert any(item["schedule_id"] == schedule["id"] for item in processed)
    schedule_runs = store.list_schedule_runs(limit=10, schedule_id=schedule["id"])
    assert len(schedule_runs) == 1
    first_run = schedule_runs[0]
    assert first_run["status"] == "failed"
    assert first_run["attempt_number"] == 1
    updated = store.get_schedule(schedule["id"])
    assert updated is not None
    assert updated["last_run_at"] == schedule["last_run_at"]
    assert updated["next_run_at"] is not None
    assert updated["next_run_at"] > first_run["completed_at"]


def test_schedule_daemon_executes_retry_after_backoff_window(tmp_path: Path) -> None:
    store = GnosysStore(path=tmp_path / "gnosys.sqlite3")
    store.initialize()
    schedule = store.create_schedule(
        name="Retry chain schedule",
        target_type="skill",
        target_ref="skill-001",
        schedule_expression="FREQ=DAILY;BYHOUR=9;BYMINUTE=0",
        timezone="America/New_York",
        enabled=True,
        approval_policy="autonomous",
        failure_policy="retry_once",
        last_run_at="2026-04-05T13:00:00Z",
        next_run_at="2026-04-06T13:00:00Z",
    )

    failing_daemon = ScheduleDaemon(store, FailingOrchestrationEngine(), poll_interval_seconds=0.01)
    failing_daemon.run_once()

    after_failure = store.get_schedule(schedule["id"])
    assert after_failure is not None
    assert after_failure["next_run_at"] is not None

    store.update_schedule(
        schedule["id"],
        name=after_failure["name"],
        target_type=after_failure["target_type"],
        target_ref=after_failure["target_ref"],
        schedule_expression=after_failure["schedule_expression"],
        timezone=after_failure["timezone"],
        enabled=after_failure["enabled"],
        approval_policy=after_failure["approval_policy"],
        failure_policy=after_failure["failure_policy"],
        last_run_at=after_failure["last_run_at"],
        next_run_at="2026-04-06T13:10:00Z",
        project_id=after_failure["project_id"],
    )

    daemon = ScheduleDaemon(store, OrchestrationEngine(store), poll_interval_seconds=0.01)
    processed = daemon.run_once()

    assert any(item["schedule_id"] == schedule["id"] for item in processed)
    schedule_runs = store.list_schedule_runs(limit=10, schedule_id=schedule["id"])
    retry_run = next(run for run in schedule_runs if run["attempt_number"] == 2)
    first_run = next(run for run in schedule_runs if run["attempt_number"] == 1)
    assert retry_run["status"] == "completed"
    assert retry_run["attempt_number"] == 2
    assert retry_run["retry_of_run_id"] == first_run["id"]


def test_retry_schedule_run_reuses_existing_active_retry(tmp_path: Path) -> None:
    store = GnosysStore(path=tmp_path / "gnosys.sqlite3")
    app = create_app(store=store)
    client = TestClient(app)
    client.patch("/api/policy", json={"autonomy_mode": "Full Access", "kill_switch": False})

    initial_response = client.post("/api/schedules/schedule-001/run", params={"requested_by": "scheduler"})
    assert initial_response.status_code == 201
    initial_run = initial_response.json()

    schedule = store.get_schedule(initial_run["schedule_id"])
    assert schedule is not None
    active_retry = store.create_schedule_run(
        schedule_id=schedule["id"],
        schedule_name=schedule["name"],
        target_type=schedule["target_type"],
        target_ref=schedule["target_ref"],
        requested_by="scheduler",
        result_summary="Retry already in progress.",
        retry_of_run_id=initial_run["id"],
        attempt_number=initial_run["attempt_number"] + 1,
        status="running",
    )

    retry_response = client.post(f"/api/schedule-runs/{initial_run['id']}/retry", params={"requested_by": "scheduler"})

    assert retry_response.status_code == 201
    assert retry_response.json()["id"] == active_retry["id"]
    schedule_runs = store.list_schedule_runs(limit=10, schedule_id=schedule["id"], retry_of_run_id=initial_run["id"])
    assert len(schedule_runs) == 1
