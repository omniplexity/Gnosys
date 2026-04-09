from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import re
from typing import Any

from .memory import MemoryEngine
from .store import GnosysStore


PREFERENCE_PATTERNS = ("i want", "i prefer", "please", "should", "needs to")
STYLE_KEYWORDS = ("clean", "minimal", "organized", "professional", "structured", "modern", "focused")
GOAL_KEYWORDS = ("build", "implement", "ship", "create", "develop", "improve", "learn", "memory", "agent")


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [part.strip(" -") for part in parts if part.strip()]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        normalized = item.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(item)
    return ordered


class SessionLearningEngine:
    def __init__(self, store: GnosysStore, memory_engine: MemoryEngine) -> None:
        self.store = store
        self.memory_engine = memory_engine

    def should_reflect(self, messages: list[dict[str, Any]], *, task_run_created: bool) -> bool:
        user_messages = [message for message in messages if message["role"] == "user"]
        if task_run_created:
            return True
        return len(user_messages) >= 2 and len(messages) >= 4

    def reflect_session(self, *, session: dict[str, Any], messages: list[dict[str, Any]]) -> dict[str, Any]:
        recent_messages = messages[-8:]
        user_messages = [message for message in recent_messages if message["role"] == "user"]
        assistant_messages = [message for message in recent_messages if message["role"] == "assistant"]
        latest_user_text = " ".join(message["content"] for message in user_messages[-3:])

        preferences = _dedupe(
            sentence
            for message in user_messages
            for sentence in _sentences(message["content"])
            if any(pattern in sentence.lower() for pattern in PREFERENCE_PATTERNS)
        )[:4]
        working_style = _dedupe(
            sentence
            for message in user_messages
            for sentence in _sentences(message["content"])
            if any(keyword in sentence.lower() for keyword in STYLE_KEYWORDS)
        )[:4]
        recurring_goals = _dedupe(
            sentence
            for message in user_messages
            for sentence in _sentences(message["content"])
            if any(keyword in sentence.lower() for keyword in GOAL_KEYWORDS)
        )[:4]
        personal_context = _dedupe(
            sentence
            for message in user_messages
            for sentence in _sentences(message["content"])
            if "user" in sentence.lower() or "workflow" in sentence.lower() or "project" in sentence.lower()
        )[:3]

        role_counter = Counter(message["role"] for message in recent_messages)
        identity_refinements = []
        if working_style:
            identity_refinements.append(f"Prioritize a {working_style[0]} interaction style when responding in this session.")
        if recurring_goals:
            identity_refinements.append(f"Keep returning to the user goal: {recurring_goals[0]}")
        identity_refinements = identity_refinements[:3]

        summary = (
            f"Session reflection captured {len(user_messages)} user message(s) and {len(assistant_messages)} assistant reply/replies. "
            f"The current focus is {latest_user_text[:140] or 'maintaining continuity in the session'}."
        )

        reflection = self.store.create_session_reflection(
            chat_session_id=session["id"],
            summary=summary,
            user_preferences=preferences,
            working_style=working_style,
            recurring_goals=recurring_goals,
            personal_context=personal_context,
            identity_refinements=identity_refinements,
            source_message_ids=[message["id"] for message in recent_messages],
        )

        memory_items: list[dict[str, Any]] = []
        if preferences:
            memory_items.append(
                self.memory_engine.ingest(
                    title=f"Session preference · {session['title']}",
                    summary=preferences[0][:180],
                    content="\n".join(preferences),
                    provenance="session-reflection",
                    source_ref=reflection["id"],
                    layer="Semantic",
                    scope="session",
                    confidence=0.82,
                    freshness=0.88,
                    tags=["session", "preference"],
                    state="candidate",
                )
            )
        if recurring_goals:
            memory_items.append(
                self.memory_engine.ingest(
                    title=f"Session goal · {session['title']}",
                    summary=recurring_goals[0][:180],
                    content="\n".join(recurring_goals),
                    provenance="session-reflection",
                    source_ref=reflection["id"],
                    layer="Episodic",
                    scope="session",
                    confidence=0.8,
                    freshness=0.86,
                    tags=["session", "goal"],
                    state="candidate",
                )
            )

        proposals: list[dict[str, Any]] = []
        if working_style:
            proposals.append(
                self.store.create_identity_proposal(
                    chat_session_id=session["id"],
                    target_file="IDENTITY.md",
                    proposal_kind="working-style",
                    rationale="Recent user messages expressed clear interaction preferences.",
                    proposed_content=f"- Working style preference: {working_style[0]}",
                )
            )
        if identity_refinements:
            proposals.append(
                self.store.create_identity_proposal(
                    chat_session_id=session["id"],
                    target_file="SOUL.md",
                    proposal_kind="agent-refinement",
                    rationale="Reflection suggested a stable refinement to the master agent's ongoing posture.",
                    proposed_content=f"- Reflection refinement: {identity_refinements[0]}",
                )
            )

        self.store.record_event(
            event_type="session.reflection",
            source="session-learning",
            payload={
                "chat_session_id": session["id"],
                "reflection_id": reflection["id"],
                "memory_item_ids": [item["id"] for item in memory_items],
                "identity_proposal_ids": [proposal["id"] for proposal in proposals],
                "role_counts": dict(role_counter),
            },
        )
        return {
            "reflection": reflection,
            "memory_items": memory_items,
            "identity_proposals": proposals,
        }

    def create_daily_memory(self, *, session: dict[str, Any], messages: list[dict[str, Any]]) -> dict[str, Any]:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        user_messages = [message["content"] for message in messages if message["role"] == "user"][-4:]
        assistant_messages = [message["content"] for message in messages if message["role"] == "assistant"][-3:]
        summary = user_messages[-1][:180] if user_messages else f"Daily summary for {session['title']}"
        content_parts = [
            f"Session: {session['title']}",
            f"Date: {today}",
            "Recent user focus:",
            *[f"- {text[:180]}" for text in user_messages],
            "Recent assistant synthesis:",
            *[f"- {text[:180]}" for text in assistant_messages],
        ]
        item = self.memory_engine.ingest(
            title=f"Daily memory · {session['title']} · {today}",
            summary=summary,
            content="\n".join(content_parts),
            provenance="daily-session-rollup",
            source_ref=f"{session['id']}:{today}",
            layer="Episodic",
            scope="session",
            confidence=0.84,
            freshness=0.94,
            tags=["daily", "session", "rollup"],
            state="candidate",
        )
        self.store.record_event(
            event_type="session.daily_memory",
            source="session-learning",
            payload={"chat_session_id": session["id"], "memory_item_id": item["id"], "date": today},
        )
        return item
