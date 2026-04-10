from __future__ import annotations

from datetime import date, datetime

import pytest

from core.storage.package_manifest import (
    PackageManifest,
    PackageManifestArtifactPointer,
    PackageManifestExample,
    PackageManifestMaterialization,
    PackageManifestRawManifest,
    validate_package_manifest_payload,
)


def test_package_manifest_normalizes_selected_examples_and_artifacts() -> None:
    manifest = PackageManifest(
        package_id=" train:2026-03 ",
        selected_examples=(
            PackageManifestExample(
                example_id=" example-001 ",
                planning_index_ref=" planning:index:protein:P12345 ",
                source_record_refs=(" raw:protein:P12345 ", "raw:protein:P12345"),
                canonical_ids=(" protein:P12345 ", "protein:P12345"),
                artifact_pointers=(
                    PackageManifestArtifactPointer(
                        artifact_kind=" feature_vector ",
                        pointer=" cache/features/p12345.npy ",
                        selector="sequence",
                        source_name=" UniProt ",
                    ),
                    PackageManifestArtifactPointer(
                        artifact_kind="mmcif",
                        pointer=" cache/structures/p12345.cif ",
                        selector="chain=A",
                        source_name=" RCSB ",
                        notes=(" hydrate on selection ", "hydrate on selection"),
                    ),
                ),
            ),
            PackageManifestExample(
                example_id="example-002",
                planning_index_ref="planning:index:protein:P67890",
                source_record_refs=("raw:protein:P67890",),
                canonical_ids=("protein:P67890",),
                artifact_pointers=(
                    PackageManifestArtifactPointer(
                        artifact_kind="embedding",
                        pointer="cache/embeddings/p67890.pt",
                    ),
                ),
            ),
        ),
        raw_manifests=(
            PackageManifestRawManifest(
                source_name=" UniProt ",
                raw_manifest_id=" UniProt:2026_03:download:raw ",
                raw_manifest_ref=" manifests/uniprot-2026_03.json ",
                release_version=" 2026_03 ",
                release_date=date(2026, 3, 22),
                retrieval_mode=" Download ",
                source_locator=" https://example.org/uniprot ",
                planning_index_ref=" planning:index:protein:P12345 ",
            ),
            PackageManifestRawManifest(
                source_name="BindingDB",
                raw_manifest_id="BindingDB:2026.02:download:raw",
                raw_manifest_ref="manifests/bindingdb-2026.02.json",
                release_version="2026.02",
                retrieval_mode="download",
                planning_index_ref="planning:index:assay:RS123",
            ),
        ),
        planning_index_refs=(" planning:index:protein:P12345 ", "planning:index:assay:RS123"),
        materialization=PackageManifestMaterialization(
            split_name=" train ",
            split_artifact_id=" split:train:2026-03 ",
            materialization_run_id=" run-009 ",
            materialization_mode=" Selective ",
            materialized_at=datetime(2026, 3, 22, 15, 30, 0),
            package_version=" v1 ",
            package_state=" Published ",
            published_at=datetime(2026, 3, 22, 15, 45, 0),
            notes=(" finalized package ",),
        ),
        provenance=(" builder:run-009 ", " builder:run-009 "),
        notes=(" selected examples only ",),
    )

    assert manifest.package_id == "train:2026-03"
    assert manifest.manifest_id == "package:train:2026-03:v1"
    assert manifest.package_state == "published"
    assert manifest.package_version == "v1"
    assert manifest.published_at == "2026-03-22T15:45:00"
    assert manifest.selected_example_ids == ("example-001", "example-002")
    assert manifest.selected_examples[0].canonical_ids == ("protein:P12345",)
    assert manifest.selected_examples[0].artifact_pointers[0].artifact_kind == "feature"
    assert manifest.selected_examples[0].artifact_pointers[1].artifact_kind == "structure"
    assert manifest.raw_manifests[0].raw_manifest_id == "UniProt:2026_03:download:raw"
    assert manifest.raw_manifests[0].release_date == "2026-03-22"
    assert manifest.raw_manifests[0].retrieval_mode == "download"
    assert manifest.planning_index_refs == (
        "planning:index:protein:P12345",
        "planning:index:assay:RS123",
    )
    assert manifest.materialization is not None
    assert manifest.materialization.package_state == "published"
    assert manifest.materialization.materialization_mode == "selective"
    assert manifest.materialization.materialized_at == "2026-03-22T15:30:00"
    assert manifest.materialization.published_at == "2026-03-22T15:45:00"

    payload = manifest.to_dict()
    assert payload["manifest_id"] == "package:train:2026-03:v1"
    assert payload["selected_example_ids"] == ["example-001", "example-002"]
    assert payload["raw_manifest_count"] == 2
    assert payload["selected_examples"][0]["artifact_pointers"][1]["artifact_kind"] == "structure"
    assert payload["materialization"]["split_name"] == "train"


def test_validate_package_manifest_payload_accepts_common_aliases() -> None:
    manifest = validate_package_manifest_payload(
        {
            "package": "package-002",
            "examples": [
                {
                    "id": "example-a",
                    "planning_ref": "planning:index:protein:P12345",
                    "record_refs": ("raw:protein:P12345",),
                    "canonical_id": "protein:P12345",
                    "artifacts": [
                        {
                            "kind": "pdb",
                            "path": "cache/structures/p12345.pdb",
                            "selection": "chain=A",
                            "source": "RCSB",
                        }
                    ],
                }
            ],
            "source_manifests": [
                {
                    "source": "UniProt",
                    "manifest_id": "UniProt:2026_03:download:raw",
                    "manifest_ref": "manifests/uniprot.json",
                    "version": "2026_03",
                    "mode": "download",
                    "planning_ref": "planning:index:protein:P12345",
                }
            ],
            "planning_refs": ("planning:index:protein:P12345",),
            "split_metadata": {
                "split": "validation",
                "split_id": "split:validation:2026-03",
                "run_id": "run-010",
                "strategy": "selective",
                "materialized": "2026-03-22T10:00:00",
                "version": "2.0.0",
                "state": "frozen",
            },
            "lineage": ("builder:run-010",),
        }
    )

    assert manifest.package_id == "package-002"
    assert manifest.selected_example_ids == ("example-a",)
    assert manifest.raw_manifests[0].raw_manifest_id == "UniProt:2026_03:download:raw"
    assert manifest.selected_examples[0].artifact_pointers[0].artifact_kind == "structure"
    assert manifest.materialization is not None
    assert manifest.materialization.split_name == "validation"
    assert manifest.materialization.package_state == "frozen"
    assert manifest.provenance == ("builder:run-010",)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {
                "package_id": "package-003",
                "selected_examples": (),
                "raw_manifests": (
                    PackageManifestRawManifest(
                        source_name="UniProt",
                        raw_manifest_id="UniProt:2026_03:download:raw",
                        raw_manifest_ref="manifests/uniprot.json",
                        release_version="2026_03",
                    ),
                ),
                "planning_index_refs": ("planning:index:protein:P12345",),
            },
            "selected_examples must not be empty",
        ),
        (
            {
                "package_id": "package-003",
                "selected_examples": (
                    PackageManifestExample(
                        example_id="example-a",
                        artifact_pointers=(
                            PackageManifestArtifactPointer(
                                artifact_kind="feature",
                                pointer="cache/features/example-a.npy",
                            ),
                        ),
                    ),
                ),
                "raw_manifests": (),
                "planning_index_refs": ("planning:index:protein:P12345",),
            },
            "raw_manifests must not be empty",
        ),
        (
            {
                "package_id": "package-003",
                "selected_examples": (
                    PackageManifestExample(
                        example_id="example-a",
                        artifact_pointers=(
                            PackageManifestArtifactPointer(
                                artifact_kind="feature",
                                pointer="cache/features/example-a.npy",
                            ),
                        ),
                    ),
                ),
                "raw_manifests": (
                    PackageManifestRawManifest(
                        source_name="UniProt",
                        raw_manifest_id="UniProt:2026_03:download:raw",
                        raw_manifest_ref="manifests/uniprot.json",
                        release_version="2026_03",
                    ),
                ),
                "planning_index_refs": (),
            },
            "planning_index_refs must not be empty",
        ),
        (
            {
                "package_id": "package-003",
                "selected_examples": (
                    PackageManifestExample(
                        example_id="example-a",
                        artifact_pointers=(
                            PackageManifestArtifactPointer(
                                artifact_kind="feature",
                                pointer="cache/features/example-a.npy",
                            ),
                        ),
                    ),
                ),
                "raw_manifests": (
                    PackageManifestRawManifest(
                        source_name="UniProt",
                        raw_manifest_id="UniProt:2026_03:download:raw",
                        raw_manifest_ref="manifests/uniprot.json",
                        release_version="2026_03",
                    ),
                ),
                "planning_index_refs": ("planning:index:protein:P12345",),
                "materialization": {"package_state": "published"},
            },
            "materialization must be a PackageManifestMaterialization",
        ),
    ],
)
def test_package_manifest_rejects_invalid_input(kwargs, message) -> None:
    with pytest.raises((ValueError, TypeError), match=message):
        PackageManifest(**kwargs)


def test_package_manifest_materialization_requires_version_when_published() -> None:
    with pytest.raises(ValueError, match="published package materializations require"):
        PackageManifestMaterialization(
            package_state="published",
            materialized_at="2026-03-22T00:00:00",
            published_at="2026-03-22T00:00:00",
        )
