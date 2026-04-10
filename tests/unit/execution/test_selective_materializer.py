from __future__ import annotations

from core.storage.canonical_store import CanonicalStore, CanonicalStoreRecord
from core.storage.package_manifest import (
    PackageManifest,
    PackageManifestArtifactPointer,
    PackageManifestExample,
    PackageManifestRawManifest,
)
from execution.materialization.selective_materializer import materialize_selected_examples


def _package_manifest(
    *,
    canonical_id: str = "protein:P12345",
    include_structure_pointer: bool = True,
) -> PackageManifest:
    artifact_pointers = [
        PackageManifestArtifactPointer(
            artifact_kind="feature",
            pointer="artifacts/features/example-1.npy",
            selector="feature:0",
            source_name="source-a",
            source_record_id="source-a:1",
            notes=("pinned",),
        ),
    ]
    if include_structure_pointer:
        artifact_pointers.append(
            PackageManifestArtifactPointer(
                artifact_kind="structure",
                pointer="artifacts/structures/example-1.cif",
                selector="structure:0",
                source_name="source-a",
                source_record_id="source-a:1",
            )
        )

    return PackageManifest(
        package_id="package-001",
        selected_examples=(
            PackageManifestExample(
                example_id="example-1",
                planning_index_ref="planning/index/example-1",
                source_record_refs=("source-a:1",),
                canonical_ids=(canonical_id,),
                artifact_pointers=tuple(artifact_pointers),
                notes=("selected example",),
            ),
        ),
        raw_manifests=(
            PackageManifestRawManifest(
                source_name="source-a",
                raw_manifest_id="raw-source-a-001",
                raw_manifest_ref="raw/source-a/001.json",
                release_version="2026-03-22",
                source_locator="https://example.test/source-a",
                planning_index_ref="planning/index/example-1",
            ),
        ),
        planning_index_refs=("planning/index/example-1",),
        provenance=("prov:package",),
        notes=("package notes",),
    )


def _canonical_store() -> CanonicalStore:
    return CanonicalStore(
        records=(
            CanonicalStoreRecord(
                canonical_id="protein:P12345",
                entity_kind="protein",
                canonical_payload={"accession": "P12345"},
                provenance_refs=("prov:protein",),
            ),
        ),
    )


def test_materialize_selected_examples_preserves_pinned_selection_only() -> None:
    package_manifest = _package_manifest()
    result = materialize_selected_examples(
        package_manifest,
        available_artifacts={
            "artifacts/features/example-1.npy": {
                "materialized_ref": "materialized/features/example-1.npy",
                "checksum": "sha256:feature",
                "provenance_refs": ("prov:feature",),
            },
            "artifacts/structures/example-1.cif": "materialized/structures/example-1.cif",
            "artifacts/structures/ignored.cif": "materialized/structures/ignored.cif",
        },
        canonical_store=_canonical_store(),
        materialization_run_id="run-001",
        materialized_at="2026-03-22T12:00:00Z",
    )

    assert result.status == "materialized"
    assert result.selected_example_ids == ("example-1",)
    assert result.storage_key.startswith("materialization/package-001/")
    assert result.provenance_refs[0] == package_manifest.manifest_id
    assert result.selected_examples[0].status == "materialized"
    assert result.selected_examples[0].selected_artifact_pointers == (
        "artifacts/features/example-1.npy",
        "artifacts/structures/example-1.cif",
    )
    assert len(result.selected_examples[0].materialized_artifacts) == 2
    assert {
        item.materialized_ref for item in result.selected_examples[0].materialized_artifacts
    } == {
        "materialized/features/example-1.npy",
        "materialized/structures/example-1.cif",
    }
    assert all(
        item.artifact_pointer.pointer != "artifacts/structures/ignored.cif"
        for item in result.selected_examples[0].materialized_artifacts
    )
    assert result.to_dict()["manifest_id"] == result.manifest_id
    round_tripped = type(result).from_dict(result.to_dict())
    assert round_tripped.manifest_id == result.manifest_id
    assert round_tripped.selected_example_ids == result.selected_example_ids


def test_materialize_selected_examples_reports_missing_artifacts_without_widening() -> None:
    package_manifest = _package_manifest()
    result = materialize_selected_examples(
        package_manifest,
        available_artifacts={
            "artifacts/features/example-1.npy": {
                "materialized_ref": "materialized/features/example-1.npy",
            },
            "artifacts/structures/ignored.cif": "materialized/structures/ignored.cif",
        },
        canonical_store=_canonical_store(),
    )

    assert result.status == "partial"
    assert len(result.issues) == 1
    assert result.issues[0].kind == "missing_artifact_payload"
    assert result.selected_examples[0].status == "partial"
    assert result.selected_examples[0].selected_artifact_pointers == (
        "artifacts/features/example-1.npy",
        "artifacts/structures/example-1.cif",
    )
    assert len(result.selected_examples[0].materialized_artifacts) == 1
    assert result.selected_examples[0].materialized_artifacts[0].materialized_ref == (
        "materialized/features/example-1.npy"
    )
    assert result.selected_examples[0].issues[0].artifact_pointer == (
        "artifacts/structures/example-1.cif"
    )
    assert all(
        item.artifact_pointer.pointer != "artifacts/structures/ignored.cif"
        for item in result.selected_examples[0].materialized_artifacts
    )


def test_materialize_selected_examples_exposes_missing_canonical_records() -> None:
    package_manifest = _package_manifest(
        canonical_id="protein:P99999",
        include_structure_pointer=False,
    )
    result = materialize_selected_examples(
        package_manifest,
        available_artifacts={
            "artifacts/features/example-1.npy": "materialized/features/example-1.npy",
        },
        canonical_store=_canonical_store(),
    )

    assert result.status == "partial"
    assert result.selected_examples[0].status == "partial"
    assert result.selected_examples[0].issues[0].kind == "missing_canonical_record"
    assert result.selected_examples[0].issues[0].canonical_id == "protein:P99999"
    assert len(result.selected_examples[0].materialized_artifacts) == 1
