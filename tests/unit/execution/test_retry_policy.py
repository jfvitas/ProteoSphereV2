from __future__ import annotations

import pytest

from execution.retries.policy import (
    CheckpointDisposition,
    FailureClass,
    FailureDisposition,
    FailureSignal,
    RetryPolicy,
    TaskFailureState,
)


def test_retry_policy_marks_transient_failures_retryable_and_checkpoint_resumable():
    policy = RetryPolicy(default_retry_limit=3, base_backoff_seconds=2.0, jitter_fraction=0.0)
    signal = FailureSignal(
        failure_class=FailureClass.TRANSIENT_IO,
        node_type="source_acquire",
        checkpoint_available=True,
        checkpoint_valid=True,
        alternate_source_available=True,
    )

    decision = policy.evaluate(signal, attempt=1)

    assert decision.failure_disposition == FailureDisposition.RETRYABLE
    assert decision.task_state == TaskFailureState.FAILED_RETRYABLE
    assert decision.should_retry is True
    assert decision.is_terminal is False
    assert decision.retry_limit == 3
    assert decision.remaining_attempts == 2
    assert decision.next_delay_seconds == 2.0
    assert decision.checkpoint_disposition == CheckpointDisposition.RESUME_FROM_CHECKPOINT
    assert decision.alternate_source_allowed is True


def test_retry_policy_marks_schema_mismatch_nonretryable_and_preserves_checkpoint():
    policy = RetryPolicy(default_retry_limit=3, jitter_fraction=0.0)
    signal = FailureSignal(
        failure_class=FailureClass.SCHEMA_MISMATCH,
        checkpoint_available=True,
        checkpoint_valid=True,
    )

    decision = policy.evaluate(signal, attempt=1)

    assert decision.failure_disposition == FailureDisposition.NONRETRYABLE
    assert decision.task_state == TaskFailureState.FAILED_NONRETRYABLE
    assert decision.should_retry is False
    assert decision.is_terminal is True
    assert decision.next_delay_seconds is None
    assert decision.checkpoint_disposition == CheckpointDisposition.PRESERVE_CHECKPOINT
    assert decision.alternate_source_allowed is False


def test_retry_policy_exhausts_retry_budget_for_retryable_failures():
    policy = RetryPolicy(default_retry_limit=1, base_backoff_seconds=1.0, jitter_fraction=0.0)
    signal = FailureSignal(failure_class=FailureClass.RATE_LIMIT)

    decision = policy.evaluate(signal, attempt=1)

    assert decision.failure_disposition == FailureDisposition.RETRYABLE
    assert decision.task_state == TaskFailureState.FAILED_NONRETRYABLE
    assert decision.should_retry is False
    assert decision.is_terminal is True
    assert decision.remaining_attempts == 0
    assert decision.next_delay_seconds is None
    assert decision.checkpoint_disposition == CheckpointDisposition.NO_CHECKPOINT


def test_retry_policy_rejects_negative_attempts():
    policy = RetryPolicy()

    with pytest.raises(ValueError, match="attempt must be >= 0"):
        policy.evaluate(FailureSignal(failure_class=FailureClass.TRANSIENT_IO), attempt=-1)


def test_retry_policy_is_deterministic_by_default():
    policy = RetryPolicy()
    signal = FailureSignal(failure_class=FailureClass.TRANSIENT_IO)

    first = policy.evaluate(signal, attempt=1)
    second = policy.evaluate(signal, attempt=1)

    assert first.next_delay_seconds == second.next_delay_seconds == 1.0
