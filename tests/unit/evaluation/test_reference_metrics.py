from __future__ import annotations

import pytest

from datasets.baseline.schema import (
    BaselineDatasetExample,
    BaselineDatasetSchema,
    BaselineEntityRef,
    BaselineFeaturePointer,
    BaselineLabel,
)
from evaluation.reference.metrics import (
    DEFAULT_REFERENCE_METRICS_ID,
    ReferenceMetrics,
    summarize_reference_metrics,
)
from models.reference.model import ReferenceModel


def test_summarize_reference_metrics_reports_conservative_contract_values() -> None:
    dataset = _dataset_schema()
    result = ReferenceModel().run(dataset)

    metrics = summarize_reference_metrics(result, provenance={"benchmark": "starter-wave"})

    assert isinstance(metrics, ReferenceMetrics)
    assert metrics.metrics_id == DEFAULT_REFERENCE_METRICS_ID
    assert metrics.model_name == "baseline-reference-model-skeleton"
    assert metrics.dataset_contract == "BaselineDatasetSchema"
    assert metrics.dataset_id == "baseline-demo"
    assert metrics.schema_version == 1
    assert metrics.example_count == 2
    assert metrics.requested_modalities == ("sequence", "structure")
    assert metrics.available_modalities == ("sequence", "structure", "ligand")
    assert metrics.missing_requested_modalities == ()
    assert metrics.requested_modality_presence_rate == {
        "sequence": pytest.approx(0.5),
        "structure": pytest.approx(0.5),
    }
    assert metrics.requested_coverage_mean == pytest.approx(0.5)
    assert metrics.requested_coverage_min == pytest.approx(0.5)
    assert metrics.requested_coverage_max == pytest.approx(0.5)
    assert metrics.complete_requested_example_count == 0
    assert metrics.complete_requested_rate == pytest.approx(0.0)
    assert metrics.lineage_complete_example_count == 1
    assert metrics.lineage_complete_rate == pytest.approx(0.5)
    assert metrics.split_counts == {"train": 1, "val": 1}
    assert metrics.example_metrics[0].requested_coverage == pytest.approx(0.5)
    assert metrics.example_metrics[0].complete_requested_modalities is False
    assert metrics.example_metrics[1].feature_modalities == ("structure", "ligand")
    assert metrics.provenance["benchmark"] == "starter-wave"
    assert metrics.provenance["dataset_id"] == "baseline-demo"
    assert metrics.to_dict()["example_count"] == 2


def test_summarize_reference_metrics_rejects_empty_inputs() -> None:
    empty_dataset = BaselineDatasetSchema(
        dataset_id="empty-baseline",
        requested_modalities=("sequence",),
        examples=(),
    )

    with pytest.raises(ValueError, match="at least one example"):
        summarize_reference_metrics(empty_dataset)


def _dataset_schema() -> BaselineDatasetSchema:
    return BaselineDatasetSchema(
        dataset_id="baseline-demo",
        requested_modalities=("sequence", "structure"),
        examples=(
            BaselineDatasetExample(
                example_id="example-1",
                protein_ref=BaselineEntityRef(
                    entity_kind="protein",
                    canonical_id="P12345",
                    source_record_id="SRC-1",
                ),
                feature_pointers=(
                    BaselineFeaturePointer(
                        modality="sequence",
                        pointer="residues:1-20",
                        feature_family="sequence_window",
                    ),
                ),
                labels=(
                    BaselineLabel(
                        label_name="affinity",
                        label_kind="continuous",
                        value=5.4,
                        unit="uM",
                    ),
                ),
                source_lineage_refs=("source://unit-test/example-1",),
                split="train",
            ),
            BaselineDatasetExample(
                example_id="example-2",
                protein_ref=BaselineEntityRef(
                    entity_kind="protein",
                    canonical_id="P67890",
                    source_record_id="SRC-2",
                ),
                structure_ref=BaselineEntityRef(
                    entity_kind="structure",
                    canonical_id="1ABC",
                ),
                ligand_ref=BaselineEntityRef(
                    entity_kind="ligand",
                    canonical_id="CHEBI:1234",
                ),
                feature_pointers=(
                    BaselineFeaturePointer(
                        modality="structure",
                        pointer="chain:A",
                        feature_family="structure_context",
                    ),
                    BaselineFeaturePointer(
                        modality="ligand",
                        pointer="ligand:L1",
                        feature_family="ligand_context",
                    ),
                ),
                labels=(
                    BaselineLabel(
                        label_name="label",
                        label_kind="binary",
                        value=True,
                    ),
                ),
                split="val",
            ),
        ),
        source_packages=("source://unit-test/package",),
    )
