from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..deps import AppServices, get_services
from ..models import MemoryBrowseResponse, MemoryConsolidationResponse, MemoryIngestRequest, MemoryItemRecord, MemoryLayerRecord, MemoryRetrievalResponse, MemoryReviewResponse


router = APIRouter()


@router.get("/api/memory", response_model=list[MemoryLayerRecord])
def memory_layers(services: AppServices = Depends(get_services)) -> list[MemoryLayerRecord]:
    return [MemoryLayerRecord(**layer) for layer in services.store.list_memory_layers()]


@router.get("/api/memory/items", response_model=list[MemoryItemRecord])
def memory_items(limit: int = 25, project_id: str | None = None, services: AppServices = Depends(get_services)) -> list[MemoryItemRecord]:
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    return [MemoryItemRecord(**item) for item in services.store.list_memory_items(limit=limit, project_id=project_id)]


@router.get("/api/memory/review", response_model=MemoryReviewResponse)
def review_memory(limit: int = 25, services: AppServices = Depends(get_services)) -> MemoryReviewResponse:
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    return MemoryReviewResponse(**services.memory_engine.review_queue(limit=limit))


@router.get("/api/memory/browser", response_model=MemoryBrowseResponse)
def browse_memory(query: str | None = None, project_id: str | None = None, limit: int = 12, services: AppServices = Depends(get_services)) -> MemoryBrowseResponse:
    if limit < 1 or limit > 50:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 50")
    browser = services.memory_engine.browse(query=query, project_id=project_id, limit=limit)
    return MemoryBrowseResponse(
        query=browser["query"],
        project_id=browser["project_id"],
        total_count=browser["total_count"],
        daily_memories=[MemoryItemRecord(**item) for item in browser["daily_memories"]],
        long_term_memories=[MemoryItemRecord(**item) for item in browser["long_term_memories"]],
        pinned_memories=[MemoryItemRecord(**item) for item in browser["pinned_memories"]],
        candidate_memories=[MemoryItemRecord(**item) for item in browser["candidate_memories"]],
        contradictions=browser["contradictions"],
    )


@router.post("/api/memory/items", response_model=MemoryItemRecord, status_code=201)
def ingest_memory(payload: MemoryIngestRequest, services: AppServices = Depends(get_services)) -> MemoryItemRecord:
    services.gate_mutation(action="memory.ingest", subject_type="memory_item", subject_ref=payload.title, payload=payload.model_dump(), project_id=payload.project_id)
    item = services.memory_engine.ingest(
        title=payload.title,
        summary=payload.summary,
        content=payload.content,
        provenance=payload.provenance,
        source_ref=payload.source_ref,
        layer=payload.layer,
        scope=payload.scope,
        project_id=payload.project_id,
        confidence=payload.confidence,
        freshness=payload.freshness,
        tags=payload.tags,
        state=payload.state,
    )
    return MemoryItemRecord(**item)


@router.post("/api/memory/items/{item_id}/promote", response_model=MemoryItemRecord)
def promote_memory_item(item_id: str, services: AppServices = Depends(get_services)) -> MemoryItemRecord:
    item = services.store.update_memory_item_state(item_id, "validated")
    services.store.record_event(event_type="memory.promoted", source="ui", payload={"memory_item_id": item_id, "state": item["state"]})
    return MemoryItemRecord(**item)


@router.post("/api/memory/items/{item_id}/pin", response_model=MemoryItemRecord)
def pin_memory_item(item_id: str, services: AppServices = Depends(get_services)) -> MemoryItemRecord:
    return MemoryItemRecord(**services.memory_engine.pin(item_id))


@router.post("/api/memory/items/{item_id}/forget", response_model=MemoryItemRecord)
def forget_memory_item(item_id: str, services: AppServices = Depends(get_services)) -> MemoryItemRecord:
    return MemoryItemRecord(**services.memory_engine.forget(item_id))


@router.post("/api/memory/items/{item_id}/archive", response_model=MemoryItemRecord)
def archive_memory_item(item_id: str, services: AppServices = Depends(get_services)) -> MemoryItemRecord:
    item = services.memory_engine.forget(item_id)
    services.store.record_event(event_type="memory.archived", source="ui", payload={"memory_item_id": item_id, "state": item["state"]})
    return MemoryItemRecord(**item)


@router.post("/api/memory/consolidate", response_model=MemoryConsolidationResponse)
def consolidate_memory(services: AppServices = Depends(get_services)) -> MemoryConsolidationResponse:
    return MemoryConsolidationResponse(**services.memory_engine.consolidate())


@router.get("/api/memory/retrieve", response_model=MemoryRetrievalResponse)
def retrieve_memory(
    query: str,
    role: str = "orchestrator",
    scope: str | None = None,
    project_id: str | None = None,
    limit: int = 5,
    services: AppServices = Depends(get_services),
) -> MemoryRetrievalResponse:
    if limit < 1 or limit > 20:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 20")
    result = services.memory_engine.retrieve(query=query, role=role, scope=scope, project_id=project_id, limit=limit)
    return MemoryRetrievalResponse(query=result.query, scope=result.scope, role=result.role, items=[MemoryItemRecord(**item) for item in result.items], trace=result.trace)
