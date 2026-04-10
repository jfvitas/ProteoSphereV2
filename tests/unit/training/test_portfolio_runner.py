from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

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
from training.runtime.experiment_registry import DEFAULT_EXPERIMENT_REGISTRY_ID
from training.runtime.portfolio_runner import (
    DEFAULT_PORTFOLIO_MATRIX_ID,
    DEFAULT_PORTFOLIO_RUNNER_ID,
    PortfolioAblationSpec,
    PortfolioCandidateSpec,
    expand_portfolio_matrix,
    run_portfolio_matrix,
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


def test_expand_portfolio_matrix_normalizes_candidates_and_ablations():
    slices = expand_portfolio_matrix(
        [
            {
                "candidate_id": "alpha",
                "rank": 2,
                "model_name": "multimodal-fusion-baseline-v1",
                "requested_modalities": (
                    "sequence",
                    "structure",
                    "ligand",
                    "sequence",
                ),
                "fusion_dim": "8",
                "notes": ("alpha note",),
                "tags": ("portfolio",),
            },
            PortfolioCandidateSpec(
                candidate_id="beta",
                rank=5,
                model_name="multimodal-fusion-baseline-v1",
                requested_modalities=("sequence", "ligand"),
                fusion_dim=6,
                notes=("beta note",),
                tags=("portfolio",),
            ),
        ],
        ablations=(
            {
                "ablation_id": "drop-ligand",
                "rank_offset": 7,
                "drop_modalities": ("ligand",),
                "notes": ("drop ligand",),
            },
            PortfolioAblationSpec(
                ablation_id="sequence-only",
                rank_offset=10,
                keep_only_modalities=("sequence",),
                notes=("keep sequence",),
                tags=("ablation",),
            ),
        ),
    )

    assert [item.slice_id for item in slices] == [
        "alpha:base",
        "alpha:drop-ligand",
        "alpha:sequence-only",
        "beta:base",
        "beta:drop-ligand",
        "beta:sequence-only",
    ]
    assert slices[0].requested_modalities == ("sequence", "structure", "ligand")
    assert slices[1].requested_modalities == ("sequence", "structure")
    assert slices[1].parent_slice_id == "alpha:base"
    assert slices[1].rank == 9
    assert slices[2].requested_modalities == ("sequence",)
    assert slices[2].parent_slice_id == "alpha:base"
    assert slices[3].requested_modalities == ("sequence", "ligand")
    assert slices[4].requested_modalities == ("sequence",)
    assert slices[4].parent_slice_id == "beta:base"
    assert slices[5].notes == ("beta note", "keep sequence")


def test_run_portfolio_matrix_registers_slices_deterministically(tmp_path):
    runtime = _build_storage_runtime()
    ppi_representation = _build_ppi_representation()
    slices = expand_portfolio_matrix(
        [
            {
                "candidate_id": "alpha",
                "rank": 1,
                "model_name": "multimodal-fusion-baseline-v1",
                "requested_modalities": ("sequence", "structure", "ligand"),
                "fusion_dim": 8,
                "notes": ("alpha note",),
            },
            {
                "candidate_id": "beta",
                "rank": 5,
                "model_name": "multimodal-fusion-baseline-v1",
                "requested_modalities": ("sequence", "ligand"),
                "fusion_dim": 6,
                "notes": ("beta note",),
            },
        ]
    )

    first = run_portfolio_matrix(
        runtime,
        slices,
        ppi_representation=ppi_representation,
        runner_id=DEFAULT_PORTFOLIO_RUNNER_ID,
        matrix_id=DEFAULT_PORTFOLIO_MATRIX_ID,
        deterministic_seed_base=19,
        provenance=("portfolio provenance",),
        notes=("portfolio note",),
    )
    second = run_portfolio_matrix(
        runtime,
        slices,
        ppi_representation=ppi_representation,
        runner_id=DEFAULT_PORTFOLIO_RUNNER_ID,
        matrix_id=DEFAULT_PORTFOLIO_MATRIX_ID,
        deterministic_seed_base=19,
        provenance=("portfolio provenance",),
        notes=("portfolio note",),
    )

    assert first == second
    assert first.runner_id == DEFAULT_PORTFOLIO_RUNNER_ID
    assert first.matrix_id == DEFAULT_PORTFOLIO_MATRIX_ID
    assert first.slice_count == 2
    assert first.record_count == 2
    assert first.source_path == "training/runtime/portfolio_runner.py"
    assert first.run_signature == second.run_signature
    assert first.provenance_refs[0] == runtime.package_manifest.manifest_id
    assert "portfolio provenance" in first.provenance_refs
    assert "portfolio note" in first.notes

    alpha, beta = first.records
    assert alpha.slice_id == "alpha:base"
    assert beta.slice_id == "beta:base"
    assert alpha.deterministic_seed == 19
    assert beta.deterministic_seed == 20
    assert alpha.registry_id == DEFAULT_EXPERIMENT_REGISTRY_ID
    assert alpha.registry_signature != beta.registry_signature
    assert alpha.backend_ready is True
    assert beta.backend_ready is True
    assert alpha.contract_fidelity == "fusion-forward-plus-checkpointed-prototype"
    assert beta.contract_fidelity == "fusion-forward-plus-checkpointed-prototype"
    assert alpha.runtime_status["backend_ready"] is True
    assert alpha.runtime_status["provenance"]["processed_examples"] == 1
    assert alpha.runtime_status["provenance"]["checkpoint_ref"].startswith("checkpoint://")
    assert Path(alpha.runtime_status["provenance"]["checkpoint_path"]).exists()
    assert Path(beta.runtime_status["provenance"]["checkpoint_path"]).exists()
    assert first.to_dict()["record_count"] == 2
    assert first.to_dict()["records"][0]["registry_signature"] == alpha.registry_signature
