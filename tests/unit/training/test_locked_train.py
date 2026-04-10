from __future__ import annotations

import pytest

from training.reference.locked_train import (
    LockedReferenceTrainingBackend,
    load_locked_training_spec,
    prepare_locked_reference_training,
)


def test_load_locked_training_spec_reads_master_handoff_defaults() -> None:
    spec = load_locked_training_spec()

    assert spec.optimizer == "adamw"
    assert spec.learning_rate == pytest.approx(1e-4)
    assert spec.batch_size == 32
    assert spec.epochs == 100
    assert spec.scheduler == "cosine"
    assert spec.mixed_precision is True
    assert (
        spec.source_path
        == "master_handoff_package/01_LOCKDOWN_SPEC/training/default_training.yaml"
    )


def test_locked_reference_training_backend_builds_deterministic_plan_and_state() -> None:
    backend = LockedReferenceTrainingBackend()

    first = backend.prepare(
        train_examples=65,
        val_examples=33,
        gradient_accumulation_steps=2,
        deterministic_seed=17,
        mixed_precision_dtype="bf16",
    )
    second = backend.prepare(
        train_examples=65,
        val_examples=33,
        gradient_accumulation_steps=2,
        deterministic_seed=17,
        mixed_precision_dtype="bf16",
    )

    assert first.plan == second.plan
    assert first.state == second.state
    assert first.plan.precision_mode == "bf16"
    assert first.plan.steps_per_epoch == 3
    assert first.plan.validation_steps == 2
    assert first.plan.optimizer_steps_per_epoch == 2
    assert first.plan.total_optimizer_steps == 200
    assert first.plan.effective_batch_size == 64
    assert [point.step for point in first.plan.learning_rate_points] == [0, 66, 133, 199]
    assert first.plan.learning_rate_points[0].learning_rate == pytest.approx(1e-4)
    assert first.plan.learning_rate_points[-1].learning_rate == pytest.approx(0.0)
    assert first.state.next_learning_rate == pytest.approx(1e-4)
    assert first.state.checkpoint_tag == "seed-0017-epoch-000"
    assert first.state.rng_streams == {"python": 17, "numpy": 17, "torch": 17}


def test_locked_reference_training_backend_reports_blocked_runtime_honestly() -> None:
    result = prepare_locked_reference_training(
        train_examples=96,
        val_examples=16,
        deterministic_seed=7,
    )

    assert result.blocked_stages == ("trainer_runtime",)
    assert result.plan.status.backend_ready is False
    assert result.plan.status.blocker is not None
    assert result.plan.status.resolved_backend == "contract-plan-only"
    assert result.plan.status.contract_fidelity == "configuration-and-plan-only"
    assert "no real deep-learning trainer runtime" in result.plan.status.blocker.reason.lower()
    assert "deterministic cosine learning-rate preview" in result.plan.status.provenance[
        "real_components"
    ]
    assert "AdamW optimizer object construction" in result.plan.status.provenance[
        "abstracted_components"
    ]
    assert result.state.phase == "blocked"


def test_locked_reference_training_backend_to_dict_exposes_stable_contract_shape() -> None:
    result = prepare_locked_reference_training(
        train_examples=40,
        val_examples=10,
        deterministic_seed=7,
    )

    payload = result.to_dict()

    assert set(payload) == {"spec", "plan", "state", "blockers"}
    assert payload["spec"]["optimizer"] == "adamw"
    assert payload["plan"]["scheduler_name"] == "cosine"
    assert payload["plan"]["status"]["resolved_backend"] == "contract-plan-only"
    assert payload["plan"]["learning_rate_points"][0] == {
        "step": 0,
        "learning_rate": pytest.approx(1e-4),
    }
    assert payload["state"]["rng_streams"] == {"python": 7, "numpy": 7, "torch": 7}
    assert payload["state"]["phase"] == "blocked"
    assert payload["blockers"] == [
        {
            "stage": "trainer_runtime",
            "requested_backend": "adamw+cosine+fp16",
            "reason": (
                "The repository can load the locked training spec and derive a deterministic "
                "plan/state contract, but no real deep-learning trainer runtime is wired under "
                "training/reference yet."
            ),
        }
    ]
