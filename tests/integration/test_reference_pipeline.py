from __future__ import annotations

import json

import pytest

from execution.reference_pipeline import (
    ReferencePipeline,
    ReferencePipelineConfig,
    load_reference_pipeline_spec,
    run_reference_pipeline,
)


def test_reference_pipeline_runs_end_to_end_through_builder_model_training_and_metrics() -> None:
    result = run_reference_pipeline(
        run_id="reference-run-001",
        dataset_id="reference-pipeline-demo",
        requested_modalities=("sequence", "structure"),
        examples=_example_payloads(),
        source_packages=("source://unit-test/package",),
        notes=("reference pipeline smoke test",),
        metadata={"purpose": "integration-smoke"},
    )

    assert result.spec.pipeline_name == "reference-execution-pipeline"
    assert result.dataset.dataset_id == "reference-pipeline-demo"
    assert result.dataset.example_count == 2
    assert result.dataset.requested_modalities == ("sequence", "structure")
    assert result.model_result.example_count == 2
    assert result.model_result.status.backend_ready is True
    assert result.training_result.planned_epoch_count == 1
    assert result.training_result.executed_epoch_count == 0
    assert result.training_result.status.backend_ready is False
    assert result.training_result.status.blocker is not None
    assert result.training_result.status.blocker.stage == "trainer_runtime"
    assert result.metrics.example_count == 2
    assert result.metrics.requested_modalities == ("sequence", "structure")
    assert result.status == "partial"
    assert result.blocked_stages == ("trainer_runtime",)
    assert "trainer backend" in result.reason.lower()
    assert result.summary["dataset"]["example_count"] == 2
    assert result.summary["training"]["planned_epoch_count"] == 1
    assert json.loads(json.dumps(result.to_dict()))["training_result"]["status"]["blocker"][
        "stage"
    ] == "trainer_runtime"


def test_reference_pipeline_preserves_dataset_modality_blockers() -> None:
    result = ReferencePipeline(
        ReferencePipelineConfig(
            run_id="reference-run-002",
            dataset_id="reference-pipeline-missing-modality",
            requested_modalities=("sequence", "structure", "ligand"),
            examples=_example_payloads(),
            metadata={"purpose": "integration-smoke"},
        )
    ).run()

    assert result.model_result.missing_requested_modalities == ("ligand",)
    assert result.training_result.missing_requested_modalities == ("ligand",)
    assert result.status == "partial"
    assert result.blocked_stages == ("modality_coverage", "trainer_runtime")
    assert "ligand" in result.reason.lower()
    payload = result.to_dict()
    assert payload["summary"]["blocked_stage_count"] == 2
    assert payload["metrics"]["example_count"] == 2


def test_reference_pipeline_rejects_empty_examples() -> None:
    with pytest.raises(ValueError, match="examples must not be empty"):
        ReferencePipelineConfig(
            run_id="reference-run-empty",
            dataset_id="reference-empty",
            examples=(),
        )


def test_reference_pipeline_spec_reports_pipeline_contract_surface() -> None:
    spec = load_reference_pipeline_spec()

    assert spec.pipeline_name == "reference-execution-pipeline"
    assert spec.source_path == "execution/reference_pipeline.py"
    assert spec.config["contract"] == (
        "baseline_builder_plus_reference_model_plus_reference_training_plus_reference_metrics"
    )
    assert spec.config["truth_boundary"] == "fail_closed"


def _example_payloads() -> tuple[dict[str, object], dict[str, object]]:
    return (
        {
            "example_id": "example-1",
            "protein_ref": {
                "entity_kind": "protein",
                "canonical_id": "P31749",
                "source_record_id": "SRC-1",
            },
            "feature_pointers": (
                {
                    "modality": "sequence",
                    "pointer": "artifact://sequence/P31749",
                    "feature_family": "sequence_window",
                },
                {
                    "modality": "affinity",
                    "pointer": "artifact://binding/P31749",
                    "feature_family": "binding_support",
                },
            ),
            "labels": (
                {
                    "label_name": "kd_nanomolar",
                    "label_kind": "continuous",
                    "value": 22.5,
                    "unit": "nM",
                },
            ),
            "source_lineage_refs": ("source://unit-test/example-1",),
            "split": "train",
        },
        {
            "example_id": "example-2",
            "protein_ref": {
                "entity_kind": "protein",
                "canonical_id": "P69905",
                "source_record_id": "SRC-2",
            },
            "structure_ref": {
                "entity_kind": "structure",
                "canonical_id": "1ABC",
            },
            "feature_pointers": (
                {
                    "modality": "sequence",
                    "pointer": "artifact://sequence/P69905",
                    "feature_family": "sequence_window",
                },
                {
                    "modality": "structure",
                    "pointer": "chain:A",
                    "feature_family": "structure_context",
                },
            ),
            "labels": (
                {
                    "label_name": "presence",
                    "label_kind": "binary",
                    "value": True,
                },
            ),
            "source_lineage_refs": ("source://unit-test/example-2",),
            "split": "val",
        },
    )
