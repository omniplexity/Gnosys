from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from ..store import GnosysStore


STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "into",
    "this",
    "that",
    "your",
    "their",
    "have",
    "will",
    "about",
    "should",
    "through",
    "runtime",
    "task",
    "work",
}


def _tokenize(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 2 and token not in STOPWORDS]


@dataclass(slots=True)
class SkillLearningSummary:
    created_skills: list[dict[str, Any]]
    analyzed_runs: int
    repeated_patterns: int
    skipped_patterns: int


class SkillLearningService:
    def __init__(self, store: GnosysStore) -> None:
        self.store = store

    def extract_from_recent_runs(self, *, requested_by: str = "ui", limit: int = 12) -> SkillLearningSummary:
        runs = [
            run
            for run in self.store.list_task_runs(limit=limit)
            if str(run.get("status", "")).lower() == "completed" and not bool(run.get("approval_required"))
        ]
        patterns = self._group_repeated_patterns(runs)
        created_skills: list[dict[str, Any]] = []
        skipped_patterns = 0

        for pattern in patterns:
            if self._has_existing_signature(pattern["signature"]):
                skipped_patterns += 1
                continue
            skill = self._create_skill_from_pattern(pattern, requested_by=requested_by)
            created_skills.append(skill)

        return SkillLearningSummary(
            created_skills=created_skills,
            analyzed_runs=len(runs),
            repeated_patterns=len(patterns),
            skipped_patterns=skipped_patterns,
        )

    def _group_repeated_patterns(self, runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for run in runs:
            agent_runs = self.store.list_agent_runs(task_run_id=str(run["id"]), limit=50)
            specialists = [
                str(agent_run["agent_name"])
                for agent_run in agent_runs
                if agent_run.get("run_kind") == "specialist" and agent_run.get("agent_name") not in {"Planner", "Orchestrator"}
            ]
            keywords = _tokenize(str(run.get("objective", "")))[:2]
            if not specialists or not keywords:
                continue
            signature = f"{'-'.join(keywords)}::{'>'.join(sorted(set(specialists)))}"
            grouped.setdefault(signature, []).append({"run": run, "agent_runs": agent_runs, "specialists": specialists, "keywords": keywords})

        patterns: list[dict[str, Any]] = []
        for signature, episodes in grouped.items():
            if len(episodes) < 2:
                continue
            patterns.append(
                {
                    "signature": signature,
                    "episodes": episodes,
                    "keywords": episodes[0]["keywords"],
                    "specialists": sorted({specialist for episode in episodes for specialist in episode["specialists"]}),
                    "project_id": episodes[0]["run"].get("project_id"),
                }
            )
        patterns.sort(key=lambda item: len(item["episodes"]), reverse=True)
        return patterns

    def _has_existing_signature(self, signature: str) -> bool:
        for skill in self.store.list_skills():
            hints = skill.get("invocation_hints", [])
            if isinstance(hints, list) and signature in hints:
                return True
        return False

    def _create_skill_from_pattern(self, pattern: dict[str, Any], *, requested_by: str) -> dict[str, Any]:
        keywords = pattern["keywords"]
        specialists = pattern["specialists"]
        episodes = pattern["episodes"]
        name = f"{' '.join(word.title() for word in keywords)} Procedure"
        description = (
            f"Learned from {len(episodes)} successful runs. Reuses the repeated specialist path "
            f"{', '.join(specialists)} for objectives related to {' and '.join(keywords)}."
        )
        evidence_count = len(episodes)
        success_signals = [
            f"{evidence_count} completed runs without approval gating",
            f"Specialist path: {' -> '.join(specialists)}",
        ]
        invocation_hints = [pattern["signature"], *keywords, *specialists]
        provenance_summary = f"Derived from repeated successful run pattern {pattern['signature']}."
        skill = self.store.create_skill(
            name=name,
            description=description,
            scope="workspace" if pattern.get("project_id") is None else "project",
            version="0.1.0",
            source_type="learned",
            status="candidate",
            project_id=pattern.get("project_id"),
            provenance_summary=provenance_summary,
            evidence_count=evidence_count,
            success_signals=success_signals,
            invocation_hints=invocation_hints,
            promotion_summary="Awaiting explicit review and test validation before activation.",
        )

        for episode in episodes:
            run = episode["run"]
            agent_runs = [
                agent_run
                for agent_run in episode["agent_runs"]
                if agent_run.get("run_kind") == "specialist" and agent_run.get("agent_name") in specialists
            ]
            summary = (
                f"{run['objective']} | specialists: "
                f"{', '.join(agent_run['agent_name'] for agent_run in agent_runs[:3])}"
            )
            self.store.create_skill_learning_evidence(
                skill_id=str(skill["id"]),
                task_run_id=str(run["id"]),
                agent_run_id=str(agent_runs[0]["id"]) if agent_runs else None,
                source_kind="task_run",
                pattern_signature=pattern["signature"],
                evidence_summary=summary,
                success_score=1.0,
            )

        self.store.record_event(
            event_type="skill.learned",
            source="skill-learning",
            payload={
                "skill_id": skill["id"],
                "pattern_signature": pattern["signature"],
                "evidence_count": evidence_count,
                "requested_by": requested_by,
            },
        )
        return self.store.get_skill(str(skill["id"])) or skill
