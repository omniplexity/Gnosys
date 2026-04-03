# Vector Store Component

## Overview

The Vector Store provides semantic search capabilities using vector embeddings with cosine similarity.

## File

`python/src/gnosys_backend/vector_store.py`

## Class: VectorStore

```python
class VectorStore:
    def __init__(self, db: Database, config: AppConfig) -> None: ...
    
    def store_vector(self, memory_id: str, content: str, 
                     vector: list[float], 
                     metadata: dict[str, Any]) -> None: ...
    
    def search_similar(self, query_vector: list[float], 
                       limit: int = 10, 
                       memory_ids: list[str] | None = None,
                       memory_type: str | None = None,
                       tier: str | None = None) -> list[dict[str, Any]]: ...
    
    def delete_vector(self, memory_id: str) -> bool: ...
    
    def close(self) -> None: ...
```

## Features

### Vector Embeddings

- Uses configurable embeddings provider (local or OpenAI)
- Supports batch embedding generation
- 384-dimensional vectors (default, configurable)

### Cosine Similarity

Search uses cosine similarity for ranking:
```python
similarity = dot(v1, v2) / (||v1|| * ||v2||)
```

### Hybrid Search

Combines semantic and keyword search:
1. Generate query embedding
2. Get keyword matches from SQLite
3. Get semantic matches from vector store
4. Re-rank using weighted combination

## Configuration

```json
{
  "embeddings": {
    "provider": "local",
    "model": "sentence-transformers/all-MiniLM-L6-v2",
    "dimension": 384
  }
}
```

## Usage

```python
from gnosys_backend.vector_store import VectorStore

vectors = VectorStore(db, config)

# Store embedding
vectors.store_vector(
    memory_id="uuid",
    content="Memory content",
    vector=[0.1, 0.2, ...],
    metadata={"memory_type": "conversational", "tier": "episodic"}
)

# Search
results = vectors.search_similar(query_vector, limit=10)
```
