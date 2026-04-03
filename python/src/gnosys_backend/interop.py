"""
Data Interoperability module for Gnosys.

Provides import/export formats and compatibility with other systems.
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


# ==============================================================================
# Import/Export Formats
# ==============================================================================


class ExportFormat(str, Enum):
    """Supported export formats."""

    JSON = "json"
    JSONL = "jsonl"
    MARKDOWN = "markdown"
    SQL_DUMP = "sql_dump"


class ImportFormat(str, Enum):
    """Supported import formats."""

    JSON = "json"
    JSONL = "jsonl"
    MARKDOWN = "markdown"
    SQL_DUMP = "sql_dump"
    MEM0 = "mem0"
    ZEP = "zep"
    CHROMA = "chroma"


# ==============================================================================
# Memory Exporter
# ==============================================================================


class MemoryExporter:
    """
    Exports Gnosys memory data to various formats.
    """

    def __init__(self, memories: list[dict[str, Any]]):
        self.memories = memories

    def to_json(self, output_path: Path) -> str:
        """Export to JSON format."""
        export_data = {
            "version": "1.0.0",
            "exported_at": datetime.now().isoformat(),
            "memories": self.memories,
            "count": len(self.memories),
        }

        with open(output_path, "w") as f:
            json.dump(export_data, f, indent=2)

        return str(output_path)

    def to_jsonl(self, output_path: Path) -> str:
        """Export to JSONL format (one record per line)."""
        with open(output_path, "w") as f:
            for memory in self.memories:
                f.write(json.dumps(memory) + "\n")

        return str(output_path)

    def to_markdown(self, output_path: Path) -> str:
        """Export to Markdown format."""
        lines = [
            "# Gnosys Memory Export",
            "",
            f"**Exported**: {datetime.now().isoformat()}",
            f"**Total Memories**: {len(self.memories)}",
            "",
            "---",
            "",
        ]

        for i, memory in enumerate(self.memories, 1):
            memory_id = memory.get("id", f"memory_{i}")
            tier = memory.get("tier", "unknown")
            mem_type = memory.get("type", "unknown")
            content = memory.get("content", "")
            created = memory.get("created_at", "unknown")

            lines.extend(
                [
                    f"## {memory_id}",
                    "",
                    f"**Tier**: {tier}",
                    f"**Type**: {mem_type}",
                    f"**Created**: {created}",
                    "",
                    content,
                    "",
                    "---",
                    "",
                ]
            )

        with open(output_path, "w") as f:
            f.write("\n".join(lines))

        return str(output_path)

    def to_sql_dump(self, output_path: Path) -> str:
        """Export to SQL dump format."""
        lines = [
            "-- Gnosys Memory SQL Dump",
            f"-- Exported: {datetime.now().isoformat()}",
            "",
            "BEGIN TRANSACTION;",
            "",
        ]

        for memory in self.memories:
            memory_id = memory.get("id", "").replace("'", "''")
            tier = memory.get("tier", "").replace("'", "''")
            mem_type = memory.get("type", "").replace("'", "''")
            content = memory.get("content", "").replace("'", "''")
            metadata = json.dumps(memory.get("metadata", {})).replace("'", "''")
            created = memory.get("created_at", 0)

            lines.append(
                f"INSERT INTO memory_items "
                f"(id, tier, type, content, metadata, created_at) "
                f"VALUES ('{memory_id}', '{tier}', '{mem_type}', "
                f"'{content}', '{metadata}', {created});"
            )

        lines.extend(
            [
                "",
                "COMMIT;",
            ]
        )

        with open(output_path, "w") as f:
            f.write("\n".join(lines))

        return str(output_path)


# ==============================================================================
# Memory Importer
# ==============================================================================


class MemoryImporter:
    """
    Imports memory data from various formats.
    """

    def from_json(self, input_path: Path) -> list[dict[str, Any]]:
        """Import from JSON format."""
        with open(input_path) as f:
            data = json.load(f)

        if "memories" in data:
            return data["memories"]
        elif isinstance(data, list):
            return data
        return []

    def from_jsonl(self, input_path: Path) -> list[dict[str, Any]]:
        """Import from JSONL format."""
        memories = []

        with open(input_path) as f:
            for line in f:
                if line.strip():
                    memories.append(json.loads(line))

        return memories

    def from_markdown(self, input_path: Path) -> list[dict[str, Any]]:
        """Import from Markdown format."""
        memories = []
        current_memory: dict[str, Any] | None = None

        with open(input_path) as f:
            for line in f:
                line = line.rstrip()

                if line.startswith("## "):
                    if current_memory and current_memory.get("content"):
                        memories.append(current_memory)

                    memory_id = line[3:].strip()
                    current_memory = {
                        "id": memory_id,
                        "content": "",
                        "tier": "semantic",
                        "type": "conversational",
                    }

                elif line.startswith("**Tier**: "):
                    if current_memory:
                        current_memory["tier"] = line[10:].strip()

                elif line.startswith("**Type**: "):
                    if current_memory:
                        current_memory["type"] = line[10:].strip()

                elif line.startswith("**Created**: "):
                    if current_memory:
                        current_memory["created_at"] = line[12:].strip()

                elif (
                    line
                    and not line.startswith("#")
                    and not line.startswith("---")
                    and current_memory
                ):
                    current_memory["content"] += line + "\n"

        if current_memory and current_memory.get("content"):
            memories.append(current_memory)

        return memories

    def from_mem0(self, input_path: Path) -> list[dict[str, Any]]:
        """Import from Mem0 format."""
        with open(input_path) as f:
            data = json.load(f)

        memories = []

        if "memories" in data:
            for mem in data["memories"]:
                memories.append(
                    {
                        "tier": "semantic",
                        "type": "conversational",
                        "content": mem.get("content", ""),
                        "metadata": {
                            "imported_from": "mem0",
                            "original_id": mem.get("id"),
                        },
                    }
                )

        if "messages" in data:
            for msg in data["messages"]:
                memories.append(
                    {
                        "tier": "episodic",
                        "type": "conversational",
                        "content": msg.get("content", ""),
                        "metadata": {
                            "imported_from": "mem0",
                            "role": msg.get("role"),
                        },
                    }
                )

        return memories

    def from_zep(self, input_path: Path) -> list[dict[str, Any]]:
        """Import from Zep format."""
        with open(input_path) as f:
            data = json.load(f)

        memories = []

        # Zep uses sessions and messages structure
        if "sessions" in data:
            for session in data["sessions"]:
                for msg in session.get("messages", []):
                    memories.append(
                        {
                            "tier": "episodic",
                            "type": "conversational",
                            "content": msg.get("content", ""),
                            "metadata": {
                                "imported_from": "zep",
                                "session_id": session.get("id"),
                            },
                        }
                    )

        return memories

    def from_chroma(self, input_path: Path) -> list[dict[str, Any]]:
        """Import from Chroma format."""
        with open(input_path) as f:
            data = json.load(f)

        memories = []

        if "ids" in data and "metadatas" in data:
            for i, mem_id in enumerate(data["ids"]):
                metadata = data["metadatas"][i] if i < len(data["metadatas"]) else {}
                document = (
                    data["documents"][i] if i < len(data.get("documents", [])) else ""
                )

                memories.append(
                    {
                        "tier": "semantic",
                        "type": "conversational",
                        "content": document,
                        "metadata": {
                            "imported_from": "chroma",
                            "original_id": mem_id,
                            **metadata,
                        },
                    }
                )

        return memories


# ==============================================================================
# Skill Importer/Exporter
# ==============================================================================


class SkillExporter:
    """
    Exports Gnosys skills to various formats.
    """

    def __init__(self, skills: list[dict[str, Any]]):
        self.skills = skills

    def to_openclaw_format(self, output_dir: Path) -> list[str]:
        """Export to OpenClaw SKILL.md format."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        exported = []

        for skill in self.skills:
            skill_name = skill.get("name", "unknown_skill")

            # Create skill directory
            skill_dir = output_dir / skill_name
            skill_dir.mkdir(exist_ok=True)

            # Write SKILL.md
            skill_content = self._generate_skill_md(skill)
            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text(skill_content)

            # Write metadata.json
            metadata = {
                "name": skill_name,
                "version": skill.get("version", "1.0.0"),
                "created": skill.get("created_at"),
                "last_used": skill.get("last_used_at"),
                "use_count": skill.get("trigger_count", 0),
                "success_rate": skill.get("success_rate", 1.0),
            }

            metadata_file = skill_dir / "metadata.json"
            metadata_file.write_text(json.dumps(metadata, indent=2))

            exported.append(str(skill_dir))

        return exported

    def _generate_skill_md(self, skill: dict[str, Any]) -> str:
        """Generate SKILL.md content."""
        workflow = skill.get("workflow", [])
        tools = skill.get("tools", [])

        lines = [
            f"# Skill: {skill.get('name', 'Unnamed')}",
            "",
            skill.get("description", "No description available."),
            "",
            "## Triggers",
            "",
            "- Automatic skill detection",
            "",
            "## Workflow",
            "",
        ]

        for i, step in enumerate(workflow, 1):
            lines.append(f"{i}. {step}")

        lines.extend(
            [
                "",
                "## Tools",
                "",
                ", ".join(tools) if tools else "None specified",
                "",
                "## Parameters",
                "",
            ]
        )

        params = skill.get("parameters", {})
        for param, desc in params.items():
            lines.append(f"- `{param}`: {desc}")

        return "\n".join(lines)


class SkillImporter:
    """
    Imports skills from various formats.
    """

    def from_openclaw(self, input_dir: Path) -> list[dict[str, Any]]:
        """Import from OpenClaw SKILL.md format."""
        skills = []

        input_dir = Path(input_dir)
        if not input_dir.exists():
            return skills

        for skill_dir in input_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_file = skill_dir / "SKILL.md"
            metadata_file = skill_dir / "metadata.json"

            if not skill_file.exists():
                continue

            # Parse SKILL.md
            content = skill_file.read_text()
            lines = content.split("\n")

            workflow = []
            in_workflow = False
            tools = []
            params = {}
            description = ""

            for line in lines:
                if line.startswith("## Workflow"):
                    in_workflow = True
                    continue
                elif line.startswith("## Tools"):
                    in_workflow = False
                    continue
                elif line.startswith("## Parameters"):
                    continue
                elif line.startswith("# Skill:"):
                    name = line.replace("# Skill:", "").strip()
                elif in_workflow and line.strip() and line[0].isdigit():
                    step = (
                        line.split(".", 1)[1].strip() if "." in line else line.strip()
                    )
                    workflow.append(step)
                elif description == "" and line.strip():
                    description = line.strip()

            # Parse metadata if exists
            metadata = {}
            if metadata_file.exists():
                try:
                    metadata = json.loads(metadata_file.read_text())
                except Exception:
                    pass

            skills.append(
                {
                    "name": metadata.get("name", skill_dir.name),
                    "version": metadata.get("version", "1.0.0"),
                    "description": description,
                    "workflow": workflow,
                    "tools": tools,
                    "parameters": params,
                    "created_at": metadata.get("created"),
                    "last_used_at": metadata.get("last_used"),
                    "trigger_count": metadata.get("use_count", 0),
                    "success_rate": metadata.get("success_rate", 1.0),
                }
            )

        return skills


# ==============================================================================
# Interoperability Service
# ==============================================================================


class InteropService:
    """
    Main service for data interoperability.
    """

    def __init__(self):
        self.importers = {
            "json": MemoryImporter().from_json,
            "jsonl": MemoryImporter().from_jsonl,
            "markdown": MemoryImporter().from_markdown,
            "mem0": MemoryImporter().from_mem0,
            "zep": MemoryImporter().from_zep,
            "chroma": MemoryImporter().from_chroma,
        }

    def import_memories(
        self,
        input_path: Path,
        format: ImportFormat,
    ) -> list[dict[str, Any]]:
        """Import memories from a file."""
        if format not in self.importers:
            raise ValueError(f"Unsupported import format: {format}")

        return self.importers[format.value](input_path)

    def export_memories(
        self,
        memories: list[dict[str, Any]],
        output_path: Path,
        format: ExportFormat,
    ) -> str:
        """Export memories to a file."""
        exporter = MemoryExporter(memories)

        if format == ExportFormat.JSON:
            return exporter.to_json(output_path)
        elif format == ExportFormat.JSONL:
            return exporter.to_jsonl(output_path)
        elif format == ExportFormat.MARKDOWN:
            return exporter.to_markdown(output_path)
        elif format == ExportFormat.SQL_DUMP:
            return exporter.to_sql_dump(output_path)

        raise ValueError(f"Unsupported export format: {format}")

    def import_skills(
        self,
        input_dir: Path,
        format: str = "openclaw",
    ) -> list[dict[str, Any]]:
        """Import skills from a directory."""
        if format == "openclaw":
            return SkillImporter().from_openclaw(input_dir)

        raise ValueError(f"Unsupported skill format: {format}")

    def export_skills(
        self,
        skills: list[dict[str, Any]],
        output_dir: Path,
        format: str = "openclaw",
    ) -> list[str]:
        """Export skills to a directory."""
        if format == "openclaw":
            return SkillExporter(skills).to_openclaw_format(output_dir)

        raise ValueError(f"Unsupported skill format: {format}")

    def transform_format(
        self,
        data: Any,
        from_format: ImportFormat,
        to_format: ExportFormat,
    ) -> dict[str, Any]:
        """Transform data between formats."""
        # This would require more complex transformation logic
        # For now, return the data as-is
        return {"data": data, "from": from_format.value, "to": to_format.value}
