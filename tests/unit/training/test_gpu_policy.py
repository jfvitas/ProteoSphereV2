from __future__ import annotations

import pytest

from training.runtime.gpu_policy import (
    GPUJobRequest,
    GPUSchedulingPolicy,
    GPUWorkerSnapshot,
    capacity_available,
    count_active_gpu_workers,
    evaluate_gpu_request,
    gpu_slots_remaining,
)


def test_gpu_policy_classifies_training_titles_and_gpu_runtime_targets() -> None:
    title_decision = evaluate_gpu_request(
        {"task_id": "P5-T009", "title": "Implement flagship training entrypoint"}
    )
    runtime_decision = evaluate_gpu_request(
        {
            "task_id": "job-3",
            "title": "Inference prep",
            "requested_device": "multi_gpu_data_parallel",
        }
    )

    assert title_decision.gpu_required is True
    assert title_decision.allowed is True
    assert title_decision.assignment == "gpu"
    assert "title_marker:train" in title_decision.matched_signals
    assert runtime_decision.gpu_required is True
    assert runtime_decision.allowed is True
    assert runtime_decision.assignment == "gpu"
    assert "requested_device:multi_gpu_data_parallel" in runtime_decision.matched_signals


def test_gpu_policy_blocks_gpu_requests_when_capacity_is_exhausted() -> None:
    policy = GPUSchedulingPolicy(gpu_worker_limit=1)
    request = GPUJobRequest(
        task_id="P5-T010",
        title="Implement GPU scheduling policy",
        requested_device="single_cuda_gpu",
    )
    active_workers = [
        GPUWorkerSnapshot(
            task_id="P5-T009",
            title="Implement flagship training entrypoint",
            gpu_heavy=True,
            device_target="single_cuda_gpu",
        )
    ]

    decision = policy.evaluate(request, active_workers=active_workers)

    assert decision.allowed is False
    assert decision.assignment == "defer"
    assert decision.gpu_required is True
    assert decision.active_gpu_workers == 1
    assert decision.gpu_worker_limit == 1
    assert decision.gpu_slots_remaining == 0
    assert "capacity exhausted" in decision.reason.lower()


def test_gpu_policy_keeps_cpu_requests_allowed_when_gpu_capacity_is_full() -> None:
    active_workers = [
        {"task_id": "P5-T009", "title": "Implement flagship training entrypoint", "gpu_heavy": True}
    ]

    decision = evaluate_gpu_request(
        {"task_id": "docs-1", "title": "Write release notes", "requested_device": "cpu"},
        active_workers=active_workers,
    )

    assert decision.allowed is True
    assert decision.assignment == "cpu"
    assert decision.gpu_required is False
    assert decision.active_gpu_workers == 1
    assert decision.gpu_slots_remaining == 0
    assert capacity_available(
        {"task_id": "docs-1", "title": "Write release notes", "requested_device": "cpu"},
        active_workers=active_workers,
    )


def test_gpu_policy_counts_workers_and_reports_stable_payload_shape() -> None:
    active_workers = [
        {
            "task_id": "P5-T009",
            "title": "Implement flagship training entrypoint",
            "gpu_heavy": True,
        },
        {"task_id": "P6-T006", "title": "Scaffold operator app", "gpu_heavy": False},
    ]
    policy = GPUSchedulingPolicy(gpu_worker_limit=2)

    assert count_active_gpu_workers(active_workers) == 1
    assert gpu_slots_remaining(active_workers, gpu_worker_limit=2) == 1

    decision = policy.evaluate(
        {"task_id": "job-4", "title": "Validation", "requested_device": "cuda"}
    )
    payload = decision.to_dict()

    assert payload["policy_name"] == "gpu_capacity_policy_v1"
    assert payload["task_id"] == "job-4"
    assert payload["assignment"] == "gpu"
    assert payload["request"]["requested_device"] == "cuda"
    assert payload["request"]["task_id"] == "job-4"


def test_gpu_policy_rejects_negative_worker_limits() -> None:
    with pytest.raises(ValueError, match="gpu_worker_limit"):
        GPUSchedulingPolicy(gpu_worker_limit=-1)
