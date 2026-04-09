from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..deps import AppServices, get_services
from ..models import ApprovalRequestRecord, ApprovalResolveRequest


router = APIRouter()


@router.get("/api/approvals", response_model=list[ApprovalRequestRecord])
def list_approvals(limit: int = 25, services: AppServices = Depends(get_services)) -> list[ApprovalRequestRecord]:
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    return [ApprovalRequestRecord(**request) for request in services.store.list_approval_requests(limit=limit)]


@router.post("/api/approvals/{approval_id}/resolve", response_model=ApprovalRequestRecord)
def resolve_approval(
    approval_id: str,
    payload: ApprovalResolveRequest,
    services: AppServices = Depends(get_services),
) -> ApprovalRequestRecord:
    updated = services.store.update_approval_request(approval_id, status=payload.status, resolved_by=payload.resolved_by)
    approval = services.store.get_approval_request(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if payload.status == "approved":
        services.approval_service.execute_approved_request(approval)
    elif approval["action"] == "schedule.run":
        services.approval_service.resolve_schedule_rejection(approval, resolved_by=payload.resolved_by)
    services.store.record_event(
        event_type="approval.resolved",
        source="ui",
        payload={"approval_id": approval_id, "status": payload.status, "resolved_by": payload.resolved_by},
    )
    return ApprovalRequestRecord(**updated)
