"""
Backup & Recovery module for Gnosys.

Provides full/selective backup, restore, and migration capabilities.
"""

from __future__ import annotations

import json
import os
import shutil
import tarfile
import tempfile
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel


# ==============================================================================
# Models
# ==============================================================================


class BackupRecord(BaseModel):
    """Record of a backup."""

    id: str
    backup_type: str  # full, incremental, selective
    components: list[str]
    file_path: str
    checksum: str
    size_bytes: int | None = None
    created_at: datetime


class BackupConfig(BaseModel):
    """Configuration for backup operations."""

    schedule: str = "daily"  # daily, weekly, monthly
    retention_daily: int = 7
    retention_weekly: int = 4
    retention_monthly: int = 12
    location: Path = Path("~/.openclaw/gnosys/backups")
    compression: str = "gzip"  # gzip, bzip2, none
    incremental_enabled: bool = True  # v1.0 - Enable incremental backups
    incremental_since_last: bool = True  # Backup changes since last backup


class IncrementalBackupManager:
    """
    Manages incremental backups for Gnosys v1.0.

    Tracks file changes since last backup and creates incremental archives.
    Supports restore to any point in the backup chain.
    """

    def __init__(
        self,
        db_path: Path,
        vectors_path: Path,
        skills_dir: Path | None = None,
        config: BackupConfig | None = None,
    ):
        self.db_path = Path(db_path)
        self.vectors_path = Path(vectors_path)
        self.skills_dir = Path(skills_dir) if skills_dir else None
        self.config = config or BackupConfig()

        # Ensure backup location exists
        self.config.location = self.config.location.expanduser().resolve()
        self.config.location.mkdir(parents=True, exist_ok=True)

        # Track last backup state
        self._last_backup_file = self.config.location / ".last_backup_state.json"
        self._last_state: dict[str, Any] = self._load_last_state()

    def _load_last_state(self) -> dict[str, Any]:
        """Load last backup state."""
        if self._last_backup_file.exists():
            try:
                with open(self._last_backup_file) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"full_backup": None, "incremental_backups": []}

    def _save_last_state(self) -> None:
        """Save last backup state."""
        with open(self._last_backup_file, "w") as f:
            json.dump(self._last_state, f)

    def _get_file_hash(self, file_path: Path) -> str | None:
        """Get file hash for change detection."""
        if not file_path.exists():
            return None

        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _get_changed_files(
        self,
        last_backup_time: float | None,
    ) -> dict[str, Path | None]:
        """Get files that have changed since last backup."""
        all_components = {
            "database": self.db_path,
            "vectors": self.vectors_path,
            "skills": self.skills_dir,
        }

        changed = {}
        for name, path in all_components.items():
            if not path or not path.exists():
                continue

            if path.is_file():
                # Check file modification time and hash
                mtime = path.stat().st_mtime
                if last_backup_time is None or mtime > last_backup_time:
                    changed[name] = path
            else:
                # Directory - check for new/modified files
                modified = []
                for subfile in path.rglob("*"):
                    if subfile.is_file():
                        mtime = subfile.stat().st_mtime
                        if last_backup_time is None or mtime > last_backup_time:
                            modified.append(subfile)

                if modified:
                    changed[name] = path

        return changed

    def create_incremental(
        self,
        output_path: Path | None = None,
    ) -> BackupRecord:
        """Create an incremental backup."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Get last backup time
        last_full = self._last_state.get("full_backup")
        last_incr = self._last_state.get("incremental_backups", [])
        last_time = None

        if last_incr:
            last_time = max(b.get("timestamp", 0) for b in last_incr)
        elif last_full:
            last_time = last_full.get("timestamp", 0)

        # Get changed files
        changed = self._get_changed_files(last_time)

        if not changed:
            # No changes, create empty marker
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = (
                output_path or self.config.location / f"gnosys_incr_{timestamp}.tar.gz"
            )
            with tarfile.open(output_path, "w:gz") as tar:
                pass  # Empty archive as marker

            record = BackupRecord(
                id=f"incremental_{timestamp}",
                backup_type="incremental",
                components=[],
                file_path=str(output_path),
                checksum="",
                size_bytes=0,
                created_at=datetime.now(),
            )
        else:
            # Create incremental archive
            output_path = (
                output_path or self.config.location / f"gnosys_incr_{timestamp}.tar.gz"
            )

            temp_dir = tempfile.mkdtemp()
            try:
                with tarfile.open(output_path, "w:gz") as tar:
                    for name, path in changed.items():
                        if path.is_file():
                            tar.add(path, arcname=name)
                        elif path.exists():
                            # For directories, add changed files
                            for subfile in path.rglob("*"):
                                if subfile.is_file():
                                    arcname = f"{name}/{subfile.name}"
                                    tar.add(subfile, arcname=arcname)

                # Calculate checksum
                checksum = self._calculate_checksum(output_path)
                size = output_path.stat().st_size

                record = BackupRecord(
                    id=f"incremental_{timestamp}",
                    backup_type="incremental",
                    components=list(changed.keys()),
                    file_path=str(output_path),
                    checksum=checksum,
                    size_bytes=size,
                    created_at=datetime.now(),
                )
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        # Update state
        self._last_state.setdefault("incremental_backups", []).append(
            {
                "id": record.id,
                "timestamp": record.created_at.timestamp(),
                "components": record.components,
            }
        )
        self._save_last_state()

        return record

    def create_full_incremental_chain(
        self,
        output_path: Path | None = None,
    ) -> tuple[BackupRecord, BackupRecord]:
        """Create a full backup then start incremental chain."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create full backup first
        full_output = (
            output_path or self.config.location / f"gnosys_full_{timestamp}.tar.gz"
        )

        components = {
            "database": self.db_path,
            "vectors": self.vectors_path,
            "skills": self.skills_dir,
        }

        temp_dir = tempfile.mkdtemp()
        try:
            with tarfile.open(full_output, "w:gz") as tar:
                for name, path in components.items():
                    if path and path.exists():
                        tar.add(path, arcname=name)

            checksum = self._calculate_checksum(full_output)
            size = full_output.stat().st_size

            full_record = BackupRecord(
                id=f"full_{timestamp}",
                backup_type="full",
                components=list(components.keys()),
                file_path=str(full_output),
                checksum=checksum,
                size_bytes=size,
                created_at=datetime.now(),
            )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        # Reset incremental state
        self._last_state = {
            "full_backup": {
                "id": full_record.id,
                "timestamp": full_record.created_at.timestamp(),
                "components": full_record.components,
            },
            "incremental_backups": [],
        }
        self._save_last_state()

        # Now create initial incremental
        incr_record = self.create_incremental()

        return full_record, incr_record

    def restore_chain(
        self,
        target_dir: Path,
        overwrite: bool = False,
    ) -> dict[str, str]:
        """Restore from full + incremental chain."""
        results = {}

        # Find full backup
        full_backup = self._last_state.get("full_backup", {})
        if full_backup:
            full_path = self.config.location / f"{full_backup['id']}.tar.gz"
            if full_path.exists():
                # Restore full
                with tarfile.open(full_path, "r:gz") as tar:
                    tar.extractall(target_dir)

        # Apply incremental backups in order
        for incr in self._last_state.get("incremental_backups", []):
            incr_path = self.config.location / f"{incr['id']}.tar.gz"
            if incr_path.exists():
                with tarfile.open(incr_path, "r:gz") as tar:
                    tar.extractall(target_dir)

        results["restored"] = str(target_dir)
        return results

    def get_chain_info(self) -> dict[str, Any]:
        """Get information about the backup chain."""
        return {
            "last_full": self._last_state.get("full_backup"),
            "incremental_count": len(self._last_state.get("incremental_backups", [])),
            "incremental_backups": self._last_state.get("incremental_backups", []),
        }


class RestoreConfig(BaseModel):
    """Configuration for restore operations."""

    backup_path: Path
    target_dir: Path
    components: list[str] | None = None  # None = all
    overwrite: bool = False


# ==============================================================================
# Backup Manager
# ==============================================================================


class BackupManager:
    """
    Manages backup operations for Gnosys data.
    """

    def __init__(
        self,
        db_path: Path,
        vectors_path: Path,
        skills_dir: Path | None = None,
        config: BackupConfig | None = None,
    ):
        self.db_path = Path(db_path)
        self.vectors_path = Path(vectors_path)
        self.skills_dir = Path(skills_dir) if skills_dir else None
        self.config = config or BackupConfig()

        # Ensure backup location exists
        self.config.location = self.config.location.expanduser().resolve()
        self.config.location.mkdir(parents=True, exist_ok=True)

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return f"sha256:{sha256.hexdigest()}"

    def _get_components(self, components: list[str] | None) -> dict[str, Path | None]:
        """Get paths for requested components."""
        all_components = {
            "database": self.db_path,
            "vectors": self.vectors_path,
            "skills": self.skills_dir,
            "config": Path("./config.json"),  # Relative to gnosys root
        }

        if components is None:
            return all_components

        return {
            k: v
            for k, v in all_components.items()
            if k in components and v and v.exists()
        }

    def create_full_backup(self, output_path: Path | None = None) -> BackupRecord:
        """Create a full backup of all components."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"gnosys_full_{timestamp}"

        if output_path is None:
            output_path = self.config.location / f"{backup_name}.tar.gz"

        components = self._get_components(None)
        temp_dir = tempfile.mkdtemp()

        try:
            # Create tar archive
            with tarfile.open(output_path, "w:gz") as tar:
                for name, path in components.items():
                    if path and path.exists():
                        tar.add(path, arcname=name)

            # Calculate checksum
            checksum = self._calculate_checksum(output_path)

            # Get file size
            size = output_path.stat().st_size

            record = BackupRecord(
                id=backup_name,
                backup_type="full",
                components=list(components.keys()),
                file_path=str(output_path),
                checksum=checksum,
                size_bytes=size,
                created_at=datetime.now(),
            )

            return record

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def create_selective_backup(
        self,
        components: list[str],
        output_path: Path | None = None,
    ) -> BackupRecord:
        """Create a selective backup of specific components."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"gnosys_selective_{timestamp}"

        if output_path is None:
            output_path = self.config.location / f"{backup_name}.tar.gz"

        component_paths = self._get_components(components)
        temp_dir = tempfile.mkdtemp()

        try:
            with tarfile.open(output_path, "w:gz") as tar:
                for name, path in component_paths.items():
                    if path and path.exists():
                        tar.add(path, arcname=name)

            checksum = self._calculate_checksum(output_path)
            size = output_path.stat().st_size

            record = BackupRecord(
                id=backup_name,
                backup_type="selective",
                components=components,
                file_path=str(output_path),
                checksum=checksum,
                size_bytes=size,
                created_at=datetime.now(),
            )

            return record

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def list_backups(self) -> list[BackupRecord]:
        """List all available backups."""
        backups = []

        for file_path in self.config.location.glob("gnosys_*.tar.gz"):
            try:
                # Extract basic info from filename
                name = file_path.stem
                parts = name.split("_")
                backup_type = parts[1] if len(parts) > 1 else "unknown"

                record = BackupRecord(
                    id=name,
                    backup_type=backup_type,
                    components=[],
                    file_path=str(file_path),
                    checksum="",
                    size_bytes=file_path.stat().st_size,
                    created_at=datetime.fromtimestamp(file_path.stat().st_mtime),
                )
                backups.append(record)
            except Exception:
                continue

        return sorted(backups, key=lambda x: x.created_at, reverse=True)

    def verify_backup(self, backup_path: Path) -> bool:
        """Verify backup integrity."""
        if not backup_path.exists():
            return False

        try:
            # Try to open the tar file
            with tarfile.open(backup_path, "r:gz") as tar:
                # List contents to verify it's valid
                members = tar.getmembers()
                return len(members) > 0
        except Exception:
            return False


# ==============================================================================
# Restore Manager
# ==============================================================================


class RestoreManager:
    """
    Manages restore operations for Gnosys data.
    """

    def __init__(
        self,
        db_path: Path,
        vectors_path: Path,
        skills_dir: Path | None = None,
    ):
        self.db_path = Path(db_path)
        self.vectors_path = Path(vectors_path)
        self.skills_dir = Path(skills_dir) if skills_dir else None

    def restore(
        self,
        backup_path: Path,
        target_dir: Path,
        components: list[str] | None = None,
        overwrite: bool = False,
    ) -> dict[str, str]:
        """
        Restore from a backup.

        Returns:
            Dictionary mapping component names to restored paths
        """
        results = {}

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        # Create temp extraction directory
        temp_dir = tempfile.mkdtemp()

        try:
            # Extract archive
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(temp_dir)

            # Restore each component
            extracted_dir = Path(temp_dir)

            component_map = {
                "database": (self.db_path, "database"),
                "vectors": (self.vectors_path, "vectors"),
                "skills": (self.skills_dir, "skills"),
            }

            for comp, (target, source) in component_map.items():
                if components and comp not in components:
                    continue

                source_path = extracted_dir / source
                if not source_path.exists():
                    continue

                if target.exists() and not overwrite:
                    # Rename existing to .old
                    old = target.with_suffix(".old")
                    if old.exists():
                        old.unlink()
                    target.rename(old)

                # Create parent directories
                target.parent.mkdir(parents=True, exist_ok=True)

                if source_path.is_file():
                    shutil.copy2(source_path, target)
                else:
                    if target.exists():
                        shutil.rmtree(target)
                    shutil.copytree(source_path, target)

                results[comp] = str(target)

            return results

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def restore_to_point_in_time(
        self,
        backup_path: Path,
        target_dir: Path,
    ) -> dict[str, str]:
        """Restore to a specific point in time (requires incremental backups)."""
        # This would require a chain of incremental backups
        # For v0.9, implement as full restore
        return self.restore(backup_path, target_dir)


# ==============================================================================
# Migration Manager
# ==============================================================================


class MigrationManager:
    """
    Manages data migration between Gnosys versions and other systems.
    """

    def __init__(self):
        self.transformers: dict[str, Any] = {}

    def register_transformer(self, name: str, transformer: Any) -> None:
        """Register a custom data transformer."""
        self.transformers[name] = transformer

    def export_to_json(self, data: dict[str, Any], output_path: Path) -> str:
        """Export data to JSON format."""
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        return str(output_path)

    def export_to_jsonl(self, records: list[dict], output_path: Path) -> str:
        """Export records to JSONL format."""
        with open(output_path, "w") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")
        return str(output_path)

    def export_to_markdown(self, memories: list[dict], output_path: Path) -> str:
        """Export memories to Markdown format."""
        lines = ["# Gnosys Memory Export\n"]

        for memory in memories:
            lines.append(f"## {memory.get('id', 'unknown')}\n")
            lines.append(f"**Tier**: {memory.get('tier', 'unknown')}\n")
            lines.append(f"**Type**: {memory.get('type', 'unknown')}\n")
            lines.append(f"**Created**: {memory.get('created_at', 'unknown')}\n")
            lines.append(f"\n{memory.get('content', '')}\n")
            lines.append("\n---\n")

        with open(output_path, "w") as f:
            f.write("\n".join(lines))

        return str(output_path)

    def import_from_json(self, input_path: Path) -> dict[str, Any]:
        """Import data from JSON format."""
        with open(input_path) as f:
            return json.load(f)

    def import_from_jsonl(self, input_path: Path) -> list[dict]:
        """Import records from JSONL format."""
        records = []
        with open(input_path) as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
        return records

    def transform_data(
        self,
        data: dict[str, Any],
        from_format: str,
        to_format: str,
    ) -> dict[str, Any]:
        """Transform data from one format to another."""
        # Built-in transformers
        if from_format == "mem0" and to_format == "gnosys":
            return self._transform_mem0_to_gnosys(data)
        elif from_format == "openclaw" and to_format == "gnosys":
            return self._transform_openclaw_to_gnosys(data)

        # Custom transformer
        if from_format in self.transformers:
            return self.transformers[from_format].transform(data, to_format)

        # Default: return as-is
        return data

    def _transform_mem0_to_gnosys(self, data: dict[str, Any]) -> dict[str, Any]:
        """Transform Mem0 format to Gnosys format."""
        # Mem0 uses: {messages: [...], memories: {...}}
        # Gnosys uses: {tier, type, content, metadata}

        transformed = {
            "memories": [],
            "version": "1.0.0",
            "imported_at": datetime.now().isoformat(),
        }

        # Transform memories
        if "memories" in data:
            for mem in data["memories"]:
                transformed["memories"].append(
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

        return transformed

    def _transform_openclaw_to_gnosys(self, data: dict[str, Any]) -> dict[str, Any]:
        """Transform OpenCLAW format to Gnosys format."""
        transformed = {
            "memories": [],
            "version": "1.0.0",
            "imported_at": datetime.now().isoformat(),
        }

        # Transform from MEMORY.md format
        if "content" in data:
            transformed["memories"].append(
                {
                    "tier": "semantic",
                    "type": "conversational",
                    "content": data["content"],
                    "metadata": {
                        "imported_from": "openclaw",
                    },
                }
            )

        return transformed


# ==============================================================================
# Backup Scheduler
# ==============================================================================


class BackupScheduler:
    """
    Schedules automatic backups.
    """

    def __init__(self, config: BackupConfig, backup_manager: BackupManager):
        self.config = config
        self.backup_manager = backup_manager

    def should_backup(self, last_backup: datetime | None) -> bool:
        """Determine if a backup should be run based on schedule."""
        if last_backup is None:
            return True

        now = datetime.now()

        if self.config.schedule == "daily":
            return (now - last_backup).days >= 1
        elif self.config.schedule == "weekly":
            return (now - last_backup).days >= 7
        elif self.config.schedule == "monthly":
            return (now - last_backup).days >= 30

        return False

    def clean_old_backups(self) -> int:
        """Clean up old backups based on retention policy."""
        backups = self.backup_manager.list_backups()
        now = datetime.now()
        removed = 0

        for backup in backups:
            age_days = (now - backup.created_at).days

            if self.config.schedule == "daily":
                if age_days > self.config.retention_daily:
                    Path(backup.file_path).unlink(missing_ok=True)
                    removed += 1
            elif self.config.schedule == "weekly":
                if age_days > self.config.retention_weekly * 7:
                    Path(backup.file_path).unlink(missing_ok=True)
                    removed += 1
            elif self.config.schedule == "monthly":
                if age_days > self.config.retention_monthly * 30:
                    Path(backup.file_path).unlink(missing_ok=True)
                    removed += 1

        return removed
