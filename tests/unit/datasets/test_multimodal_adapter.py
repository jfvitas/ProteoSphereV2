from __future__ import annotations

from datetime import UTC, datetime

from core.library.summary_record import (
    ProteinProteinSummaryRecord,
    SummaryProvenancePointer,
    SummaryRecordContext,
)
from core.storage.canonical_store import (
    CanonicalStore,
    CanonicalStoreRecord,
    CanonicalStoreSourceRef,
)
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
from datasets.multimodal.adapter import (
    MultimodalDatasetAdapter,
    build_multimodal_dataset,
    validate_multimodal_dataset_payload,
)
from execution.storage_runtime import integrate_storage_runtime
from features.ppi_representation import build_ppi_representation


def _build_storage_runtime():
    raw_manifest = PackageManifestRawManifest(
        source_name="source-a",
        raw_manifest_id="raw-manifest-1",
        raw_manifest_ref="pinned://raw-manifest-1",
        release_version="2026.03",
        planning_index_ref="planning-1",
    )
    selected_example = PackageManifestExample(
        example_id="example-1",
        planning_index_ref="planning-1",
        source_record_refs=("ppi-summary-1",),
        canonical_ids=("protein:A", "protein:B"),
        artifact_pointers=(
            PackageManifestArtifactPointer(
                artifact_kind="feature",
                pointer="sequence-feature-1",
                source_name="sequence",
                selector="sequence",
            ),
            PackageManifestArtifactPointer(
                artifact_kind="embedding",
                pointer="structure-embedding-1",
                source_name="structure",
                selector="structure",
            ),
            PackageManifestArtifactPointer(
                artifact_kind="feature",
                pointer="ligand-feature-1",
                source_name="ligand",
                selector="ligand",
            ),
        ),
    )
    package_manifest = PackageManifest(
        package_id="package-1",
        selected_examples=(selected_example,),
        raw_manifests=(raw_manifest,),
        planning_index_refs=("planning-1",),
        provenance=("package-provenance",),
    )

    planning_index = PlanningIndexSchema(
        records=(
            PlanningIndexEntry(
                planning_id="planning-1",
                source_records=(
                    PlanningIndexSourceRecord(
                        source_name="source-a",
                        source_record_id="ppi-summary-1",
                        release_version="2026.03",
                        manifest_id="raw-manifest-1",
                    ),
                ),
                canonical_ids=("protein:A", "protein:B"),
                join_status="joined",
            ),
        )
    )

    canonical_store = CanonicalStore(
        records=(
            CanonicalStoreRecord(
                canonical_id="protein:A",
                entity_kind="protein",
                canonical_payload={"protein_ref": "protein:A"},
                source_refs=(
                    CanonicalStoreSourceRef(
                        source_name="source-a",
                        source_record_id="protein:A",
                        source_manifest_id="raw-manifest-1",
                        planning_index_ref="planning-1",
                        package_id="package-1",
                    ),
                ),
                planning_index_refs=("planning-1",),
                package_ids=("package-1",),
            ),
            CanonicalStoreRecord(
                canonical_id="protein:B",
                entity_kind="protein",
                canonical_payload={"protein_ref": "protein:B"},
                source_refs=(
                    CanonicalStoreSourceRef(
                        source_name="source-a",
                        source_record_id="protein:B",
                        source_manifest_id="raw-manifest-1",
                        planning_index_ref="planning-1",
                        package_id="package-1",
                    ),
                ),
                planning_index_refs=("planning-1",),
                package_ids=("package-1",),
            ),
        )
    )

    feature_cache = FeatureCacheCatalog(
        records=(
            FeatureCacheEntry(
                cache_id="feature-sequence-1",
                feature_family="sequence",
                cache_version="v1",
                source_refs=(
                    FeatureCacheSourceRef(
                        source_name="sequence",
                        source_record_id="sequence-feature-1",
                        manifest_id="raw-manifest-1",
                        planning_id="planning-1",
                    ),
                ),
                canonical_ids=("protein:A",),
                join_status="joined",
                artifact_pointers=(
                    FeatureCacheArtifactPointer(
                        artifact_kind="summary",
                        pointer="sequence-feature-1",
                        source_name="sequence",
                        source_record_id="sequence-feature-1",
                        planning_id="planning-1",
                    ),
                ),
            ),
            FeatureCacheEntry(
                cache_id="feature-ligand-1",
                feature_family="ligand",
                cache_version="v1",
                source_refs=(
                    FeatureCacheSourceRef(
                        source_name="ligand",
                        source_record_id="ligand-feature-1",
                        manifest_id="raw-manifest-1",
                        planning_id="planning-1",
                    ),
                ),
                canonical_ids=("protein:B",),
                join_status="joined",
                artifact_pointers=(
                    FeatureCacheArtifactPointer(
                        artifact_kind="summary",
                        pointer="ligand-feature-1",
                        source_name="ligand",
                        source_record_id="ligand-feature-1",
                        planning_id="planning-1",
                    ),
                ),
            ),
        )
    )

    embedding_cache = EmbeddingCacheCatalog(
        records=(
            EmbeddingCacheEntry(
                cache_id="embedding-structure-1",
                cache_family="structure",
                cache_version="v1",
                model_identity=EmbeddingModelIdentity(
                    model_name="structure-model",
                    model_version="1",
                ),
                runtime_identity=EmbeddingRuntimeIdentity(
                    runtime_name="structure-runtime",
                    runtime_version="1",
                ),
                source_refs=(
                    EmbeddingCacheSourceRef(
                        source_name="structure",
                        source_record_id="structure-embedding-1",
                        manifest_id="raw-manifest-1",
                        planning_id="planning-1",
                        provenance_id="structure-provenance",
                    ),
                ),
                canonical_ids=("protein:A", "protein:B"),
                join_status="joined",
                artifact_pointers=(
                    EmbeddingCacheArtifactPointer(
                        artifact_kind="embedding",
                        pointer="structure-embedding-1",
                        source_name="structure",
                        source_record_id="structure-embedding-1",
                        planning_id="planning-1",
                    ),
                ),
            ),
        )
    )

    available_artifacts = {
        "sequence-feature-1": {
            "materialized_ref": "artifact://sequence-feature-1",
            "checksum": "sha256:sequence",
            "provenance_refs": ("sequence-source",),
            "notes": ("sequence note",),
        },
        "structure-embedding-1": {
            "materialized_ref": "artifact://structure-embedding-1",
            "checksum": "sha256:structure",
            "provenance_refs": ("structure-source",),
            "notes": ("structure note",),
        },
        "ligand-feature-1": {
            "materialized_ref": "artifact://ligand-feature-1",
            "checksum": "sha256:ligand",
            "provenance_refs": ("ligand-source",),
            "notes": ("ligand note",),
        },
    }

    return integrate_storage_runtime(
        package_manifest,
        planning_index=planning_index,
        canonical_store=canonical_store,
        feature_cache=feature_cache,
        embedding_cache=embedding_cache,
        available_artifacts=available_artifacts,
        materialization_run_id="materialization-run-1",
        materialized_at=datetime(2026, 3, 22, 12, 0, tzinfo=UTC),
        package_version="v1",
        split_name="train",
        split_artifact_id="split-1",
        published_at=datetime(2026, 3, 22, 12, 30, tzinfo=UTC),
        provenance_refs=("runtime-provenance",),
        notes=("runtime note",),
    )


def _build_ppi_representation():
    ppi_records = (
        ProteinProteinSummaryRecord(
            summary_id="ppi-summary-1",
            protein_a_ref="protein:A",
            protein_b_ref="protein:B",
            interaction_type="binding",
            context=SummaryRecordContext(
                provenance_pointers=(
                    SummaryProvenancePointer(
                        provenance_id="prov-ppi-1",
                        source_name="source-a",
                        source_record_id="ppi-summary-1",
                    ),
                ),
            ),
        ),
        ProteinProteinSummaryRecord(
            summary_id="ppi-summary-2",
            protein_a_ref="protein:C",
            protein_b_ref="protein:D",
            interaction_type="binding",
            context=SummaryRecordContext(
                provenance_pointers=(
                    SummaryProvenancePointer(
                        provenance_id="prov-ppi-2",
                        source_name="source-a",
                        source_record_id="ppi-summary-2",
                    ),
                ),
            ),
        ),
    )
    return build_ppi_representation(
        ppi_records,
        representation_id="ppi-representation-1",
        library_id="ppi-library-1",
        source_manifest_id="raw-manifest-1",
        provenance=("ppi-provenance",),
    )


def test_multimodal_dataset_adapter_preserves_selected_example_lineage_and_modality_refs():
    runtime = _build_storage_runtime()
    ppi_representation = _build_ppi_representation()

    adapter = MultimodalDatasetAdapter()
    dataset = adapter.adapt(
        runtime,
        ppi_representation=ppi_representation,
        provenance=("adapter-provenance",),
        notes=("adapter note",),
    )

    assert dataset.package_id == "package-1"
    assert dataset.package_manifest_id == runtime.package_manifest.manifest_id
    assert dataset.selected_example_ids == ("example-1",)
    assert dataset.status == "ready"
    assert dataset.requested_modalities == ("sequence", "structure", "ligand", "ppi")

    example = dataset.examples[0]
    assert example.selected_example.example_id == "example-1"
    assert example.available_modalities == ("sequence", "structure", "ligand", "ppi")
    assert example.missing_modalities == ()
    assert example.modality_refs["sequence"] == ("artifact://sequence-feature-1",)
    assert example.modality_refs["structure"] == ("artifact://structure-embedding-1",)
    assert example.modality_refs["ligand"] == ("artifact://ligand-feature-1",)
    assert example.ppi_summary_ids == ("ppi-summary-1",)
    assert example.pair_id == ppi_representation.records[0].pair_id
    assert len(ppi_representation.records) == 2

    assert runtime.package_manifest.manifest_id in dataset.provenance_refs
    assert "raw-manifest-1" in dataset.provenance_refs
    assert "adapter-provenance" in dataset.provenance_refs

    round_trip = validate_multimodal_dataset_payload(dataset.to_dict())
    assert round_trip.selected_example_ids == dataset.selected_example_ids
    assert round_trip.examples[0].available_modalities == example.available_modalities
    assert round_trip.examples[0].ppi_summary_ids == example.ppi_summary_ids


def test_multimodal_dataset_adapter_reports_missing_ppi_input_explicitly():
    runtime = _build_storage_runtime()

    dataset = build_multimodal_dataset(runtime, ppi_representation=None)

    assert dataset.status == "partial"
    assert dataset.selected_example_ids == ("example-1",)

    example = dataset.examples[0]
    assert example.available_modalities == ("sequence", "structure", "ligand")
    assert "ppi" in example.missing_modalities
    assert any(issue.kind == "missing_ppi_representation_record" for issue in dataset.issues)
    assert any(
        issue.kind == "missing_requested_modality" and issue.modality == "ppi"
        for issue in dataset.issues
    )
