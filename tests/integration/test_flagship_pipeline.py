from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

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
from execution.flagship_pipeline import run_flagship_pipeline
from execution.storage_runtime import integrate_storage_runtime
from features.esm2_embeddings import ProteinEmbeddingResult
from features.ppi_representation import build_ppi_representation
from models.multimodal.ligand_encoder import LigandEmbeddingResult
from models.multimodal.structure_encoder import StructureEmbeddingResult
from training.multimodal.runtime import MultimodalFeatureBundle, execute_multimodal_training


def test_flagship_pipeline_runs_end_to_end_and_serializes_cleanly() -> None:
    result = run_flagship_pipeline(
        _storage_runtime(),
        ppi_representation=_ppi_representation(),
        sequence_embedding=_sequence_embedding(),
        structure_embedding=_structure_embedding(),
        ligand_embedding=_ligand_embedding(),
        provenance=("pipeline-provenance",),
        notes=("pipeline note",),
    )

    assert result.pipeline_id == "P5-I012"
    assert result.status == "partial"
    assert result.storage_runtime_status == "integrated"
    assert result.training.dataset.status == "ready"
    assert result.training.plan.status.blocker is not None
    assert result.training.plan.status.blocker.stage == "trainer_runtime"
    assert result.gpu_decision.allowed is True
    assert result.gpu_decision.assignment == "gpu"
    assert result.fusion_result.is_complete is True
    assert result.uncertainty_result.coverage == pytest.approx(1.0)
    assert result.metrics.example_count == 1
    assert result.metrics.complete_rate == pytest.approx(1.0)
    assert result.experiment_registry.record_count == 1
    assert result.experiment_registry.records[0].backend_ready is True
    assert (
        result.experiment_registry.records[0].contract_fidelity
        == "fusion-forward-plus-checkpointed-prototype"
    )
    assert result.experiment_registry.records[0].runtime_status["resolved_backend"] == (
        "local-prototype-runtime"
    )
    assert result.training.plan.status.provenance["runtime_resolved_backend"] == (
        "local-prototype-runtime"
    )
    assert result.training.plan.status.provenance["runtime_checkpoint_ref"].startswith(
        "checkpoint://"
    )
    assert (
        result.experiment_registry.records[0].checkpoint_tag
        == result.training.state.checkpoint_tag
    )
    assert result.blockers[0].stage == "trainer_runtime"
    assert "no real multimodal trainer runtime" in result.limitations[0].lower()

    payload = result.to_dict()
    assert json.dumps(payload)
    assert payload["pipeline_id"] == "P5-I012"
    assert payload["status"] == "partial"
    assert payload["training"]["dataset"]["status"] == "ready"
    assert payload["gpu_decision"]["allowed"] is True
    assert payload["fusion_result"]["available_modalities"] == [
        "sequence",
        "structure",
        "ligand",
    ]
    assert payload["metrics"]["example_count"] == 1
    assert payload["experiment_registry"]["record_count"] == 1
    assert payload["experiment_registry"]["records"][0]["runtime_status"]["backend_ready"] is True
    assert (
        payload["training"]["plan"]["status"]["provenance"]["runtime_checkpoint_ref"].startswith(
            "checkpoint://"
        )
    )


def test_flagship_pipeline_surfaces_partial_ppi_inputs_explicitly() -> None:
    result = run_flagship_pipeline(
        _storage_runtime(),
        ppi_representation=None,
        sequence_embedding=_sequence_embedding(),
        structure_embedding=_structure_embedding(),
        ligand_embedding=_ligand_embedding(),
        provenance=("pipeline-provenance",),
        notes=("pipeline note",),
    )

    assert result.status == "partial"
    assert result.training.dataset.status == "partial"
    assert result.training.plan.missing_modalities == ("ppi",)
    assert any("ppi lane may be partial" in item.lower() for item in result.limitations)
    assert result.fusion_result.is_complete is True
    assert result.experiment_registry.record_count == 1

    payload = result.to_dict()
    assert json.dumps(payload)
    assert payload["training"]["dataset"]["status"] == "partial"
    assert payload["training"]["plan"]["missing_modalities"] == ["ppi"]


def test_flagship_runtime_resume_is_identity_safe_and_fail_closed(tmp_path) -> None:
    runtime = _storage_runtime()
    ppi_representation = _ppi_representation()
    feature_bundles = {
        "example-1": MultimodalFeatureBundle(
            example_id="example-1",
            sequence_embedding=_sequence_embedding(),
            structure_embedding=_structure_embedding(),
            ligand_embedding=_ligand_embedding(),
            provenance={"bundle": "example-1"},
        )
    }
    checkpoint_dir = tmp_path / "checkpoints"

    first = execute_multimodal_training(
        runtime,
        ppi_representation=ppi_representation,
        feature_bundles=feature_bundles,
        checkpoint_dir=checkpoint_dir,
        deterministic_seed=19,
        provenance=("pipeline-provenance",),
        notes=("pipeline note",),
    )
    resumed = execute_multimodal_training(
        runtime,
        ppi_representation=ppi_representation,
        feature_bundles=feature_bundles,
        checkpoint_dir=checkpoint_dir,
        resume=True,
        deterministic_seed=19,
        provenance=("pipeline-provenance",),
        notes=("pipeline note",),
    )

    assert first.plan.status.backend_ready is True
    assert first.plan.status.blocker is None
    assert first.checkpoint.resumed_from is None
    assert resumed.checkpoint.resumed_from == first.checkpoint.checkpoint_ref
    assert resumed.checkpoint.processed_examples == first.checkpoint.processed_examples
    assert resumed.checkpoint.processable_example_ids == first.checkpoint.processable_example_ids
    assert resumed.checkpoint.dataset_signature == first.checkpoint.dataset_signature
    assert resumed.checkpoint.feature_bundle_signature == first.checkpoint.feature_bundle_signature
    assert resumed.plan.status.provenance["resumed_from"] == first.checkpoint.checkpoint_ref
    assert resumed.plan.status.provenance["feature_bundle_signature"] == (
        first.checkpoint.feature_bundle_signature
    )

    mismatched_feature_bundles = {
        "example-1": MultimodalFeatureBundle(
            example_id="example-1",
            sequence_embedding=_sequence_embedding(),
            structure_embedding=_structure_embedding(),
            ligand_embedding=_ligand_embedding(),
            provenance={"bundle": "example-1", "variant": "mismatched"},
        )
    }

    with pytest.raises(ValueError, match="run_id does not match"):
        execute_multimodal_training(
            runtime,
            ppi_representation=ppi_representation,
            feature_bundles=mismatched_feature_bundles,
            checkpoint_dir=checkpoint_dir,
            resume=True,
            deterministic_seed=19,
            provenance=("pipeline-provenance",),
            notes=("pipeline note",),
        )


def _storage_runtime():
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
        },
        "structure-embedding-1": {
            "materialized_ref": "artifact://structure-embedding-1",
            "checksum": "sha256:structure",
            "provenance_refs": ("structure-source",),
        },
        "ligand-feature-1": {
            "materialized_ref": "artifact://ligand-feature-1",
            "checksum": "sha256:ligand",
            "provenance_refs": ("ligand-source",),
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


def _ppi_representation():
    ppi_record = ProteinProteinSummaryRecord(
        summary_id="ppi-summary-1",
        protein_a_ref="protein:A",
        protein_b_ref="protein:B",
        interaction_type="binding",
        interaction_id="interaction-1",
        interaction_refs=("interaction-1",),
        evidence_refs=("evidence-1",),
        organism_name="Homo sapiens",
        taxon_id=9606,
        physical_interaction=True,
        join_status="joined",
        context=SummaryRecordContext(
            provenance_pointers=(
                SummaryProvenancePointer(
                    provenance_id="prov-ppi-1",
                    source_name="source-a",
                    source_record_id="ppi-summary-1",
                ),
            ),
        ),
    )
    return build_ppi_representation(
        (ppi_record,),
        representation_id="ppi-representation-1",
        library_id="ppi-library-1",
        source_manifest_id="raw-manifest-1",
        provenance=("ppi-provenance",),
    )


def _sequence_embedding() -> ProteinEmbeddingResult:
    return ProteinEmbeddingResult(
        sequence="ACD",
        model_name="sequence-test",
        embedding_dim=3,
        residue_embeddings=(
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
        ),
        pooled_embedding=(1.0, 0.0, 0.0),
        cls_embedding=(0.0, 0.0, 0.0),
        provenance={"backend": "sequence-test"},
    )


def _structure_embedding() -> StructureEmbeddingResult:
    return StructureEmbeddingResult(
        pdb_id="1ABC",
        model_name="structure-test",
        embedding_dim=3,
        token_ids=("atom", "residue"),
        token_embeddings=((0.0, 1.0, 1.0), (1.0, 0.0, 1.0)),
        pooled_embedding=(0.0, 1.0, 0.0),
        graph_kinds=("atom", "residue"),
        source="graph-summary",
        frozen=True,
        provenance={"backend": "structure-test"},
    )


def _ligand_embedding() -> LigandEmbeddingResult:
    return LigandEmbeddingResult(
        canonical_id="ligand:test",
        ligand_id="L1",
        name="Test ligand",
        source="ligand-test",
        source_id="L1",
        smiles="CCO",
        inchi=None,
        inchikey=None,
        formula="C2H6O",
        charge=0,
        model_name="ligand-test",
        embedding_dim=3,
        token_ids=("smiles",),
        token_embeddings=((0.5, 0.25, 0.75),),
        pooled_embedding=(0.0, 0.0, 1.0),
        source_kind="ligand_baseline",
        frozen=True,
        provenance={"backend": "ligand-test"},
    )
