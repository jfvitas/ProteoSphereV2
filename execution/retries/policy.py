from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class FailureClass(StrEnum):
    """Explicit failure classes used to drive retry decisions."""

    TRANSIENT_IO = "transient_io"
    RATE_LIMIT = "rate_limit"
    RESOURCE_PRESSURE = "resource_pressure"
    EXTERNAL_DEPENDENCY = "external_dependency"
    SCHEMA_MISMATCH = "schema_mismatch"
    CONFIG_MISMATCH = "config_mismatch"
    CODE_BUG = "code_bug"
    INPUT_VALIDATION = "input_validation"
    CHECKPOINT_CORRUPTION = "checkpoint_corruption"
    UNKNOWN = "unknown"


class FailureDisposition(StrEnum):
    RETRYABLE = "retryable"
    NONRETRYABLE = "nonretryable"


class TaskFailureState(StrEnum):
    FAILED_RETRYABLE = "failed_retryable"
    FAILED_NONRETRYABLE = "failed_nonretryable"


class CheckpointDisposition(StrEnum):
    NO_CHECKPOINT = "no_checkpoint"
    RESUME_FROM_CHECKPOINT = "resume_from_checkpoint"
    PRESERVE_CHECKPOINT = "preserve_checkpoint"
    INVALIDATE_CHECKPOINT = "invalidate_checkpoint"


@dataclass(frozen=True)
class FailureSignal:
    """Structured failure metadata passed into the retry policy."""

    failure_class: FailureClass
    message: str = ""
    node_type: str | None = None
    checkpoint_available: bool = False
    checkpoint_valid: bool = True
    alternate_source_available: bool = False


@dataclass(frozen=True)
class RetryDecision:
    """Concrete retry/recovery outcome for a failure signal."""

    failure_class: FailureClass
    failure_disposition: FailureDisposition
    task_state: TaskFailureState
    should_retry: bool
    is_terminal: bool
    retry_limit: int
    remaining_attempts: int
    next_delay_seconds: float | None
    checkpoint_disposition: CheckpointDisposition
    alternate_source_allowed: bool


@dataclass(frozen=True)
class RetryPolicy:
    """Deterministic retry policy with checkpoint-aware recovery hints."""

    default_retry_limit: int = 3
    base_backoff_seconds: float = 1.0
    max_backoff_seconds: float = 60.0
    jitter_fraction: float = 0.0
    retryable_failure_classes: frozenset[FailureClass] = field(
        default_factory=lambda: frozenset(
            {
                FailureClass.TRANSIENT_IO,
                FailureClass.RATE_LIMIT,
                FailureClass.RESOURCE_PRESSURE,
                FailureClass.EXTERNAL_DEPENDENCY,
            }
        )
    )
    nonretryable_failure_classes: frozenset[FailureClass] = field(
        default_factory=lambda: frozenset(
            {
                FailureClass.SCHEMA_MISMATCH,
                FailureClass.CONFIG_MISMATCH,
                FailureClass.CODE_BUG,
                FailureClass.INPUT_VALIDATION,
                FailureClass.CHECKPOINT_CORRUPTION,
                FailureClass.UNKNOWN,
            }
        )
    )

    def __post_init__(self) -> None:
        if self.default_retry_limit < 0:
            raise ValueError("default_retry_limit must be >= 0")
        if self.base_backoff_seconds <= 0:
            raise ValueError("base_backoff_seconds must be > 0")
        if self.max_backoff_seconds < self.base_backoff_seconds:
            raise ValueError("max_backoff_seconds must be >= base_backoff_seconds")
        if not 0 <= self.jitter_fraction <= 1:
            raise ValueError("jitter_fraction must be between 0 and 1")
        if self.retryable_failure_classes & self.nonretryable_failure_classes:
            raise ValueError("failure classes cannot be both retryable and nonretryable")

    def classify(self, signal: FailureSignal) -> FailureDisposition:
        if signal.failure_class in self.retryable_failure_classes:
            return FailureDisposition.RETRYABLE
        return FailureDisposition.NONRETRYABLE

    def retry_limit_for(self, node_retry_limit: int | None = None) -> int:
        if node_retry_limit is None:
            return self.default_retry_limit
        if node_retry_limit < 0:
            raise ValueError("node_retry_limit must be >= 0")
        return node_retry_limit

    def evaluate(
        self,
        signal: FailureSignal,
        *,
        attempt: int,
        node_retry_limit: int | None = None,
    ) -> RetryDecision:
        if attempt < 0:
            raise ValueError("attempt must be >= 0")

        retry_limit = self.retry_limit_for(node_retry_limit)
        failure_disposition = self.classify(signal)
        retry_budget_remaining = max(retry_limit - attempt, 0)
        should_retry = (
            failure_disposition == FailureDisposition.RETRYABLE
            and retry_budget_remaining > 0
        )
        is_terminal = not should_retry
        task_state = (
            TaskFailureState.FAILED_RETRYABLE
            if should_retry
            else TaskFailureState.FAILED_NONRETRYABLE
        )

        if signal.checkpoint_available and signal.checkpoint_valid:
            checkpoint_disposition = (
                CheckpointDisposition.RESUME_FROM_CHECKPOINT
                if should_retry
                else CheckpointDisposition.PRESERVE_CHECKPOINT
            )
        elif signal.checkpoint_available and not signal.checkpoint_valid:
            checkpoint_disposition = CheckpointDisposition.INVALIDATE_CHECKPOINT
        else:
            checkpoint_disposition = CheckpointDisposition.NO_CHECKPOINT

        next_delay_seconds = None
        if should_retry:
            # attempt counts completed failures; the first retry uses the base delay.
            retry_index = max(attempt - 1, 0)
            delay = self.base_backoff_seconds * (2**retry_index)
            next_delay_seconds = min(max(delay, 0.0), self.max_backoff_seconds)

        alternate_source_allowed = (
            should_retry
            and signal.node_type == "source_acquire"
            and signal.alternate_source_available
            and signal.failure_class in {
                FailureClass.TRANSIENT_IO,
                FailureClass.EXTERNAL_DEPENDENCY,
                FailureClass.RATE_LIMIT,
            }
        )

        return RetryDecision(
            failure_class=signal.failure_class,
            failure_disposition=failure_disposition,
            task_state=task_state,
            should_retry=should_retry,
            is_terminal=is_terminal,
            retry_limit=retry_limit,
            remaining_attempts=retry_budget_remaining,
            next_delay_seconds=next_delay_seconds,
            checkpoint_disposition=checkpoint_disposition,
            alternate_source_allowed=alternate_source_allowed,
        )
