from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field


class RetentionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episodic_days: int = Field(default=30, ge=1)
    archive_days: int = Field(default=365, ge=1)
    default_search_limit: int = Field(default=10, ge=1, le=100)


class EmbeddingsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(default="local", description="Provider: 'local' or 'openai'")
    model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", description="Model name"
    )
    dimension: int = Field(default=384, description="Embedding dimension")
    openai_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI model when provider is 'openai'",
    )
    batch_size: int = Field(
        default=32, description="Batch size for embedding generation"
    )


class PipelineConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=True)
    max_agents: int = Field(default=10, ge=1)
    default_timeout_seconds: int = Field(default=300, ge=1)


class PatternDetectionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trajectory_limit: int = Field(default=100, ge=1)
    min_sequence_length: int = Field(default=2, ge=1)
    min_frequency: int = Field(default=2, ge=1)


class DatasetGenerationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    min_trajectories: int = Field(default=100, ge=1)


class LearningConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=True)
    pattern_detection: PatternDetectionConfig = Field(
        default_factory=PatternDetectionConfig
    )
    dataset_generation: DatasetGenerationConfig = Field(
        default_factory=DatasetGenerationConfig
    )


class SkillDetectionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_pattern_count: int = Field(default=3, ge=1)
    success_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    min_task_complexity: str = Field(default="medium")


class SkillStorageConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    directory: Path = Field(default=Path("~/.openclaw/gnosys/skills"))
    max_skills: int = Field(default=100, ge=1)
    auto_cleanup: bool = True
    delete_below_success_rate: float = Field(default=0.5, ge=0.0, le=1.0)


class SkillsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=True)
    auto_detect: bool = True
    detection: SkillDetectionConfig = Field(default_factory=SkillDetectionConfig)
    storage: SkillStorageConfig = Field(default_factory=SkillStorageConfig)


class SchedulerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=True)
    max_concurrent: int = Field(default=5, ge=1)
    timeout_seconds: int = Field(default=300, ge=1)
    retry_enabled: bool = True
    retry_max_attempts: int = Field(default=3, ge=1)
    retry_backoff: str = Field(default="exponential")


class APIAuthConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(default="bearer")
    token: str = Field(default="gnosys_api_token")


class APICorsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )


class APIRateLimitConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    requests_per_minute: int = Field(default=60, ge=1)


class APIConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=True)
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8766, ge=1, le=65535)
    auth: APIAuthConfig = Field(default_factory=APIAuthConfig)
    cors: APICorsConfig = Field(default_factory=APICorsConfig)
    rate_limit: APIRateLimitConfig = Field(default_factory=APIRateLimitConfig)


class BackupConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=True)
    schedule: str = Field(default="daily")  # daily, weekly, monthly
    retention_daily: int = Field(default=7, ge=1)
    retention_weekly: int = Field(default=4, ge=1)
    retention_monthly: int = Field(default=12, ge=1)
    location: Path = Field(default=Path("~/.openclaw/gnosys/backups"))
    compression: str = Field(default="gzip")


class MonitoringConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=True)
    metrics_port: int = Field(default=8767, ge=1, le=65535)
    health_check_interval_seconds: int = Field(default=60, ge=1)


class MemoryStorageConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    directory: Path = Field(default=Path("~/.openclaw/gnosys/memory"))
    max_slots: int = Field(default=1000, ge=1)


class ContextConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=True)
    max_tokens: int = Field(default=4096, ge=256, le=16384)
    default_tiers: list[str] = Field(
        default_factory=lambda: ["working", "episodic", "semantic"]
    )


class EncryptionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=False)
    algorithm: str = Field(default="AES-256-GCM")
    key_storage: str = Field(default="env")  # env, system_keychain


class SecretsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    storage: str = Field(default="env")  # env, system_keychain
    providers: dict[str, str] = Field(default_factory=dict)


class SubAgentSandboxConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    network_access: bool = False
    file_system: str = Field(default="restricted")  # unrestricted, restricted, none
    allowed_paths: list[str] = Field(default_factory=list)
    max_memory_mb: int = Field(default=512)
    max_cpu_percent: int = Field(default=50)


class SandboxConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=False)
    sub_agent: SubAgentSandboxConfig = Field(default_factory=SubAgentSandboxConfig)


class ExecApprovalConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=False)
    auto_approve_safe: bool = True
    dangerous_tools: list[str] = Field(
        default_factory=lambda: ["exec", "process", "browser"]
    )
    require_approval: list[str] = Field(default_factory=lambda: ["shell", "delete"])


class SecurityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    encryption: EncryptionConfig = Field(default_factory=EncryptionConfig)
    secrets: SecretsConfig = Field(default_factory=SecretsConfig)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)
    exec_approval: ExecApprovalConfig = Field(default_factory=ExecApprovalConfig)


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    db_path: Path = Field(default=Path("./data/gnosys.db"))
    vectors_path: Path = Field(default=Path("./data/vectors.db"))
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8766, ge=1, le=65535)
    retention: RetentionConfig = Field(default_factory=RetentionConfig)
    embeddings: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    learning: LearningConfig = Field(default_factory=LearningConfig)
    skills: SkillsConfig = Field(default_factory=SkillsConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    backup: BackupConfig = Field(default_factory=BackupConfig)
    context: ContextConfig = Field(default_factory=ContextConfig)
    memory: MemoryStorageConfig = Field(default_factory=MemoryStorageConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)

    def resolved_db_path(self) -> Path:
        return self.db_path.expanduser().resolve()

    def resolved_vectors_path(self) -> Path:
        return self.vectors_path.expanduser().resolve()

    def ensure_runtime_paths(self) -> None:
        self.resolved_db_path().parent.mkdir(parents=True, exist_ok=True)
        self.resolved_vectors_path().parent.mkdir(parents=True, exist_ok=True)
        # Create skills storage directory
        skills_dir = self.skills.storage.directory.expanduser().resolve()
        skills_dir.mkdir(parents=True, exist_ok=True)
        # Create backup directory
        backup_dir = self.backup.location.expanduser().resolve()
        backup_dir.mkdir(parents=True, exist_ok=True)
        # Create memory storage directory
        memory_dir = self.memory.directory.expanduser().resolve()
        memory_dir.mkdir(parents=True, exist_ok=True)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    return int(raw)


def load_config(overrides: Mapping[str, Any] | None = None) -> AppConfig:
    data: dict[str, Any] = {
        "db_path": os.getenv("GNOSYS_DB_PATH", "./data/gnosys.db"),
        "vectors_path": os.getenv("GNOSYS_VECTORS_PATH", "./data/vectors.db"),
        "host": os.getenv("GNOSYS_HOST", "127.0.0.1"),
        "port": _env_int("GNOSYS_PORT", 8766),
        "retention": {
            "episodic_days": _env_int("GNOSYS_RETENTION_EPISODIC_DAYS", 30),
            "archive_days": _env_int("GNOSYS_RETENTION_ARCHIVE_DAYS", 365),
            "default_search_limit": _env_int("GNOSYS_DEFAULT_SEARCH_LIMIT", 10),
        },
        "embeddings": {
            "provider": os.getenv("GNOSYS_EMBEDDINGS_PROVIDER", "local"),
            "model": os.getenv(
                "GNOSYS_EMBEDDINGS_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
            ),
            "dimension": _env_int("GNOSYS_EMBEDDINGS_DIMENSION", 384),
            "openai_model": os.getenv(
                "GNOSYS_EMBEDDINGS_OPENAI_MODEL", "text-embedding-3-small"
            ),
            "batch_size": _env_int("GNOSYS_EMBEDDINGS_BATCH_SIZE", 32),
        },
        "pipeline": {
            "enabled": os.getenv("GNOSYS_PIPELINE_ENABLED", "true").lower() == "true",
            "max_agents": _env_int("GNOSYS_PIPELINE_MAX_AGENTS", 10),
            "default_timeout_seconds": _env_int("GNOSYS_PIPELINE_TIMEOUT", 300),
        },
        "learning": {
            "enabled": os.getenv("GNOSYS_LEARNING_ENABLED", "true").lower() == "true",
            "pattern_detection": {
                "trajectory_limit": _env_int("GNOSYS_LEARNING_TRAJECTORY_LIMIT", 100),
                "min_sequence_length": _env_int("GNOSYS_LEARNING_MIN_SEQ_LENGTH", 2),
                "min_frequency": _env_int("GNOSYS_LEARNING_MIN_FREQ", 2),
            },
            "dataset_generation": {
                "success_threshold": float(
                    os.getenv("GNOSYS_LEARNING_SUCCESS_THRESHOLD", "0.8")
                ),
                "min_trajectories": _env_int("GNOSYS_LEARNING_MIN_TRAJECTORIES", 100),
            },
        },
        "skills": {
            "enabled": os.getenv("GNOSYS_SKILLS_ENABLED", "true").lower() == "true",
            "auto_detect": os.getenv("GNOSYS_SKILLS_AUTO_DETECT", "true").lower()
            == "true",
            "detection": {
                "min_pattern_count": _env_int("GNOSYS_SKILLS_MIN_PATTERN", 3),
                "success_threshold": float(
                    os.getenv("GNOSYS_SKILLS_SUCCESS_THRESHOLD", "0.8")
                ),
            },
            "storage": {
                "directory": os.getenv(
                    "GNOSYS_SKILLS_DIR", "~/.openclaw/gnosys/skills"
                ),
                "max_skills": _env_int("GNOSYS_SKILLS_MAX", 100),
            },
        },
        "scheduler": {
            "enabled": os.getenv("GNOSYS_SCHEDULER_ENABLED", "true").lower() == "true",
            "max_concurrent": _env_int("GNOSYS_SCHEDULER_MAX_CONCURRENT", 5),
            "timeout_seconds": _env_int("GNOSYS_SCHEDULER_TIMEOUT", 300),
        },
        "api": {
            "enabled": os.getenv("GNOSYS_API_ENABLED", "true").lower() == "true",
            "host": os.getenv("GNOSYS_API_HOST", "127.0.0.1"),
            "port": _env_int("GNOSYS_API_PORT", 8766),
            "auth": {
                "type": os.getenv("GNOSYS_API_AUTH_TYPE", "bearer"),
                "token": os.getenv("GNOSYS_API_TOKEN", "gnosys_api_token"),
            },
        },
        "monitoring": {
            "enabled": os.getenv("GNOSYS_MONITORING_ENABLED", "true").lower() == "true",
            "metrics_port": _env_int("GNOSYS_MONITORING_PORT", 8767),
        },
        "backup": {
            "enabled": os.getenv("GNOSYS_BACKUP_ENABLED", "true").lower() == "true",
            "schedule": os.getenv("GNOSYS_BACKUP_SCHEDULE", "daily"),
            "retention_daily": _env_int("GNOSYS_BACKUP_RETENTION_DAILY", 7),
            "retention_weekly": _env_int("GNOSYS_BACKUP_RETENTION_WEEKLY", 4),
            "retention_monthly": _env_int("GNOSYS_BACKUP_RETENTION_MONTHLY", 12),
            "location": os.getenv(
                "GNOSYS_BACKUP_LOCATION", "~/.openclaw/gnosys/backups"
            ),
        },
        "context": {
            "enabled": os.getenv("GNOSYS_CONTEXT_ENABLED", "true").lower() == "true",
            "max_tokens": _env_int("GNOSYS_CONTEXT_MAX_TOKENS", 4096),
        },
        "memory": {
            "directory": os.getenv("GNOSYS_MEMORY_DIR", "~/.openclaw/gnosys/memory"),
            "max_slots": _env_int("GNOSYS_MEMORY_MAX_SLOTS", 1000),
        },
        "security": {
            "encryption": {
                "enabled": os.getenv(
                    "GNOSYS_SECURITY_ENCRYPTION_ENABLED", "false"
                ).lower()
                == "true",
                "algorithm": os.getenv(
                    "GNOSYS_SECURITY_ENCRYPTION_ALGORITHM", "AES-256-GCM"
                ),
                "key_storage": os.getenv(
                    "GNOSYS_SECURITY_ENCRYPTION_KEY_STORAGE", "env"
                ),
            },
            "secrets": {
                "storage": os.getenv("GNOSYS_SECRETS_STORAGE", "env"),
                "providers": {
                    "openai": os.getenv("GNOSYS_OPENAI_KEY", ""),
                    "anthropic": os.getenv("GNOSYS_ANTHROPIC_KEY", ""),
                },
            },
            "sandbox": {
                "enabled": os.getenv("GNOSYS_SECURITY_SANDBOX_ENABLED", "false").lower()
                == "true",
                "sub_agent": {
                    "network_access": os.getenv(
                        "GNOSYS_SANDBOX_NETWORK_ACCESS", "false"
                    ).lower()
                    == "true",
                    "file_system": os.getenv("GNOSYS_SANDBOX_FS", "restricted"),
                    "allowed_paths": os.getenv(
                        "GNOSYS_SANDBOX_ALLOWED_PATHS", ""
                    ).split(",")
                    if os.getenv("GNOSYS_SANDBOX_ALLOWED_PATHS")
                    else [],
                    "max_memory_mb": _env_int("GNOSYS_SANDBOX_MAX_MEMORY_MB", 512),
                    "max_cpu_percent": _env_int("GNOSYS_SANDBOX_MAX_CPU_PERCENT", 50),
                },
            },
            "exec_approval": {
                "enabled": os.getenv("GNOSYS_EXEC_APPROVAL_ENABLED", "false").lower()
                == "true",
                "auto_approve_safe": os.getenv(
                    "GNOSYS_EXEC_AUTO_APPROVE", "true"
                ).lower()
                == "true",
            },
        },
    }
    if overrides:
        data = _deep_merge(data, dict(overrides))
    config = AppConfig.model_validate(data)
    config.ensure_runtime_paths()
    return config


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged
