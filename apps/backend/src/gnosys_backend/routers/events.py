from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..deps import AppServices, get_services
from ..models import EventCreateRequest, EventRecord


router = APIRouter()


@router.get("/api/events", response_model=list[EventRecord])
def events(limit: int = 25, services: AppServices = Depends(get_services)) -> list[EventRecord]:
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    return [EventRecord(**event) for event in services.store.list_events(limit=limit)]


@router.post("/api/events", response_model=EventRecord, status_code=201)
def create_event(payload: EventCreateRequest, services: AppServices = Depends(get_services)) -> EventRecord:
    event = services.store.record_event(event_type=payload.type, source=payload.source, payload=payload.payload)
    return EventRecord(**event)
