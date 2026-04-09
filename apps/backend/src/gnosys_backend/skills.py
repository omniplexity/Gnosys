from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from .store import GnosysStore, utc_now


PROMOTION_TEST_THRESHOLD = 0.7


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 1}


def _bump_version(version: str) -> str:
    parts = version.split(".")
    if len(parts) >= 3 and all(part.isdigit() for part in parts[:3]):
        major, minor, patch = (int(parts[0]), int(parts[1]), int(parts[2]))
        return f"{major}.{minor}.{patch + 1}"
    if version.endswith("-draft"):
        return version
    return f"{version}.1"


@dataclass(slots=True)
class SkillLifecycleResult:
    skill: dict[str, Any]
    parent_skill: dict[str, Any] | None
    related_skills: list[dict[str, Any]]
    test_runs: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    lifecycle_state: str
    ready_for_promotion: bool


class SkillEngine:
    def __init__(self, store: GnosysStore) -> None:
        self.store = store

    def create_learned_draft(self, skill_id: str, *, requested_by: str = "ui") -> dict[str, Any]:
        source = self.store.get_skill(skill_id)
        if source is None:
            raise KeyError(skill_id)
        draft = self.store.create_skill(
            name=f"{source['name']} Draft",
            description=source["description"],
            scope=source["scope"],
            version=_bump_version(str(source["version"])),
            source_type="learned",
            status="draft",
            parent_skill_id=source["id"],
            project_id=source.get("project_id"),
            provenance_summary=f"Draft forked from {source['name']} ({source['id']}).",
            invocation_hints=source.get("invocation_hints", []),
        )
        self.store.record_event(
            event_type="skill.draft_created",
            source="skill-engine",
            payload={
                "skill_id": draft["id"],
                "parent_skill_id": source["id"],
                "requested_by": requested_by,
            },
        )
        return draft

    def propose_from_session(self, chat_session_id: str, *, requested_by: str = "ui") -> dict[str, Any]:
        session = self.store.get_chat_session(chat_session_id)
        if session is None:
            raise KeyError(chat_session_id)
        reflections = self.store.list_session_reflections(chat_session_id, limit=10)
        if not reflections:
            raise ValueError("Session does not have enough reflection data to propose a skill")

        pattern_pool: list[str] = []
        for reflection in reflections:
            pattern_pool.extend(reflection.get("recurring_goals", []))
            pattern_pool.extend(reflection.get("working_style", []))
            pattern_pool.extend(reflection.get("user_preferences", []))
        if not pattern_pool:
            raise ValueError("No repeatable workflow pattern was found in the session reflections")

        title_seed = pattern_pool[0]
        base_name = " ".join(title_seed.split()[:4]).strip().title() or "Session Workflow"
        name = f"{base_name} Skill"
        description = (
            f"Learned from {session['title']}. Repeats the workflow pattern: "
            f"{'; '.join(pattern_pool[:3])}"
        )
        related_active = [
            skill for skill in self.store.list_skills()
            if skill["status"] == "active" and (_tokenize(skill["name"]) & _tokenize(name))
        ]
        parent_skill_id = related_active[0]["id"] if related_active else None
        proposed = self.store.create_skill(
            name=name,
            description=description,
            scope="session",
            version="0.1.0",
            source_type="learned",
            status="candidate",
            parent_skill_id=parent_skill_id,
            provenance_summary=f"Learned from session reflections for {session['title']}.",
            evidence_count=len(reflections),
            success_signals=[f"{len(reflections)} session reflections informed this draft"],
            invocation_hints=list(_tokenize(" ".join(pattern_pool[:4]))),
        )
        self.store.record_event(
            event_type="skill.proposed",
            source="skill-engine",
            payload={
                "skill_id": proposed["id"],
                "chat_session_id": chat_session_id,
                "parent_skill_id": parent_skill_id,
                "requested_by": requested_by,
            },
        )
        return proposed

    def improve_skill(self, skill_id: str, *, requested_by: str = "ui") -> dict[str, Any]:
        skill = self.store.get_skill(skill_id)
        if skill is None:
            raise KeyError(skill_id)
        latest_tests = self.store.list_skill_test_runs(skill_id=skill_id, limit=3)
        refinement_notes = [run["summary"] for run in latest_tests] or ["Refine coverage and reusable execution steps."]
        improved = self.store.create_skill(
            name=f"{skill['name']} Draft",
            description=f"{skill['description']} Improvement notes: {' '.join(refinement_notes[:2])}",
            scope=skill["scope"],
            version=_bump_version(str(skill["version"])),
            source_type="learned",
            status="draft",
            parent_skill_id=skill["id"],
            project_id=skill.get("project_id"),
            provenance_summary=f"Recursive improvement draft derived from {skill['id']}.",
            evidence_count=max(1, len(latest_tests)),
            success_signals=[run["summary"] for run in latest_tests[:3]],
            invocation_hints=skill.get("invocation_hints", []),
        )
        self.store.record_event(
            event_type="skill.improved",
            source="skill-engine",
            payload={"skill_id": improved["id"], "parent_skill_id": skill_id, "requested_by": requested_by},
        )
        return improved

    def find_matching_skills(self, objective: str, *, project_id: str | None = None, limit: int = 3) -> list[dict[str, Any]]:
        objective_tokens = _tokenize(objective)
        matches: list[tuple[float, dict[str, Any]]] = []
        for skill in self.store.list_skills():
            if skill["status"] != "active":
                continue
            if project_id and skill.get("project_id") not in {None, project_id}:
                continue
            skill_tokens = _tokenize(" ".join([skill["name"], skill["description"], skill["scope"], skill["source_type"]]))
            overlap = len(objective_tokens & skill_tokens)
            if overlap == 0:
                continue
            score = overlap + float(skill.get("test_score", 0.0))
            matches.append((score, skill))
        matches.sort(key=lambda item: item[0], reverse=True)
        return [skill for _, skill in matches[:limit]]

    def find_routing_context(self, objective: str, *, project_id: str | None = None, limit: int = 3) -> dict[str, Any]:
        active_skills = self.find_matching_skills(objective, project_id=project_id, limit=limit)
        objective_tokens = _tokenize(objective)
        candidate_matches: list[tuple[float, dict[str, Any]]] = []
        for skill in self.store.list_skills():
            if skill["status"] != "candidate":
                continue
            if project_id and skill.get("project_id") not in {None, project_id}:
                continue
            hint_tokens = _tokenize(
                " ".join(
                    [
                        skill["name"],
                        skill["description"],
                        " ".join(skill.get("invocation_hints", [])),
                        " ".join(skill.get("success_signals", [])),
                    ]
                )
            )
            overlap = len(objective_tokens & hint_tokens)
            if overlap == 0:
                continue
            score = overlap + min(float(skill.get("evidence_count", 0)) * 0.25, 1.0)
            candidate_matches.append((score, skill))
        candidate_matches.sort(key=lambda item: item[0], reverse=True)
        candidates = [skill for _, skill in candidate_matches[:limit]]
        notes = [
            f"Active skills: {', '.join(skill['name'] for skill in active_skills)}"
            if active_skills
            else "No active skills matched this objective.",
            f"Learned candidates: {', '.join(skill['name'] for skill in candidates)}"
            if candidates
            else "No learned candidates were close enough to bias routing.",
        ]
        return {"active": active_skills, "candidates": candidates, "notes": notes}

    def test_skill(
        self,
        skill_id: str,
        *,
        scenario: str,
        expected_outcome: str,
        requested_by: str = "ui",
    ) -> dict[str, Any]:
        skill = self.store.get_skill(skill_id)
        if skill is None:
            raise KeyError(skill_id)
        skill_text = " ".join([skill["name"], skill["description"], skill["scope"], skill["source_type"], skill["status"]])
        scenario_tokens = _tokenize(scenario)
        expected_tokens = _tokenize(expected_outcome)
        skill_tokens = _tokenize(skill_text)
        scenario_overlap = len(skill_tokens & scenario_tokens)
        expected_overlap = len(skill_tokens & expected_tokens)
        coverage = (scenario_overlap * 0.45) + (expected_overlap * 0.45)
        score = min(1.0, 0.25 + coverage + (0.1 if skill["source_type"] == "learned" else 0.05))
        passed = score >= PROMOTION_TEST_THRESHOLD
        observed_outcome = (
            f"Observed {skill['name']} against scenario '{scenario}' with {scenario_overlap} scenario matches and "
            f"{expected_overlap} expected matches."
        )
        summary = "Skill test passed." if passed else "Skill test needs refinement."
        test_run = self.store.create_skill_test_run(
            skill_id=skill_id,
            scenario=scenario,
            expected_outcome=expected_outcome,
            observed_outcome=observed_outcome,
            passed=passed,
            score=round(score, 4),
            summary=summary,
            requested_by=requested_by,
        )
        self.store.update_skill(
            skill_id,
            name=skill["name"],
            description=skill["description"],
            scope=skill["scope"],
            version=skill["version"],
            source_type=skill["source_type"],
            status="candidate" if skill["status"] == "draft" else skill["status"],
            parent_skill_id=skill.get("parent_skill_id"),
            promoted_from_skill_id=skill.get("promoted_from_skill_id"),
            latest_test_run_id=test_run["id"],
            test_status="passed" if passed else "failed",
            test_score=score,
            test_summary=summary,
            project_id=skill.get("project_id"),
            provenance_summary=skill.get("provenance_summary"),
            evidence_count=int(skill.get("evidence_count", 0)),
            success_signals=skill.get("success_signals", []),
            invocation_hints=skill.get("invocation_hints", []),
        )
        self.store.record_event(
            event_type="skill.tested",
            source="skill-engine",
            payload={
                "skill_id": skill_id,
                "test_run_id": test_run["id"],
                "passed": passed,
                "score": score,
                "requested_by": requested_by,
            },
        )
        return test_run

    def promote_skill(self, skill_id: str, *, requested_by: str = "ui") -> dict[str, Any]:
        skill = self.store.get_skill(skill_id)
        if skill is None:
            raise KeyError(skill_id)
        if skill.get("test_status") != "passed" or float(skill.get("test_score", 0.0)) < PROMOTION_TEST_THRESHOLD:
            raise ValueError("Skill must pass testing before promotion")

        related_active = [
            item
            for item in self.store.list_skills()
            if item["id"] != skill_id
            and item["name"] == skill["name"]
            and item.get("project_id") == skill.get("project_id")
            and item["status"] == "active"
        ]
        previous_active_id = related_active[0]["id"] if related_active else skill.get("parent_skill_id")
        for sibling in related_active:
            self.store.update_skill(
                sibling["id"],
                name=sibling["name"],
                description=sibling["description"],
                scope=sibling["scope"],
                version=sibling["version"],
                source_type=sibling["source_type"],
                status="deprecated",
                parent_skill_id=sibling.get("parent_skill_id"),
                promoted_from_skill_id=skill_id,
                latest_test_run_id=sibling.get("latest_test_run_id"),
                test_status=sibling.get("test_status", "untested"),
                test_score=float(sibling.get("test_score", 0.0)),
                test_summary=sibling.get("test_summary", ""),
                project_id=sibling.get("project_id"),
                provenance_summary=sibling.get("provenance_summary"),
                evidence_count=int(sibling.get("evidence_count", 0)),
                success_signals=sibling.get("success_signals", []),
                invocation_hints=sibling.get("invocation_hints", []),
                promotion_summary=f"Deprecated in favor of {skill_id}.",
                rollback_summary=sibling.get("rollback_summary", ""),
            )

        promoted_at = utc_now()
        promoted = self.store.update_skill(
            skill_id,
            name=skill["name"],
            description=skill["description"],
            scope=skill["scope"],
            version=skill["version"],
            source_type=skill["source_type"],
            status="active",
            parent_skill_id=skill.get("parent_skill_id"),
            promoted_from_skill_id=previous_active_id,
            latest_test_run_id=skill.get("latest_test_run_id"),
            test_status=skill.get("test_status", "passed"),
            test_score=float(skill.get("test_score", 0.0)),
            test_summary=skill.get("test_summary", ""),
            project_id=skill.get("project_id"),
            provenance_summary=skill.get("provenance_summary"),
            evidence_count=int(skill.get("evidence_count", 0)),
            success_signals=skill.get("success_signals", []),
            invocation_hints=skill.get("invocation_hints", []),
            promotion_summary=f"Promoted after passing tests with score {float(skill.get('test_score', 0.0)):.2f}.",
            last_promoted_at=promoted_at,
        )
        self.store.record_event(
            event_type="skill.promoted",
            source="skill-engine",
            payload={
                "skill_id": skill_id,
                "previous_skill_id": previous_active_id,
                "requested_by": requested_by,
            },
        )
        return promoted

    def rollback_skill(self, skill_id: str, *, requested_by: str = "ui") -> dict[str, Any]:
        skill = self.store.get_skill(skill_id)
        if skill is None:
            raise KeyError(skill_id)
        target_id = skill.get("promoted_from_skill_id") or skill.get("parent_skill_id")
        if not target_id:
            raise ValueError("No previous skill version is available for rollback")
        target = self.store.get_skill(str(target_id))
        if target is None:
            raise KeyError(str(target_id))

        self.store.update_skill(
            skill_id,
            name=skill["name"],
            description=skill["description"],
            scope=skill["scope"],
            version=skill["version"],
            source_type=skill["source_type"],
            status="archived",
            parent_skill_id=skill.get("parent_skill_id"),
            promoted_from_skill_id=skill.get("promoted_from_skill_id"),
            latest_test_run_id=skill.get("latest_test_run_id"),
            test_status=skill.get("test_status", "untested"),
            test_score=float(skill.get("test_score", 0.0)),
            test_summary=f"Rolled back to {target['id']}",
            project_id=skill.get("project_id"),
            provenance_summary=skill.get("provenance_summary"),
            evidence_count=int(skill.get("evidence_count", 0)),
            success_signals=skill.get("success_signals", []),
            invocation_hints=skill.get("invocation_hints", []),
            rollback_summary=f"Archived after rollback to {target['id']}.",
            last_rolled_back_at=utc_now(),
        )
        restored = self.store.update_skill(
            target["id"],
            name=target["name"],
            description=target["description"],
            scope=target["scope"],
            version=target["version"],
            source_type=target["source_type"],
            status="active",
            parent_skill_id=target.get("parent_skill_id"),
            promoted_from_skill_id=skill_id,
            latest_test_run_id=target.get("latest_test_run_id"),
            test_status=target.get("test_status", "untested"),
            test_score=float(target.get("test_score", 0.0)),
            test_summary=target.get("test_summary", ""),
            project_id=target.get("project_id"),
            provenance_summary=target.get("provenance_summary"),
            evidence_count=int(target.get("evidence_count", 0)),
            success_signals=target.get("success_signals", []),
            invocation_hints=target.get("invocation_hints", []),
            rollback_summary=f"Restored after rollback of {skill_id}.",
            last_rolled_back_at=utc_now(),
        )
        self.store.record_event(
            event_type="skill.rolled_back",
            source="skill-engine",
            payload={
                "skill_id": skill_id,
                "restored_skill_id": restored["id"],
                "requested_by": requested_by,
            },
        )
        return restored

    def get_lifecycle(self, skill_id: str) -> SkillLifecycleResult:
        skill = self.store.get_skill(skill_id)
        if skill is None:
            raise KeyError(skill_id)
        parent_skill = self.store.get_skill(str(skill["parent_skill_id"])) if skill.get("parent_skill_id") else None
        related_skills = [
            item
            for item in self.store.list_skills()
            if item.get("parent_skill_id") == skill_id or item.get("promoted_from_skill_id") == skill_id
        ]
        test_runs = self.store.list_skill_test_runs(skill_id=skill_id, limit=20)
        evidence = self.store.list_skill_learning_evidence(skill_id=skill_id, limit=20)
        ready_for_promotion = skill["status"] in {"draft", "candidate"} and skill.get("test_status") == "passed" and float(skill.get("test_score", 0.0)) >= PROMOTION_TEST_THRESHOLD
        if skill["status"] == "active":
            lifecycle_state = "active"
        elif skill["status"] == "candidate":
            lifecycle_state = "candidate"
        elif skill["status"] == "deprecated":
            lifecycle_state = "deprecated"
        elif skill["status"] == "archived":
            lifecycle_state = "archived"
        elif test_runs:
            lifecycle_state = "tested"
        else:
            lifecycle_state = "draft"
        return SkillLifecycleResult(
            skill=skill,
            parent_skill=parent_skill,
            related_skills=related_skills,
            test_runs=test_runs,
            evidence=evidence,
            lifecycle_state=lifecycle_state,
            ready_for_promotion=ready_for_promotion,
        )
