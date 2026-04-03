"""
Error Handling module for Gnosys.

Provides error codes, retry policies, and circuit breaker functionality.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TypeVar


# ==============================================================================
# Error Codes
# ==============================================================================


class ErrorCode(int, Enum):
    """Gnosys error codes."""

    # Memory errors (1000-1099)
    MEMORY_TIER_NOT_FOUND = 1000
    MEMORY_ITEM_NOT_FOUND = 1001
    MEMORY_STORAGE_FULL = 1002
    MEMORY_EMBEDDING_FAILED = 1003
    MEMORY_INVALID_TYPE = 1004
    MEMORY_CONSOLIDATION_FAILED = 1005

    # Pipeline errors (1100-1199)
    PIPELINE_AGENT_SPAWN_FAILED = 1100
    PIPELINE_AGENT_TIMEOUT = 1101
    PIPELINE_COORDINATION_FAILED = 1102
    PIPELINE_AGENT_NOT_FOUND = 1103
    PIPELINE_INVALID_PATTERN = 1104
    PIPELINE_MAX_DEPTH_EXCEEDED = 1105

    # Skills errors (1200-1299)
    SKILLS_SKILL_NOT_FOUND = 1200
    SKILLS_EXTRACTION_FAILED = 1201
    SKILLS_VERSION_CONFLICT = 1202
    SKILLS_STORAGE_FAILED = 1203
    SKILLS_DETECTION_FAILED = 1204

    # Learning errors (1300-1399)
    LEARNING_ANALYSIS_FAILED = 1300
    LEARNING_DATASET_FAILED = 1301
    LEARNING_TRAJECTORY_NOT_FOUND = 1302
    LEARNING_PATTERN_NOT_FOUND = 1303

    # Scheduler errors (1400-1499)
    SCHEDULER_TASK_NOT_FOUND = 1400
    SCHEDULER_INVALID_SCHEDULE = 1401
    SCHEDULER_DELIVERY_FAILED = 1402
    SCHEDULER_EXECUTION_FAILED = 1403
    SCHEDULER_MAX_CONCURRENT_EXCEEDED = 1404

    # Security errors (1500-1599)
    SECURITY_ENCRYPTION_FAILED = 1500
    SECURITY_DECRYPTION_FAILED = 1501
    SECURITY_SECRETS_FAILED = 1502
    SECURITY_SANDBOX_VIOLATION = 1503
    SECURITY_APPROVAL_DENIED = 1504

    # External errors (1600-1699)
    EXTERNAL_API_RATE_LIMITED = 1600
    EXTERNAL_PROVIDER_UNAVAILABLE = 1601
    EXTERNAL_MODEL_NOT_FOUND = 1602
    EXTERNAL_CONNECTION_FAILED = 1603

    # General errors (1700-1799)
    GENERAL_INVALID_INPUT = 1700
    GENERAL_CONFIGURATION_ERROR = 1701
    GENERAL_INTERNAL_ERROR = 1702


class GnosysError(Exception):
    """Base exception for Gnosys errors."""

    def __init__(
        self, message: str, code: ErrorCode = ErrorCode.GENERAL_INTERNAL_ERROR
    ):
        self.message = message
        self.code = code
        super().__init__(f"[{code.value}] {message}")


class MemoryError(GnosysError):
    """Memory-related errors."""

    def __init__(self, message: str, code: ErrorCode = ErrorCode.MEMORY_ITEM_NOT_FOUND):
        super().__init__(message, code)


class PipelineError(GnosysError):
    """Pipeline-related errors."""

    def __init__(
        self, message: str, code: ErrorCode = ErrorCode.PIPELINE_COORDINATION_FAILED
    ):
        super().__init__(message, code)


class SkillsError(GnosysError):
    """Skills-related errors."""

    def __init__(
        self, message: str, code: ErrorCode = ErrorCode.SKILLS_SKILL_NOT_FOUND
    ):
        super().__init__(message, code)


class LearningError(GnosysError):
    """Learning-related errors."""

    def __init__(
        self, message: str, code: ErrorCode = ErrorCode.LEARNING_ANALYSIS_FAILED
    ):
        super().__init__(message, code)


class SchedulerError(GnosysError):
    """Scheduler-related errors."""

    def __init__(
        self, message: str, code: ErrorCode = ErrorCode.SCHEDULER_EXECUTION_FAILED
    ):
        super().__init__(message, code)


class SecurityError(GnosysError):
    """Security-related errors."""

    def __init__(
        self, message: str, code: ErrorCode = ErrorCode.SECURITY_ENCRYPTION_FAILED
    ):
        super().__init__(message, code)


class ExternalError(GnosysError):
    """External API errors."""

    def __init__(
        self, message: str, code: ErrorCode = ErrorCode.EXTERNAL_CONNECTION_FAILED
    ):
        super().__init__(message, code)


# ==============================================================================
# Retry Policy
# ==============================================================================


class BackoffType(str, Enum):
    """Types of backoff strategies."""

    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    enabled: bool = True
    max_attempts: int = 3
    backoff_type: BackoffType = BackoffType.EXPONENTIAL
    base_seconds: float = 1.0
    max_seconds: float = 30.0
    retryable_errors: list[ErrorCode] = field(default_factory=list)


class RetryPolicy:
    """
    Implements retry logic with configurable backoff.
    """

    def __init__(self, config: RetryConfig | None = None):
        self.config = config or RetryConfig()

    def should_retry(self, attempt: int, error: Exception) -> bool:
        """Determine if a retry should be attempted."""
        if not self.config.enabled:
            return False

        if attempt >= self.config.max_attempts:
            return False

        # Check if error is retryable
        if isinstance(error, GnosysError):
            if self.config.retryable_errors:
                return error.code in self.config.retryable_errors
            return True

        # For non-Gnosys errors, retry by default
        return True

    def get_delay(self, attempt: int) -> float:
        """Calculate the delay before the next retry."""
        if self.config.backoff_type == BackoffType.FIXED:
            return self.config.base_seconds
        elif self.config.backoff_type == BackoffType.LINEAR:
            return min(self.config.base_seconds * attempt, self.config.max_seconds)
        elif self.config.backoff_type == BackoffType.EXPONENTIAL:
            delay = self.config.base_seconds * (2 ** (attempt - 1))
            return min(delay, self.config.max_seconds)
        return self.config.base_seconds

    async def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute a function with retry logic."""
        attempt = 0
        last_error: Exception | None = None

        while attempt < self.config.max_attempts:
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                last_error = e

                if not self.should_retry(attempt, e):
                    raise

                delay = self.get_delay(attempt)
                await asyncio.sleep(delay)
                attempt += 1

        if last_error:
            raise last_error
        raise GnosysError("Max retries exceeded", ErrorCode.GENERAL_INTERNAL_ERROR)


# ==============================================================================
# Circuit Breaker
# ==============================================================================


class CircuitState(str, Enum):
    """States of the circuit breaker."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    enabled: bool = True
    failure_threshold: int = 5
    success_threshold: int = 2
    recovery_timeout_seconds: int = 60
    half_open_max_calls: int = 3


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker."""

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    state_changes: int = 0


class CircuitBreaker:
    """
    Implements circuit breaker pattern for fault tolerance.
    """

    def __init__(self, config: CircuitBreakerConfig | None = None):
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: float | None = None
        self.half_open_calls = 0
        self.stats = CircuitBreakerStats()

    def _can_attempt(self) -> bool:
        """Check if a call can be attempted."""
        if not self.config.enabled:
            return True

        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time:
                elapsed = time.time() - self.last_failure_time
                if elapsed >= self.config.recovery_timeout_seconds:
                    self._transition_to_half_open()
                    return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.config.half_open_max_calls

        return True

    def _transition_to_half_open(self) -> None:
        """Transition to half-open state."""
        self.state = CircuitState.HALF_OPEN
        self.half_open_calls = 0
        self.stats.state_changes += 1

    def _transition_to_open(self) -> None:
        """Transition to open state."""
        self.state = CircuitState.OPEN
        self.last_failure_time = time.time()
        self.stats.state_changes += 1

    def _transition_to_closed(self) -> None:
        """Transition to closed state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.stats.state_changes += 1

    def record_success(self) -> None:
        """Record a successful call."""
        self.stats.successful_calls += 1
        self.stats.total_calls += 1

        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            self.success_count += 1

            if self.success_count >= self.config.success_threshold:
                self._transition_to_closed()
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call."""
        self.stats.failed_calls += 1
        self.stats.total_calls += 1
        self.failure_count += 1

        if self.state == CircuitState.HALF_OPEN:
            self._transition_to_open()
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self._transition_to_open()

    def record_rejection(self) -> None:
        """Record a rejected call."""
        self.stats.rejected_calls += 1

    async def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute a function through the circuit breaker."""
        if not self._can_attempt():
            self.record_rejection()
            raise GnosysError(
                "Circuit breaker is open",
                ErrorCode.EXTERNAL_PROVIDER_UNAVAILABLE,
            )

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise

    def get_state(self) -> dict[str, Any]:
        """Get current circuit breaker state."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "stats": {
                "total_calls": self.stats.total_calls,
                "successful_calls": self.stats.successful_calls,
                "failed_calls": self.stats.failed_calls,
                "rejected_calls": self.stats.rejected_calls,
                "state_changes": self.stats.state_changes,
            },
        }


# ==============================================================================
# Error Handler
# ==============================================================================


class ErrorHandler:
    """
    Central error handler that coordinates retry and circuit breaker.
    """

    def __init__(
        self,
        retry_config: RetryConfig | None = None,
        circuit_breaker_config: CircuitBreakerConfig | None = None,
    ):
        self.retry_policy = RetryPolicy(retry_config)
        self.circuit_breaker = CircuitBreaker(circuit_breaker_config)

    async def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        use_circuit_breaker: bool = True,
        use_retry: bool = True,
        **kwargs: Any,
    ) -> Any:
        """Execute with error handling."""
        if use_circuit_breaker:
            return await self.circuit_breaker.execute(
                self._with_retry if use_retry else func,
                *args,
                **kwargs,
            )
        elif use_retry:
            return await self.retry_policy.execute(func, *args, **kwargs)
        else:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)

    async def _with_retry(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Wrap function with retry logic."""
        return await self.retry_policy.execute(func, *args, **kwargs)

    def get_status(self) -> dict[str, Any]:
        """Get error handler status."""
        return {
            "retry": {
                "enabled": self.retry_policy.config.enabled,
                "max_attempts": self.retry_policy.config.max_attempts,
                "backoff_type": self.retry_policy.config.backoff_type.value,
            },
            "circuit_breaker": self.circuit_breaker.get_state(),
        }


# ==============================================================================
# Error Logger
# ==============================================================================


class ErrorLogger:
    """Logs errors for analysis and debugging."""

    def __init__(self, log_path: str | None = None):
        self.log_path = log_path

    def log_error(
        self,
        error: Exception,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Log an error with context."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        log_entry = {
            "timestamp": timestamp,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {},
        }

        if isinstance(error, GnosysError):
            log_entry["error_code"] = error.code.value

        # Print to console in development
        import json

        print(f"[ERROR] {json.dumps(log_entry)}")

        # Write to file if path is configured
        if self.log_path:
            try:
                with open(self.log_path, "a") as f:
                    f.write(json.dumps(log_entry) + "\n")
            except Exception:
                pass
