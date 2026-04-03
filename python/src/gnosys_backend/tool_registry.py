"""
Tool Registry module for Gnosys v1.0.

Provides dynamic tool loading, versioning, and discovery.
"""

from __future__ import annotations

import json
import importlib
import importlib.util
import inspect
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel


# ==============================================================================
# Tool Definition
# ==============================================================================


class ToolParameter(BaseModel):
    """Tool parameter definition."""

    name: str
    type: str
    description: str = ""
    required: bool = False
    default: Any = None


class ToolDefinition(BaseModel):
    """Tool manifest definition."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    parameters: list[ToolParameter] = []
    returns: dict[str, Any] = {}
    requires: list[str] = []  # Other tools required
    capabilities: list[str] = []  # file_ops, network, etc.
    path: str | None = None  # Path to tool module


# ==============================================================================
# Tool Version
# ==============================================================================


class ToolVersion(BaseModel):
    """A specific version of a tool."""

    version: str
    definition: ToolDefinition
    loaded_at: datetime
    source: str  # builtin, external, custom


# ==============================================================================
# Tool Registry
# ==============================================================================


class ToolRegistry:
    """
    Dynamic tool registry with versioning.

    Features:
    - Semantic versioning
    - Dependency resolution
    - Rollback capability
    - Tool discovery
    """

    def __init__(self, scan_paths: list[str] | None = None):
        self.scan_paths = [Path(p).expanduser() for p in (scan_paths or [])]

        # Registered tools
        self._tools: dict[str, dict[str, ToolVersion]] = {}
        self._latest: dict[str, ToolVersion] = {}

        # Built-in tools
        self._register_builtins()

    def _register_builtins(self) -> None:
        """Register Gnosys built-in tools."""
        builtins = [
            ToolDefinition(
                name="gnosys_store_memory",
                version="1.0.0",
                description="Store a memory in the memory system",
                parameters=[
                    ToolParameter(
                        name="content",
                        type="string",
                        description="Memory content",
                        required=True,
                    ),
                    ToolParameter(
                        name="tier",
                        type="string",
                        description="Memory tier (working, episodic, semantic)",
                        required=False,
                        default="semantic",
                    ),
                ],
                returns={"type": "object"},
                capabilities=["memory_ops"],
            ),
            ToolDefinition(
                name="gnosys_get_memory",
                version="1.0.0",
                description="Fetch a memory by ID",
                parameters=[
                    ToolParameter(
                        name="id",
                        type="string",
                        description="Memory ID",
                        required=True,
                    ),
                ],
                returns={"type": "object"},
                capabilities=["memory_ops"],
            ),
            ToolDefinition(
                name="gnosys_search",
                version="1.0.0",
                description="Search memories by query",
                parameters=[
                    ToolParameter(
                        name="query",
                        type="string",
                        description="Search query",
                        required=True,
                    ),
                ],
                returns={"type": "array"},
                capabilities=["memory_ops"],
            ),
            ToolDefinition(
                name="gnosys_semantic_search",
                version="1.0.0",
                description="Semantic search over memories",
                parameters=[
                    ToolParameter(
                        name="query",
                        type="string",
                        description="Search query",
                        required=True,
                    ),
                    ToolParameter(
                        name="limit",
                        type="number",
                        description="Max results",
                        required=False,
                        default=10,
                    ),
                ],
                returns={"type": "array"},
                capabilities=["memory_ops", "embeddings"],
            ),
            ToolDefinition(
                name="gnosys_skills",
                version="1.0.0",
                description="List, create, and manage skills",
                parameters=[
                    ToolParameter(
                        name="action",
                        type="string",
                        description="Action: list, create, use",
                        required=True,
                    ),
                ],
                returns={"type": "object"},
                capabilities=["skill_ops"],
            ),
            ToolDefinition(
                name="gnosys_scheduler",
                version="1.0.0",
                description="Schedule and manage periodic tasks",
                parameters=[
                    ToolParameter(
                        name="action",
                        type="string",
                        description="Action: list, create, run, delete",
                        required=True,
                    ),
                ],
                returns={"type": "object"},
                capabilities=["scheduling"],
            ),
            ToolDefinition(
                name="gnosys_backup",
                version="1.0.0",
                description="Create and manage backups",
                parameters=[
                    ToolParameter(
                        name="action",
                        type="string",
                        description="Action: create, list, restore",
                        required=True,
                    ),
                ],
                returns={"type": "object"},
                capabilities=["backup"],
            ),
            ToolDefinition(
                name="gnosys_pipeline",
                version="1.0.0",
                description="Execute multi-agent pipeline",
                parameters=[
                    ToolParameter(
                        name="task",
                        type="string",
                        description="Task description",
                        required=True,
                    ),
                ],
                returns={"type": "object"},
                capabilities=["multi_agent"],
            ),
            ToolDefinition(
                name="gnosys_learning",
                version="1.0.0",
                description="Learning and pattern detection",
                parameters=[
                    ToolParameter(
                        name="action",
                        type="string",
                        description="Action: detect, generate, metrics",
                        required=True,
                    ),
                ],
                returns={"type": "object"},
                capabilities=["learning"],
            ),
            ToolDefinition(
                name="gnosys_status",
                version="1.0.0",
                description="Get system status and diagnostics",
                parameters=[],
                returns={"type": "object"},
                capabilities=["diagnostics"],
            ),
        ]

        for tool_def in builtins:
            self.register(tool_def, source="builtin")

    def register(
        self,
        definition: ToolDefinition,
        source: str = "external",
    ) -> None:
        """Register a tool definition."""
        version = ToolVersion(
            version=definition.version,
            definition=definition,
            loaded_at=datetime.now(),
            source=source,
        )

        name = definition.name

        # Store by version
        if name not in self._tools:
            self._tools[name] = {}

        self._tools[name][definition.version] = version

        # Update latest
        self._latest[name] = version

    def unregister(self, name: str, version: str | None = None) -> bool:
        """Unregister a tool."""
        if name not in self._tools:
            return False

        if version:
            if version in self._tools[name]:
                del self._tools[name][version]
                if not self._tools[name]:
                    del self._tools[name]
            # Update latest
            if name in self._tools and self._tools[name]:
                versions = sorted(
                    self._tools[name].keys(),
                    key=lambda v: tuple(map(int, v.split("."))),
                    reverse=True,
                )
                self._latest[name] = self._tools[name][versions[0]]
        else:
            del self._tools[name]
            if name in self._latest:
                del self._latest[name]

        return True

    def get(self, name: str, version: str | None = None) -> ToolDefinition | None:
        """Get a tool definition."""
        if name not in self._tools:
            return None

        if version:
            tool_version = self._tools[name].get(version)
            return tool_version.definition if tool_version else None

        # Return latest
        latest = self._latest.get(name)
        return latest.definition if latest else None

    def list_tools(
        self,
        capability: str | None = None,
        source: str | None = None,
    ) -> list[dict[str, Any]]:
        """List available tools."""
        tools = []

        for name, versions in self._tools.items():
            for ver, tool_version in versions.items():
                definition = tool_version.definition

                # Filter by capability
                if capability and capability not in definition.capabilities:
                    continue

                # Filter by source
                if source and tool_version.source != source:
                    continue

                tools.append(
                    {
                        "name": name,
                        "version": ver,
                        "description": definition.description,
                        "capabilities": definition.capabilities,
                        "source": tool_version.source,
                    }
                )

        return tools

    def find(self, capability: str) -> list[ToolDefinition]:
        """Find tools by capability."""
        tools = []

        for name, versions in self._latest.items():
            definition = versions.definition
            if capability in definition.capabilities:
                tools.append(definition)

        return tools

    def check_compatibility(
        self,
        name: str,
        version: str,
    ) -> bool:
        """Check if a tool version is compatible."""
        if name not in self._tools:
            return False

        # Simple semantic version check (major.minor.patch)
        tool_version = self._tools[name].get(version)
        if not tool_version:
            return False

        return True

    def get_versions(self, name: str) -> list[str]:
        """Get all versions of a tool."""
        if name not in self._tools:
            return []

        return sorted(
            self._tools[name].keys(),
            key=lambda v: tuple(map(int, v.split("."))),
        )

    def rollback(self, name: str, target_version: str | None = None) -> bool:
        """Rollback to a previous version."""
        if name not in self._tools or len(self._tools[name]) < 2:
            return False

        versions = sorted(
            self._tools[name].keys(),
            key=lambda v: tuple(map(int, v.split("."))),
            reverse=True,
        )

        if target_version:
            if target_version not in self._tools[name]:
                return False
            self._latest[name] = self._tools[name][target_version]
        else:
            # Rollback to previous version
            current_idx = versions.index(self._latest[name].version)
            if current_idx + 1 < len(versions):
                prev_version = versions[current_idx + 1]
                self._latest[name] = self._tools[name][prev_version]

        return True

    def scan_directory(self, directory: Path) -> int:
        """Scan a directory for tools."""
        found = 0

        # Look for tool.json files
        for tool_file in directory.rglob("tool.json"):
            try:
                with open(tool_file) as f:
                    tool_data = json.load(f)

                definition = ToolDefinition(**tool_data)
                self.register(definition, source="external")
                found += 1

            except Exception:
                continue

        # Look for Python modules with tool_manifest
        for py_file in directory.rglob("*.py"):
            try:
                spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    if hasattr(module, "tool_manifest"):
                        definition = ToolDefinition(**module.tool_manifest)
                        self.register(definition, source="external")
                        found += 1

            except Exception:
                continue

        return found

    def scan(self) -> int:
        """Scan all configured paths for tools."""
        found = 0

        for path in self.scan_paths:
            if path.exists() and path.is_dir():
                found += self.scan_directory(path)

        return found

    def stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        total_tools = len(self._tools)
        total_versions = sum(len(v) for v in self._tools.values())

        sources = {}
        for name, versions in self._tools.items():
            for ver, tool_version in versions.items():
                source = tool_version.source
                sources[source] = sources.get(source, 0) + 1

        return {
            "total_tools": total_tools,
            "total_versions": total_versions,
            "sources": sources,
            "scan_paths": [str(p) for p in self.scan_paths],
        }
