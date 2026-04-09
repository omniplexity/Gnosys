from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from fastapi import HTTPException, Request

from .memory import MemoryEngine
from .models import PolicyDecisionRecord
from .policy import PolicyEngine
from .runtime import OrchestrationEngine
from .session_learning import SessionLearningEngine
from .skills import SkillEngine
from .store import GnosysStore


@dataclass(slots=True)
class AppServices:
    store: GnosysStore
    memory_engine: MemoryEngine
    session_learning: SessionLearningEngine
    orchestration_engine: OrchestrationEngine
    policy_engine: PolicyEngine
    skill_engine: SkillEngine
    scheduler_service: Any | None = None
    approval_service: Any | None = None
    replay_service: Any | None = None
    schedule_runner: Any | None = None

    def gate_mutation(
        self,
        *,
        action: str,
        subject_type: str,
        subject_ref: str,
        payload: dict[str, object],
        project_id: str | None = None,
        requested_by: str = "ui",
    ) -> None:
        decision = self.policy_engine.evaluate(
            action=action,
            payload=payload,
            entity_type=subject_type,
            entity_id=subject_ref,
            project_id=project_id,
            mutating=True,
        )
        if decision.allowed:
            return
        approval = self.store.create_approval_request(
            action=action,
            subject_type=subject_type,
            subject_ref=subject_ref,
            sensitivity=decision.sensitivity,
            reason=decision.reason,
            payload={
                "action": action,
                "subject_type": subject_type,
                "subject_ref": subject_ref,
                "requested_by": requested_by,
                "payload": payload,
                "policy": self.policy_engine.snapshot(),
            },
            requested_by=requested_by,
        )
        self.store.record_event(
            event_type="approval.requested",
            source="policy",
            payload={
                "approval_id": approval["id"],
                "action": action,
                "subject_type": subject_type,
                "subject_ref": subject_ref,
                "sensitivity": decision.sensitivity,
                "mode": decision.mode,
                "reason": decision.reason,
            },
        )
        raise HTTPException(
            status_code=423,
            detail={
                "message": "Approval required",
                "decision": PolicyDecisionRecord(**asdict(decision)).model_dump(),
                "approval_request": approval,
                "policy": self.policy_engine.snapshot(),
            },
        )

    @staticmethod
    def approved_request_payload(approval: dict[str, object]) -> dict[str, object]:
        payload = approval.get("payload", {})
        if isinstance(payload, dict):
            nested = payload.get("payload", {})
            if isinstance(nested, dict):
                return nested
        return {}

    @staticmethod
    def payload_project_id(payload: dict[str, object]) -> str | None:
        project_id = payload.get("project_id")
        return project_id if isinstance(project_id, str) and project_id else None

    def resolve_optional_project_id(self, payload: Any, existing: dict[str, object]) -> str | None:
        if "project_id" not in payload.model_fields_set:
            project_id = existing.get("project_id")
            return project_id if isinstance(project_id, str) and project_id else None
        return payload.project_id


def get_services(request: Request) -> AppServices:
    return request.app.state.services
