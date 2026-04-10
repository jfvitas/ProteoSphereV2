from __future__ import annotations

from core.storage.canonical_store import CanonicalStore, CanonicalStoreRecord
from core.storage.embedding_cache import (
    EmbeddingCacheArtifactPointer,
    EmbeddingCacheCatalog,
    EmbeddingCacheEntry,
    EmbeddingCacheSourceRef,
    EmbeddingModelIdentity,
    EmbeddingRuntimeIdentity,
)
from core.storage.feature_cache import (
    FeatureCacheArtifactPointer,
    FeatureCacheCatalog,
    FeatureCacheEntry,
    FeatureCacheSourceRef,
)
from core.storage.package_manifest import (
    PackageManifest,
    PackageManifestArtifactPointer,
    PackageManifestExample,
    PackageManifestRawManifest,
)
from core.storage.planning_index_schema import (
    PlanningIndexEntry,
    PlanningIndexSchema,
    PlanningIndexSourceRecord,
)
from execution.storage_runtime import integrate_storage_runtime


def _package_manifest() -> PackageManifest:
    return PackageManifest(
        package_id="package-001",
        selected_examples=(
            PackageManifestExample(
                example_id="example-1",
                planning_index_ref="planning/example-1",
                source_record_refs=("source-a:1",),
                canonical_ids=("protein:P12345",),
                artifact_pointers=(
                    PackageManifestArtifactPointer(
                        artifact_kind="feature",
                        pointer="artifacts/features/example-1.npy",
                        selector="feature:0",
                        source_name="source-a",
                        source_record_id="source-a:1",
                    ),
                    PackageManifestArtifactPointer(
                        artifact_kind="embedding",
                        pointer="artifacts/embeddings/example-1.pt",
                        selector="embedding:0",
                        source_name="source-a",
                        source_record_id="source-a:1",
                    ),
                ),
            ),
        ),
        raw_manifests=(
            PackageManifestRawManifest(
                source_name="source-a",
                raw_manifest_id="raw-source-a-001",
                raw_manifest_ref="raw/source-a/001.json",
                release_version="2026-03-22",
                source_locator="https://example.test/source-a",
                planning_index_ref="planning/example-1",
            ),
        ),
        planning_index_refs=("planning/example-1",),
        provenance=("prov:package",),
        notes=("selected examples only",),
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


def _planning_index(*, include_example: bool = True) -> PlanningIndexSchema:
    records = ()
    if include_example:
        records = (
            PlanningIndexEntry(
                planning_id="planning/example-1",
                source_records=(
                    PlanningIndexSourceRecord(
                        source_name="source-a",
                        source_record_id="source-a:1",
                        release_version="2026-03-22",
                        manifest_id="raw/source-a/001.json",
                    ),
                ),
                canonical_ids=("protein:P12345",),
                join_status="joined",
                join_confidence=1.0,
            ),
        )
    return PlanningIndexSchema(records=records)


def _feature_cache() -> FeatureCacheCatalog:
    return FeatureCacheCatalog(
        records=(
            FeatureCacheEntry(
                cache_id="feature-cache-001",
                feature_family="sequence",
                cache_version="v1",
                source_refs=(
                    FeatureCacheSourceRef(
                        source_name="source-a",
                        source_record_id="source-a:1",
                        planning_id="planning/example-1",
                    ),
                ),
                canonical_ids=("protein:P12345",),
                join_status="joined",
                join_confidence=1.0,
                artifact_pointers=(
                    FeatureCacheArtifactPointer(
                        artifact_kind="feature_matrix",
                        pointer="artifacts/features/example-1.npy",
                        selector="feature:0",
                        source_name="source-a",
                        source_record_id="source-a:1",
                        planning_id="planning/example-1",
                    ),
                ),
            ),
        ),
    )


def _embedding_cache() -> EmbeddingCacheCatalog:
    return EmbeddingCacheCatalog(
        records=(
            EmbeddingCacheEntry(
                cache_id="embedding-cache-001",
                cache_family="sequence",
                cache_version="v1",
                model_identity=EmbeddingModelIdentity(
                    model_name="toy-embedding",
                    model_version="1",
                ),
                runtime_identity=EmbeddingRuntimeIdentity(
                    runtime_name="runtime",
                    runtime_version="1",
                ),
                source_refs=(
                    EmbeddingCacheSourceRef(
                        source_name="source-a",
                        source_record_id="source-a:1",
                        manifest_id="cache:embedding:001",
                        planning_id="planning/example-1",
                        provenance_id="prov:embedding",
                    ),
                ),
                provenance_refs=("prov:embedding",),
                canonical_ids=("protein:P12345",),
                join_status="joined",
                join_confidence=1.0,
                artifact_pointers=(
                    EmbeddingCacheArtifactPointer(
                        artifact_kind="embedding",
                        pointer="artifacts/embeddings/example-1.pt",
                        selector="embedding:0",
                        source_name="source-a",
                        source_record_id="source-a:1",
                        planning_id="planning/example-1",
                    ),
                ),
            ),
        ),
    )


def test_selected_example_package_materialization_is_integrated_end_to_end() -> None:
    runtime = integrate_storage_runtime(
        _package_manifest(),
        planning_index=_planning_index(),
        canonical_store=_canonical_store(),
        feature_cache=_feature_cache(),
        embedding_cache=_embedding_cache(),
        available_artifacts={
            "artifacts/features/example-1.npy": {
                "materialized_ref": "materialized/features/example-1.npy",
                "checksum": "sha256:feature",
                "provenance_refs": ("prov:feature",),
            },
            "artifacts/embeddings/example-1.pt": "materialized/embeddings/example-1.pt",
        },
        materialization_run_id="run-001",
        materialized_at="2026-03-22T13:00:00Z",
        package_version="v1",
        package_state="frozen",
        split_name="train",
        split_artifact_id="split:train:001",
        provenance_refs=("runtime:integration",),
    )

    assert runtime.status == "integrated"
    assert runtime.selected_example_ids == ("example-1",)
    assert runtime.selective_materialization.status == "materialized"
    assert runtime.package_build.status == "built"
    assert runtime.package_build.package_manifest.selected_example_ids == ("example-1",)
    assert runtime.package_build.package_manifest.materialization is not None
    assert runtime.package_build.package_manifest.materialization.split_name == "train"
    assert runtime.package_build.package_manifest.materialization.package_version == "v1"
    assert runtime.package_build.package_manifest.materialization.package_state == "frozen"
    assert runtime.package_build.package_manifest.provenance[:2] == (
        "package:package-001:draft",
        "prov:package",
    )
    assert runtime.package_build.package_manifest.provenance[-1] == "runtime:integration"
    assert (
        runtime.package_build.package_manifest.selected_examples[0]
        .artifact_pointers[0]
        .pointer
        == "artifacts/features/example-1.npy"
    )
    assert runtime.to_dict()["status"] == "integrated"


def test_selected_example_package_materialization_surfaces_missing_inputs() -> None:
    runtime = integrate_storage_runtime(
        _package_manifest(),
        planning_index=_planning_index(include_example=False),
        canonical_store=_canonical_store(),
        feature_cache=_feature_cache(),
        embedding_cache=None,
        available_artifacts={
            "artifacts/features/example-1.npy": "materialized/features/example-1.npy",
            "artifacts/embeddings/example-1.pt": "materialized/embeddings/example-1.pt",
        },
        package_state="draft",
    )

    assert runtime.status == "partial"
    assert runtime.package_build.status == "built"
    assert runtime.selective_materialization.status == "materialized"
    assert {issue.kind for issue in runtime.issues} == {
        "missing_planning_index_entry",
        "missing_embedding_cache_entry",
    }
    assert runtime.package_build.package_manifest.selected_example_ids == ("example-1",)
    assert runtime.package_build.package_manifest.materialization is not None
    assert runtime.package_build.package_manifest.materialization.package_state == "draft"
