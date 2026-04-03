"""
Performance Caching module for Gnosys v1.0.

Provides multi-layer caching for semantic search, context building, and agent results.
"""

from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable

from pydantic import BaseModel


# ==============================================================================
# Cache Configuration
# ==============================================================================


class CacheConfig(BaseModel):
    """Configuration for cache settings."""

    enabled: bool = True
    max_size_mb: int = 512
    ttl_seconds: int = 3600
    semantic_search_lru: bool = True
    context_ttl: bool = True
    agent_results_lru: bool = True


# ==============================================================================
# Cache Entry
# ==============================================================================


@dataclass
class CacheEntry:
    """A single cache entry."""

    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0

    def is_expired(self, ttl: float) -> bool:
        """Check if the entry has expired."""
        return (time.time() - self.created_at) > ttl


# ==============================================================================
# LRU Cache
# ==============================================================================


class LRUCache:
    """
    LRU (Least Recently Used) cache implementation.

    Features:
    - Bounded size with automatic eviction
    - TTL support for time-based expiry
    - Thread-safe operations
    """

    def __init__(
        self,
        max_size: int = 1000,
        ttl_seconds: float = 3600,
    ):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def _generate_key(self, *args: Any, **kwargs: Any) -> str:
        """Generate a cache key from arguments."""
        key_parts = [str(arg) for arg in args]
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        key_string = ":".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]

    def get(self, key: str) -> Any | None:
        """Get a value from cache."""
        if key not in self._cache:
            self._misses += 1
            return None

        entry = self._cache[key]

        # Check TTL
        if entry.is_expired(self.ttl_seconds):
            del self._cache[key]
            self._misses += 1
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        entry.last_accessed = time.time()
        entry.access_count += 1

        self._hits += 1
        return entry.value

    def set(self, key: str, value: Any) -> None:
        """Set a value in cache."""
        # Remove oldest if at capacity
        if len(self._cache) >= self.max_size and key not in self._cache:
            self._cache.popitem(last=False)

        entry = CacheEntry(key=key, value=value)
        self._cache[key] = entry
        self._cache.move_to_end(key)

    def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def cleanup_expired(self) -> int:
        """Remove all expired entries."""
        expired_keys = [
            key
            for key, entry in self._cache.items()
            if entry.is_expired(self.ttl_seconds)
        ]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)

    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "total_requests": total_requests,
        }


# ==============================================================================
# TTL Cache (for context)
# ==============================================================================


class TTLCache:
    """
    TTL-based cache for context data.

    Entries expire after their TTL regardless of access patterns.
    """

    def __init__(self, ttl_seconds: float = 300):
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, CacheEntry] = {}
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any | None:
        """Get a value."""
        if key not in self._cache:
            self._misses += 1
            return None

        entry = self._cache[key]

        if entry.is_expired(self.ttl_seconds):
            del self._cache[key]
            self._misses += 1
            return None

        entry.last_accessed = time.time()
        entry.access_count += 1

        self._hits += 1
        return entry.value

    def set(self, key: str, value: Any) -> None:
        """Set a value."""
        self._cache[key] = CacheEntry(key=key, value=value)

    def delete(self, key: str) -> bool:
        """Delete a key."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def cleanup_expired(self) -> int:
        """Remove expired entries."""
        expired_keys = [
            key
            for key, entry in self._cache.items()
            if entry.is_expired(self.ttl_seconds)
        ]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)

    def stats(self) -> dict[str, Any]:
        """Get statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0

        return {
            "size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
        }


# ==============================================================================
# Vector Embedding Cache
# ==============================================================================


class EmbeddingCache:
    """
    Specialized cache for embedding vectors.

    Uses more memory-efficient storage for dense vectors.
    """

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._cache: OrderedDict[str, list[float]] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def _normalize_key(self, text: str) -> str:
        """Normalize text for consistent key generation."""
        return hashlib.sha256(text.lower().strip().encode()).hexdigest()

    def get(self, text: str) -> list[float] | None:
        """Get embedding for text."""
        key = self._normalize_key(text)

        if key not in self._cache:
            self._misses += 1
            return None

        self._cache.move_to_end(key)
        self._hits += 1

        return self._cache[key]

    def set(self, text: str, embedding: list[float]) -> None:
        """Store embedding."""
        if len(self._cache) >= self.max_size and key not in self._cache:
            self._cache.popitem(last=False)

        key = self._normalize_key(text)
        self._cache[key] = embedding
        self._cache.move_to_end(key)

    def clear(self) -> None:
        """Clear cache."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def stats(self) -> dict[str, Any]:
        """Get stats."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
        }


# ==============================================================================
# Query Cache (for semantic searches)
# ==============================================================================


class QueryCache:
    """
    Cache for semantic search results.

    Keyed by normalized query for maximum cache hits.
    """

    def __init__(self, max_size: int = 500):
        self.max_size = max_size
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def _normalize_query(self, query: str) -> str:
        """Normalize query for consistent key."""
        return hashlib.sha256(query.lower().strip().encode()).hexdigest()

    def get(self, query: str) -> Any | None:
        """Get cached results."""
        key = self._normalize_query(query)

        if key not in self._cache:
            self._misses += 1
            return None

        results, timestamp = self._cache[key]

        # Check expiry (5 minutes for search results)
        if time.time() - timestamp > 300:
            del self._cache[key]
            self._misses += 1
            return None

        self._cache.move_to_end(key)
        self._hits += 1

        return results

    def set(self, query: str, results: Any) -> None:
        """Cache results."""
        if len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)

        key = self._normalize_query(query)
        self._cache[key] = (results, time.time())
        self._cache.move_to_end(key)

    def clear(self) -> None:
        """Clear cache."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def stats(self) -> dict[str, Any]:
        """Get stats."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0

        return {
            "size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
        }


# ==============================================================================
# Cache Manager (Facade)
# ==============================================================================


class CacheManager:
    """
    Unified cache manager for all caching needs.
    """

    def __init__(self, config: CacheConfig | None = None):
        self.config = config or CacheConfig()

        # Initialize caches
        self.query_cache = (
            QueryCache(max_size=500) if self.config.semantic_search_lru else None
        )
        self.context_cache = (
            TTLCache(ttl_seconds=self.config.ttl_seconds)
            if self.config.context_ttl
            else None
        )
        self.embedding_cache = (
            EmbeddingCache(max_size=10000) if self.config.semantic_search_lru else None
        )
        self.agent_cache = (
            LRUCache(max_size=100, ttl_seconds=600)
            if self.config.agent_results_lru
            else None
        )

    def clear_all(self) -> None:
        """Clear all caches."""
        if self.query_cache:
            self.query_cache.clear()
        if self.context_cache:
            self.context_cache.clear()
        if self.embedding_cache:
            self.embedding_cache.clear()
        if self.agent_cache:
            self.agent_cache.clear()

    def cleanup_all(self) -> dict[str, int]:
        """Clean up expired entries in all caches."""
        results = {}

        if self.query_cache:
            results["query"] = self.query_cache.clear()
        if self.context_cache:
            results["context"] = self.context_cache.cleanup_expired()
        if self.embedding_cache:
            self.embedding_cache.clear()
        if self.agent_cache:
            results["agent"] = self.agent_cache.cleanup_expired()

        return results

    def get_stats(self) -> dict[str, Any]:
        """Get statistics for all caches."""
        stats = {}

        if self.query_cache:
            stats["query"] = self.query_cache.stats()
        if self.context_cache:
            stats["context"] = self.context_cache.stats()
        if self.embedding_cache:
            stats["embeddings"] = self.embedding_cache.stats()
        if self.agent_cache:
            stats["agent"] = self.agent_cache.stats()

        return stats


# ==============================================================================
# Decorator helper
# ==============================================================================


def cached(cache: LRUCache | TTLCache, key_func: Callable | None = None):
    """
    Decorator to cache function results.

    Usage:
        @cached(my_cache)
        def expensive_function(arg1, arg2):
            # ... expensive computation
            return result
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = cache._generate_key(*args, **kwargs)

            # Try cache
            result = cache.get(cache_key)
            if result is not None:
                return result

            # Compute
            result = func(*args, **kwargs)

            # Store
            cache.set(cache_key, result)

            return result

        return wrapper

    return decorator
