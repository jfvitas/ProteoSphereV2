from __future__ import annotations

import json

import pytest

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
from execution.checkpoints.store import CheckpointRecord, CheckpointStore
from execution.storage_runtime import integrate_storage_runtime
from features.esm2_embeddings import ProteinEmbeddingResult
from models.multimodal.ligand_encoder import LigandEmbeddingResult
from models.multimodal.structure_encoder import StructureEmbeddingResult
from tests.unit.training.test_multimodal_train import (
    _build_ppi_representation,
    _build_storage_runtime,
)
from training.multimodal.runtime import (
    MultimodalFeatureBundle,
    MultimodalRuntimeCheckpoint,
    execute_multimodal_training,
)


def _build_two_example_storage_runtime(*, reordered: bool = False):
    raw_manifest = PackageManifestRawManifest(
        source_name="source-a",
        raw_manifest_id="raw-manifest-1",
        raw_manifest_ref="pinned://raw-manifest-1",
        release_version="2026.03",
        planning_index_ref="planning-1",
    )
    example_1 = PackageManifestExample(
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
    example_2 = PackageManifestExample(
        example_id="example-2",
        planning_index_ref="planning-2",
        source_record_refs=("ppi-summary-2",),
        canonical_ids=("protein:C", "protein:D"),
        artifact_pointers=(
            PackageManifestArtifactPointer(
                artifact_kind="feature",
                pointer="sequence-feature-2",
                source_name="sequence",
                selector="sequence",
            ),
            PackageManifestArtifactPointer(
                artifact_kind="embedding",
                pointer="structure-embedding-2",
                source_name="structure",
                selector="structure",
            ),
            PackageManifestArtifactPointer(
                artifact_kind="feature",
                pointer="ligand-feature-2",
                source_name="ligand",
                selector="ligand",
            ),
        ),
    )
    package_manifest = PackageManifest(
        package_id="package-2",
        selected_examples=(example_2, example_1) if reordered else (example_1, example_2),
        raw_manifests=(raw_manifest,),
        planning_index_refs=("planning-1", "planning-2"),
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
            PlanningIndexEntry(
                planning_id="planning-2",
                source_records=(
                    PlanningIndexSourceRecord(
                        source_name="source-a",
                        source_record_id="ppi-summary-2",
                        release_version="2026.03",
                        manifest_id="raw-manifest-1",
                    ),
                ),
                canonical_ids=("protein:C", "protein:D"),
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
                source_refs=(),
                planning_index_refs=("planning-1",),
                package_ids=("package-2",),
            ),
            CanonicalStoreRecord(
                canonical_id="protein:B",
                entity_kind="protein",
                canonical_payload={"protein_ref": "protein:B"},
                source_refs=(),
                planning_index_refs=("planning-1",),
                package_ids=("package-2",),
            ),
            CanonicalStoreRecord(
                canonical_id="protein:C",
                entity_kind="protein",
                canonical_payload={"protein_ref": "protein:C"},
                source_refs=(),
                planning_index_refs=("planning-2",),
                package_ids=("package-2",),
            ),
            CanonicalStoreRecord(
                canonical_id="protein:D",
                entity_kind="protein",
                canonical_payload={"protein_ref": "protein:D"},
                source_refs=(),
                planning_index_refs=("planning-2",),
                package_ids=("package-2",),
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
                cache_id="feature-sequence-2",
                feature_family="sequence",
                cache_version="v1",
                source_refs=(
                    FeatureCacheSourceRef(
                        source_name="sequence",
                        source_record_id="sequence-feature-2",
                        manifest_id="raw-manifest-1",
                        planning_id="planning-2",
                    ),
                ),
                canonical_ids=("protein:C",),
                join_status="joined",
                artifact_pointers=(
                    FeatureCacheArtifactPointer(
                        artifact_kind="summary",
                        pointer="sequence-feature-2",
                        source_name="sequence",
                        source_record_id="sequence-feature-2",
                        planning_id="planning-2",
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
            FeatureCacheEntry(
                cache_id="feature-ligand-2",
                feature_family="ligand",
                cache_version="v1",
                source_refs=(
                    FeatureCacheSourceRef(
                        source_name="ligand",
                        source_record_id="ligand-feature-2",
                        manifest_id="raw-manifest-1",
                        planning_id="planning-2",
                    ),
                ),
                canonical_ids=("protein:D",),
                join_status="joined",
                artifact_pointers=(
                    FeatureCacheArtifactPointer(
                        artifact_kind="summary",
                        pointer="ligand-feature-2",
                        source_name="ligand",
                        source_record_id="ligand-feature-2",
                        planning_id="planning-2",
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
                        provenance_id="structure-provenance-1",
                    ),
                ),
                canonical_ids=("protein:A",),
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
            EmbeddingCacheEntry(
                cache_id="embedding-structure-2",
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
                        source_record_id="structure-embedding-2",
                        manifest_id="raw-manifest-1",
                        planning_id="planning-2",
                        provenance_id="structure-provenance-2",
                    ),
                ),
                canonical_ids=("protein:C",),
                join_status="joined",
                artifact_pointers=(
                    EmbeddingCacheArtifactPointer(
                        artifact_kind="embedding",
                        pointer="structure-embedding-2",
                        source_name="structure",
                        source_record_id="structure-embedding-2",
                        planning_id="planning-2",
                    ),
                ),
            ),
        )
    )

    available_artifacts = {
        "sequence-feature-1": {
            "materialized_ref": "artifact://sequence-feature-1",
            "checksum": "sha256:sequence-1",
            "provenance_refs": ("sequence-source-1",),
            "notes": ("sequence note 1",),
        },
        "structure-embedding-1": {
            "materialized_ref": "artifact://structure-embedding-1",
            "checksum": "sha256:structure-1",
            "provenance_refs": ("structure-source-1",),
            "notes": ("structure note 1",),
        },
        "ligand-feature-1": {
            "materialized_ref": "artifact://ligand-feature-1",
            "checksum": "sha256:ligand-1",
            "provenance_refs": ("ligand-source-1",),
            "notes": ("ligand note 1",),
        },
        "sequence-feature-2": {
            "materialized_ref": "artifact://sequence-feature-2",
            "checksum": "sha256:sequence-2",
            "provenance_refs": ("sequence-source-2",),
            "notes": ("sequence note 2",),
        },
        "structure-embedding-2": {
            "materialized_ref": "artifact://structure-embedding-2",
            "checksum": "sha256:structure-2",
            "provenance_refs": ("structure-source-2",),
            "notes": ("structure note 2",),
        },
        "ligand-feature-2": {
            "materialized_ref": "artifact://ligand-feature-2",
            "checksum": "sha256:ligand-2",
            "provenance_refs": ("ligand-source-2",),
            "notes": ("ligand note 2",),
        },
    }

    return integrate_storage_runtime(
        package_manifest,
        planning_index=planning_index,
        canonical_store=canonical_store,
        feature_cache=feature_cache,
        embedding_cache=embedding_cache,
        available_artifacts=available_artifacts,
        materialization_run_id="materialization-run-2",
        materialized_at="2026-03-22T12:00:00Z",
        package_version="v1",
        split_name="train",
        split_artifact_id="split-2",
        published_at="2026-03-22T12:30:00Z",
        provenance_refs=("runtime-provenance",),
        notes=("runtime note",),
    )


def _build_real_feature_bundle(
    example_id: str,
    *,
    bundle_tag: str,
    bundle_source: str,
) -> MultimodalFeatureBundle:
    sequence_embedding = ProteinEmbeddingResult(
        sequence="ACDEFG",
        model_name="sequence-real-model",
        embedding_dim=8,
        residue_embeddings=(
            (0.10, 0.11, 0.12, 0.13, 0.14, 0.15, 0.16, 0.17),
            (0.20, 0.21, 0.22, 0.23, 0.24, 0.25, 0.26, 0.27),
        ),
        pooled_embedding=(0.15, 0.16, 0.17, 0.18, 0.19, 0.20, 0.21, 0.22),
        cls_embedding=None,
        source="sequence-real-input",
        frozen=True,
        provenance={
            "bundle_tag": bundle_tag,
            "bundle_source": bundle_source,
            "modality": "sequence",
        },
    )
    structure_embedding = StructureEmbeddingResult(
        pdb_id="1real",
        model_name="structure-real-model",
        embedding_dim=8,
        token_ids=("chain-A", "chain-B"),
        token_embeddings=(
            (0.30, 0.31, 0.32, 0.33, 0.34, 0.35, 0.36, 0.37),
            (0.40, 0.41, 0.42, 0.43, 0.44, 0.45, 0.46, 0.47),
        ),
        pooled_embedding=(0.35, 0.36, 0.37, 0.38, 0.39, 0.40, 0.41, 0.42),
        graph_kinds=("residue", "residue"),
        source="structure-real-input",
        frozen=True,
        provenance={
            "bundle_tag": bundle_tag,
            "bundle_source": bundle_source,
            "modality": "structure",
        },
    )
    ligand_embedding = LigandEmbeddingResult(
        canonical_id=f"ligand:{example_id}",
        ligand_id=f"{example_id}-ligand",
        name="Ligand Real",
        source="ligand-real-input",
        source_id=f"{example_id}-ligand-source",
        smiles="C1CCCCC1",
        inchi="InChI=1S/C6H12",
        inchikey="XDTMQSROBMDMFD-UHFFFAOYSA-N",
        formula="C6H12",
        charge=0,
        model_name="ligand-real-model",
        embedding_dim=8,
        token_ids=("atom-1", "atom-2"),
        token_embeddings=(
            (0.50, 0.51, 0.52, 0.53, 0.54, 0.55, 0.56, 0.57),
            (0.60, 0.61, 0.62, 0.63, 0.64, 0.65, 0.66, 0.67),
        ),
        pooled_embedding=(0.55, 0.56, 0.57, 0.58, 0.59, 0.60, 0.61, 0.62),
        source_kind="ligand_real_input",
        frozen=True,
        provenance={
            "bundle_tag": bundle_tag,
            "bundle_source": bundle_source,
            "modality": "ligand",
        },
    )
    return MultimodalFeatureBundle(
        example_id=example_id,
        sequence_embedding=sequence_embedding,
        structure_embedding=structure_embedding,
        ligand_embedding=ligand_embedding,
        provenance={
            "bundle_tag": bundle_tag,
            "bundle_source": bundle_source,
            "example_id": example_id,
        },
    )


def test_execute_multimodal_training_runs_fusion_and_writes_checkpoint(tmp_path):
    runtime = _build_storage_runtime()
    ppi_representation = _build_ppi_representation()
    feature_bundles = {
        "example-1": _build_real_feature_bundle(
            "example-1",
            bundle_tag="feature-bundle-1",
            bundle_source="unit-test",
        )
    }

    result = execute_multimodal_training(
        runtime,
        ppi_representation=ppi_representation,
        deterministic_seed=19,
        feature_bundles=feature_bundles,
        checkpoint_dir=tmp_path / "checkpoints",
        provenance=("runtime-provenance",),
        notes=("runtime note",),
    )

    assert result.plan.status.backend_ready is True
    assert result.plan.status.resolved_backend == "local-prototype-runtime"
    assert result.plan.status.blocker is None
    assert result.state.phase == "completed"
    assert result.state.processed_examples == 1
    assert result.checkpoint.processed_examples == 1
    assert result.checkpoint.completed_example_ids == ("example-1",)
    assert result.checkpoint.processable_example_ids == ("example-1",)
    assert result.checkpoint.feature_bundle_signature != "none"
    assert result.example_results[0].input_mode == "real-feature-bundle"
    assert result.example_results[0].feature_bundle_provenance["bundle_tag"] == (
        "feature-bundle-1"
    )
    assert result.example_results[0].fusion_result.available_modalities == (
        "sequence",
        "structure",
        "ligand",
    )
    assert result.example_results[0].fusion_result.provenance["modality_sources"] == {
        "sequence": "sequence-real-input",
        "structure": "structure-real-input",
        "ligand": "ligand-real-input",
    }

    checkpoint_path = tmp_path / "checkpoints" / f"{result.checkpoint.checkpoint_tag}.json"
    assert checkpoint_path.exists()

    payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    runtime_record = CheckpointRecord.from_dict(payload)
    assert runtime_record.run_id == result.checkpoint.run_id
    assert runtime_record.checkpoint_state["checkpoint_ref"] == result.checkpoint.checkpoint_ref
    assert runtime_record.metadata["checkpoint_tag"] == result.checkpoint.checkpoint_tag
    assert (
        runtime_record.metadata["feature_bundle_signature"]
        == result.checkpoint.feature_bundle_signature
    )
    assert runtime_record.checkpoint_state["processed_examples"] == 1
    assert runtime_record.provenance["objective"] == "modality-coverage-regression"

    store = CheckpointStore()
    stored_record = store.save(runtime_record)
    loaded_record = store.load_run_checkpoint(runtime_record.run_id)
    round_tripped_checkpoint = MultimodalRuntimeCheckpoint.from_checkpoint_record(loaded_record)
    assert stored_record == runtime_record
    assert loaded_record == runtime_record
    assert round_tripped_checkpoint == result.checkpoint


def test_execute_multimodal_training_resume_matches_full_run(tmp_path):
    runtime = _build_two_example_storage_runtime()
    ppi_representation = _build_ppi_representation()
    feature_bundles = {
        "example-1": _build_real_feature_bundle(
            "example-1",
            bundle_tag="feature-bundle-1",
            bundle_source="unit-test",
        ),
        "example-2": _build_real_feature_bundle(
            "example-2",
            bundle_tag="feature-bundle-2",
            bundle_source="unit-test",
        ),
    }
    checkpoint_path = tmp_path / "resume" / "trainer.json"

    partial = execute_multimodal_training(
        runtime,
        ppi_representation=ppi_representation,
        deterministic_seed=7,
        feature_bundles=feature_bundles,
        checkpoint_path=checkpoint_path,
        max_examples=1,
    )
    resumed = execute_multimodal_training(
        runtime,
        ppi_representation=ppi_representation,
        deterministic_seed=7,
        feature_bundles=feature_bundles,
        checkpoint_path=checkpoint_path,
        resume=True,
    )
    full = execute_multimodal_training(
        runtime,
        ppi_representation=ppi_representation,
        deterministic_seed=7,
        feature_bundles=feature_bundles,
        checkpoint_path=tmp_path / "full" / "trainer.json",
    )

    assert partial.state.phase == "paused"
    assert partial.checkpoint.completed_example_ids == ("example-1",)
    assert partial.checkpoint.processable_example_ids == ("example-1", "example-2")
    assert (
        partial.checkpoint.feature_bundle_signature
        == resumed.checkpoint.feature_bundle_signature
    )
    assert partial.example_results[0].input_mode == "real-feature-bundle"
    assert resumed.checkpoint.resumed_from == partial.checkpoint.checkpoint_ref
    assert resumed.state.processed_examples == full.state.processed_examples
    assert resumed.checkpoint.head_weights == full.checkpoint.head_weights
    assert resumed.checkpoint.loss_history == full.checkpoint.loss_history
    assert resumed.checkpoint.completed_example_ids == ("example-1", "example-2")
    assert resumed.example_results[0].input_mode == "real-feature-bundle"
    assert resumed.plan.status.backend_ready is True


def test_execute_multimodal_training_rejects_changed_feature_bundle_resume(tmp_path):
    runtime = _build_two_example_storage_runtime()
    ppi_representation = _build_ppi_representation()
    initial_feature_bundles = {
        "example-1": _build_real_feature_bundle(
            "example-1",
            bundle_tag="feature-bundle-1",
            bundle_source="unit-test",
        ),
        "example-2": _build_real_feature_bundle(
            "example-2",
            bundle_tag="feature-bundle-2",
            bundle_source="unit-test",
        ),
    }
    changed_feature_bundles = {
        "example-1": _build_real_feature_bundle(
            "example-1",
            bundle_tag="feature-bundle-1",
            bundle_source="unit-test",
        ),
        "example-2": _build_real_feature_bundle(
            "example-2",
            bundle_tag="feature-bundle-2-changed",
            bundle_source="unit-test",
        ),
    }
    checkpoint_path = tmp_path / "resume" / "trainer.json"

    execute_multimodal_training(
        runtime,
        ppi_representation=ppi_representation,
        deterministic_seed=7,
        feature_bundles=initial_feature_bundles,
        checkpoint_path=checkpoint_path,
        max_examples=1,
    )

    with pytest.raises(ValueError, match="run_id does not match"):
        execute_multimodal_training(
            runtime,
            ppi_representation=ppi_representation,
            deterministic_seed=7,
            feature_bundles=changed_feature_bundles,
            checkpoint_path=checkpoint_path,
            resume=True,
        )


def test_execute_multimodal_training_rejects_stale_checkpoint_identity(tmp_path):
    runtime = _build_two_example_storage_runtime()
    ppi_representation = _build_ppi_representation()
    feature_bundles = {
        "example-1": _build_real_feature_bundle(
            "example-1",
            bundle_tag="feature-bundle-1",
            bundle_source="unit-test",
        ),
        "example-2": _build_real_feature_bundle(
            "example-2",
            bundle_tag="feature-bundle-2",
            bundle_source="unit-test",
        ),
    }
    checkpoint_path = tmp_path / "resume" / "trainer.json"

    execute_multimodal_training(
        runtime,
        ppi_representation=ppi_representation,
        deterministic_seed=7,
        feature_bundles=feature_bundles,
        checkpoint_path=checkpoint_path,
        max_examples=1,
    )

    payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    payload["checkpoint_state"]["plan_signature"] = "stale-plan-signature"
    checkpoint_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    with pytest.raises(ValueError, match="plan signature"):
        execute_multimodal_training(
            runtime,
            ppi_representation=ppi_representation,
            deterministic_seed=7,
            feature_bundles=feature_bundles,
            checkpoint_path=checkpoint_path,
            resume=True,
        )


def test_execute_multimodal_training_rejects_reordered_resume_tail(tmp_path):
    runtime = _build_two_example_storage_runtime()
    reordered_runtime = _build_two_example_storage_runtime(reordered=True)
    ppi_representation = _build_ppi_representation()
    checkpoint_path = tmp_path / "resume" / "trainer.json"

    execute_multimodal_training(
        runtime,
        ppi_representation=ppi_representation,
        deterministic_seed=7,
        checkpoint_path=checkpoint_path,
        max_examples=1,
    )

    with pytest.raises(ValueError, match="plan signature does not match"):
        execute_multimodal_training(
            reordered_runtime,
            ppi_representation=ppi_representation,
            deterministic_seed=7,
            checkpoint_path=checkpoint_path,
            resume=True,
        )


def test_execute_multimodal_training_requires_supported_modalities(tmp_path):
    runtime = _build_storage_runtime()

    with pytest.raises(ValueError, match="fusion-supported"):
        execute_multimodal_training(
            runtime,
            requested_modalities=("ppi",),
            checkpoint_dir=tmp_path / "checkpoints",
        )
