from __future__ import annotations

from fastapi import HTTPException

from ..deps import AppServices


class ApprovalService:
    def __init__(self, services: AppServices) -> None:
        self.services = services

    def execute_approved_request(self, approval: dict[str, object]) -> dict[str, object]:
        action = str(approval.get("action", ""))
        subject_ref = str(approval.get("subject_ref", ""))
        requested_by = str(approval.get("requested_by", "ui"))
        payload = self.services.approved_request_payload(approval)
        store = self.services.store

        if action == "task.create":
            task = store.create_task(
                title=str(payload.get("title", "Untitled task")),
                summary=str(payload.get("summary", "")),
                status=str(payload.get("status", "Inbox")),
                priority=str(payload.get("priority", "Medium")),
                project_id=self.services.payload_project_id(payload),
            )
            store.record_event(event_type="task.created", source="approval", payload={"task_id": task["id"], "title": task["title"], "requested_by": requested_by})
            return {"task": task}
        if action == "task.update":
            task = store.update_task(
                subject_ref,
                title=str(payload.get("title", "Untitled task")),
                summary=str(payload.get("summary", "")),
                status=str(payload.get("status", "Inbox")),
                priority=str(payload.get("priority", "Medium")),
                project_id=self.services.payload_project_id(payload),
            )
            store.record_event(event_type="task.updated", source="approval", payload={"task_id": subject_ref, "status": task["status"], "requested_by": requested_by})
            return {"task": task}
        if action == "task.delete":
            store.delete_task(subject_ref)
            store.record_event(event_type="task.deleted", source="approval", payload={"task_id": subject_ref, "requested_by": requested_by})
            return {"task_id": subject_ref}
        if action == "agent.create":
            agent = store.create_agent(name=str(payload.get("name", "Untitled agent")), role=str(payload.get("role", "Unassigned")), status=str(payload.get("status", "Idle")))
            store.record_event(event_type="agent.created", source="approval", payload={"agent_id": agent["id"], "name": agent["name"], "requested_by": requested_by})
            return {"agent": agent}
        if action == "agent.update":
            agent = store.update_agent(subject_ref, name=str(payload.get("name", "Untitled agent")), role=str(payload.get("role", "Unassigned")), status=str(payload.get("status", "Idle")))
            store.record_event(event_type="agent.updated", source="approval", payload={"agent_id": subject_ref, "status": agent["status"], "requested_by": requested_by})
            return {"agent": agent}
        if action == "agent.delete":
            store.delete_agent(subject_ref)
            store.record_event(event_type="agent.deleted", source="approval", payload={"agent_id": subject_ref, "requested_by": requested_by})
            return {"agent_id": subject_ref}
        if action == "project.create":
            project = store.create_project(name=str(payload.get("name", "Untitled project")), summary=str(payload.get("summary", "")), status=str(payload.get("status", "Planned")), owner=str(payload.get("owner", "Gnosys")))
            store.record_event(event_type="project.created", source="approval", payload={"project_id": project["id"], "name": project["name"], "requested_by": requested_by})
            return {"project": project}
        if action == "project.update":
            project = store.update_project(subject_ref, name=str(payload.get("name", "Untitled project")), summary=str(payload.get("summary", "")), status=str(payload.get("status", "Planned")), owner=str(payload.get("owner", "Gnosys")))
            store.record_event(event_type="project.updated", source="approval", payload={"project_id": subject_ref, "status": project["status"], "requested_by": requested_by})
            return {"project": project}
        if action == "project.delete":
            store.delete_project(subject_ref)
            store.record_event(event_type="project.deleted", source="approval", payload={"project_id": subject_ref, "requested_by": requested_by})
            return {"project_id": subject_ref}
        if action == "project_thread.create":
            thread = store.create_project_thread(project_id=str(payload.get("project_id", "")), title=str(payload.get("title", "Untitled thread")), summary=str(payload.get("summary", "")), status=str(payload.get("status", "Open")))
            store.record_event(event_type="project_thread.created", source="approval", payload={"thread_id": thread["id"], "project_id": thread["project_id"], "requested_by": requested_by})
            return {"project_thread": thread}
        if action == "project_thread.update":
            thread = store.update_project_thread(subject_ref, title=str(payload.get("title", "Untitled thread")), summary=str(payload.get("summary", "")), status=str(payload.get("status", "Open")))
            store.record_event(event_type="project_thread.updated", source="approval", payload={"thread_id": subject_ref, "project_id": thread["project_id"], "requested_by": requested_by})
            return {"project_thread": thread}
        if action == "project_thread.delete":
            store.delete_project_thread(subject_ref)
            store.record_event(event_type="project_thread.deleted", source="approval", payload={"thread_id": subject_ref, "requested_by": requested_by})
            return {"project_thread_id": subject_ref}
        if action == "chat_session.create":
            session = store.create_chat_session(title=str(payload.get("title", "Untitled session")), summary=str(payload.get("summary", "")), status=str(payload.get("status", "Active")))
            store.record_event(event_type="chat_session.created", source="approval", payload={"session_id": session["id"], "title": session["title"], "requested_by": requested_by})
            return {"chat_session": session}
        if action == "chat_session.update":
            session = store.update_chat_session(subject_ref, title=str(payload.get("title", "Untitled session")), summary=str(payload.get("summary", "")), status=str(payload.get("status", "Active")))
            store.record_event(event_type="chat_session.updated", source="approval", payload={"session_id": subject_ref, "status": session["status"], "requested_by": requested_by})
            return {"chat_session": session}
        if action == "chat_session.delete":
            store.delete_chat_session(subject_ref)
            store.record_event(event_type="chat_session.deleted", source="approval", payload={"session_id": subject_ref, "requested_by": requested_by})
            return {"chat_session_id": subject_ref}
        if action == "skill.create":
            skill = store.create_skill(
                name=str(payload.get("name", "Untitled skill")),
                description=str(payload.get("description", "")),
                scope=str(payload.get("scope", "workspace")),
                version=str(payload.get("version", "0.1.0")),
                source_type=str(payload.get("source_type", "authored")),
                status=str(payload.get("status", "draft")),
                project_id=self.services.payload_project_id(payload),
            )
            store.record_event(event_type="skill.created", source="approval", payload={"skill_id": skill["id"], "name": skill["name"], "requested_by": requested_by})
            return {"skill": skill}
        if action == "skill.update":
            skill = store.update_skill(
                subject_ref,
                name=str(payload.get("name", "Untitled skill")),
                description=str(payload.get("description", "")),
                scope=str(payload.get("scope", "workspace")),
                version=str(payload.get("version", "0.1.0")),
                source_type=str(payload.get("source_type", "authored")),
                status=str(payload.get("status", "draft")),
                project_id=self.services.payload_project_id(payload),
            )
            store.record_event(event_type="skill.updated", source="approval", payload={"skill_id": subject_ref, "status": skill["status"], "requested_by": requested_by})
            return {"skill": skill}
        if action == "skill.delete":
            store.delete_skill(subject_ref)
            store.record_event(event_type="skill.deleted", source="approval", payload={"skill_id": subject_ref, "requested_by": requested_by})
            return {"skill_id": subject_ref}
        if action == "schedule.create":
            schedule = store.create_schedule(
                name=str(payload.get("name", "Untitled schedule")),
                target_type=str(payload.get("target_type", "skill")),
                target_ref=str(payload.get("target_ref", "")),
                schedule_expression=str(payload.get("schedule_expression", "")),
                timezone=str(payload.get("timezone", "America/New_York")),
                enabled=bool(payload.get("enabled", True)),
                approval_policy=str(payload.get("approval_policy", "inherit")),
                failure_policy=str(payload.get("failure_policy", "retry_once")),
                last_run_at=payload.get("last_run_at"),
                next_run_at=payload.get("next_run_at"),
                project_id=self.services.payload_project_id(payload),
            )
            store.record_event(event_type="schedule.created", source="approval", payload={"schedule_id": schedule["id"], "name": schedule["name"], "requested_by": requested_by})
            return {"schedule": schedule}
        if action == "schedule.update":
            schedule = store.update_schedule(
                subject_ref,
                name=str(payload.get("name", "Untitled schedule")),
                target_type=str(payload.get("target_type", "skill")),
                target_ref=str(payload.get("target_ref", "")),
                schedule_expression=str(payload.get("schedule_expression", "")),
                timezone=str(payload.get("timezone", "America/New_York")),
                enabled=bool(payload.get("enabled", True)),
                approval_policy=str(payload.get("approval_policy", "inherit")),
                failure_policy=str(payload.get("failure_policy", "retry_once")),
                last_run_at=payload.get("last_run_at"),
                next_run_at=payload.get("next_run_at"),
                project_id=self.services.payload_project_id(payload),
            )
            store.record_event(event_type="schedule.updated", source="approval", payload={"schedule_id": subject_ref, "enabled": schedule["enabled"], "requested_by": requested_by})
            return {"schedule": schedule}
        if action == "schedule.delete":
            store.delete_schedule(subject_ref)
            store.record_event(event_type="schedule.deleted", source="approval", payload={"schedule_id": subject_ref, "requested_by": requested_by})
            return {"schedule_id": subject_ref}
        if action == "schedule.run":
            schedule = store.get_schedule(subject_ref)
            if schedule is None:
                raise HTTPException(status_code=404, detail="Schedule not found")
            pending_run = self.services.scheduler_service.latest_pending_run(subject_ref)
            run = self.services.scheduler_service.dispatch_schedule_run(
                schedule,
                requested_by=requested_by,
                existing_run_id=pending_run["id"] if pending_run is not None else None,
                retry_of_run_id=payload.get("retry_of_run_id") if isinstance(payload.get("retry_of_run_id"), str) else None,
                attempt_number=int(payload.get("attempt_number", 1)),
            )
            return {"schedule_run": run, "schedule_id": subject_ref}
        if action == "memory.ingest":
            item = self.services.memory_engine.ingest(
                title=str(payload.get("title", "Untitled memory")),
                summary=str(payload.get("summary", "")),
                content=str(payload.get("content", "")),
                provenance=str(payload.get("provenance", "approval")),
                source_ref=str(payload.get("source_ref", "")),
                layer=str(payload.get("layer", "Semantic")),
                scope=str(payload.get("scope", "workspace")),
                confidence=float(payload.get("confidence", 0.7)),
                freshness=float(payload.get("freshness", 0.7)),
                tags=list(payload.get("tags", [])) if isinstance(payload.get("tags", []), list) else [],
                state=str(payload.get("state", "candidate")),
                project_id=self.services.payload_project_id(payload),
            )
            return {"memory_item": item}
        if action == "orchestration.launch":
            result = self.services.orchestration_engine.launch(
                objective=str(payload.get("objective", "")),
                task_title=payload.get("task_title") if isinstance(payload.get("task_title"), str) else None,
                task_summary=payload.get("task_summary") if isinstance(payload.get("task_summary"), str) else None,
                requested_by=requested_by,
                mode=str(payload.get("mode", "Supervised")),
                priority=str(payload.get("priority", "High")),
                task_id=payload.get("task_id") if isinstance(payload.get("task_id"), str) else None,
                project_id=payload.get("project_id") if isinstance(payload.get("project_id"), str) else None,
                project_thread_id=payload.get("project_thread_id") if isinstance(payload.get("project_thread_id"), str) else None,
                chat_session_id=payload.get("chat_session_id") if isinstance(payload.get("chat_session_id"), str) else None,
                bypass_policy=True,
            )
            return {"task": result.task, "task_run": result.task_run, "agent_runs": result.agent_runs}
        raise HTTPException(status_code=422, detail=f"Unsupported approval action: {action}")

    def resolve_schedule_rejection(self, approval: dict[str, object], *, resolved_by: str) -> None:
        self.services.scheduler_service.reject_pending_approval(approval, resolved_by=resolved_by)
