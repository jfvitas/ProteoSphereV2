from __future__ import annotations

from datasets.baseline.schema import (
    BaselineDatasetExample,
    BaselineDatasetSchema,
    BaselineEntityRef,
    BaselineFeaturePointer,
    BaselineLabel,
)
from models.reference.model import (
    ReferenceModel,
    load_reference_model_spec,
    summarize_reference_dataset,
)


def test_load_reference_model_spec_exposes_baseline_contract_surface() -> None:
    spec = load_reference_model_spec()

    assert spec.model_name == "baseline-reference-model-skeleton"
    assert spec.dataset_contract == "BaselineDatasetSchema"
    assert spec.source_path == "datasets/baseline/schema.py"
    assert spec.config["contract"] == "baseline_dataset_schema"
    assert spec.config["interface"] == "summary_only"
    assert spec.config["schema_source"] == "datasets/baseline/schema.py"
    assert spec.config["builder_source"] == "datasets/baseline/builder.py"


def test_reference_model_summarizes_a_baseline_dataset_schema() -> None:
    dataset = _dataset_schema()
    model = ReferenceModel()

    result = model.run(dataset)

    assert result.dataset_id == "baseline-demo"
    assert result.schema_version == 1
    assert result.example_count == 2
    assert result.requested_modalities == ("sequence", "structure")
    assert result.available_modalities == ("sequence", "structure", "ligand")
    assert result.missing_requested_modalities == ()
    assert result.lineage_complete_example_count == 1
    assert result.blockers == ()
    assert result.blocked_stages == ()
    assert result.status.backend_ready is True
    assert result.status.resolved_backend == "baseline-dataset-summary"
    assert [summary.example_id for summary in result.example_summaries] == [
        "example-1",
        "example-2",
    ]
    assert result.example_summaries[0].protein_accession == "P12345"
    assert result.example_summaries[0].feature_modalities == ("sequence",)
    assert result.example_summaries[0].lineage_complete is True
    assert result.example_summaries[1].feature_modalities == ("structure", "ligand")
    assert result.example_summaries[1].lineage_complete is False

    payload = result.to_dict()
    assert payload["spec"]["model_name"] == "baseline-reference-model-skeleton"
    assert payload["dataset_id"] == "baseline-demo"
    assert payload["example_count"] == 2
    assert payload["status"]["backend_ready"] is True
    assert payload["example_summaries"][0]["feature_modalities"] == ["sequence"]


def test_reference_model_reports_missing_requested_modalities() -> None:
    dataset = BaselineDatasetSchema(
        dataset_id="baseline-missing-modalities",
        requested_modalities=("sequence", "structure"),
        examples=(
            BaselineDatasetExample(
                example_id="example-1",
                protein_ref=BaselineEntityRef(
                    entity_kind="protein",
                    canonical_id="P99999",
                ),
                feature_pointers=(
                    BaselineFeaturePointer(
                        modality="sequence",
                        pointer="residues:1-20",
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
            ),
        ),
    )

    result = summarize_reference_dataset(dataset)

    assert result.available_modalities == ("sequence",)
    assert result.missing_requested_modalities == ("structure",)
    assert result.status.backend_ready is False
    assert result.status.blocker is not None
    assert "structure" in result.status.blocker.reason
    assert result.blocked_stages == ("modality_coverage",)


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
