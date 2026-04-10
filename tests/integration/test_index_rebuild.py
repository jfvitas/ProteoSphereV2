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
from core.storage.planning_index_schema import PlanningIndexSchema
from execution.indexing.protein_index import build_protein_planning_index
from execution.ingest.sequences import ingest_sequence_records
from execution.storage_runtime import integrate_storage_runtime


def _sequence_records() -> list[dict[str, object]]:
    return [
        {
            "accession": "P12345",
            "sequence": "ACDEFGHIK",
            "organism": "Homo sapiens",
            "name": "Alpha protein",
            "source": "UniProt",
            "source_id": "P12345_HUMAN",
            "reviewed": True,
            "provenance": {"source_ids": ["raw/uniprot/p12345.json"]},
        },
        {
            "accession": "P12345",
            "sequence": "ACDEFGHIK",
            "organism": "Homo sapiens",
            "name": "Beta protein",
            "source": "UniProt",
            "source_id": "P12345_HUMAN",
            "reviewed": True,
            "provenance": {"source_ids": ["raw/uniprot/p12345-alt.json"]},
        },
        {
            "accession": "Q99999",
            "sequence": "MEEPQSDPSV",
            "organism": "Homo sapiens",
            "name": "Gamma protein",
            "source": "UniProt",
            "source_id": "Q99999_HUMAN",
            "reviewed": True,
            "provenance": {"source_ids": ["raw/uniprot/q99999.json"]},
        },
    ]


def _canonical_store() -> CanonicalStore:
    return CanonicalStore(
        records=(
            CanonicalStoreRecord(
                canonical_id="protein:P12345",
                entity_kind="protein",
                canonical_payload={"accession": "P12345"},
                provenance_refs=("prov:protein:P12345",),
            ),
            CanonicalStoreRecord(
                canonical_id="protein:Q99999",
                entity_kind="protein",
                canonical_payload={"accession": "Q99999"},
                provenance_refs=("prov:protein:Q99999",),
            ),
        ),
    )


def _planning_index() -> PlanningIndexSchema:
    ingest_result = ingest_sequence_records(
        _sequence_records(),
        source_release={
            "source_name": "UniProt",
            "release_version": "2026_02",
            "release_date": "2026-03-01",
            "retrieval_mode": "download",
            "source_locator": "https://example.org/uniprot",
            "manifest_id": "UniProt:2026_02:download",
        },
    )
    return build_protein_planning_index(ingest_result)


def _feature_cache() -> FeatureCacheCatalog:
    return FeatureCacheCatalog(
        records=(
            FeatureCacheEntry(
                cache_id="feature-cache-p12345",
                feature_family="sequence",
                cache_version="v1",
                source_refs=(
                    FeatureCacheSourceRef(
                        source_name="UniProt",
                        source_record_id="P12345",
                        planning_id="protein:P12345",
                    ),
                ),
                canonical_ids=("protein:P12345",),
                join_status="joined",
                join_confidence=1.0,
                artifact_pointers=(
                    FeatureCacheArtifactPointer(
                        artifact_kind="feature_matrix",
                        pointer="artifacts/features/p12345.npy",
                        selector="feature:0",
                        source_name="UniProt",
                        source_record_id="P12345",
                        planning_id="protein:P12345",
                    ),
                ),
            ),
            FeatureCacheEntry(
                cache_id="feature-cache-q99999",
                feature_family="sequence",
                cache_version="v1",
                source_refs=(
                    FeatureCacheSourceRef(
                        source_name="UniProt",
                        source_record_id="Q99999",
                        planning_id="protein:Q99999",
                    ),
                ),
                canonical_ids=("protein:Q99999",),
                join_status="joined",
                join_confidence=1.0,
                artifact_pointers=(
                    FeatureCacheArtifactPointer(
                        artifact_kind="feature_matrix",
                        pointer="artifacts/features/q99999.npy",
                        selector="feature:0",
                        source_name="UniProt",
                        source_record_id="Q99999",
                        planning_id="protein:Q99999",
                    ),
                ),
            ),
        ),
    )


def _embedding_cache() -> EmbeddingCacheCatalog:
    return EmbeddingCacheCatalog(
        records=(
            EmbeddingCacheEntry(
                cache_id="embedding-cache-p12345",
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
                        source_name="UniProt",
                        source_record_id="P12345",
                        manifest_id="cache:embedding:p12345",
                        planning_id="protein:P12345",
                        provenance_id="prov:embedding:p12345",
                    ),
                ),
                provenance_refs=("prov:embedding:p12345",),
                canonical_ids=("protein:P12345",),
                join_status="joined",
                join_confidence=1.0,
                artifact_pointers=(
                    EmbeddingCacheArtifactPointer(
                        artifact_kind="embedding",
                        pointer="artifacts/embeddings/p12345.pt",
                        selector="embedding:0",
                        source_name="UniProt",
                        source_record_id="P12345",
                        planning_id="protein:P12345",
                    ),
                ),
            ),
            EmbeddingCacheEntry(
                cache_id="embedding-cache-q99999",
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
                        source_name="UniProt",
                        source_record_id="Q99999",
                        manifest_id="cache:embedding:q99999",
                        planning_id="protein:Q99999",
                        provenance_id="prov:embedding:q99999",
                    ),
                ),
                provenance_refs=("prov:embedding:q99999",),
                canonical_ids=("protein:Q99999",),
                join_status="joined",
                join_confidence=1.0,
                artifact_pointers=(
                    EmbeddingCacheArtifactPointer(
                        artifact_kind="embedding",
                        pointer="artifacts/embeddings/q99999.pt",
                        selector="embedding:0",
                        source_name="UniProt",
                        source_record_id="Q99999",
                        planning_id="protein:Q99999",
                    ),
                ),
            ),
        ),
    )


def _package_manifest() -> PackageManifest:
    return PackageManifest(
        package_id="package-rebuild-001",
        selected_examples=(
            PackageManifestExample(
                example_id="example-p12345",
                planning_index_ref="protein:P12345",
                source_record_refs=("raw/uniprot/p12345.json",),
                canonical_ids=("protein:P12345",),
                artifact_pointers=(
                    PackageManifestArtifactPointer(
                        artifact_kind="feature",
                        pointer="artifacts/features/p12345.npy",
                        selector="feature:0",
                        source_name="UniProt",
                        source_record_id="P12345",
                    ),
                    PackageManifestArtifactPointer(
                        artifact_kind="embedding",
                        pointer="artifacts/embeddings/p12345.pt",
                        selector="embedding:0",
                        source_name="UniProt",
                        source_record_id="P12345",
                    ),
                ),
            ),
            PackageManifestExample(
                example_id="example-q99999",
                planning_index_ref="protein:Q99999",
                source_record_refs=("raw/uniprot/q99999.json",),
                canonical_ids=("protein:Q99999",),
                artifact_pointers=(
                    PackageManifestArtifactPointer(
                        artifact_kind="feature",
                        pointer="artifacts/features/q99999.npy",
                        selector="feature:0",
                        source_name="UniProt",
                        source_record_id="Q99999",
                    ),
                    PackageManifestArtifactPointer(
                        artifact_kind="embedding",
                        pointer="artifacts/embeddings/q99999.pt",
                        selector="embedding:0",
                        source_name="UniProt",
                        source_record_id="Q99999",
                    ),
                ),
            ),
        ),
        raw_manifests=(
            PackageManifestRawManifest(
                source_name="UniProt",
                raw_manifest_id="UniProt:2026_02:download:raw",
                raw_manifest_ref="manifests/uniprot-2026_02.json",
                release_version="2026_02",
                retrieval_mode="download",
                source_locator="https://example.org/uniprot",
                planning_index_ref="protein:P12345",
            ),
        ),
        planning_index_refs=("protein:P12345", "protein:Q99999"),
    )


def test_planning_index_rebuild_is_deterministic_and_preserves_join_state() -> None:
    planning_index = _planning_index()
    rebuilt = PlanningIndexSchema.from_dict(planning_index.to_dict())

    assert rebuilt.to_dict() == planning_index.to_dict()
    assert [entry.planning_id for entry in rebuilt.records] == [
        "protein:P12345",
        "protein:Q99999",
    ]
    assert [entry.join_status for entry in rebuilt.records] == ["ambiguous", "joined"]


def test_storage_runtime_flags_missing_rebuilt_planning_entries() -> None:
    planning_index = _planning_index()
    rebuilt = PlanningIndexSchema.from_dict(planning_index.to_dict())
    stripped = PlanningIndexSchema(records=(rebuilt.get("protein:Q99999"),))

    runtime = integrate_storage_runtime(
        _package_manifest(),
        planning_index=stripped,
        canonical_store=_canonical_store(),
        feature_cache=_feature_cache(),
        embedding_cache=_embedding_cache(),
        available_artifacts={
            "artifacts/features/p12345.npy": "materialized/features/p12345.npy",
            "artifacts/embeddings/p12345.pt": "materialized/embeddings/p12345.pt",
            "artifacts/features/q99999.npy": "materialized/features/q99999.npy",
            "artifacts/embeddings/q99999.pt": "materialized/embeddings/q99999.pt",
        },
        materialization_run_id="run-rebuild-001",
        materialized_at="2026-03-22T13:00:00Z",
        package_version="v1",
        package_state="frozen",
        split_name="train",
        split_artifact_id="split:train:rebuild",
    )

    assert runtime.status == "partial"
    assert runtime.selective_materialization.status == "materialized"
    assert runtime.package_build.status == "built"
    assert any(issue.kind == "missing_planning_index_entry" for issue in runtime.issues)
    assert any(issue.example_id == "example-p12345" for issue in runtime.issues)
