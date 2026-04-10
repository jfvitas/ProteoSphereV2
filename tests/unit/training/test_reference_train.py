from __future__ import annotations

from datasets.baseline.schema import (
    BaselineDatasetExample,
    BaselineDatasetSchema,
    BaselineEntityRef,
    BaselineFeaturePointer,
    BaselineLabel,
)
from training.reference.train import (
    ReferenceTrainingLoop,
    load_reference_training_spec,
    train_reference_dataset,
)


def _build_dataset(
    *,
    requested_modalities: tuple[str, ...] = ("sequence", "affinity"),
) -> BaselineDatasetSchema:
    return BaselineDatasetSchema(
        dataset_id="training-preview-dataset",
        requested_modalities=requested_modalities,
        examples=(
            BaselineDatasetExample(
                example_id="example-1",
                protein_ref=BaselineEntityRef(
                    entity_kind="protein",
                    canonical_id="protein:P31749",
                ),
                feature_pointers=(
                    BaselineFeaturePointer(
                        modality="sequence",
                        pointer="artifact://sequence/P31749",
                    ),
                    BaselineFeaturePointer(
                        modality="affinity",
                        pointer="artifact://binding/P31749",
                    ),
                ),
                labels=(
                    BaselineLabel(
                        label_name="kd_nanomolar",
                        label_kind="continuous",
                        value=22.5,
                        unit="nM",
                    ),
                ),
                source_lineage_refs=("raw://bindingdb/BDBM123",),
            ),
            BaselineDatasetExample(
                example_id="example-2",
                protein_ref=BaselineEntityRef(
                    entity_kind="protein",
                    canonical_id="protein:P69905",
                ),
                feature_pointers=(
                    BaselineFeaturePointer(
                        modality="sequence",
                        pointer="artifact://sequence/P69905",
                    ),
                ),
                labels=(
                    BaselineLabel(
                        label_name="presence",
                        label_kind="binary",
                        value=True,
                    ),
                ),
                source_lineage_refs=("raw://uniprot/P69905",),
            ),
        ),
    )


def test_load_reference_training_spec_reports_reference_training_contract() -> None:
    spec = load_reference_training_spec()

    assert spec.model_contract == "baseline-reference-model-skeleton"
    assert spec.training_contract == "reference-training-loop-skeleton"
    assert spec.config["training_mode"] == "summary_only"
    assert spec.source_path == "training/reference/train.py"


def test_reference_training_loop_builds_conservative_dry_run_summary() -> None:
    dataset = _build_dataset()

    loop = ReferenceTrainingLoop()
    result = loop.train(dataset)

    assert result.dataset_id == "training-preview-dataset"
    assert result.example_count == 2
    assert result.planned_epoch_count == 1
    assert result.executed_epoch_count == 0
    assert result.blocked_stages == ("trainer_runtime",)
    assert result.status.backend_ready is False
    assert result.status.resolved_backend == "contract-plan-only"
    assert result.status.contract_fidelity == "summary-only"
    assert result.dataset_summary.example_count == 2
    assert result.dataset_summary.lineage_complete_example_count == 2
    assert result.epoch_summaries[0].label_count == 2
    assert result.epoch_summaries[0].backend_mode == "contract-plan-only"
    assert result.to_dict()["status"]["blocker"]["stage"] == "trainer_runtime"


def test_reference_training_loop_preserves_modality_blockers_from_dataset_summary() -> None:
    dataset = _build_dataset(requested_modalities=("sequence", "affinity", "structure"))

    result = train_reference_dataset(dataset)

    assert result.dataset_summary.missing_requested_modalities == ("structure",)
    assert result.blocked_stages[:2] == ("modality_coverage", "trainer_runtime")
    assert "structure" in result.status.blocker.reason
    assert result.status.provenance["planned_epoch_count"] == 1
    assert result.to_dict()["missing_requested_modalities"] == ["structure"]
