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
from execution.storage_runtime import integrate_storage_runtime
from features.ppi_representation import build_ppi_representation
from training.multimodal.train import prepare_multimodal_training, train_multimodal_model
from training.runtime.experiment_registry import (
    DEFAULT_EXPERIMENT_REGISTRY_ID,
    DEFAULT_TRAINING_ENTRYPOINT,
    build_experiment_registry,
    register_experiment,
)


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


def test_build_experiment_registry_materializes_a_deterministic_record():
    runtime = _build_storage_runtime()
    ppi_representation = _build_ppi_representation()
    training_result = train_multimodal_model(
        runtime,
        ppi_representation=ppi_representation,
        deterministic_seed=7,
        provenance=("training-provenance",),
        notes=("training note",),
    )

    first = build_experiment_registry(
        runtime,
        ppi_representation=ppi_representation,
        deterministic_seed=7,
        training_result=training_result,
        provenance=("registry-provenance",),
        notes=("registry note",),
    )
    second = register_experiment(
        runtime,
        ppi_representation=ppi_representation,
        deterministic_seed=7,
        training_result=training_result,
        provenance=("registry-provenance",),
        notes=("registry note",),
    )

    assert first == second
    assert first.registry_id == DEFAULT_EXPERIMENT_REGISTRY_ID
    assert first.record_count == 1
    assert first.source_path == "training/runtime/experiment_registry.py"
    assert first.registry_signature == second.registry_signature

    record = first.records[0]
    assert record.training_entrypoint == DEFAULT_TRAINING_ENTRYPOINT
    assert record.model_name == "multimodal-fusion-baseline-v1"
    assert record.fusion_dim == 8
    assert record.requested_modalities == ("sequence", "structure", "ligand", "ppi")
    assert record.fusion_modalities == ("sequence", "structure", "ligand")
    assert record.observed_modalities == ("sequence", "structure", "ligand", "ppi")
    assert record.missing_modalities == ()
    assert record.checkpoint_ref == f"checkpoint://{record.checkpoint_tag}"
    assert record.backend_ready is True
    assert record.runtime_status["backend_ready"] is True
    assert record.runtime_status["resolved_backend"] == "local-prototype-runtime"
    assert record.contract_fidelity == "fusion-forward-plus-checkpointed-prototype"
    assert record.blocker is None
    assert "package-provenance" in record.provenance_refs
    assert "ppi-provenance" in record.provenance_refs
    assert "registry-provenance" in first.provenance_refs
    assert "runtime-provenance" in first.provenance_refs
    assert record.runtime_status["provenance"]["processed_examples"] == 1
    assert (
        record.runtime_status["provenance"]["input_mode_counts"][
            "surrogate_materialized_ref"
        ]
        == 1
    )

    payload = first.to_dict()
    assert payload["registry_id"] == DEFAULT_EXPERIMENT_REGISTRY_ID
    assert payload["record_count"] == 1
    assert payload["records"][0]["checkpoint_ref"] == record.checkpoint_ref
    assert payload["records"][0]["training_entrypoint"] == DEFAULT_TRAINING_ENTRYPOINT
    assert payload["records"][0]["runtime_status"]["resolved_backend"] == "local-prototype-runtime"
    assert payload["records"][0]["blocker"] is None


def test_build_experiment_registry_keeps_ppi_gap_explicit_without_a_representation():
    runtime = _build_storage_runtime()

    blocked_result = prepare_multimodal_training(runtime, deterministic_seed=3)
    registry = build_experiment_registry(
        runtime,
        deterministic_seed=3,
        training_result=blocked_result,
    )

    record = registry.records[0]
    assert record.missing_modalities == ("ppi",)
    assert record.observed_modalities == ("sequence", "structure", "ligand")
    assert record.backend_ready is False
    assert record.blocker is not None
    assert registry.records[0].provenance_refs
    assert registry.to_dict()["records"][0]["missing_modalities"] == ["ppi"]
    assert registry.to_dict()["records"][0]["runtime_status"]["backend_ready"] is False


def test_build_experiment_registry_preserves_blocked_planner_runtime_metadata():
    runtime = _build_storage_runtime()
    ppi_representation = _build_ppi_representation()
    blocked_result = prepare_multimodal_training(
        runtime,
        ppi_representation=ppi_representation,
        deterministic_seed=11,
        provenance=("training-provenance",),
        notes=("training note",),
    )

    registry = build_experiment_registry(
        runtime,
        ppi_representation=ppi_representation,
        deterministic_seed=11,
        training_result=blocked_result,
        provenance=("registry-provenance",),
        notes=("registry note",),
    )

    record = registry.records[0]
    assert record.backend_ready is False
    assert record.contract_fidelity == "dataset-and-fusion-plan-only"
    assert record.blocker is not None
    assert record.runtime_status["backend_ready"] is False
    assert record.runtime_status["blocker"]["stage"] == "trainer_runtime"
    assert record.runtime_status["blocker"]["requested_backend"].endswith(
        "+multimodal-dataset-adapter"
    )
    assert record.runtime_status["blocker"]["reason"].lower().startswith(
        "the repository can materialize the multimodal dataset"
    )
