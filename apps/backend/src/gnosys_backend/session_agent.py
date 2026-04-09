from __future__ import annotations

from pathlib import Path
import re
from typing import Any


ACTION_PATTERNS = (
    "build",
    "implement",
    "create",
    "update",
    "refactor",
    "ship",
    "write",
    "plan",
    "research",
    "investigate",
    "compare",
    "analyze",
    "audit",
    "review",
    "test",
    "fix",
    "run",
    "schedule",
    "automate",
)


def should_execute(content: str) -> bool:
    normalized = content.strip().lower()
    if not normalized:
        return False
    if normalized.endswith("?") and not any(pattern in normalized for pattern in ACTION_PATTERNS):
        return False
    return any(pattern in normalized for pattern in ACTION_PATTERNS)


def load_identity_bundle(session: dict[str, Any]) -> dict[str, str]:
    bundle: dict[str, str] = {}
    for key in ("agent_path", "soul_path", "identity_path", "heartbeat_path"):
        path_value = session.get(key)
        if not path_value:
            bundle[key] = ""
            continue
        file_path = Path(str(path_value))
        bundle[key] = file_path.read_text(encoding="utf-8") if file_path.exists() else ""
    return bundle


def update_heartbeat(
    session: dict[str, Any],
    *,
    latest_user_message: str,
    latest_assistant_message: str,
    task_run_id: str | None,
) -> None:
    heartbeat_path = session.get("heartbeat_path")
    if not heartbeat_path:
        return
    file_path = Path(str(heartbeat_path))
    lines = [
        "# HEARTBEAT",
        "",
        f"- last_user_message: {latest_user_message[:160]}",
        f"- last_assistant_message: {latest_assistant_message[:160]}",
        f"- last_task_run_id: {task_run_id or 'none'}",
    ]
    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_answer_message(
    *,
    session: dict[str, Any],
    content: str,
    recent_messages: list[dict[str, Any]],
    identity_bundle: dict[str, str],
    memory_items: list[dict[str, Any]],
) -> str:
    continuity = ""
    prior_user_messages = [message["content"] for message in recent_messages if message["role"] == "user"]
    if prior_user_messages:
        continuity = f"I’m continuing a persistent session with {len(prior_user_messages)} prior user message(s) in context. "

    identity_hint = ""
    identity_text = " ".join(
        text for text in (
            identity_bundle.get("agent_path", ""),
            identity_bundle.get("soul_path", ""),
            identity_bundle.get("identity_path", ""),
        )
        if text.strip()
    )
    identity_tokens = [token for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9 _-]{3,}", identity_text) if not token.startswith("#")]
    if identity_tokens:
        identity_hint = f"Session identity context is active through {identity_tokens[0][:80]}. "

    memory_hint = ""
    if memory_items:
        memory_titles = ", ".join(item["title"] for item in memory_items[:2])
        memory_hint = f"Relevant memory surfaced: {memory_titles}. "

    session_title = session.get("title", "this session")
    return (
        f"{continuity}{identity_hint}{memory_hint}"
        f"In {session_title}, I’m treating your message as a direct conversational request rather than a delegated work run. "
        f"My current answer is: {content.strip()}"
    )


def build_execution_message(
    *,
    session: dict[str, Any],
    identity_bundle: dict[str, str],
    memory_items: list[dict[str, Any]],
    task_run: dict[str, Any] | None,
    agent_runs: list[dict[str, Any]],
    approvals_required: list[str],
) -> str:
    memory_hint = ""
    if memory_items:
        memory_titles = ", ".join(item["title"] for item in memory_items[:2])
        memory_hint = f"I carried forward relevant memory from {memory_titles}. "

    identity_hint = ""
    if identity_bundle.get("identity_path", "").strip():
        identity_hint = "Session identity and continuity files were loaded before planning. "

    if task_run is None:
        return (
            f"{identity_hint}{memory_hint}"
            f"I understand the request in {session.get('title', 'this session')}, but it needs approval before I can execute it. "
            f"{approvals_required[0] if approvals_required else 'Approval has been requested.'}"
        )

    specialist_names: list[str] = []
    for run in agent_runs:
        name = str(run.get("agent_name", ""))
        if name and name != "Orchestrator" and name not in specialist_names:
            specialist_names.append(name)
    specialist_summary = ", ".join(specialist_names[:4]) if specialist_names else "the core specialist team"
    return (
        f"{identity_hint}{memory_hint}"
        f"I’ve turned this into a bounded work run in {session.get('title', 'this session')}. "
        f"Task run {task_run['id']} is {task_run['status'].lower()} and is currently routed through {specialist_summary}. "
        f"{task_run['summary']}"
    )
