from __future__ import annotations

import pytest

from datasets.baseline.schema import (
    BaselineDatasetExample,
    BaselineDatasetSchema,
    BaselineEntityRef,
    BaselineFeaturePointer,
    BaselineLabel,
)


def test_baseline_dataset_schema_round_trips_and_preserves_lineage() -> None:
    example = BaselineDatasetExample(
        example_id="baseline-example-1",
        protein_ref=BaselineEntityRef(
            entity_kind="protein",
            canonical_id="protein:P31749",
            source_record_id="uniprot:P31749",
            join_status="joined",
        ),
        structure_ref=BaselineEntityRef(
            entity_kind="structure",
            canonical_id="structure:4HHB",
            source_record_id="pdb:4HHB",
        ),
        ligand_ref=BaselineEntityRef(
            entity_kind="compound",
            canonical_id="ligand:ATP",
            source_record_id="chembl:25",
        ),
        observation_ref=BaselineEntityRef(
            entity_kind="measurement",
            canonical_id="observation:BDBM123",
            source_record_id="bindingdb:BDBM123",
        ),
        feature_pointers=(
            BaselineFeaturePointer(
                modality="protein",
                pointer="artifact://sequence/P31749",
                feature_family="sequence_baseline",
                source_name="UniProt",
            ),
            BaselineFeaturePointer(
                modality="assay",
                pointer="artifact://affinity/BDBM123",
                feature_family="affinity_baseline",
                source_name="BindingDB",
            ),
        ),
        labels=(
            BaselineLabel(
                label_name="kd_nanomolar",
                label_kind="regression",
                value=22.5,
                unit="nM",
                qualifier="=",
                source_record_id="bindingdb:BDBM123",
            ),
        ),
        source_lineage_refs=("raw://bindingdb/BDBM123", "normalized://assay/BDBM123"),
        split="train",
        metadata={"species": "human", "feature_dims": {"sequence": 128, "affinity": 6}},
    )
    dataset = BaselineDatasetSchema(
        dataset_id="baseline-dataset",
        examples=(example,),
        requested_modalities=("sequence", "affinity"),
        package_id="package-123",
        package_state="draft",
        source_packages=("raw-package-1",),
    )

    restored = BaselineDatasetSchema.from_dict(dataset.to_dict())

    assert restored == dataset
    assert restored.example_count == 1
    assert restored.lineage_complete_example_count == 1
    assert restored.available_modalities == ("sequence", "affinity")


def test_baseline_dataset_example_rejects_missing_features_and_duplicate_pointers() -> None:
    protein_ref = BaselineEntityRef(entity_kind="protein", canonical_id="protein:P69905")

    with pytest.raises(ValueError, match="feature_pointers must contain at least one pointer"):
        BaselineDatasetExample(
            example_id="baseline-example-empty",
            protein_ref=protein_ref,
            feature_pointers=(),
        )

    with pytest.raises(ValueError, match="duplicate feature pointer"):
        BaselineDatasetExample(
            example_id="baseline-example-dup",
            protein_ref=protein_ref,
            feature_pointers=(
                BaselineFeaturePointer(modality="sequence", pointer="artifact://seq/P69905"),
                BaselineFeaturePointer(modality="sequence", pointer="artifact://seq/P69905"),
            ),
        )


def test_baseline_dataset_schema_rejects_duplicate_examples_and_missing_labels_with_values(
) -> None:
    protein_ref = BaselineEntityRef(entity_kind="protein", canonical_id="protein:P68871")
    pointer = BaselineFeaturePointer(modality="sequence", pointer="artifact://seq/P68871")

    with pytest.raises(ValueError, match="missing labels must not carry a value"):
        BaselineLabel(label_name="activity", label_kind="missing", value=1)

    example = BaselineDatasetExample(
        example_id="baseline-example-dup",
        protein_ref=protein_ref,
        feature_pointers=(pointer,),
    )

    with pytest.raises(ValueError, match="duplicate example_id"):
        BaselineDatasetSchema(
            dataset_id="baseline-dataset",
            examples=(example, example),
        )
