from __future__ import annotations

from datetime import date

import pytest

from datasets.baseline.builder import BaselineDatasetBuilder, build_baseline_dataset
from datasets.baseline.schema import (
    BaselineDatasetExample,
    BaselineEntityRef,
    BaselineFeaturePointer,
    BaselineLabel,
)


def test_baseline_dataset_builder_normalizes_examples_and_metadata() -> None:
    builder = BaselineDatasetBuilder(
        dataset_id="baseline-dataset",
        requested_modalities=("Sequence", "affinity", "sequence"),
        package_id="package-123",
        package_state="draft",
        created_at=date(2026, 4, 3),
        source_packages=("raw-package-1", "RAW-PACKAGE-1"),
        notes=("  keep lineage ", ""),
        metadata={"source": "baseline", "feature_dims": {"sequence": 128, "affinity": 6}},
    )

    dataset = builder.build(
        [
            {
                "example_id": "baseline-example-1",
                "protein_ref": {
                    "entity_kind": "protein",
                    "canonical_id": "protein:P31749",
                },
                "feature_pointers": [
                    {
                        "modality": "protein",
                        "pointer": "artifact://sequence/P31749",
                        "feature_family": "sequence_baseline",
                    },
                    {
                        "modality": "assay",
                        "pointer": "artifact://affinity/BDBM123",
                        "feature_family": "affinity_baseline",
                    },
                ],
                "labels": [
                    {
                        "label_name": "kd_nanomolar",
                        "label_kind": "regression",
                        "value": 22.5,
                        "unit": "nM",
                        "qualifier": "=",
                    }
                ],
                "source_lineage_refs": ["raw://bindingdb/BDBM123"],
            },
            BaselineDatasetExample(
                example_id="baseline-example-2",
                protein_ref=BaselineEntityRef(
                    entity_kind="protein",
                    canonical_id="protein:P69905",
                    source_record_id="uniprot:P69905",
                ),
                feature_pointers=(
                    BaselineFeaturePointer(
                        modality="sequence",
                        pointer="artifact://sequence/P69905",
                        feature_family="sequence_baseline",
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
        ]
    )

    assert dataset.dataset_id == "baseline-dataset"
    assert dataset.schema_version == 1
    assert dataset.example_count == 2
    assert dataset.available_modalities == ("sequence", "affinity")
    assert dataset.lineage_complete_example_count == 2
    assert dataset.package_id == "package-123"
    assert dataset.package_state == "draft"
    assert dataset.created_at == "2026-04-03"
    assert dataset.source_packages == ("raw-package-1",)
    assert dataset.notes == ("keep lineage",)
    assert dataset.metadata["source"] == "baseline"
    assert dataset.metadata["feature_dims"] == {"sequence": 128, "affinity": 6}
    assert dataset.examples[0].example_id == "baseline-example-1"
    assert dataset.examples[0].labels[0].value == 22.5
    assert dataset.examples[1].protein_ref.canonical_id == "protein:P69905"


def test_build_baseline_dataset_rejects_empty_example_sets() -> None:
    with pytest.raises(ValueError, match="examples must not be empty"):
        build_baseline_dataset([], dataset_id="baseline-dataset")


def test_build_baseline_dataset_rejects_duplicate_example_ids() -> None:
    example = BaselineDatasetExample(
        example_id="baseline-example-dup",
        protein_ref=BaselineEntityRef(entity_kind="protein", canonical_id="protein:P68871"),
        feature_pointers=(
            BaselineFeaturePointer(modality="sequence", pointer="artifact://sequence/P68871"),
        ),
    )

    with pytest.raises(ValueError, match="duplicate example_id"):
        build_baseline_dataset(
            (example, example),
            dataset_id="baseline-dataset",
        )
