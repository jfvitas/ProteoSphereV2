from __future__ import annotations

from pathlib import Path

from execution.reference_pipeline import run_reference_pipeline


def test_reference_smoke_readme_exists_and_describes_the_smoke_run() -> None:
    readme_path = (
        Path(__file__).resolve().parents[2] / "runs" / "reference_smoke" / "README.md"
    )
    contents = readme_path.read_text(encoding="utf-8")

    assert readme_path.is_file()
    assert "Reference Smoke Run" in contents
    assert "summary-only" in contents
    assert "tests\\integration\\test_reference_smoke_run.py" in contents
    assert "trainer_runtime" in contents


def test_reference_smoke_run_stays_truthful_about_partial_training() -> None:
    result = run_reference_pipeline(
        run_id="reference-smoke-run-001",
        dataset_id="reference-smoke-package",
        requested_modalities=("sequence", "structure"),
        examples=_example_payloads(),
        source_packages=("source://smoke/package",),
        notes=("reference smoke run",),
        metadata={"purpose": "smoke-run"},
    )

    assert result.status == "partial"
    assert result.dataset.example_count == 2
    assert result.model_result.status.backend_ready is True
    assert result.training_result.status.backend_ready is False
    assert result.training_result.status.blocker is not None
    assert result.training_result.status.blocker.stage == "trainer_runtime"
    assert result.metrics.example_count == 2
    assert result.metrics.complete_requested_rate == 1.0
    assert result.summary["blocked_stage_count"] == 1
    assert result.spec.config["status"] == "summary_only"


def _example_payloads() -> tuple[dict[str, object], dict[str, object]]:
    return (
        {
            "example_id": "smoke-example-1",
            "protein_ref": {
                "entity_kind": "protein",
                "canonical_id": "P31749",
                "source_record_id": "SMOKE-1",
            },
            "feature_pointers": (
                {
                    "modality": "sequence",
                    "pointer": "artifact://sequence/P31749",
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
                    "label_name": "kd_nanomolar",
                    "label_kind": "continuous",
                    "value": 22.5,
                    "unit": "nM",
                },
            ),
            "source_lineage_refs": ("source://smoke/example-1",),
            "split": "train",
        },
        {
            "example_id": "smoke-example-2",
            "protein_ref": {
                "entity_kind": "protein",
                "canonical_id": "P69905",
                "source_record_id": "SMOKE-2",
            },
            "feature_pointers": (
                {
                    "modality": "sequence",
                    "pointer": "artifact://sequence/P69905",
                    "feature_family": "sequence_window",
                },
                {
                    "modality": "structure",
                    "pointer": "chain:B",
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
            "source_lineage_refs": ("source://smoke/example-2",),
            "split": "val",
        },
    )
