from __future__ import annotations

import pytest

from core.storage.canonical_store import CanonicalStore, CanonicalStoreRecord
from core.storage.package_manifest import (
    PackageManifest,
    PackageManifestArtifactPointer,
    PackageManifestExample,
    PackageManifestRawManifest,
)
from execution.materialization.package_builder import build_training_package
from execution.materialization.selective_materializer import materialize_selected_examples


def _package_manifest(*, canonical_id: str = "protein:P12345") -> PackageManifest:
    return PackageManifest(
        package_id="package-001",
        selected_examples=(
            PackageManifestExample(
                example_id="example-1",
                planning_index_ref="planning/index/example-1",
                source_record_refs=("source-a:1",),
                canonical_ids=(canonical_id,),
                artifact_pointers=(
                    PackageManifestArtifactPointer(
                        artifact_kind="feature",
                        pointer="artifacts/features/example-1.npy",
                        selector="feature:0",
                        source_name="source-a",
                        source_record_id="source-a:1",
                    ),
                    PackageManifestArtifactPointer(
                        artifact_kind="structure",
                        pointer="artifacts/structures/example-1.cif",
                        selector="structure:0",
                        source_name="source-a",
                        source_record_id="source-a:1",
                    ),
                ),
            )
        ,),
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


def test_build_training_package_assembles_final_manifest() -> None:
    selective_result = materialize_selected_examples(
        _package_manifest(),
        available_artifacts={
            "artifacts/features/example-1.npy": {
                "materialized_ref": "materialized/features/example-1.npy",
                "checksum": "sha256:feature",
                "provenance_refs": ("prov:feature",),
            },
            "artifacts/structures/example-1.cif": "materialized/structures/example-1.cif",
        },
        canonical_store=_canonical_store(),
        materialization_run_id="run-100",
        materialized_at="2026-03-22T12:34:00Z",
    )

    build = build_training_package(
        selective_result,
        package_version="v1",
        package_state="frozen",
        split_name="train",
        split_artifact_id="split:train:001",
        materialization_run_id="run-100",
        materialized_at="2026-03-22T12:34:00Z",
        provenance_refs=("builder:run-100",),
        notes=("assembled training package",),
    )

    assert build.status == "built"
    assert build.package_id == "package-001"
    assert build.selected_example_ids == ("example-1",)
    assert build.package_manifest.manifest_id == "package:package-001:v1"
    assert build.package_manifest.selected_example_ids == ("example-1",)
    assert build.package_manifest.provenance[:2] == (
        selective_result.package_manifest_id,
        "prov:package",
    )
    assert "raw/source-a/001.json" in build.package_manifest.provenance
    assert "planning/index/example-1" in build.package_manifest.provenance
    assert build.package_manifest.provenance[-1] == "builder:run-100"
    assert build.package_manifest.materialization is not None
    assert build.package_manifest.materialization.materialization_mode == "selective"
    assert build.package_manifest.materialization.split_name == "train"
    assert build.package_manifest.materialization.package_version == "v1"
    assert build.package_manifest.materialization.package_state == "frozen"
    assert build.to_dict()["package_manifest"]["manifest_id"] == "package:package-001:v1"
    round_tripped = type(build).from_dict(build.to_dict())
    assert round_tripped.package_manifest.manifest_id == build.package_manifest.manifest_id
    assert round_tripped.selected_example_ids == build.selected_example_ids


def test_build_training_package_preserves_partial_selection_and_issues() -> None:
    selective_result = materialize_selected_examples(
        _package_manifest(),
        available_artifacts={
            "artifacts/features/example-1.npy": "materialized/features/example-1.npy",
        },
        canonical_store=_canonical_store(),
    )

    build = build_training_package(
        selective_result,
        package_state="draft",
        notes=("partial package",),
    )

    assert build.status == "partial"
    assert build.package_manifest.selected_example_ids == ("example-1",)
    assert build.package_manifest.materialization is not None
    assert build.package_manifest.materialization.package_state == "draft"
    assert build.issues[0].example_id == "example-1"
    assert build.issues[0].message == "selected artifact payload is missing"


def test_build_training_package_rejects_published_incomplete_packages() -> None:
    selective_result = materialize_selected_examples(
        _package_manifest(canonical_id="protein:P99999"),
        available_artifacts={
            "artifacts/features/example-1.npy": "materialized/features/example-1.npy",
            "artifacts/structures/example-1.cif": "materialized/structures/example-1.cif",
        },
        canonical_store=_canonical_store(),
    )

    with pytest.raises(
        ValueError,
        match="published training packages require a fully materialized selection",
    ):
        build_training_package(
            selective_result,
            package_state="published",
            package_version="v1",
            published_at="2026-03-22T12:45:00Z",
        )
