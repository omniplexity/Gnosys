from __future__ import annotations

import math
import re
from typing import Any

from gnosys_backend.config import AppConfig
from gnosys_backend.embeddings import EmbeddingsProvider
from gnosys_backend.memory_store import MemoryStore
from gnosys_backend.models import (
    ContextItem,
    ContextRetrieveRequest,
    ContextRetrieveResponse,
    ContextTier,
    MemoryRecord,
)
from gnosys_backend.vector_store import VectorStore


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

DEFAULT_TIER_WEIGHTS: dict[ContextTier, float] = {
    "working": 1.0,
    "episodic": 0.8,
    "semantic": 0.6,
    "archive": 0.4,
}

CHARS_PER_TOKEN = 4


class ContextRetrievalStore:
    def __init__(
        self,
        memory_store: MemoryStore,
        vector_store: VectorStore,
        embeddings_provider: EmbeddingsProvider,
        config: AppConfig,
        tier_weights: dict[ContextTier, float] | None = None,
    ) -> None:
        self._memory_store = memory_store
        self._vector_store = vector_store
        self._embeddings = embeddings_provider
        self._config = config
        self._tier_weights = tier_weights or DEFAULT_TIER_WEIGHTS.copy()

    def retrieve(self, request: ContextRetrieveRequest) -> ContextRetrieveResponse:
        tiers_to_search = self._filter_requested_tiers(request.include_tiers)
        all_items: list[ContextItem] = []

        if self._embeddings.is_available():
            all_items = self._semantic_search_all_tiers(request.query, tiers_to_search)
        else:
            all_items = self._keyword_search_all_tiers(request.query, tiers_to_search)

        all_items = self._apply_tier_weights(all_items)

        all_items.sort(key=lambda x: (-x.blended_score, -x.score))

        selected_items, used_tokens, dropped = self._budget_selection(
            all_items, request.max_tokens
        )

        assembly_text = self._build_assembly_text(selected_items)

        return ContextRetrieveResponse(
            query=request.query,
            items=selected_items,
            tiers_included=self._extract_tiers(selected_items),
            token_budget=request.max_tokens,
            used_tokens=used_tokens,
            remaining_tokens=max(0, request.max_tokens - used_tokens),
            truncated=len(dropped) > 0,
            dropped_count=len(dropped),
            assembly_text=assembly_text,
        )

    def _filter_requested_tiers(
        self, include_tiers: list[ContextTier]
    ) -> list[ContextTier]:
        tier_order = ["working", "episodic", "semantic", "archive"]
        return sorted(include_tiers, key=lambda t: tier_order.index(t))

    def _semantic_search_all_tiers(
        self, query: str, tiers: list[ContextTier]
    ) -> list[ContextItem]:
        query_embedding = self._embeddings.embed(query)
        items: list[ContextItem] = []

        for tier in tiers:
            tier_memories = self._get_tier_memories(tier)
            memory_ids = [m.id for m in tier_memories]

            if not memory_ids:
                continue

            vector_results = self._vector_store.search_similar(
                query_vector=query_embedding,
                limit=self._config.retention.default_search_limit,
                memory_ids=memory_ids,
            )

            tier_items = self._build_context_items_from_vector_search(
                query, tier, tier_memories, vector_results
            )
            items.extend(tier_items)

        return items

    def _keyword_search_all_tiers(
        self, query: str, tiers: list[ContextTier]
    ) -> list[ContextItem]:
        items: list[ContextItem] = []

        for tier in tiers:
            tier_memories = self._get_tier_memories(tier)
            memory_map = {m.id: m for m in tier_memories}

            search_response = self._memory_store.search_memories(
                query=query,
                tier=tier,
            )

            for rank, result in enumerate(search_response.results):
                memory = memory_map.get(result.memory.id)
                if memory is None:
                    continue

                est_tokens = self._estimate_token_count(memory)
                items.append(
                    ContextItem(
                        rank=rank + 1,
                        memory=memory,
                        score=float(result.score),
                        blended_score=float(result.score),
                        matched_keywords=result.matched_keywords,
                        estimated_tokens=est_tokens,
                    )
                )

        return items

    def _build_context_items_from_vector_search(
        self,
        query: str,
        tier: ContextTier,
        tier_memories: list[MemoryRecord],
        vector_results: list[dict[str, Any]],
    ) -> list[ContextItem]:
        memory_map = {m.id: m for m in tier_memories}
        memory_keyword_scores = self._get_keyword_scores(query, tier_memories)
        items: list[ContextItem] = []

        for rank, result in enumerate(vector_results):
            memory = memory_map.get(result["memory_id"])
            if memory is None:
                continue

            semantic_score = result.get("similarity", 0.0)
            keyword_score = memory_keyword_scores.get(memory.id, 0.0)
            blended = self._blend_scores(semantic_score, keyword_score)

            est_tokens = self._estimate_token_count(memory)
            items.append(
                ContextItem(
                    rank=rank + 1,
                    memory=memory,
                    score=semantic_score,
                    blended_score=blended,
                    matched_keywords=[],
                    estimated_tokens=est_tokens,
                )
            )

        return items

    def _get_keyword_scores(
        self, query: str, memories: list[MemoryRecord]
    ) -> dict[str, float]:
        tokens = TOKEN_PATTERN.findall(query.lower())
        if not tokens:
            return {}

        scores: dict[str, float] = {}
        for memory in memories:
            keywords = set(
                TOKEN_PATTERN.findall(
                    f"{memory.content} {' '.join(memory.tags)} {memory.memory_type}".lower()
                )
            )
            matched = sum(1 for t in tokens if t in keywords)
            scores[memory.id] = float(matched * 10) + (
                50 if query.lower() in memory.content.lower() else 0
            )
        return scores

    def _get_tier_memories(self, tier: ContextTier) -> list[MemoryRecord]:
        limit = self._config.retention.default_search_limit * 2

        search_result = self._memory_store.search_memories(
            query="",
            tier=tier,
            limit=limit,
        )
        memories = [r.memory for r in search_result.results]

        if not memories:
            search_result = self._memory_store.search_memories(
                query="*",
                tier=tier,
                limit=limit,
            )
            memories = [r.memory for r in search_result.results]

        return memories

    def _apply_tier_weights(self, items: list[ContextItem]) -> list[ContextItem]:
        for item in items:
            tier_weight = self._tier_weights.get(item.memory.tier, 0.5)
            if item.blended_score is not None:
                item.blended_score = item.blended_score * tier_weight
        return items

    def _blend_scores(self, semantic_score: float, keyword_score: float) -> float:
        semantic_weight = 0.7
        keyword_weight = 0.3
        return (semantic_score * semantic_weight) + (keyword_score * keyword_weight)

    def _estimate_token_count(self, memory: MemoryRecord) -> int:
        content_tokens = math.ceil(len(memory.content) / CHARS_PER_TOKEN)

        metadata_text = f"{memory.memory_type} {memory.tier} {' '.join(memory.tags)}"
        metadata_tokens = math.ceil(len(metadata_text) / CHARS_PER_TOKEN)

        return content_tokens + metadata_tokens

    def _budget_selection(
        self, items: list[ContextItem], max_tokens: int
    ) -> tuple[list[ContextItem], int, list[ContextItem]]:
        selected: list[ContextItem] = []
        used_tokens = 0
        dropped: list[ContextItem] = []

        for item in items:
            if used_tokens + item.estimated_tokens > max_tokens:
                dropped.append(item)
                continue

            selected.append(item)
            used_tokens += item.estimated_tokens

        return selected, used_tokens, dropped

    def _build_assembly_text(self, items: list[ContextItem]) -> str:
        if not items:
            return ""

        parts: list[str] = []
        for item in items:
            tier_label = f"[{item.memory.tier.upper()}]"
            parts.append(f"{tier_label} {item.memory.content}")

        return "\n\n".join(parts)

    def _extract_tiers(self, items: list[ContextItem]) -> list[ContextTier]:
        tiers = set(item.memory.tier for item in items)
        tier_order = ["working", "episodic", "semantic", "archive"]
        return sorted(tiers, key=lambda t: tier_order.index(t))
