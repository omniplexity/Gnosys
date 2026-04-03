"""
Security module for Gnosys.

Provides encryption, secrets management, agent sandboxing, and execution approval.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from pathlib import Path
from typing import Any

from pydantic import BaseModel


# Error codes for security
class SecurityError(Exception):
    """Base exception for security-related errors."""

    code = 1500


class EncryptionError(SecurityError):
    """Encryption/decryption failed."""

    code = 1501


class SecretsError(SecurityError):
    """Secrets management failed."""

    code = 1502


class SandboxError(SecurityError):
    """Sandbox violation detected."""

    code = 1503


class ExecutionApprovalError(SecurityError):
    """Execution approval denied."""

    code = 1504


# ==============================================================================
# Encryption
# ==============================================================================


class EncryptionManager:
    """
    Manages data encryption at rest using AES-256-GCM.

    Note: Full implementation requires a cryptographic library.
    This provides the interface and mock encryption for v0.9.
    """

    def __init__(
        self,
        enabled: bool = False,
        algorithm: str = "AES-256-GCM",
        key_storage: str = "env",
    ):
        self.enabled = enabled
        self.algorithm = algorithm
        self.key_storage = key_storage
        self._key: bytes | None = None

    def initialize(self, key: str | None = None) -> None:
        """Initialize encryption with a key."""
        if not self.enabled:
            return

        if key:
            self._key = key.encode("utf-8")[:32].ljust(32, b"\0")
        else:
            # Try to load from environment
            env_key = os.getenv("GNOSYS_ENCRYPTION_KEY")
            if env_key:
                self._key = env_key.encode("utf-8")[:32].ljust(32, b"\0")
            else:
                # Generate a new key (for first-time setup)
                self._key = secrets.token_bytes(32)
                # In production, this would be stored securely

    def encrypt(self, data: str) -> str:
        """Encrypt plaintext data."""
        if not self.enabled or not self._key:
            return data

        try:
            # UseFernet from cryptography library would be used here
            # For v0.9, we use a simple XOR as placeholder
            data_bytes = data.encode("utf-8")
            key_bytes = self._key * (len(data_bytes) // len(self._key) + 1)
            encrypted = bytes(
                a ^ b for a, b in zip(data_bytes, key_bytes[: len(data_bytes)])
            )
            return encrypted.hex()
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {e}")

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt encrypted data."""
        if not self.enabled or not self._key:
            return encrypted_data

        try:
            data_bytes = bytes.fromhex(encrypted_data)
            key_bytes = self._key * (len(data_bytes) // len(self._key) + 1)
            decrypted = bytes(
                a ^ b for a, b in zip(data_bytes, key_bytes[: len(data_bytes)])
            )
            return decrypted.decode("utf-8")
        except Exception as e:
            raise EncryptionError(f"Decryption failed: {e}")

    def encrypt_dict(self, data: dict[str, Any]) -> str:
        """Encrypt a dictionary as JSON."""
        return self.encrypt(json.dumps(data))

    def decrypt_dict(self, encrypted_data: str) -> dict[str, Any]:
        """Decrypt to a dictionary."""
        return json.loads(self.decrypt(encrypted_data))


# ==============================================================================
# Secrets Management
# ==============================================================================


class KeychainManager:
    """
    System keychain integration for secure secret storage.

    Supports:
    - Windows Credential Manager (via keyring)
    - macOS Keychain (via keyring)
    - Linux Secret Service (via keyring)
    """

    def __init__(self, app_name: str = "gnosys"):
        self.app_name = app_name
        self._keyring = None
        self._initialize_keyring()

    def _initialize_keyring(self) -> None:
        """Initialize the keyring backend."""
        try:
            import keyring

            self._keyring = keyring
        except ImportError:
            # keyring not available, will fallback to env/encrypted file
            pass

    def get_secret(self, key: str) -> str | None:
        """Get a secret from the system keychain."""
        if self._keyring:
            try:
                return self._keyring.get_password(self.app_name, key)
            except Exception:
                return None
        return None

    def set_secret(self, key: str, value: str) -> bool:
        """Set a secret in the system keychain."""
        if self._keyring:
            try:
                self._keyring.set_password(self.app_name, key, value)
                return True
            except Exception:
                return False
        return False

    def delete_secret(self, key: str) -> bool:
        """Delete a secret from the system keychain."""
        if self._keyring:
            try:
                self._keyring.delete_password(self.app_name, key)
                return True
            except Exception:
                return False
        return False

    def list_keys(self) -> list[str]:
        """List all keys stored for this app."""
        # Note: keyring doesn't provide list, so this is limited
        return []


class SecretsManager:
    """
    Manages API keys and secrets securely.

    Supports multiple storage backends:
    - env: Environment variables
    - system_keychain: OS keychain (Windows Credential Manager, macOS Keychain, etc.)
    - encrypted_file: Encrypted file storage
    """

    def __init__(
        self,
        storage: str = "env",
        providers: dict[str, str] | None = None,
        keychain_app_name: str = "gnosys",
    ):
        self.storage = storage
        self.providers = providers or {}
        self.keychain_app_name = keychain_app_name

        self._secrets: dict[str, str] = {}
        self._keychain: KeychainManager | None = None
        self._loaded = False
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the secrets manager."""
        if self._initialized:
            return

        if self.storage == "system_keychain":
            self._keychain = KeychainManager(self.keychain_app_name)

        self._initialized = True

    def load_secrets(self) -> None:
        """Load secrets from storage."""
        if self._loaded:
            return

        self.initialize()

        if self.storage == "env":
            # Load from environment variables
            for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]:
                env_value = os.getenv(key)
                if env_value:
                    # Map to gnosys naming
                    provider = key.lower().replace("_api_key", "")
                    self._secrets[provider] = env_value

        elif self.storage == "system_keychain" and self._keychain:
            # Load from keychain (lazy load - only when needed)
            for provider in self.providers:
                secret = self._keychain.get_secret(provider)
                if secret:
                    self._secrets[provider] = secret

        self._loaded = True

    def get_secret(self, provider: str) -> str | None:
        """Get a secret for a provider."""
        self.load_secrets()

        # Check memory first
        if provider in self._secrets:
            return self._secrets[provider]

        # Try keychain if configured
        if self.storage == "system_keychain" and self._keychain:
            secret = self._keychain.get_secret(provider)
            if secret:
                self._secrets[provider] = secret
                return secret

        # Check initial providers config
        return self.providers.get(provider)

    def set_secret(self, provider: str, value: str) -> bool:
        """Set a secret in storage."""
        self.load_secrets()
        self._secrets[provider] = value

        if self.storage == "system_keychain" and self._keychain:
            return self._keychain.set_secret(provider, value)

        return True

    def delete_secret(self, provider: str) -> bool:
        """Delete a secret."""
        if provider in self._secrets:
            del self._secrets[provider]

        if self.storage == "system_keychain" and self._keychain:
            return self._keychain.delete_secret(provider)

        return True

    def list_providers(self) -> list[str]:
        """List available secret providers."""
        self.load_secrets()
        return list(self._secrets.keys())

    def has_secret(self, provider: str) -> bool:
        """Check if a secret exists."""
        self.load_secrets()
        return provider in self._secrets and bool(self._secrets[provider])


# ==============================================================================
# Agent Sandboxing
# ==============================================================================


class PathValidator:
    """Validates file system paths against allowed paths."""

    def __init__(self, allowed_paths: list[str] | None = None):
        self.allowed_paths = [
            Path(p).expanduser().resolve() for p in (allowed_paths or [])
        ]

    def is_allowed(self, path: str) -> bool:
        """Check if a path is within allowed paths."""
        if not self.allowed_paths:
            return True  # No restrictions

        try:
            requested = Path(path).expanduser().resolve()
            for allowed in self.allowed_paths:
                try:
                    requested.relative_to(allowed)
                    return True
                except ValueError:
                    continue
            return False
        except Exception:
            return False


class AgentSandbox:
    """
    Provides sandboxing for sub-agents.
    """

    def __init__(
        self,
        enabled: bool = False,
        network_access: bool = False,
        file_system: str = "restricted",
        allowed_paths: list[str] | None = None,
        max_memory_mb: int = 512,
        max_cpu_percent: int = 50,
    ):
        self.enabled = enabled
        self.network_access = network_access
        self.file_system = file_system
        self.path_validator = PathValidator(allowed_paths)
        self.max_memory_mb = max_memory_mb
        self.max_cpu_percent = max_cpu_percent

    def check_file_access(self, path: str) -> bool:
        """Check if file access is allowed."""
        if not self.enabled:
            return True

        if self.file_system == "unrestricted":
            return True
        elif self.file_system == "none":
            return False

        return self.path_validator.is_allowed(path)

    def check_network_access(self) -> bool:
        """Check if network access is allowed."""
        if not self.enabled:
            return True
        return self.network_access

    def check_tool(self, tool_name: str, params: dict[str, Any]) -> bool:
        """
        Check if a tool execution is allowed.

        Returns True if allowed, False otherwise.
        """
        if not self.enabled:
            return True

        # Check file system operations
        fs_tools = ["read", "write", "edit", "glob", "grep"]
        if tool_name in fs_tools:
            if "filePath" in params:
                if not self.check_file_access(params["filePath"]):
                    return False

        # Check network operations
        net_tools = ["webfetch", "websearch", "codesearch"]
        if tool_name in net_tools:
            if not self.check_network_access():
                return False

        return True


# ==============================================================================
# Execution Approval
# ==============================================================================


class ApprovalDecision(BaseModel):
    """Result of an approval check."""

    approved: bool
    reason: str | None = None
    auto_approved: bool = False


class ExecutionApproval:
    """
    Manages execution approval for dangerous operations.
    """

    def __init__(
        self,
        enabled: bool = False,
        auto_approve_safe: bool = True,
        dangerous_tools: list[str] | None = None,
        require_approval: list[str] | None = None,
    ):
        self.enabled = enabled
        self.auto_approve_safe = auto_approve_safe
        self.dangerous_tools = dangerous_tools or ["exec", "process", "browser"]
        self.require_approval = require_approval or ["shell", "delete"]

    def check(self, tool_name: str, params: dict[str, Any]) -> ApprovalDecision:
        """
        Check if tool execution should be approved.

        Args:
            tool_name: Name of the tool to execute
            params: Parameters being passed to the tool

        Returns:
            ApprovalDecision with approval status and reason
        """
        if not self.enabled:
            return ApprovalDecision(approved=True, reason="Approval disabled")

        if tool_name in self.dangerous_tools:
            if self.auto_approve_safe and self._is_safe_execution(tool_name, params):
                return ApprovalDecision(
                    approved=True,
                    reason=f"Auto-approved safe execution of {tool_name}",
                    auto_approved=True,
                )
            return ApprovalDecision(
                approved=False,
                reason=f"Tool {tool_name} requires explicit approval",
            )

        if tool_name in self.require_approval:
            return ApprovalDecision(
                approved=False,
                reason=f"Tool {tool_name} requires approval",
            )

        return ApprovalDecision(approved=True, reason="No approval required")

    def _is_safe_execution(self, tool_name: str, params: dict[str, Any]) -> bool:
        """Determine if an execution is considered safe."""
        # Safe executions are those with limited blast radius
        # This is a placeholder implementation
        return True


# ==============================================================================
# Security Manager (facade)
# ==============================================================================


class SecurityManager:
    """
    Facade for all security functionality.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        config = config or {}

        # Encryption
        enc_config = config.get("encryption", {})
        self.encryption = EncryptionManager(
            enabled=enc_config.get("enabled", False),
            algorithm=enc_config.get("algorithm", "AES-256-GCM"),
            key_storage=enc_config.get("key_storage", "env"),
        )

        # Secrets
        secrets_config = config.get("secrets", {})
        self.secrets = SecretsManager(
            storage=secrets_config.get("storage", "env"),
            providers=secrets_config.get("providers", {}),
        )

        # Sandbox
        sandbox_config = config.get("sandbox", {})
        sub_agent = sandbox_config.get("sub_agent", {})
        self.sandbox = AgentSandbox(
            enabled=sandbox_config.get("enabled", False),
            network_access=sub_agent.get("network_access", False),
            file_system=sub_agent.get("file_system", "restricted"),
            allowed_paths=sub_agent.get("allowed_paths", []),
            max_memory_mb=sub_agent.get("max_memory_mb", 512),
            max_cpu_percent=sub_agent.get("max_cpu_percent", 50),
        )

        # Execution approval
        exec_config = config.get("exec_approval", {})
        self.exec_approval = ExecutionApproval(
            enabled=exec_config.get("enabled", False),
            auto_approve_safe=exec_config.get("auto_approve_safe", True),
            dangerous_tools=exec_config.get("dangerous_tools"),
            require_approval=exec_config.get("require_approval"),
        )

    def initialize(self) -> None:
        """Initialize security components."""
        self.encryption.initialize()

    def encrypt_memory_content(self, content: str) -> str:
        """Encrypt memory content."""
        return self.encryption.encrypt(content)

    def decrypt_memory_content(self, encrypted_content: str) -> str:
        """Decrypt memory content."""
        return self.encryption.decrypt(encrypted_content)

    def get_api_key(self, provider: str) -> str | None:
        """Get API key for a provider."""
        return self.secrets.get_secret(provider)

    def check_tool_execution(
        self, tool_name: str, params: dict[str, Any]
    ) -> ApprovalDecision:
        """Check if tool execution is allowed."""
        return self.exec_approval.check(tool_name, params)

    def check_file_access(self, path: str) -> bool:
        """Check if file access is allowed."""
        return self.sandbox.check_file_access(path)
