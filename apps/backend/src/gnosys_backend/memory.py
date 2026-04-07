from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .store import GnosysStore, utc_now


ROLE_LAYER_BIAS: dict[str, list[str]] = {
    "orchestrator": ["Active Context", "Episodic", "Semantic"],
    "planner": ["Episodic", "Semantic", "Active Context"],
    "memory_steward": ["Semantic", "Episodic", "Active Context"],
    "critic": ["Semantic", "Episodic", "Active Context"],
}

ROLE_SCOPE_PRIORITY: dict[str, list[str]] = {
    "orchestrator": ["session", "project", "workspace", "user"],
    "planner": ["project", "workspace", "session", "user"],
    "memory_steward": ["workspace", "project", "session", "user"],
    "critic": ["workspace", "project", "session", "user"],
}


def tokenize(query: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", query.lower()) if len(token) > 1]


@dataclass(slots=True)
class MemoryRetrievalResult:
    query: str
    scope: str | None
    role: str
    items: list[dict[str, Any]]
    trace: list[dict[str, str]]


class MemoryEngine:
    def __init__(self, store: GnosysStore) -> None:
        self.store = store

    def retrieve(
        self,
        *,
        query: str,
        role: str,
        scope: str | None = None,
        project_id: str | None = None,
        limit: int = 5,
    ) -> MemoryRetrievalResult:
        tokens = tokenize(query)
        normalized_role = role.lower()
        active_bias = ROLE_LAYER_BIAS.get(normalized_role, ROLE_LAYER_BIAS["orchestrator"])
        scope_priority = ROLE_SCOPE_PRIORITY.get(normalized_role, ROLE_SCOPE_PRIORITY["orchestrator"])
        candidates = self.store.list_memory_items(limit=100, scope=scope, project_id=project_id)

        scored = [self._score_candidate(item, tokens, active_bias, scope_priority, scope, project_id) for item in candidates]
        scored.sort(key=lambda candidate: candidate["score"], reverse=True)
        selected = scored[:limit]

        trace = [
            {
                "stage": "normalize",
                "detail": f"Tokens: {', '.join(tokens) if tokens else 'none'}",
            },
            {
                "stage": "scope",
                "detail": f"Scope filter: {scope or 'all'}",
            },
            {
                "stage": "project",
                "detail": f"Project filter: {project_id or 'all'}",
            },
            {
                "stage": "role-bias",
                "detail": f"Role {normalized_role} prioritizes {', '.join(active_bias)}",
            },
            {
                "stage": "ranking",
                "detail": f"Ranked {len(scored)} memory items and returned {len(selected)}",
            },
        ]

        results = []
        for item in selected:
            self.store.touch_memory_item(item["id"])
            results.append(
                {
                    "id": item["id"],
                    "layer": item["layer"],
                    "scope": item["scope"],
                    "state": item["state"],
                    "title": item["title"],
                    "summary": item["summary"],
                    "content": item["content"],
                    "provenance": item["provenance"],
                    "source_ref": item["source_ref"],
                    "confidence": item["confidence"],
                    "freshness": item["freshness"],
                    "tags": item["tags"],
                    "created_at": item["created_at"],
                    "updated_at": item["updated_at"],
                    "last_accessed_at": item["last_accessed_at"],
                    "score": round(item["score"], 4),
                    "reason": item["reason"],
                }
            )

        self.store.record_event(
            event_type="memory.retrieval",
            source="memory-engine",
            payload={
                "query": query,
                "role": normalized_role,
                "scope": scope,
                "result_count": len(results),
            },
        )

        return MemoryRetrievalResult(query=query, scope=scope, role=normalized_role, items=results, trace=trace)

    def ingest(
        self,
        *,
        title: str,
        summary: str,
        content: str,
        provenance: str,
        source_ref: str,
        layer: str = "Semantic",
        scope: str = "workspace",
        confidence: float = 0.7,
        freshness: float = 0.7,
        tags: list[str] | None = None,
        state: str = "candidate",
        project_id: str | None = None,
    ) -> dict[str, Any]:
        item_id = f"memory-item-{utc_now().replace(':', '').replace('-', '').replace('T', '').replace('Z', '')}"
        item = self.store.upsert_memory_item(
            {
                "id": item_id,
                "layer": layer,
                "scope": scope,
                "state": state,
                "title": title,
                "summary": summary,
                "content": content,
                "provenance": provenance,
                "source_ref": source_ref,
                "confidence": confidence,
                "freshness": freshness,
                "tags": tags or [],
                "project_id": project_id,
            }
        )
        self.store.record_event(
            event_type="memory.ingest",
            source="memory-engine",
            payload={"memory_item_id": item["id"], "state": item["state"], "title": item["title"]},
        )
        return item

    def consolidate(self) -> dict[str, Any]:
        items = self.store.list_memory_items(limit=1000)
        by_signature: dict[str, dict[str, Any]] = {}
        promoted = 0
        archived = 0

        for item in items:
            signature = self._signature(item)
            existing = by_signature.get(signature)
            if existing is None:
                by_signature[signature] = item
                continue

            winner = self._choose_winner(existing, item)
            loser = item if winner["id"] == existing["id"] else existing
            by_signature[signature] = winner

            if loser["state"] != "archived":
                self.store.update_memory_item_state(loser["id"], "archived")
                archived += 1

        for item in by_signature.values():
            if item["state"] == "candidate" and item["confidence"] >= 0.9 and item["freshness"] >= 0.8:
                self.store.update_memory_item_state(item["id"], "validated")
                promoted += 1

        self.store.record_event(
            event_type="memory.consolidate",
            source="memory-engine",
            payload={
                "promoted": promoted,
                "archived": archived,
                "reviewed": len(items),
            },
        )
        return {"reviewed": len(items), "promoted": promoted, "archived": archived}

    def _score_candidate(
        self,
        item: dict[str, Any],
        tokens: list[str],
        active_bias: list[str],
        scope_priority: list[str],
        query_scope: str | None,
        project_id: str | None,
    ) -> dict[str, Any]:
        text_blob = " ".join([item["title"], item["summary"], item["content"], " ".join(item["tags"]) ]).lower()
        matches = sum(1 for token in tokens if token in text_blob)
        keyword_score = matches / max(len(tokens), 1) if tokens else 0.18
        confidence_score = float(item["confidence"]) * 0.4
        freshness_score = float(item["freshness"]) * 0.25
        state_bonus = {"validated": 0.25, "candidate": 0.08, "archived": -0.4}.get(item["state"], 0.0)
        layer_bonus = 0.12 if item["layer"] in active_bias else 0.0
        scope_bonus = 0.14 if query_scope and item["scope"] == query_scope else 0.0
        project_bonus = 0.12 if project_id and item.get("project_id") == project_id else 0.0
        scope_priority_bonus = 0.08 if item["scope"] == scope_priority[0] else 0.0
        recency_bonus = 0.05 if item.get("last_accessed_at") else 0.0
        score = keyword_score + confidence_score + freshness_score + state_bonus + layer_bonus + scope_bonus + project_bonus + scope_priority_bonus + recency_bonus

        reason_parts = [
            f"{matches} token matches",
            f"layer={item['layer']}",
            f"state={item['state']}",
            f"scope={item['scope']}",
            f"project={item.get('project_id') or 'none'}",
        ]

        return {
            **item,
            "score": score,
            "reason": ", ".join(reason_parts),
        }

    def _signature(self, item: dict[str, Any]) -> str:
        title = re.sub(r"[^a-z0-9]+", " ", item["title"].lower()).strip()
        summary = re.sub(r"[^a-z0-9]+", " ", item["summary"].lower()).strip()
        return f"{item['layer']}::{title}::{summary}"

    def _choose_winner(self, left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
        left_rank = (left["state"] == "validated", left["confidence"], left["freshness"])
        right_rank = (right["state"] == "validated", right["confidence"], right["freshness"])
        return right if right_rank > left_rank else left
