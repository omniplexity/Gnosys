"""
Skill System - Autonomous skill detection, extraction, storage, and refinement.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gnosys_backend.config import SkillsConfig
from gnosys_backend.db import Database, decode_json, encode_json
from gnosys_backend.models import (
    SkillCreateRequest,
    SkillListResponse,
    SkillMatchRequest,
    SkillMatchResponse,
    SkillRecord,
    SkillRefineRequest,
    SkillRefineResponse,
)


class SkillSystem:
    """Autonomous skill system for extracting and managing reusable workflows."""

    def __init__(self, db: Database, config: SkillsConfig) -> None:
        self._db = db
        self._config = config
        self._skills_dir = config.storage.directory.expanduser().resolve()
        self._skills_dir.mkdir(parents=True, exist_ok=True)

    async def detect_patterns_from_trajectories(
        self,
        trajectory_limit: int = 100,
        min_frequency: int = 3,
        min_sequence_length: int = 2,
    ) -> list[dict[str, Any]]:
        """
        Analyze trajectories to detect repeated tool sequences.

        Returns list of detected patterns with tool sequences and frequency.
        """
        # Get recent trajectories
        trajectories = self._db.fetch_all(
            """
            SELECT steps_json, success 
            FROM trajectories 
            ORDER BY started_at DESC 
            LIMIT ?
            """,
            (trajectory_limit,),
        )

        if not trajectories:
            return []

        # Extract tool sequences
        tool_sequences: list[tuple[tuple[str, ...], bool]] = []
        for row in trajectories:
            steps = decode_json(row["steps_json"])
            if len(steps) >= min_sequence_length:
                sequence = tuple(step.get("tool") for step in steps if step.get("tool"))
                if len(sequence) >= min_sequence_length:
                    tool_sequences.append((sequence, bool(row["success"])))

        if not tool_sequences:
            return []

        # Count sequence frequencies
        sequence_counts: dict[tuple[str, ...], dict[str, Any]] = {}
        for sequence, success in tool_sequences:
            if sequence not in sequence_counts:
                sequence_counts[sequence] = {
                    "sequence": list(sequence),
                    "frequency": 0,
                    "success_count": 0,
                }
            sequence_counts[sequence]["frequency"] += 1
            if success:
                sequence_counts[sequence]["success_count"] += 1

        # Filter by minimum frequency and calculate success rate
        patterns = []
        for seq, data in sequence_counts.items():
            if data["frequency"] >= min_frequency:
                success_rate = data["success_count"] / data["frequency"]
                if success_rate >= self._config.detection.success_threshold:
                    patterns.append(
                        {
                            "tools": data["sequence"],
                            "frequency": data["frequency"],
                            "success_rate": success_rate,
                        }
                    )

        return sorted(patterns, key=lambda p: p["frequency"], reverse=True)

    async def extract_skill(
        self,
        name: str,
        tools: list[str],
        workflow: list[str],
        triggers: list[str] | None = None,
        parameters: dict[str, Any] | None = None,
        compounds_from: list[str] | None = None,
        description: str | None = None,
    ) -> SkillRecord:
        """Extract and store a new skill."""
        now = datetime.now(timezone.utc)
        skill_id = str(uuid.uuid4())
        version = "1.0.0"

        # Store in database
        self._db.execute(
            """
            INSERT INTO skills (
                id, name, version, triggers_json, workflow_json, tools_json,
                parameters_json, description, compounds_from_json, use_count,
                success_rate, trigger_count, created_at, updated_at, last_used_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                skill_id,
                name,
                version,
                encode_json(triggers or []),
                encode_json(workflow),
                encode_json(tools),
                encode_json(parameters or {}),
                description,
                encode_json(compounds_from or []),
                0,
                0.0,
                0,
                now.isoformat(),
                now.isoformat(),
                None,
            ),
        )

        # Create SKILL.md file
        await self._write_skill_file(
            skill_id=skill_id,
            name=name,
            version=version,
            triggers=triggers or [],
            workflow=workflow,
            tools=tools,
            parameters=parameters or {},
            description=description,
            compounds_from=compounds_from or [],
        )

        return SkillRecord(
            id=skill_id,
            name=name,
            version=version,
            triggers=triggers or [],
            workflow=workflow,
            tools=tools,
            parameters=parameters or {},
            description=description,
            compounds_from=compounds_from or [],
            use_count=0,
            success_rate=0.0,
            trigger_count=0,
            created_at=now,
            updated_at=now,
            last_used_at=None,
        )

    async def _write_skill_file(
        self,
        skill_id: str,
        name: str,
        version: str,
        triggers: list[str],
        workflow: list[str],
        tools: list[str],
        parameters: dict[str, Any],
        description: str | None,
        compounds_from: list[str],
    ) -> None:
        """Write SKILL.md file for the skill."""
        # Use skill_id for directory to avoid name collision issues
        # (e.g., "Data Export" and "data_export" would collide if using name)
        skill_dir = self._skills_dir / skill_id
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_md = f"""# Skill: {name}

**Version**: {version}
**ID**: {skill_id}

## Triggers
{chr(10).join(f"- {t}" for t in triggers) if triggers else "- (auto-detected)"}

## Workflow
{chr(10).join(f"{i + 1}. {step}" for i, step in enumerate(workflow))}

## Tools
{", ".join(tools) if tools else "N/A"}

## Parameters
{json.dumps(parameters, indent=2) if parameters else "None"}

## Description
{description or "Auto-extracted skill from task execution patterns."}

## Metadata
- **Use Count**: 0
- **Success Rate**: 0.0
- **Compounds From**: {", ".join(compounds_from) if compounds_from else "None"}
"""
        (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

        # Write metadata.json
        metadata = {
            "id": skill_id,
            "name": name,
            "version": version,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "use_count": 0,
            "success_rate": 0.0,
            "trigger_count": 0,
            "compounds_from": compounds_from,
        }
        (skill_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )

    async def list_skills(self) -> SkillListResponse:
        """List all skills."""
        rows = self._db.fetch_all(
            """
            SELECT id, name, version, triggers_json, workflow_json, tools_json,
                   parameters_json, description, compounds_from_json, use_count,
                   success_rate, trigger_count, created_at, updated_at, last_used_at
            FROM skills
            ORDER BY use_count DESC
            """
        )

        skills = []
        for row in rows:
            skills.append(
                SkillRecord(
                    id=row["id"],
                    name=row["name"],
                    version=row["version"],
                    triggers=decode_json(row["triggers_json"]),
                    workflow=decode_json(row["workflow_json"]),
                    tools=decode_json(row["tools_json"]),
                    parameters=decode_json(row["parameters_json"]),
                    description=row["description"],
                    compounds_from=decode_json(row["compounds_from_json"]),
                    use_count=row["use_count"],
                    success_rate=row["success_rate"],
                    trigger_count=row["trigger_count"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                    # Normalize to naive datetime to avoid timezone issues
                    last_used_at=datetime.fromisoformat(row["last_used_at"]).replace(
                        tzinfo=None
                    )
                    if row["last_used_at"]
                    else None,
                )
            )

        return SkillListResponse(count=len(skills), skills=skills)

    async def get_skill(self, skill_id: str) -> SkillRecord | None:
        """Get a skill by ID."""
        row = self._db.fetch_one(
            """
            SELECT id, name, version, triggers_json, workflow_json, tools_json,
                   parameters_json, description, compounds_from_json, use_count,
                   success_rate, trigger_count, created_at, updated_at, last_used_at
            FROM skills WHERE id = ?
            """,
            (skill_id,),
        )

        if not row:
            return None

        return SkillRecord(
            id=row["id"],
            name=row["name"],
            version=row["version"],
            triggers=decode_json(row["triggers_json"]),
            workflow=decode_json(row["workflow_json"]),
            tools=decode_json(row["tools_json"]),
            parameters=decode_json(row["parameters_json"]),
            description=row["description"],
            compounds_from=decode_json(row["compounds_from_json"]),
            use_count=row["use_count"],
            success_rate=row["success_rate"],
            trigger_count=row["trigger_count"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            last_used_at=datetime.fromisoformat(row["last_used_at"])
            if row["last_used_at"]
            else None,
        )

    async def match_skill(self, request: SkillMatchRequest) -> SkillMatchResponse:
        """Match a task description to the best fitting skill."""
        task_lower = request.task.lower()

        # Get all skills
        skills_response = await self.list_skills()
        if not skills_response.skills:
            return SkillMatchResponse(matched=False, skill=None, confidence=0.0)

        best_match: SkillRecord | None = None
        best_confidence = 0.0

        for skill in skills_response.skills:
            confidence = 0.0

            # Check triggers
            for trigger in skill.triggers:
                if trigger.lower() in task_lower:
                    confidence += 0.5

            # Check tool overlap with task context
            if request.context:
                context_str = str(request.context).lower()
                for tool in skill.tools:
                    if tool.lower() in context_str:
                        confidence += 0.3

            # Bonus for high use count and success rate
            if skill.use_count > 0:
                confidence += min(skill.use_count / 100, 0.2)
            if skill.success_rate > 0.8:
                confidence += 0.1

            if confidence > best_confidence:
                best_confidence = confidence
                best_match = skill

        if best_match and best_confidence >= 0.3:
            # Update usage stats
            await self._record_skill_usage(best_match.id, success=True)
            return SkillMatchResponse(
                matched=True,
                skill=best_match,
                confidence=min(best_confidence, 1.0),
            )

        return SkillMatchResponse(matched=False, skill=None, confidence=0.0)

    async def _record_skill_usage(self, skill_id: str, success: bool) -> None:
        """Record skill usage for analytics."""
        row = self._db.fetch_one(
            "SELECT use_count, success_rate, trigger_count FROM skills WHERE id = ?",
            (skill_id,),
        )
        if not row:
            return

        new_use_count = row["use_count"] + 1
        new_trigger_count = row["trigger_count"] + 1
        # Update success rate using exponential moving average
        old_rate = row["success_rate"]
        new_rate = old_rate * 0.9 + (1.0 if success else 0.0) * 0.1

        now = datetime.now(timezone.utc)
        self._db.execute(
            """
            UPDATE skills 
            SET use_count = ?, success_rate = ?, trigger_count = ?,
                updated_at = ?, last_used_at = ?
            WHERE id = ?
            """,
            (
                new_use_count,
                new_rate,
                new_trigger_count,
                now.isoformat(),
                now.isoformat(),
                skill_id,
            ),
        )

    async def refine_skill(
        self, skill_id: str, request: SkillRefineRequest
    ) -> SkillRefineResponse:
        """Refine a skill based on feedback."""
        skill = await self.get_skill(skill_id)
        if not skill:
            raise ValueError(f"Skill {skill_id} not found")

        # Validate version format before parsing
        version_pattern = re.compile(r"^\d+\.\d+\.\d+$")
        if not skill.version or not version_pattern.match(skill.version):
            raise ValueError(f"Invalid version format: {skill.version}")

        # Parse current version
        major, minor, patch = map(int, skill.version.split("."))

        # Increment version based on feedback
        if request.success:
            # Minor version bump for improvements
            minor += 1
        else:
            # Patch version bump for bug fixes
            patch += 1

        new_version = f"{major}.{minor}.{patch}"
        now = datetime.now(timezone.utc)

        # Update skill in database
        self._db.execute(
            """
            UPDATE skills 
            SET version = ?, updated_at = ?
            WHERE id = ?
            """,
            (new_version, now.isoformat(), skill_id),
        )

        # Update SKILL.md file
        skill_dir = self._skills_dir / skill.name.replace(" ", "_").lower()
        if skill_dir.exists():
            skill_md_path = skill_dir / "SKILL.md"
            if skill_md_path.exists():
                content = skill_md_path.read_text(encoding="utf-8")
                content = content.replace(
                    f"**Version**: {skill.version}",
                    f"**Version**: {new_version}",
                )
                skill_md_path.write_text(content, encoding="utf-8")

        updated_skill = await self.get_skill(skill_id)
        if not updated_skill:
            raise ValueError(f"Failed to retrieve updated skill {skill_id}")

        return SkillRefineResponse(
            skill=updated_skill,
            previous_version=skill.version,
            new_version=new_version,
        )

    async def delete_skill(self, skill_id: str) -> bool:
        """Delete a skill."""
        skill = await self.get_skill(skill_id)
        if not skill:
            return False

        # Delete from database
        self._db.execute("DELETE FROM skills WHERE id = ?", (skill_id,))

        # Delete skill files
        skill_dir = self._skills_dir / skill.name.replace(" ", "_").lower()
        if skill_dir.exists():
            import shutil

            shutil.rmtree(skill_dir)

        return True

    async def get_skill_stats(self) -> dict[str, Any]:
        """Get skill system statistics."""
        row = self._db.fetch_one(
            "SELECT COUNT(*) as total, SUM(use_count) as total_uses FROM skills"
        )
        if not row or row["total"] == 0:
            return {
                "total_skills": 0,
                "total_uses": 0,
                "avg_success_rate": 0.0,
                "top_skills": [],
            }

        # Get top skills
        top_rows = self._db.fetch_all(
            "SELECT name, use_count, success_rate FROM skills ORDER BY use_count DESC LIMIT 5"
        )
        top_skills = [
            {
                "name": r["name"],
                "use_count": r["use_count"],
                "success_rate": r["success_rate"],
            }
            for r in top_rows
        ]

        # Calculate average success rate
        avg_rate_row = self._db.fetch_one(
            "SELECT AVG(success_rate) as avg_rate FROM skills WHERE use_count > 0"
        )
        avg_rate = (
            avg_rate_row["avg_rate"]
            if avg_rate_row and avg_rate_row["avg_rate"]
            else 0.0
        )

        return {
            "total_skills": row["total"],
            "total_uses": row["total_uses"] or 0,
            "avg_success_rate": round(avg_rate, 2),
            "top_skills": top_skills,
        }
