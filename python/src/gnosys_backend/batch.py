"""
Batch Processing module for Gnosys v1.0.

Provides batch operations for memory inserts, vector indexing, and parallel processing.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel


# ==============================================================================
# Configuration
# ==============================================================================


class BatchConfig(BaseModel):
    """Configuration for batch processing."""

    enabled: bool = True
    max_batch_size: int = 100
    max_wait_ms: int = 100
    max_concurrent_batches: int = 4


# ==============================================================================
# Batch Item
# ==============================================================================


@dataclass
class BatchItem:
    """An item waiting to be processed."""

    id: str
    data: dict[str, Any]
    created_at: float
    priority: int = 0
    retries: int = 0


# ==============================================================================
# Batch Result
# ==============================================================================


@dataclass
class BatchResult:
    """Result of a batch operation."""

    item_id: str
    success: bool
    result: Any = None
    error: str | None = None
    duration_ms: float = 0.0


# ==============================================================================
# Batch Processor
# ==============================================================================


class BatchProcessor:
    """
    Generic batch processor with configurable batching strategy.

    Features:
    - Configurable batch size
    - Configurable wait time before flush
    - Priority support
    - Retry capability
    """

    def __init__(
        self,
        name: str,
        max_batch_size: int = 100,
        max_wait_ms: int = 100,
        max_concurrent_batches: int = 4,
    ):
        self.name = name
        self.max_batch_size = max_batch_size
        self.max_wait_ms = max_wait_ms
        self.max_concurrent_batches = max_concurrent_batches

        self._queue: deque[BatchItem] = deque()
        self._processing = False
        self._last_flush = time.time()
        self._lock = asyncio.Lock()

        # Stats
        self._items_processed = 0
        self._items_failed = 0

    async def add(
        self,
        item_id: str,
        data: dict[str, Any],
        priority: int = 0,
    ) -> None:
        """Add an item to the batch queue."""
        item = BatchItem(
            id=item_id,
            data=data,
            created_at=time.time(),
            priority=priority,
        )
        self._queue.append(item)

    async def flush(
        self,
        processor: Callable[[list[BatchItem]], list[BatchResult]],
    ) -> list[BatchResult]:
        """Flush the batch queue by processing items."""
        if not self._queue:
            return []

        items = []
        while self._queue and len(items) < self.max_batch_size:
            items.append(self._queue.popleft())

        # Sort by priority
        items.sort(key=lambda x: x.priority, reverse=True)

        # Process batch
        results = await processor(items)

        # Update stats
        for result in results:
            if result.success:
                self._items_processed += 1
            else:
                self._items_failed += 1

        self._last_flush = time.time()
        return results

    async def should_flush(self) -> bool:
        """Check if we should flush the batch."""
        if len(self._queue) >= self.max_batch_size:
            return True

        elapsed_ms = (time.time() - self._last_flush) * 1000
        if elapsed_ms >= self.max_wait_ms and self._queue:
            return True

        return False

    def size(self) -> int:
        """Get current queue size."""
        return len(self._queue)

    def stats(self) -> dict[str, Any]:
        """Get processing statistics."""
        total = self._items_processed + self._items_failed
        success_rate = self._items_processed / total if total > 0 else 0.0

        return {
            "name": self.name,
            "queue_size": len(self._queue),
            "max_batch_size": self.max_batch_size,
            "items_processed": self._items_processed,
            "items_failed": self._items_failed,
            "success_rate": success_rate,
        }


# ==============================================================================
# Batch Memory Store
# ==============================================================================


class BatchMemoryStore:
    """
    Batch processor for memory storage operations.
    """

    def __init__(
        self,
        max_batch_size: int = 100,
        max_wait_ms: int = 100,
    ):
        self.processor = BatchProcessor(
            name="memory_store",
            max_batch_size=max_batch_size,
            max_wait_ms=max_wait_ms,
        )

    async def add(
        self,
        item_id: str,
        tier: str,
        memory_type: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Queue a memory for batched storage."""
        data = {
            "tier": tier,
            "type": memory_type,
            "content": content,
            "metadata": metadata or {},
        }
        await self.processor.add(item_id, data)

    async def flush(
        self,
        store_func: Callable[[list[dict]], list[BatchResult]],
    ) -> list[BatchResult]:
        """Flush queued memories to storage."""

        async def processor(items: list[BatchItem]) -> list[BatchResult]:
            data = [item.data for item in items]
            results = store_func(data)
            return results

        return await self.processor.flush(processor)

    def size(self) -> int:
        """Get queue size."""
        return self.processor.size()

    async def should_flush(self) -> bool:
        """Check if should flush."""
        return await self.processor.should_flush()
