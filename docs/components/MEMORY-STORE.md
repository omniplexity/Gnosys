# Memory Store Component

## Overview

The Memory Store provides persistent storage for memories with support for multiple tiers, automatic pruning, and keyword search.

## File

`python/src/gnosys_backend/memory_store.py`

## Class: MemoryStore

```python
class MemoryStore:
    def __init__(self, db: Database, config: AppConfig) -> None: ...
    
    def store_memory(self, request: MemoryCreateRequest) -> MemoryRecord: ...
    
    def get_memory(self, memory_id: str) -> MemoryRecord | None: ...
    
    def delete_memory(self, memory_id: str) -> bool: ...
    
    def search_memories(self, query: str, limit: int | None = None, 
                       memory_type: str | None = None, 
                       tier: str | None = None) -> SearchResponse: ...
    
    def prune_expired(self) -> int: ...
    
    def health(self) -> bool: ...
    
    def get_stats(self) -> StatsResponse: ...
```

## Features

### Memory Tiers

| Tier | Description |
|------|-------------|
| `working` | Immediate context, current session |
| `episodic` | Session history, recent interactions |
| `semantic` | Entity knowledge, facts, relationships |
| `archive` | Long-term storage, historical data |

### Memory Types

| Type | Description |
|------|-------------|
| `conversational` | Chat history, messages |
| `entity` | People, places, objects |
| `procedural` | Skills and procedures |
| `factual` | Verified information |
| `emotional` | Sentiment, user state |
| `meta` | Memory about memory |

### Keyword Search

Search uses SQLite LIKE queries with keyword matching:
- Content is tokenized and indexed
- Keywords are extracted and stored separately
- Results ranked by match count

### Auto-Pruning

Expired memories are automatically pruned:
- Working memories: Session-based TTL
- Episodic memories: Configurable retention (default: 30 days)
- Archive memories: Configurable retention (default: 365 days)

## Usage

```python
from gnosys_backend.memory_store import MemoryStore
from gnosys_backend.db import Database
from gnosys_backend.config import load_config

config = load_config()
db = Database(config.resolved_db_path())
store = MemoryStore(db, config)

# Store memory
memory = store.store_memory(MemoryCreateRequest(
    content="User asked about Python",
    memory_type="conversational",
    tier="episodic"
))

# Search
results = store.search_memories("Python", limit=10)

# Stats
stats = store.get_stats()
```
