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
from datasets.multimodal.adapter import build_multimodal_dataset
from execution.flagship_pipeline import run_flagship_pipeline
from execution.storage_runtime import integrate_storage_runtime
from features.esm2_embeddings import ProteinEmbeddingResult
from features.ppi_representation import build_ppi_representation
from models.multimodal.ligand_encoder import LigandEmbeddingResult
from models.multimodal.structure_encoder import StructureEmbeddingResult
from training.multimodal.train import prepare_multimodal_training


def test_multimodal_package_flow_preserves_selected_example_scope_and_completeness() -> None:
    runtime = _storage_runtime()
    ppi_representation = _ppi_representation()

    dataset = build_multimodal_dataset(
        runtime,
        ppi_representation=ppi_representation,
        provenance=("package-flow:unit-test",),
        notes=("selected-example scope",),
    )
    training = prepare_multimodal_training(
        runtime,
        ppi_representation=ppi_representation,
        deterministic_seed=19,
        provenance=("package-flow:unit-test",),
        notes=("selected-example scope",),
    )
    pipeline = run_flagship_pipeline(
        runtime,
        ppi_representation=ppi_representation,
        sequence_embedding=_sequence_embedding(),
        structure_embedding=_structure_embedding(),
        ligand_embedding=_ligand_embedding(),
        deterministic_seed=19,
        provenance=("package-flow:unit-test",),
        notes=("selected-example scope",),
        registry_id="multimodal-package-flow-registry:v1",
    )

    assert runtime.status == "integrated"
    assert runtime.selected_example_ids == ("example-1",)
    assert runtime.package_build.status == "built"
    assert runtime.package_build.package_manifest.selected_example_ids == ("example-1",)
    assert runtime.package_build.package_manifest.materialization is not None
    assert runtime.selective_materialization.status == "materialized"
    assert runtime.to_dict()["status"] == "integrated"

    assert dataset.package_id == "package-1"
    assert dataset.status == "ready"
    assert dataset.selected_example_ids == ("example-1",)
    assert dataset.examples[0].ppi_summary_ids == ("ppi-summary-1",)
    assert dataset.examples[0].pair_id == ppi_representation.records[0].pair_id
    assert dataset.examples[0].available_modalities == (
        "sequence",
        "structure",
        "ligand",
        "ppi",
    )
    assert not dataset.issues

    assert training.dataset.status == "ready"
    assert training.dataset.selected_example_ids == ("example-1",)
    assert training.plan.observed_modalities == (
        "sequence",
        "structure",
        "ligand",
        "ppi",
    )
    assert training.plan.missing_modalities == ()
    assert training.plan.unsupported_requested_modalities == ("ppi",)
    assert training.plan.status.blocker is not None
    assert training.plan.status.blocker.stage == "trainer_runtime"
    assert training.spec.source_path == "training/multimodal/train.py"
    assert json.dumps(training.to_dict())

    assert pipeline.status == "partial"
    assert pipeline.storage_runtime_status == "integrated"
    assert pipeline.training.dataset.status == "ready"
    assert pipeline.fusion_result.is_complete is True
    assert pipeline.uncertainty_result.coverage == pytest.approx(1.0)
    assert pipeline.metrics.example_count == 1
    assert pipeline.experiment_registry.record_count == 1
    assert pipeline.experiment_registry.records[0].package_manifest_id == (
        runtime.package_build.package_manifest.manifest_id
    )
    assert json.dumps(pipeline.to_dict())


def test_multimodal_package_flow_surfaces_missing_ppi_input_explicitly() -> None:
    runtime = _storage_runtime()

    dataset = build_multimodal_dataset(runtime, ppi_representation=None)
    training = prepare_multimodal_training(runtime, ppi_representation=None, deterministic_seed=7)
    pipeline = run_flagship_pipeline(
        runtime,
        ppi_representation=None,
        sequence_embedding=_sequence_embedding(),
        structure_embedding=_structure_embedding(),
        ligand_embedding=_ligand_embedding(),
        deterministic_seed=7,
        registry_id="multimodal-package-flow-registry:v1",
    )

    assert dataset.status == "partial"
    assert dataset.selected_example_ids == ("example-1",)
    assert dataset.examples[0].available_modalities == ("sequence", "structure", "ligand")
    assert dataset.examples[0].missing_modalities == ("ppi",)
    assert any(
        issue.kind == "missing_ppi_representation_record" for issue in dataset.issues
    )
    assert any(
        issue.kind == "missing_requested_modality" and issue.modality == "ppi"
        for issue in dataset.issues
    )

    assert training.dataset.status == "partial"
    assert training.plan.missing_modalities == ("ppi",)
    assert training.plan.status.blocker is not None
    assert training.plan.status.blocker.stage == "trainer_runtime"

    assert pipeline.status == "partial"
    assert pipeline.training.dataset.status == "partial"
    assert any(
        "ppi lane may be partial" in limitation.lower() for limitation in pipeline.limitations
    )
    assert any("trainer runtime" in limitation.lower() for limitation in pipeline.limitations)
    assert json.dumps(dataset.to_dict())
    assert json.dumps(training.to_dict())
    assert json.dumps(pipeline.to_dict())


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
        canonical_ids=("protein:P69905", "protein:P68871"),
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
        notes=("selected-example scope",),
    )
    package_manifest = PackageManifest(
        package_id="package-1",
        selected_examples=(selected_example,),
        raw_manifests=(raw_manifest,),
        planning_index_refs=("planning-1",),
        provenance=("package-provenance",),
        notes=("multimodal package validation",),
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
                canonical_ids=("protein:P69905", "protein:P68871"),
                join_status="joined",
            ),
        )
    )

    canonical_store = CanonicalStore(
        records=(
            CanonicalStoreRecord(
                canonical_id="protein:P69905",
                entity_kind="protein",
                canonical_payload={"protein_ref": "protein:P69905"},
                source_refs=(
                    CanonicalStoreSourceRef(
                        source_name="UniProt",
                        source_record_id="P69905",
                        source_manifest_id="raw-manifest-1",
                        planning_index_ref="planning-1",
                        package_id="package-1",
                    ),
                ),
                planning_index_refs=("planning-1",),
                package_ids=("package-1",),
            ),
            CanonicalStoreRecord(
                canonical_id="protein:P68871",
                entity_kind="protein",
                canonical_payload={"protein_ref": "protein:P68871"},
                source_refs=(
                    CanonicalStoreSourceRef(
                        source_name="UniProt",
                        source_record_id="P68871",
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
                canonical_ids=("protein:P69905",),
                join_status="joined",
                join_confidence=1.0,
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
                canonical_ids=("protein:P68871",),
                join_status="joined",
                join_confidence=1.0,
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
                canonical_ids=("protein:P69905", "protein:P68871"),
                join_status="joined",
                join_confidence=1.0,
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
        split_artifact_id="split:train:001",
        published_at=datetime(2026, 3, 22, 12, 30, tzinfo=UTC),
        provenance_refs=("runtime-provenance",),
        notes=("runtime note",),
    )


def _ppi_representation():
    ppi_record = ProteinProteinSummaryRecord(
        summary_id="ppi-summary-1",
        protein_a_ref="protein:P69905",
        protein_b_ref="protein:P68871",
        interaction_type="binding",
        interaction_id="intact:EBI-12345678",
        interaction_refs=("IM-12345",),
        evidence_refs=("evidence-1",),
        organism_name="Homo sapiens",
        taxon_id=9606,
        physical_interaction=True,
        join_status="joined",
        context=SummaryRecordContext(
            provenance_pointers=(
                SummaryProvenancePointer(
                    provenance_id="prov:ppi-1",
                    source_name="IntAct",
                    source_record_id="ppi-summary-1",
                ),
            ),
            storage_notes=("live-source-shaped selected-example package",),
            lazy_loading_guidance=("hydrate only after the example is selected",),
            storage_tier="feature_cache",
        ),
        notes=("selected-example ppi",),
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
