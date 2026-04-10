from __future__ import annotations

import json
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
from models.multimodal.fusion_model import DEFAULT_FUSION_MODEL, FusionModel
from training.multimodal.train import prepare_multimodal_training, train_multimodal_model


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


def test_train_multimodal_model_executes_runtime_and_prepare_remains_blocked(
    tmp_path,
):
    runtime = _build_storage_runtime()
    ppi_representation = _build_ppi_representation()

    executable = train_multimodal_model(
        runtime,
        ppi_representation=ppi_representation,
        deterministic_seed=19,
        checkpoint_dir=tmp_path / "checkpoints",
        provenance=("training-provenance",),
        notes=("training note",),
    )
    blocked = prepare_multimodal_training(
        runtime,
        ppi_representation=ppi_representation,
        deterministic_seed=19,
        provenance=("training-provenance",),
        notes=("training note",),
    )

    assert executable.spec == blocked.spec
    assert executable.dataset == blocked.dataset
    assert executable.fusion_model == blocked.fusion_model
    assert executable.blocked_stages == ()
    assert isinstance(executable.fusion_model, FusionModel)
    assert executable.fusion_model.model_name == DEFAULT_FUSION_MODEL
    assert executable.fusion_model.modalities == ("sequence", "structure", "ligand")
    assert executable.dataset.status == "ready"
    assert executable.dataset.provenance_refs[0] == runtime.package_manifest.manifest_id
    assert "training-provenance" in executable.dataset.provenance_refs
    assert executable.dataset.examples[0].available_modalities == (
        "sequence",
        "structure",
        "ligand",
        "ppi",
    )
    assert executable.plan.observed_modalities == (
        "sequence",
        "structure",
        "ligand",
        "ppi",
    )
    assert executable.plan.missing_modalities == ()
    assert executable.plan.unsupported_requested_modalities == ("ppi",)
    assert executable.plan.status.backend_ready is True
    assert executable.plan.status.blocker is None
    assert executable.plan.status.resolved_backend == "local-prototype-runtime"
    assert executable.state.phase == "completed"
    assert executable.state.checkpoint_tag.startswith("package-package-1")
    assert executable.checkpoint.processed_examples == 1
    assert executable.checkpoint.completed_example_ids == ("example-1",)
    assert executable.checkpoint.feature_bundle_signature == "none"
    assert executable.example_results[0].input_mode == "surrogate-materialized-ref"

    payload = executable.to_dict()
    assert payload["spec"]["source_path"] == "training/multimodal/train.py"
    assert payload["dataset"]["example_count"] == 1
    assert payload["fusion_model"] == executable.fusion_model
    assert payload["plan"]["status"]["backend_ready"] is True
    assert payload["state"]["checkpoint_tag"] == executable.state.checkpoint_tag
    assert payload["checkpoint"]["processed_examples"] == 1
    assert payload["blockers"] == []
    checkpoint_path = tmp_path / "checkpoints" / f"{executable.checkpoint.checkpoint_tag}.json"
    assert checkpoint_path.exists()
    assert json.loads(checkpoint_path.read_text(encoding="utf-8"))["checkpoint_ref"] == (
        executable.checkpoint.checkpoint_ref
    )

    assert blocked.plan.status.backend_ready is False
    assert blocked.plan.status.blocker is not None
    assert "no real multimodal trainer runtime" in blocked.plan.status.blocker.reason.lower()
    assert blocked.state.phase == "blocked"


def test_prepare_multimodal_training_records_explicit_ppi_gap_when_no_representation_is_present():
    runtime = _build_storage_runtime()

    result = prepare_multimodal_training(runtime, deterministic_seed=7)

    assert result.dataset.status == "partial"
    assert result.dataset.examples[0].missing_modalities == ("ppi",)
    assert any(
        issue.kind == "missing_ppi_representation_record" for issue in result.dataset.issues
    )
    assert result.plan.missing_modalities == ("ppi",)
    assert result.plan.unsupported_requested_modalities == ("ppi",)
    assert result.plan.status.backend_ready is False
    assert result.plan.status.provenance["missing_modalities"] == ["ppi"]
    assert result.to_dict()["dataset"]["issues"][0]["kind"] == "missing_ppi_representation_record"
