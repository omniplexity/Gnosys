from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ..deps import AppServices, get_services
from ..models import (
    AgentRunRecord,
    ApprovalRequestRecord,
    ChatAttachmentRecord,
    ChatMessageCreateRequest,
    ChatMessageRecord,
    ChatSessionCreateRequest,
    ChatSessionRecord,
    ChatSessionSendRequest,
    ChatSessionSendResponse,
    ChatSessionUpdateRequest,
    IdentityProposalRecord,
    MemoryItemRecord,
    OrchestrationDecisionRecord,
    SessionReflectionRecord,
    SessionReflectionResponse,
    TaskRunRecord,
)
from ..session_agent import build_answer_message, build_execution_message, load_identity_bundle, should_execute, update_heartbeat


router = APIRouter()


@router.get("/api/chat-sessions", response_model=list[ChatSessionRecord])
def chat_sessions(services: AppServices = Depends(get_services)) -> list[ChatSessionRecord]:
    return [ChatSessionRecord(**session) for session in services.store.list_chat_sessions()]


@router.post("/api/chat-sessions", response_model=ChatSessionRecord, status_code=201)
def create_chat_session(payload: ChatSessionCreateRequest, services: AppServices = Depends(get_services)) -> ChatSessionRecord:
    services.gate_mutation(action="chat_session.create", subject_type="session", subject_ref=payload.title, payload=payload.model_dump())
    session = services.store.create_chat_session(title=payload.title, summary=payload.summary, status=payload.status)
    services.store.record_event(event_type="chat_session.created", source="ui", payload={"session_id": session["id"], "title": session["title"]})
    return ChatSessionRecord(**session)


@router.get("/api/chat-sessions/{session_id}", response_model=ChatSessionRecord)
def get_chat_session(session_id: str, services: AppServices = Depends(get_services)) -> ChatSessionRecord:
    session = services.store.get_chat_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return ChatSessionRecord(**session)


@router.patch("/api/chat-sessions/{session_id}", response_model=ChatSessionRecord)
def update_chat_session(session_id: str, payload: ChatSessionUpdateRequest, services: AppServices = Depends(get_services)) -> ChatSessionRecord:
    existing = services.store.get_chat_session(session_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    services.gate_mutation(action="chat_session.update", subject_type="session", subject_ref=session_id, payload=payload.model_dump())
    session = services.store.update_chat_session(session_id, title=payload.title, summary=payload.summary, status=payload.status)
    services.store.record_event(event_type="chat_session.updated", source="ui", payload={"session_id": session_id, "status": session["status"]})
    return ChatSessionRecord(**session)


@router.get("/api/chat-sessions/{session_id}/messages", response_model=list[ChatMessageRecord])
def chat_session_messages(session_id: str, limit: int = 200, services: AppServices = Depends(get_services)) -> list[ChatMessageRecord]:
    session = services.store.get_chat_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    return [ChatMessageRecord(**message) for message in services.store.list_chat_messages(session_id, limit=limit)]


@router.get("/api/chat-sessions/{session_id}/attachments", response_model=list[ChatAttachmentRecord])
def chat_session_attachments(session_id: str, limit: int = 50, services: AppServices = Depends(get_services)) -> list[ChatAttachmentRecord]:
    session = services.store.get_chat_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return [ChatAttachmentRecord(**item) for item in services.store.list_chat_attachments(session_id, limit=limit)]


@router.post("/api/chat-sessions/{session_id}/attachments", response_model=ChatAttachmentRecord, status_code=201)
async def upload_chat_session_attachment(
    session_id: str,
    file: UploadFile = File(...),
    mode: str = Form("personal"),
    project_id: str | None = Form(None),
    project_thread_id: str | None = Form(None),
    services: AppServices = Depends(get_services),
) -> ChatAttachmentRecord:
    session = services.store.get_chat_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    if mode not in {"personal", "project", "project-thread"}:
        raise HTTPException(status_code=400, detail="Unsupported chat mode")
    try:
        context_directory = Path(
            services.store.resolve_chat_context_directory(
                chat_session_id=session_id,
                mode=mode,
                project_id=project_id,
                project_thread_id=project_thread_id,
            )
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"Missing context reference: {error.args[0]}") from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    safe_name = Path(file.filename or "attachment.bin").name
    stored_name = f"{session_id[:8]}-{safe_name}"
    destination = context_directory / stored_name
    with destination.open("wb") as handle:
        shutil.copyfileobj(file.file, handle)
    attachment = services.store.create_chat_attachment(
        chat_session_id=session_id,
        mode=mode,
        project_id=project_id,
        project_thread_id=project_thread_id,
        original_name=safe_name,
        stored_name=stored_name,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=destination.stat().st_size,
        storage_path=str(destination.resolve()),
    )
    services.store.record_event(event_type="chat.attachment.uploaded", source="ui", payload={"chat_session_id": session_id, "attachment_id": attachment["id"], "mode": mode})
    return ChatAttachmentRecord(**attachment)


@router.post("/api/chat-sessions/{session_id}/messages", response_model=ChatMessageRecord, status_code=201)
def create_chat_message(session_id: str, payload: ChatMessageCreateRequest, services: AppServices = Depends(get_services)) -> ChatMessageRecord:
    session = services.store.get_chat_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    message = services.store.create_chat_message(
        chat_session_id=session_id,
        role=payload.role,
        kind=payload.kind,
        content=payload.content,
        task_run_id=payload.task_run_id,
        agent_run_ids=payload.agent_run_ids,
        metadata=payload.metadata,
    )
    services.store.record_event(event_type="chat.message.created", source="ui", payload={"chat_session_id": session_id, "message_id": message["id"], "role": message["role"], "kind": message["kind"]})
    return ChatMessageRecord(**message)


@router.post("/api/chat-sessions/{session_id}/send", response_model=ChatSessionSendResponse, status_code=201)
def send_chat_message(session_id: str, payload: ChatSessionSendRequest, services: AppServices = Depends(get_services)) -> ChatSessionSendResponse:
    session = services.store.get_chat_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    user_message = services.store.create_chat_message(
        chat_session_id=session_id,
        role="user",
        kind="message",
        content=payload.content,
        metadata={
            "requested_by": payload.requested_by,
            "selected_model": payload.selected_model,
            "reasoning_strength": payload.reasoning_strength,
            "mode": payload.mode,
            "project_id": payload.project_id,
            "project_thread_id": payload.project_thread_id,
            "attachment_ids": payload.attachment_ids,
        },
    )
    attachments = [services.store.get_chat_attachment(attachment_id) for attachment_id in payload.attachment_ids]
    attachments = [item for item in attachments if item is not None and item["chat_session_id"] == session_id]
    recent_messages = services.store.list_chat_messages(session_id, limit=40)
    identity_bundle = load_identity_bundle(session)
    memory_result = services.memory_engine.retrieve(query=payload.content, role="orchestrator", limit=3)

    generated_messages: list[dict[str, object]] = []
    task_run_payload: dict[str, object] | None = None
    agent_run_payloads: list[dict[str, object]] = []
    approval_request_payload: dict[str, object] | None = None
    decision_payload: dict[str, object] = {
        "intent_classification": "conversation",
        "execution_mode": "answer-only",
        "delegated_specialists": [],
        "invoked_skills": [],
        "approvals_triggered": False,
        "synthesis": "Master agent kept the request in direct-answer mode and did not create a task run.",
    }

    if should_execute(payload.content):
        launch_payload = {
            "objective": payload.content,
            "task_title": payload.content[:48],
            "task_summary": payload.content,
            "chat_session_id": session_id,
            "requested_by": payload.requested_by,
            "mode": services.policy_engine.snapshot()["autonomy_mode"],
            "priority": "High",
            "selected_model": payload.selected_model,
            "reasoning_strength": payload.reasoning_strength,
            "project_id": payload.project_id if payload.mode in {"project", "project-thread"} else None,
            "project_thread_id": payload.project_thread_id if payload.mode == "project-thread" else None,
            "attachment_ids": payload.attachment_ids,
        }
        try:
            services.gate_mutation(action="orchestration.launch", subject_type="chat_session", subject_ref=session_id, payload=launch_payload)
            launch = services.orchestration_engine.launch(
                objective=payload.content,
                task_title=payload.content[:48],
                task_summary=payload.content,
                requested_by=payload.requested_by,
                mode=services.policy_engine.snapshot()["autonomy_mode"],
                priority="High",
                chat_session_id=session_id,
                project_id=payload.project_id if payload.mode in {"project", "project-thread"} else None,
                project_thread_id=payload.project_thread_id if payload.mode == "project-thread" else None,
            )
            task_run_payload = launch.task_run
            agent_run_payloads = launch.agent_runs
            decision_payload = launch.decision
            generated_messages.append(
                services.store.create_chat_message(
                    chat_session_id=session_id,
                    role="system",
                    kind="event",
                    content=f"Started bounded work run {launch.task_run['id']} for this session.",
                    task_run_id=launch.task_run["id"],
                    agent_run_ids=[run["id"] for run in launch.agent_runs],
                    metadata={"event": "orchestration.launch", "task_id": launch.task["id"]},
                )
            )
            generated_messages.append(
                services.store.create_chat_message(
                    chat_session_id=session_id,
                    role="system",
                    kind="event",
                    content=launch.decision["synthesis"],
                    task_run_id=launch.task_run["id"],
                    agent_run_ids=[run["id"] for run in launch.agent_runs],
                    metadata={"event": "orchestration.route", "decision": launch.decision, "steps": launch.steps},
                )
            )
            assistant_text = build_execution_message(
                session=session,
                identity_bundle=identity_bundle,
                memory_items=memory_result.items,
                task_run=launch.task_run,
                agent_runs=launch.agent_runs,
                approvals_required=launch.approvals_required,
            )
        except HTTPException as error:
            detail = error.detail if isinstance(error.detail, dict) else {}
            approval_request_payload = detail.get("approval_request") if isinstance(detail, dict) else None
            decision_payload = {
                "intent_classification": "actionable",
                "execution_mode": "task-created",
                "delegated_specialists": [],
                "invoked_skills": [],
                "approvals_triggered": True,
                "synthesis": "Master agent classified this as actionable work, but policy created an approval gate before delegation could proceed.",
            }
            generated_messages.append(
                services.store.create_chat_message(
                    chat_session_id=session_id,
                    role="system",
                    kind="event",
                    content="Execution was gated and an approval request was created for this session.",
                    metadata={"event": "approval.requested", "approval_request": approval_request_payload or {}},
                )
            )
            assistant_text = build_execution_message(
                session=session,
                identity_bundle=identity_bundle,
                memory_items=memory_result.items,
                task_run=None,
                agent_runs=[],
                approvals_required=[str(detail.get("message", "Approval required"))] if isinstance(detail, dict) else ["Approval required"],
            )
    else:
        assistant_text = build_answer_message(
            session=session,
            content=payload.content,
            recent_messages=recent_messages[:-1],
            identity_bundle=identity_bundle,
            memory_items=memory_result.items,
        )

    assistant_message = services.store.create_chat_message(
        chat_session_id=session_id,
        role="assistant",
        kind="message",
        content=assistant_text,
        task_run_id=str(task_run_payload["id"]) if task_run_payload is not None else None,
        agent_run_ids=[str(run["id"]) for run in agent_run_payloads],
        metadata={
            "memory_item_ids": [str(item["id"]) for item in memory_result.items],
            "selected_model": payload.selected_model,
            "reasoning_strength": payload.reasoning_strength,
            "mode": payload.mode,
            "project_id": payload.project_id,
            "project_thread_id": payload.project_thread_id,
            "attachment_ids": [item["id"] for item in attachments],
            "attachment_names": [item["original_name"] for item in attachments],
        },
    )
    final_messages = services.store.list_chat_messages(session_id, limit=80)
    if services.session_learning.should_reflect(final_messages, task_run_created=task_run_payload is not None):
        reflection_result = services.session_learning.reflect_session(session=session, messages=final_messages)
        generated_messages.append(
            services.store.create_chat_message(
                chat_session_id=session_id,
                role="system",
                kind="reflection",
                content=reflection_result["reflection"]["summary"],
                metadata={
                    "reflection_id": reflection_result["reflection"]["id"],
                    "memory_item_ids": [item["id"] for item in reflection_result["memory_items"]],
                    "identity_proposal_ids": [proposal["id"] for proposal in reflection_result["identity_proposals"]],
                },
            )
        )
    update_heartbeat(session, latest_user_message=payload.content, latest_assistant_message=assistant_text, task_run_id=str(task_run_payload["id"]) if task_run_payload is not None else None)
    services.store.record_event(
        event_type="chat.message.responded",
        source="session-agent",
        payload={"chat_session_id": session_id, "user_message_id": user_message["id"], "assistant_message_id": assistant_message["id"], "task_run_id": task_run_payload["id"] if task_run_payload is not None else None},
    )
    return ChatSessionSendResponse(
        user_message=ChatMessageRecord(**user_message),
        assistant_message=ChatMessageRecord(**assistant_message),
        generated_messages=[ChatMessageRecord(**message) for message in generated_messages],
        task_run=TaskRunRecord(**task_run_payload) if task_run_payload is not None else None,
        agent_runs=[AgentRunRecord(**run) for run in agent_run_payloads],
        approval_request=ApprovalRequestRecord(**approval_request_payload) if approval_request_payload is not None else None,
        decision=OrchestrationDecisionRecord(**decision_payload),
    )


@router.delete("/api/chat-sessions/{session_id}", status_code=204)
def delete_chat_session(session_id: str, services: AppServices = Depends(get_services)) -> None:
    existing = services.store.get_chat_session(session_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    services.gate_mutation(action="chat_session.delete", subject_type="session", subject_ref=session_id, payload={"session_id": session_id})
    services.store.delete_chat_session(session_id)
    services.store.record_event(event_type="chat_session.deleted", source="ui", payload={"session_id": session_id})


@router.get("/api/chat-sessions/{session_id}/reflections", response_model=list[SessionReflectionRecord])
def chat_session_reflections(session_id: str, limit: int = 25, services: AppServices = Depends(get_services)) -> list[SessionReflectionRecord]:
    session = services.store.get_chat_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return [SessionReflectionRecord(**item) for item in services.store.list_session_reflections(session_id, limit=limit)]


@router.post("/api/chat-sessions/{session_id}/reflect", response_model=SessionReflectionResponse, status_code=201)
def reflect_chat_session(session_id: str, services: AppServices = Depends(get_services)) -> SessionReflectionResponse:
    session = services.store.get_chat_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    result = services.session_learning.reflect_session(session=session, messages=services.store.list_chat_messages(session_id, limit=80))
    return SessionReflectionResponse(
        reflection=SessionReflectionRecord(**result["reflection"]),
        memory_items=[MemoryItemRecord(**item) for item in result["memory_items"]],
        identity_proposals=[IdentityProposalRecord(**item) for item in result["identity_proposals"]],
    )


@router.post("/api/chat-sessions/{session_id}/daily-memory", response_model=MemoryItemRecord, status_code=201)
def chat_session_daily_memory(session_id: str, services: AppServices = Depends(get_services)) -> MemoryItemRecord:
    session = services.store.get_chat_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    item = services.session_learning.create_daily_memory(session=session, messages=services.store.list_chat_messages(session_id, limit=80))
    return MemoryItemRecord(**item)


@router.get("/api/chat-sessions/{session_id}/identity-proposals", response_model=list[IdentityProposalRecord])
def chat_session_identity_proposals(session_id: str, limit: int = 25, services: AppServices = Depends(get_services)) -> list[IdentityProposalRecord]:
    session = services.store.get_chat_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return [IdentityProposalRecord(**item) for item in services.store.list_identity_proposals(session_id, limit=limit)]
