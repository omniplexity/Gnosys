# Context Retrieval Component

## Overview

The Context Retrieval system provides multi-tier context retrieval with token budget management for prompt assembly.

## File

`python/src/gnosys_backend/context_retrieval.py`

## Class: ContextRetrievalStore

```python
class ContextRetrievalStore:
    def __init__(self, memory_store: MemoryStore, 
                 vector_store: VectorStore,
                 embeddings_provider: EmbeddingsProvider,
                 config: AppConfig) -> None: ...
    
    def retrieve(self, request: ContextRetrieveRequest) -> ContextRetrieveResponse: ...
```

## Features

### Token Budget Management

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_tokens` | 4000 | Maximum tokens for context |
| `budgetFraction` | 0.5 | Fraction of budget per tier |

### Tier Blending

Retrieves memories from multiple tiers with priority-based blending:

1. **Working** (highest priority) - Current session context
2. **Episodic** - Recent session history  
3. **Semantic** - Entity knowledge, facts
4. **Archive** - Historical data

### Retrieval Algorithm

```
1. Calculate token budget per tier
2. Query each tier with semantic search
3. Calculate blended scores
4. Fill budget with highest-scoring items
5. Assemble final context string
```

### Response Fields

| Field | Description |
|-------|-------------|
| `query` | Original query |
| `items` | Retrieved context items |
| `tiers_included` | Tiers that contributed |
| `token_budget` | Total budget |
| `used_tokens` | Tokens consumed |
| `remaining_tokens` | Unused tokens |
| `truncated` | Whether items were dropped |
| `dropped_count` | Items dropped due to budget |
| `assembly_text` | Assembled context string |

## Usage

```python
from gnosys_backend.context_retrieval import ContextRetrievalStore

context_store = ContextRetrievalStore(
    memory_store=store,
    vector_store=vectors,
    embeddings_provider=embeddings,
    config=config
)

# Retrieve context
response = context_store.retrieve(ContextRetrieveRequest(
    query="what was I working on",
    max_tokens=2000,
    include_tiers=["working", "episodic", "semantic", "archive"]
))

print(response.assembly_text)
```

## Configuration

```json
{
  "context": {
    "enabled": true,
    "maxTokens": 4000,
    "budgetFraction": 0.5,
    "includeTiers": ["working", "episodic", "semantic", "archive"]
  }
}
```
