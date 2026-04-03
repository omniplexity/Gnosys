from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from gnosys_backend.app import create_app
from gnosys_backend.config import AppConfig, EmbeddingsConfig, RetentionConfig


def build_client(tmp_path: Path) -> TestClient:
    config = AppConfig(
        db_path=tmp_path / "gnosys.db",
        vectors_path=tmp_path / "vectors.db",
        host="127.0.0.1",
        port=8766,
        retention=RetentionConfig(
            episodic_days=7, archive_days=90, default_search_limit=10
        ),
        embeddings=EmbeddingsConfig(provider="disabled", dimension=384),
    )
    return TestClient(create_app(config))


def test_health_endpoint_reports_healthy(tmp_path: Path) -> None:
    with build_client(tmp_path) as client:
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["service"] == "gnosys-backend"


def test_store_search_and_stats_flow(tmp_path: Path) -> None:
    with build_client(tmp_path) as client:
        first = client.post(
            "/memories",
            json={
                "content": "Austin likes deterministic systems and local tooling.",
                "memory_type": "factual",
                "tier": "episodic",
                "tags": ["austin", "preferences"],
                "metadata": {"source": "manual"},
            },
        )
        second = client.post(
            "/memories",
            json={
                "content": "Use SQLite keyword search for the first Gnosys backend release.",
                "memory_type": "procedural",
                "tier": "semantic",
                "tags": ["sqlite", "search"],
            },
        )

        assert first.status_code == 200
        assert second.status_code == 200

        search = client.get("/memories/search", params={"q": "sqlite keyword search"})
        stats = client.get("/stats")

    assert search.status_code == 200
    search_payload = search.json()
    assert search_payload["count"] == 1
    assert search_payload["results"][0]["memory"]["memory_type"] == "procedural"
    assert search_payload["results"][0]["matched_keywords"] == [
        "keyword",
        "search",
        "sqlite",
    ]

    assert stats.status_code == 200
    stats_payload = stats.json()
    assert stats_payload["total_memories"] == 2
    assert stats_payload["counts_by_type"] == {"factual": 1, "procedural": 1}
    assert stats_payload["counts_by_tier"] == {"episodic": 1, "semantic": 1}


def test_retention_defaults_apply_to_episodic_memories(tmp_path: Path) -> None:
    with build_client(tmp_path) as client:
        response = client.post(
            "/memories",
            json={
                "content": "Recent session memory",
                "memory_type": "conversational",
                "tier": "episodic",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["memory"]["expires_at"] is not None


def test_get_memory_by_id(tmp_path: Path) -> None:
    with build_client(tmp_path) as client:
        create = client.post(
            "/memories",
            json={
                "content": "Memory for get-by-id test",
                "memory_type": "test",
                "tier": "semantic",
            },
        )
        memory_id = create.json()["memory"]["id"]

        get = client.get(f"/memories/{memory_id}")

    assert get.status_code == 200
    payload = get.json()
    assert payload["memory"]["id"] == memory_id
    assert payload["memory"]["content"] == "Memory for get-by-id test"
    assert payload["memory"]["memory_type"] == "test"


def test_get_memory_not_found(tmp_path: Path) -> None:
    with build_client(tmp_path) as client:
        get = client.get("/memories/00000000-0000-0000-0000-000000000000")

    assert get.status_code == 404


def test_delete_memory(tmp_path: Path) -> None:
    with build_client(tmp_path) as client:
        create = client.post(
            "/memories",
            json={
                "content": "Memory to be deleted",
                "memory_type": "test",
                "tier": "episodic",
            },
        )
        memory_id = create.json()["memory"]["id"]

        delete = client.delete(f"/memories/{memory_id}")

        get = client.get(f"/memories/{memory_id}")

    assert delete.status_code == 200
    assert delete.json()["deleted"] == memory_id
    assert delete.json()["success"] is True
    assert get.status_code == 404


def test_delete_memory_not_found(tmp_path: Path) -> None:
    with build_client(tmp_path) as client:
        delete = client.delete("/memories/00000000-0000-0000-0000-000000000000")

    assert delete.status_code == 404


def test_prune_expired_deletes_old_episodic(tmp_path: Path) -> None:
    from datetime import datetime, timedelta, timezone

    with build_client(tmp_path) as client:
        past_date = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
        client.post(
            "/memories",
            json={
                "content": "Old episodic memory",
                "memory_type": "test",
                "tier": "episodic",
                "created_at": past_date,
                "expires_at": past_date,
            },
        )

        stats_before = client.get("/stats").json()
        assert stats_before["total_memories"] == 1

    with build_client(tmp_path) as client:
        stats_after = client.get("/stats").json()
        assert stats_after["total_memories"] == 0


def test_prune_expired_deletes_old_archive(tmp_path: Path) -> None:
    from datetime import datetime, timedelta, timezone

    with build_client(tmp_path) as client:
        past_date = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
        client.post(
            "/memories",
            json={
                "content": "Old archive memory",
                "memory_type": "test",
                "tier": "archive",
                "created_at": past_date,
                "expires_at": past_date,
            },
        )

        stats_before = client.get("/stats").json()
        assert stats_before["total_memories"] == 1

    with build_client(tmp_path) as client:
        stats_after = client.get("/stats").json()
        assert stats_after["total_memories"] == 0


def test_prune_preserves_nonexpired(tmp_path: Path) -> None:
    with build_client(tmp_path) as client:
        client.post(
            "/memories",
            json={
                "content": "Valid semantic memory",
                "memory_type": "test",
                "tier": "semantic",
            },
        )

        stats_before = client.get("/stats").json()
        assert stats_before["total_memories"] == 1

    with build_client(tmp_path) as client:
        stats_after = client.get("/stats").json()
        assert stats_after["total_memories"] == 1


def test_semantic_search_falls_back_to_keyword_when_disabled(tmp_path: Path) -> None:
    """Test that semantic search falls back to keyword search when embeddings are disabled."""
    with build_client(tmp_path) as client:
        # Store some memories
        client.post(
            "/memories",
            json={
                "content": "Python is a programming language",
                "memory_type": "factual",
                "tier": "semantic",
                "tags": ["python", "programming"],
            },
        )
        client.post(
            "/memories",
            json={
                "content": "JavaScript is also a programming language",
                "memory_type": "factual",
                "tier": "semantic",
                "tags": ["javascript", "programming"],
            },
        )

        # Search with semantic endpoint
        response = client.post(
            "/memories/semantic-search",
            json={"query": "programming language", "limit": 10},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["used_semantic_search"] is False
    assert payload["count"] == 2
    # Check results contain keyword scores (fallback behavior)
    assert all(r["keyword_score"] is not None for r in payload["results"])


# ==============================================================================
# v1.0 Tests
# ==============================================================================


def test_cache_lru_basic(tmp_path: Path) -> None:
    """Test basic LRU cache operations."""
    from gnosys_backend.cache import LRUCache

    cache = LRUCache(max_size=3, ttl_seconds=60)

    # Insert
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")

    # Get
    assert cache.get("key1") == "value1"
    assert cache.get("key2") == "value2"
    assert cache.get("key3") == "value3"

    # Stats
    stats = cache.stats()
    assert stats["size"] == 3
    assert stats["hits"] == 3


def test_cache_lru_eviction(tmp_path: Path) -> None:
    """Test LRU eviction on capacity."""
    from gnosys_backend.cache import LRUCache

    cache = LRUCache(max_size=2, ttl_seconds=60)

    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")  # Should evict key1

    assert cache.get("key1") is None  # Evicted
    assert cache.get("key2") == "value2"
    assert cache.get("key3") == "value3"


def test_query_cache(tmp_path: Path) -> None:
    """Test query cache."""
    from gnosys_backend.cache import QueryCache

    cache = QueryCache(max_size=10)

    # Cache results
    cache.set("test query", ["result1", "result2"])

    # Get cached
    results = cache.get("test query")
    assert results == ["result1", "result2"]

    # Miss
    assert cache.get("different query") is None


def test_tool_registry_builtins(tmp_path: Path) -> None:
    """Test tool registry has built-in tools."""
    from gnosys_backend.tool_registry import ToolRegistry

    registry = ToolRegistry()

    tools = registry.list_tools(source="builtin")

    assert len(tools) >= 10
    assert any(t["name"] == "gnosys_store_memory" for t in tools)
    assert any(t["name"] == "gnosys_search" for t in tools)


def test_tool_registry_find_by_capability(tmp_path: Path) -> None:
    """Test finding tools by capability."""
    from gnosys_backend.tool_registry import ToolRegistry

    registry = ToolRegistry()

    memory_tools = registry.find("memory_ops")

    assert len(memory_tools) >= 3
    assert any(t.name == "gnosys_store_memory" for t in memory_tools)


def test_tool_registry_versioning(tmp_path: Path) -> None:
    """Test tool version management."""
    from gnosys_backend.tool_registry import ToolRegistry, ToolDefinition

    registry = ToolRegistry()

    # Register tool
    defn = ToolDefinition(
        name="custom_tool",
        version="1.0.0",
        description="Test tool",
        capabilities=["custom"],
    )
    registry.register(defn, source="custom")

    versions = registry.get_versions("custom_tool")
    assert "1.0.0" in versions

    # Get specific version
    retrieved = registry.get("custom_tool", "1.0.0")
    assert retrieved is not None
    assert retrieved.name == "custom_tool"


def test_cache_manager_stats(tmp_path: Path) -> None:
    """Test cache manager statistics."""
    from gnosys_backend.cache import CacheManager, CacheConfig

    config = CacheConfig(
        enabled=True,
        semantic_search_lru=True,
        context_ttl=True,
        agent_results_lru=True,
    )

    manager = CacheManager(config)

    # Use caches
    manager.query_cache.set("query1", ["result"])
    manager.context_cache.set("ctx1", {"context": "data"})
    manager.agent_cache.set("agent1", {"agent": "data"})

    stats = manager.get_stats()

    assert "query" in stats
    assert "context" in stats
    assert "agent" in stats
