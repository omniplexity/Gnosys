from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from .policy import PolicyEngine
from .skills import SkillEngine
from .store import GnosysStore, utc_now


PERSISTENT_SPECIALISTS = {
    "planner": "Planner",
    "research": "Research Specialist",
    "builder": "Builder Specialist",
    "memory": "Memory Steward",
    "critic": "Critic / Evaluator",
    "operations": "Operations / Scheduler",
}

SPECIALIST_IDS = {
    "Planner": "agent-002",
    "Research Specialist": "agent-003",
    "Builder Specialist": "agent-004",
    "Memory Steward": "agent-005",
    "Critic / Evaluator": "agent-006",
    "Operations / Scheduler": "agent-007",
    "Orchestrator": "agent-001",
}

SPECIALIST_BY_KEYWORD = [
    ({"research", "investigate", "lookup", "analyze", "compare", "document"}, "Research Specialist"),
    ({"build", "implement", "code", "ship", "scaffold", "refactor"}, "Builder Specialist"),
    ({"memory", "retrieve", "remember", "context"}, "Memory Steward"),
    ({"review", "test", "validate", "critique", "audit"}, "Critic / Evaluator"),
    ({"schedule", "cron", "automation", "recurring"}, "Operations / Scheduler"),
]

@dataclass(slots=True)
class OrchestrationResult:
    task: dict[str, Any]
    task_run: dict[str, Any]
    agent_runs: list[dict[str, Any]]
    steps: list[dict[str, Any]]
    approvals_required: list[str]
    summary: str
    decision: dict[str, Any]


class OrchestrationEngine:
    def __init__(self, store: GnosysStore, skill_engine: SkillEngine | None = None) -> None:
        self.store = store
        self.skill_engine = skill_engine or SkillEngine(store)

    def launch(
        self,
        *,
        objective: str,
        task_title: str | None = None,
        task_summary: str | None = None,
        requested_by: str = "user",
        mode: str = "Supervised",
        priority: str = "High",
        task_id: str | None = None,
        project_id: str | None = None,
        project_thread_id: str | None = None,
        chat_session_id: str | None = None,
        bypass_policy: bool = False,
    ) -> OrchestrationResult:
        objective = objective.strip()
        task = self._ensure_task(
            task_id=task_id,
            objective=objective,
            task_title=task_title,
            task_summary=task_summary,
            priority=priority,
            project_id=project_id,
        )
        policy = PolicyEngine(self.store)
        if bypass_policy:
            approval_required = False
        else:
            policy_decision = policy.evaluate(
                action="orchestration.launch",
                payload={"objective": objective, "requested_mode": mode},
                mutating=True,
            )
            approval_required = policy_decision.requires_approval
        intent_classification = self._classify_intent(objective)
        steps = self._build_steps(objective, intent_classification=intent_classification)
        routing_context = self.skill_engine.find_routing_context(objective, project_id=project_id, limit=3)
        invoked_skills = routing_context["active"]
        invoked_skill_names = [str(skill["name"]) for skill in invoked_skills]
        candidate_skill_names = [str(skill["name"]) for skill in routing_context["candidates"]]
        if invoked_skill_names:
            steps = self._apply_skill_guidance(steps, invoked_skill_names)
        if candidate_skill_names:
            steps = self._apply_candidate_guidance(steps, candidate_skill_names)
        summary = self._summarize_run(objective, steps, approval_required)

        task_run = self.store.create_task_run(
            task_id=task["id"],
            objective=objective,
            requested_by=requested_by,
            project_id=project_id or task.get("project_id"),
            project_thread_id=project_thread_id,
            chat_session_id=chat_session_id,
            mode=mode,
            status="Needs Approval" if approval_required else "Running",
            summary=summary,
            step_count=len(steps),
            approval_required=approval_required,
        )

        root_run = self.store.create_agent_run(
            agent_id="agent-001",
            agent_name="Orchestrator",
            agent_role="Control loop and task routing",
            run_kind="orchestrator",
            status="Working",
            objective=objective,
            summary="Orchestrator accepted the request and prepared delegated work.",
            task_run_id=task_run["id"],
            parent_run_id=None,
            recursion_depth=0,
            child_count=0,
            budget_units=100,
            approval_required=approval_required,
        )
        planner_run = self.store.create_agent_run(
            agent_id="agent-002",
            agent_name="Planner",
            agent_role="Task decomposition and sequencing",
            run_kind="specialist",
            status="Reviewing",
            objective=objective,
            summary="Planner decomposed the objective into bounded execution steps.",
            task_run_id=task_run["id"],
            parent_run_id=root_run["id"],
            recursion_depth=1,
            child_count=0,
            budget_units=60,
            approval_required=approval_required,
        )

        agent_runs = [root_run, planner_run]
        approvals_required: list[str] = []
        specialist_count = 0
        worker_count = 0
        delegated_specialists: list[str] = []
        for index, step in enumerate(steps, start=1):
            specialist = self._specialist_for_step(step["intent"], objective)
            if specialist not in delegated_specialists and specialist != "Planner":
                delegated_specialists.append(specialist)
            specialist_run = self._create_specialist_run(
                task_run_id=task_run["id"],
                parent_run_id=planner_run["id"],
                objective=step["objective"],
                specialist=specialist,
                recursion_depth=1,
                child_count=index,
                approval_required=approval_required,
            )
            agent_runs.append(specialist_run)
            specialist_count += 1

            if bool(step.get("spawn_worker")):
                worker_run = self._spawn_worker(
                    task_run_id=task_run["id"],
                    parent_run_id=specialist_run["id"],
                    objective=step["objective"],
                    specialist=specialist,
                    recursion_depth=2,
                    child_count=1,
                    approval_required=approval_required,
                )
                agent_runs.append(worker_run)
                worker_count += 1
                self.store.update_agent_run(
                    specialist_run["id"],
                    status="Working",
                    child_count=1,
                    summary=f"{specialist} delegated to a bounded worker for: {step['objective'][:96]}",
                )
            else:
                self.store.update_agent_run(
                    specialist_run["id"],
                    status="Working" if not approval_required else "Waiting",
                    child_count=0,
                    summary=specialist_run["summary"],
                )

            if approval_required and step["approval_note"] not in approvals_required:
                approvals_required.append(step["approval_note"])

        self.store.update_agent_run(
            root_run["id"],
            status="Waiting" if approval_required else "Completed",
            summary="Orchestrator is waiting for approval before execution." if approval_required else "Orchestrator completed routing and synthesis.",
            completed=not approval_required,
            child_count=1,
            approval_required=approval_required,
        )
        self.store.update_agent_run(
            planner_run["id"],
            status="Waiting" if approval_required else "Completed",
            summary="Planner awaits approval on gated work." if approval_required else "Planner completed decomposition.",
            completed=not approval_required,
            child_count=specialist_count,
        )

        task_status = "Needs Approval" if approval_required else "Running"
        self.store.update_task_status(task["id"], task_status)
        self.store.update_task_run(
            task_run["id"],
            status=task_status,
            summary=summary,
            completed=False,
            step_count=len(steps),
            approval_required=approval_required,
        )

        self.store.record_event(
            event_type="orchestration.launch",
            source="orchestrator",
            payload={
                "task_run_id": task_run["id"],
                "task_id": task["id"],
                "objective": objective,
                "approval_required": approval_required,
                "steps": steps,
            },
        )

        for skill in invoked_skills:
            self.store.record_event(
                event_type="skill.invoked",
                source="orchestrator",
                payload={
                    "task_run_id": task_run["id"],
                    "skill_id": skill["id"],
                    "skill_name": skill["name"],
                    "objective": objective,
                },
            )

        if approval_required:
            self.store.record_event(
                event_type="approval.requested",
                source="policy",
                payload={
                    "task_run_id": task_run["id"],
                    "reason": "Sensitive action detected",
                    "requested_by": requested_by,
                },
            )

        self.store.record_event(
            event_type="orchestration.route",
            source="planner",
            payload={
                "task_run_id": task_run["id"],
                "agent_runs": [run["id"] for run in agent_runs],
                "worker_count": worker_count,
                "delegated_specialists": delegated_specialists,
                "intent_classification": intent_classification,
                "invoked_skills": invoked_skill_names,
                "candidate_skills": candidate_skill_names,
                "routing_notes": routing_context["notes"],
            },
        )

        decision = {
            "intent_classification": intent_classification,
            "execution_mode": "task-created",
            "delegated_specialists": delegated_specialists,
            "invoked_skills": invoked_skill_names,
            "candidate_skills": candidate_skill_names,
            "routing_notes": routing_context["notes"],
            "approvals_triggered": approval_required,
            "synthesis": self._build_synthesis(
                objective,
                delegated_specialists,
                approval_required,
                worker_count,
                invoked_skill_names,
                candidate_skill_names,
            ),
        }

        return OrchestrationResult(
            task=task,
            task_run=self.store.get_task_run(task_run["id"]) or task_run,
            agent_runs=[self.store.get_agent_run(run["id"]) or run for run in agent_runs],
            steps=steps,
            approvals_required=approvals_required,
            summary=summary,
            decision=decision,
        )

    def list_runs(self, limit: int = 10) -> list[dict[str, Any]]:
        return self.store.list_runtime_roots(limit=limit)

    def get_run(self, task_run_id: str) -> dict[str, Any]:
        task_run = self.store.get_task_run(task_run_id)
        if task_run is None:
            raise KeyError(task_run_id)
        task = self.store.get_task(task_run["task_id"])
        if task is None:
            raise KeyError(task_run["task_id"])
        return {
            "task": task,
            "task_run": task_run,
            "agent_runs": self.store.list_agent_runs(task_run_id=task_run_id, limit=100),
        }

    def _ensure_task(
        self,
        *,
        task_id: str | None,
        objective: str,
        task_title: str | None,
        task_summary: str | None,
        priority: str,
        project_id: str | None,
    ) -> dict[str, Any]:
        if task_id:
            task = self.store.get_task(task_id)
            if task is not None:
                return task
        title = task_title or self._derive_task_title(objective)
        summary = task_summary or objective
        return self.store.create_task(title=title, summary=summary, status="Inbox", priority=priority, project_id=project_id)

    def _classify_intent(self, objective: str) -> str:
        lower = objective.lower()
        if any(token in lower for token in ("schedule", "cron", "automation", "recurring")):
            return "automation"
        if any(token in lower for token in ("build", "implement", "code", "ship", "refactor", "fix")):
            return "build"
        if any(token in lower for token in ("research", "investigate", "analyze", "compare", "document")):
            return "research"
        if any(token in lower for token in ("review", "test", "validate", "audit", "verify")):
            return "evaluation"
        return "general"

    def _build_steps(self, objective: str, *, intent_classification: str) -> list[dict[str, Any]]:
        lower = objective.lower()
        steps = [
            {
                "intent": "plan",
                "objective": "Translate the request into an execution outline.",
                "assigned_agent": "Planner",
                "approval_note": "No approval gate",
                "rationale": f"Master agent classified the request as {intent_classification} and is decomposing it into bounded work.",
                "spawn_worker": False,
            }
        ]
        if any(token in lower for token in ("research", "investigate", "analyze", "compare", "document")):
            steps.append(
                {
                    "intent": "research",
                    "objective": "Gather context and verify source material.",
                    "assigned_agent": "Research Specialist",
                    "approval_note": "No approval gate",
                    "rationale": "The request needs source gathering or comparison before synthesis.",
                    "spawn_worker": True,
                }
            )
        if any(token in lower for token in ("build", "implement", "code", "ship", "refactor", "scaffold")):
            steps.append(
                {
                    "intent": "build",
                    "objective": "Implement the requested change in bounded scope.",
                    "assigned_agent": "Builder Specialist",
                    "approval_note": "No approval gate",
                    "rationale": "The request includes delivery or code-change language that warrants execution ownership.",
                    "spawn_worker": True,
                }
            )
        if any(token in lower for token in ("memory", "retrieve", "remember", "context")):
            steps.append(
                {
                    "intent": "memory",
                    "objective": "Refresh scoped memory and validate retrieval bias.",
                    "assigned_agent": "Memory Steward",
                    "approval_note": "No approval gate",
                    "rationale": "The request refers to continuity, memory, or scoped context retrieval.",
                    "spawn_worker": False,
                }
            )
        if any(token in lower for token in ("review", "test", "validate", "audit", "verify")) or len(steps) < 3:
            steps.append(
                {
                    "intent": "review",
                    "objective": "Critique the output and verify the result against expectations.",
                    "assigned_agent": "Critic / Evaluator",
                    "approval_note": "No approval gate",
                    "rationale": "The master loop keeps a critic pass in the plan so execution remains inspectable and bounded.",
                    "spawn_worker": len(objective) > 110,
                }
            )
        if any(token in lower for token in ("schedule", "cron", "automation", "recurring")):
            steps.append(
                {
                    "intent": "operations",
                    "objective": "Prepare the execution as a scheduled or repeatable run.",
                    "assigned_agent": "Operations / Scheduler",
                    "approval_note": "No approval gate",
                    "rationale": "The request asks for repeatable or scheduled operation setup.",
                    "spawn_worker": False,
                }
            )
        return steps[:5]

    def _summarize_run(self, objective: str, steps: list[dict[str, Any]], approval_required: bool) -> str:
        status = "approval required" if approval_required else "ready for execution"
        return f"{len(steps)} step plan for: {objective[:120]} ({status})."

    def _apply_skill_guidance(self, steps: list[dict[str, Any]], invoked_skill_names: list[str]) -> list[dict[str, Any]]:
        guidance = ", ".join(invoked_skill_names)
        guided_steps: list[dict[str, Any]] = []
        for step in steps:
            updated = dict(step)
            updated["rationale"] = f"{step['rationale']} Active skills informing this step: {guidance}."
            guided_steps.append(updated)
        return guided_steps

    def _apply_candidate_guidance(self, steps: list[dict[str, Any]], candidate_skill_names: list[str]) -> list[dict[str, Any]]:
        guidance = ", ".join(candidate_skill_names)
        guided_steps: list[dict[str, Any]] = []
        for step in steps:
            updated = dict(step)
            updated["rationale"] = (
                f"{step['rationale']} Learned candidates worth validating during execution: {guidance}."
            )
            guided_steps.append(updated)
        return guided_steps

    def _build_synthesis(
        self,
        objective: str,
        delegated_specialists: list[str],
        approval_required: bool,
        worker_count: int,
        invoked_skills: list[str],
        candidate_skills: list[str],
    ) -> str:
        specialist_summary = ", ".join(delegated_specialists) if delegated_specialists else "the fixed specialist team"
        state = "awaiting approval" if approval_required else "active"
        worker_summary = f"{worker_count} worker" if worker_count == 1 else f"{worker_count} workers"
        skill_summary = ""
        if invoked_skills:
            skill_summary = f" Active skills in play: {', '.join(invoked_skills)}."
        elif candidate_skills:
            skill_summary = f" Learned candidates available for validation: {', '.join(candidate_skills)}."
        return (
            f"Master agent routed this request through {specialist_summary}. "
            f"The execution plan is {state} and currently fans out to {worker_summary} where bounded delivery helps."
            f"{skill_summary}"
        )

    def _derive_task_title(self, objective: str) -> str:
        words = [word for word in objective.split() if word]
        if not words:
            return "Orchestration run"
        return " ".join(words[:6]).strip().capitalize()

    def _specialist_for_step(self, intent: str, objective: str) -> str:
        by_intent = {
            "plan": "Planner",
            "research": "Research Specialist",
            "build": "Builder Specialist",
            "memory": "Memory Steward",
            "review": "Critic / Evaluator",
            "operations": "Operations / Scheduler",
        }
        if intent in by_intent:
            return by_intent[intent]
        lower = f"{intent} {objective}".lower()
        for keywords, specialist in SPECIALIST_BY_KEYWORD:
            if any(keyword in lower for keyword in keywords):
                return specialist
        return "Planner"

    def _create_specialist_run(
        self,
        *,
        task_run_id: str,
        parent_run_id: str,
        objective: str,
        specialist: str,
        recursion_depth: int,
        child_count: int,
        approval_required: bool,
    ) -> dict[str, Any]:
        agent_id = SPECIALIST_IDS[specialist]
        summary = f"{specialist} is coordinating the bounded step for: {objective[:96]}"
        run = self.store.create_agent_run(
            agent_id=agent_id,
            agent_name=specialist,
            agent_role=specialist,
            run_kind="specialist",
            status="Working" if not approval_required else "Waiting",
            objective=objective,
            summary=summary,
            task_run_id=task_run_id,
            parent_run_id=parent_run_id,
            recursion_depth=recursion_depth,
            child_count=0,
            budget_units=40,
            approval_required=approval_required,
        )
        self.store.record_event(
            event_type="agent.delegate",
            source=specialist,
            payload={
                "task_run_id": task_run_id,
                "parent_run_id": parent_run_id,
                "agent_run_id": run["id"],
                "objective": objective,
                "specialist": specialist,
            },
        )
        return run

    def _spawn_worker(
        self,
        *,
        task_run_id: str,
        parent_run_id: str,
        objective: str,
        specialist: str,
        recursion_depth: int,
        child_count: int,
        approval_required: bool,
    ) -> dict[str, Any]:
        if recursion_depth > 2:
            raise ValueError("recursion depth limit exceeded")
        if child_count > 3:
            raise ValueError("child count limit exceeded")
        worker_agent_id = f"worker-{specialist.lower().replace(' / ', '-').replace(' ', '-')}-{uuid4().hex[:8]}"
        run = self.store.create_agent_run(
            agent_id=worker_agent_id,
            agent_name=f"{specialist} Worker",
            agent_role=f"Ephemeral worker for {specialist}",
            run_kind="worker",
            status="Working",
            objective=objective,
            summary=f"Worker completed a bounded subtask for {specialist}.",
            task_run_id=task_run_id,
            parent_run_id=parent_run_id,
            recursion_depth=recursion_depth,
            child_count=0,
            budget_units=20,
            approval_required=approval_required,
        )
        self.store.record_event(
            event_type="agent.spawn",
            source=specialist,
            payload={
                "task_run_id": task_run_id,
                "parent_run_id": parent_run_id,
                "agent_run_id": run["id"],
                "worker_agent_id": worker_agent_id,
                "objective": objective,
            },
        )
        self.store.update_agent_run(run["id"], status="Completed", completed=True, summary=run["summary"])
        return self.store.get_agent_run(run["id"]) or run
