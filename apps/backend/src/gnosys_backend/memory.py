from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

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

PROMOTION_CONFIDENCE_THRESHOLD = 0.9
PROMOTION_FRESHNESS_THRESHOLD = 0.8
PINNED_BONUS = 0.22


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
                    "pinned": bool(item.get("pinned")),
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
        item_id = f"memory-item-{utc_now().replace(':', '').replace('-', '').replace('T', '').replace('Z', '')}-{uuid4().hex[:8]}"
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

    def pin(self, item_id: str) -> dict[str, Any]:
        item = self.store.pin_memory_item(item_id, True)
        self.store.record_event(
            event_type="memory.pinned",
            source="memory-engine",
            payload={"memory_item_id": item["id"], "state": item["state"], "pinned": item["pinned"]},
        )
        return item

    def forget(self, item_id: str) -> dict[str, Any]:
        item = self.store.forget_memory_item(item_id)
        self.store.record_event(
            event_type="memory.forgotten",
            source="memory-engine",
            payload={"memory_item_id": item["id"], "state": item["state"], "pinned": item["pinned"]},
        )
        return item

    def review_queue(self, *, limit: int = 25) -> dict[str, Any]:
        candidates = self.store.list_memory_items(limit=1000, state="candidate")
        contradictions = self.detect_contradictions(limit=1000)
        scored = [self._review_candidate(item) for item in candidates]
        scored.sort(key=lambda candidate: candidate["score"], reverse=True)
        selected = scored[:limit]
        contradiction_groups = {item["signature"]: item for item in contradictions}
        for item in selected:
            if item["signature"] in contradiction_groups:
                item["conflict_count"] = int(contradiction_groups[item["signature"]]["item_count"]) - 1
            if item["signature"] in contradiction_groups and item["recommended_action"] == "promote":
                item["recommended_action"] = "review"
                item["review_reason"] = f"Conflicts with {item['conflict_count']} other memory item(s)."
        return {
            "candidate_count": len(candidates),
            "pinned_count": len([item for item in self.store.list_memory_items(limit=1000) if item.get("pinned")]),
            "contradiction_count": len(contradictions),
            "items": selected,
            "contradictions": contradictions,
        }

    def browse(self, *, query: str | None = None, project_id: str | None = None, limit: int = 12) -> dict[str, Any]:
        items = self.store.list_memory_items(limit=500, project_id=project_id)
        filtered = [item for item in items if self._matches_query(item, query)]
        contradictions = self.detect_contradictions(limit=500)
        if query:
            filtered_ids = {item["id"] for item in filtered}
            contradictions = [
                contradiction
                for contradiction in contradictions
                if filtered_ids.intersection(contradiction["item_ids"])
                or query.lower() in contradiction["signature"].lower()
            ]

        ranked = sorted(filtered, key=self._browser_rank, reverse=True)
        daily_memories = [item for item in ranked if self._is_daily_memory(item)][:limit]
        long_term_memories = [item for item in ranked if self._is_long_term_memory(item)][:limit]
        pinned_memories = [item for item in ranked if item.get("pinned")][:limit]
        candidate_memories = [self._review_candidate(item) for item in ranked if item["state"] == "candidate"][:limit]

        self.store.record_event(
            event_type="memory.browser",
            source="memory-engine",
            payload={
                "query": query,
                "project_id": project_id,
                "result_count": len(filtered),
                "daily_count": len(daily_memories),
                "long_term_count": len(long_term_memories),
                "pinned_count": len(pinned_memories),
                "candidate_count": len(candidate_memories),
                "contradiction_count": len(contradictions),
            },
        )
        return {
            "query": query,
            "project_id": project_id,
            "total_count": len(filtered),
            "daily_memories": daily_memories,
            "long_term_memories": long_term_memories,
            "pinned_memories": pinned_memories,
            "candidate_memories": candidate_memories,
            "contradictions": contradictions[:limit],
        }

    def consolidate(self) -> dict[str, Any]:
        items = self.store.list_memory_items(limit=1000)
        by_signature: dict[str, list[dict[str, Any]]] = {}
        promoted = 0
        archived = 0
        contradictions = 0

        for item in items:
            signature = self._signature(item)
            by_signature.setdefault(signature, []).append(item)

        for signature, group in by_signature.items():
            if len(group) > 1:
                contradictions += 1
                winner = self._choose_winner(*group)
                pinned_group = [item for item in group if item.get("pinned")]
                if len(pinned_group) > 1:
                    continue
                for item in group:
                    if item["id"] != winner["id"] and item["state"] != "archived" and not item.get("pinned"):
                        self.store.forget_memory_item(item["id"])
                        archived += 1
            else:
                winner = group[0]
            if winner["state"] == "candidate" and winner["confidence"] >= PROMOTION_CONFIDENCE_THRESHOLD and winner["freshness"] >= PROMOTION_FRESHNESS_THRESHOLD:
                self.store.update_memory_item_state(winner["id"], "validated")
                promoted += 1

        self.store.record_event(
            event_type="memory.consolidate",
            source="memory-engine",
            payload={
                "promoted": promoted,
                "archived": archived,
                "reviewed": len(items),
                "contradictions": contradictions,
            },
        )
        return {"reviewed": len(items), "promoted": promoted, "archived": archived, "contradictions": contradictions}

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
        pinned_bonus = PINNED_BONUS if item.get("pinned") else 0.0
        score = keyword_score + confidence_score + freshness_score + state_bonus + layer_bonus + scope_bonus + project_bonus + scope_priority_bonus + recency_bonus + pinned_bonus

        reason_parts = [
            f"{matches} token matches",
            f"layer={item['layer']}",
            f"state={item['state']}",
            f"pinned={bool(item.get('pinned'))}",
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

    def _choose_winner(self, *items: dict[str, Any]) -> dict[str, Any]:
        if not items:
            raise ValueError("At least one item is required")
        winner = items[0]
        for candidate in items[1:]:
            winner_rank = (bool(winner.get("pinned")), winner["state"] == "validated", float(winner["confidence"]), float(winner["freshness"]))
            candidate_rank = (
                bool(candidate.get("pinned")),
                candidate["state"] == "validated",
                float(candidate["confidence"]),
                float(candidate["freshness"]),
            )
            if candidate_rank > winner_rank:
                winner = candidate
        return winner

    def _review_candidate(self, item: dict[str, Any]) -> dict[str, Any]:
        confidence = float(item["confidence"])
        freshness = float(item["freshness"])
        score = confidence * 0.5 + freshness * 0.3 + (0.12 if item.get("pinned") else 0.0)
        recommended_action = "review"
        review_reason = "Needs human review before promotion."

        if item.get("pinned"):
            recommended_action = "keep pinned"
            review_reason = "Pinned memories are protected from automatic forgetting."
        elif confidence >= PROMOTION_CONFIDENCE_THRESHOLD and freshness >= PROMOTION_FRESHNESS_THRESHOLD:
            recommended_action = "promote"
            review_reason = "Confidence and freshness exceed the promotion threshold."
        elif confidence < 0.6 or freshness < 0.6:
            recommended_action = "archive"
            review_reason = "Confidence or freshness is too low for durable promotion."

        return {
            **item,
            "score": round(score, 4),
            "recommended_action": recommended_action,
            "review_reason": review_reason,
            "signature": self._signature(item),
            "conflict_count": 0,
        }

    def detect_contradictions(self, *, limit: int = 1000) -> list[dict[str, Any]]:
        items = self.store.list_memory_items(limit=limit)
        grouped: dict[str, list[dict[str, Any]]] = {}
        for item in items:
            grouped.setdefault(self._signature(item), []).append(item)

        contradictions: list[dict[str, Any]] = []
        for signature, group in grouped.items():
            if len(group) < 2:
                continue
            winner = self._choose_winner(*group)
            pinned_items = [item for item in group if item.get("pinned")]
            contradictions.append(
                {
                    "signature": signature,
                    "item_count": len(group),
                    "item_ids": [item["id"] for item in group],
                    "item_titles": [item["title"] for item in group],
                    "item_states": [item["state"] for item in group],
                    "pinned_item_id": pinned_items[0]["id"] if len(pinned_items) == 1 else None,
                    "winner_item_id": winner["id"],
                    "recommended_resolution": "keep_pinned" if len(pinned_items) == 1 else "keep_highest_quality",
                    "reason": "Multiple memories share the same semantic signature and require a single durable winner.",
                }
            )
        return contradictions

    def _matches_query(self, item: dict[str, Any], query: str | None) -> bool:
        if not query or not query.strip():
            return True
        tokens = tokenize(query)
        haystack = " ".join([item["title"], item["summary"], item["content"], item["provenance"], item["source_ref"], " ".join(item["tags"])]).lower()
        return all(token in haystack for token in tokens)

    def _browser_rank(self, item: dict[str, Any]) -> tuple[float, float, float, str]:
        return (
            1.0 if item.get("pinned") else 0.0,
            float(item["confidence"]),
            float(item["freshness"]),
            str(item["updated_at"]),
        )

    def _is_daily_memory(self, item: dict[str, Any]) -> bool:
        tags = {tag.lower() for tag in item.get("tags", [])}
        provenance = str(item.get("provenance", "")).lower()
        title = str(item.get("title", "")).lower()
        return "daily" in tags or provenance == "daily-session-rollup" or title.startswith("daily memory")

    def _is_long_term_memory(self, item: dict[str, Any]) -> bool:
        if self._is_daily_memory(item):
            return False
        if item["state"] != "validated":
            return False
        return item["layer"] in {"Semantic", "Active Context", "Episodic"} or item["scope"] in {"workspace", "user", "session", "project"}
