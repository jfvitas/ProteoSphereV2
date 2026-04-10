from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

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
    PackageManifestMaterialization,
    PackageManifestRawManifest,
)
from core.storage.planning_index_schema import (
    PlanningIndexEntry,
    PlanningIndexSchema,
    PlanningIndexSourceRecord,
)
from execution.storage_runtime import integrate_storage_runtime
from features.ppi_representation import build_ppi_representation
from training.multimodal.runtime import execute_multimodal_training
COHORT_MANIFEST = REPO_ROOT / "runs" / "real_data_benchmark" / "cohort" / "cohort_manifest.json"
SPLIT_LABELS = REPO_ROOT / "runs" / "real_data_benchmark" / "cohort" / "split_labels.json"
FULL_RESULTS_DIR = REPO_ROOT / "runs" / "real_data_benchmark" / "full_results"
RUN_MANIFEST_PATH = FULL_RESULTS_DIR / "run_manifest.json"
CHECKPOINT_PATH = FULL_RESULTS_DIR / "checkpoints" / "full-cohort-trainer.json"
RUN_SUMMARY_PATH = FULL_RESULTS_DIR / "run_summary.json"
CHECKPOINT_SUMMARY_PATH = FULL_RESULTS_DIR / "checkpoint_summary.json"
LIVE_INPUTS_PATH = FULL_RESULTS_DIR / "live_inputs.json"
LOG_PATH = FULL_RESULTS_DIR / "logs" / "full_rerun_stdout.log"

BENCHMARK_MANIFEST = REPO_ROOT / "runs" / "real_data_benchmark" / "manifest.json"
BENCHMARK_RUNBOOK = REPO_ROOT / "runs" / "real_data_benchmark" / "README.md"
BENCHMARK_CHECKLIST = REPO_ROOT / "runs" / "real_data_benchmark" / "checklist_2026_03_22.md"
RERUN_REPORT = REPO_ROOT / "docs" / "reports" / "real_data_benchmark_rerun.md"
FULL_RERUN_REPORT = REPO_ROOT / "docs" / "reports" / "real_data_benchmark_full_rerun.md"
LIVE_SMOKE_REPORTS = [
    REPO_ROOT / "docs" / "reports" / "live_source_smoke_2026_03_22.md",
    REPO_ROOT / "docs" / "reports" / "ppi_live_smoke_2026_03_22.md",
    REPO_ROOT / "docs" / "reports" / "annotation_pathway_live_smoke_2026_03_22.md",
    REPO_ROOT / "docs" / "reports" / "bindingdb_live_smoke_2026_03_22.md",
    REPO_ROOT / "docs" / "reports" / "evolutionary_live_smoke_2026_03_22.md",
]
REQUESTED_MODALITIES = ("sequence", "structure", "ligand", "ppi")


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _artifact_ref(kind: str, accession: str) -> str:
    return f"{kind}/{accession}"


def _artifact_payload(kind: str, accession: str, *, tag: str) -> dict[str, Any]:
    return {
        "materialized_ref": f"artifact://{kind}/{accession}",
        "checksum": f"sha256:{kind}:{accession}:{tag}",
        "provenance_refs": (f"{kind}:{accession}",),
        "notes": (f"materialized for {accession}",),
    }


def _selected_example(
    accession: str,
    split: str,
    bucket: str,
    *,
    planning_ref: str,
    source_refs: tuple[str, ...],
    include_structure: bool = False,
    include_ligand: bool = False,
) -> PackageManifestExample:
    artifact_pointers = [
        PackageManifestArtifactPointer(
            artifact_kind="feature",
            pointer=_artifact_ref("sequence", accession),
            selector="sequence",
            source_name="sequence",
            source_record_id=f"uniprot:{accession}",
        )
    ]
    if include_structure:
        artifact_pointers.append(
            PackageManifestArtifactPointer(
                artifact_kind="embedding",
                pointer=_artifact_ref("structure", accession),
                selector="structure",
                source_name="structure",
                source_record_id=f"alphafold:{accession}",
            )
        )
    if include_ligand:
        artifact_pointers.append(
            PackageManifestArtifactPointer(
                artifact_kind="feature",
                pointer=_artifact_ref("ligand", accession),
                selector="ligand",
                source_name="ligand",
                source_record_id=f"bindingdb:{accession}",
            )
        )
    return PackageManifestExample(
        example_id=accession,
        planning_index_ref=planning_ref,
        source_record_refs=source_refs,
        canonical_ids=(f"protein:{accession}",),
        artifact_pointers=tuple(artifact_pointers),
        notes=(f"{split}:{bucket}",),
    )


def _build_runtime_inputs(cohort: dict[str, Any], split_labels: dict[str, Any]):
    label_index = {item["accession"]: item["split"] for item in split_labels["labels"]}
    cohort_rows = cohort["cohort"]
    examples: list[PackageManifestExample] = []
    planning_entries: list[PlanningIndexEntry] = []
    canonical_records: list[CanonicalStoreRecord] = []
    feature_records: list[FeatureCacheEntry] = []
    embedding_records: list[EmbeddingCacheEntry] = []
    available_artifacts: dict[str, Any] = {}

    for row in cohort_rows:
        accession = row["accession"]
        split = label_index[accession]
        bucket = row["bucket"]
        planning_ref = f"planning/{accession}"
        source_refs = [f"uniprot:{accession}"]
        if accession in {"P69905", "P68871"}:
            source_refs.append("4HHB")
        if row["evidence_mode"] == "direct_live_smoke":
            source_refs.extend(row["evidence_refs"])

        example = _selected_example(
            accession,
            split,
            bucket,
            planning_ref=planning_ref,
            source_refs=tuple(source_refs),
            include_structure=accession == "P69905",
            include_ligand=accession == "P31749",
        )
        examples.append(example)

        planning_entries.append(
            PlanningIndexEntry(
                planning_id=planning_ref,
                source_records=(
                    PlanningIndexSourceRecord(
                        source_name="UniProt",
                        source_record_id=f"uniprot:{accession}",
                        release_version="2026-03-22",
                        manifest_id=cohort["manifest_id"],
                    ),
                ),
                canonical_ids=(f"protein:{accession}",),
                join_status="joined",
            )
        )
        canonical_records.append(
            CanonicalStoreRecord(
                canonical_id=f"protein:{accession}",
                entity_kind="protein",
                canonical_payload={
                    "accession": accession,
                    "split": split,
                    "bucket": bucket,
                    "evidence_mode": row["evidence_mode"],
                    "source_lanes": row["source_lanes"],
                },
                source_refs=(
                    CanonicalStoreSourceRef(
                        source_name="UniProt",
                        source_record_id=f"uniprot:{accession}",
                        source_manifest_id=cohort["manifest_id"],
                        planning_index_ref=planning_ref,
                        package_id="real-data-benchmark-full-2026-03-22",
                    ),
                ),
                planning_index_refs=(planning_ref,),
                package_ids=("real-data-benchmark-full-2026-03-22",),
            )
        )

        feature_pointer = _artifact_ref("sequence", accession)
        feature_records.append(
            FeatureCacheEntry(
                cache_id=f"feature-{accession}",
                feature_family="sequence",
                cache_version="v1",
                source_refs=(
                    FeatureCacheSourceRef(
                        source_name="sequence",
                        source_record_id=f"uniprot:{accession}",
                        manifest_id=cohort["manifest_id"],
                        planning_id=planning_ref,
                    ),
                ),
                canonical_ids=(f"protein:{accession}",),
                join_status="joined",
                artifact_pointers=(
                    FeatureCacheArtifactPointer(
                        artifact_kind="feature_matrix",
                        pointer=feature_pointer,
                        source_name="sequence",
                        source_record_id=f"uniprot:{accession}",
                        planning_id=planning_ref,
                    ),
                ),
            )
        )
        available_artifacts[feature_pointer] = _artifact_payload("sequence", accession, tag="v1")

        if accession == "P69905":
            embedding_pointer = _artifact_ref("structure", accession)
            embedding_records.append(
                EmbeddingCacheEntry(
                    cache_id=f"embedding-{accession}",
                    cache_family="structure",
                    cache_version="v1",
                    model_identity=EmbeddingModelIdentity(
                        model_name="alphafold-smoke-anchor",
                        model_version="1",
                    ),
                    runtime_identity=EmbeddingRuntimeIdentity(
                        runtime_name="structure-runtime",
                        runtime_version="1",
                    ),
                    source_refs=(
                        EmbeddingCacheSourceRef(
                            source_name="structure",
                            source_record_id=f"alphafold:{accession}",
                            manifest_id=cohort["manifest_id"],
                            planning_id=planning_ref,
                            provenance_id=f"alphafold:{accession}",
                        ),
                    ),
                    canonical_ids=(f"protein:{accession}",),
                    join_status="joined",
                    artifact_pointers=(
                        EmbeddingCacheArtifactPointer(
                            artifact_kind="embedding",
                            pointer=embedding_pointer,
                            source_name="structure",
                            source_record_id=f"alphafold:{accession}",
                            planning_id=planning_ref,
                        ),
                    ),
                )
            )
            available_artifacts[embedding_pointer] = _artifact_payload("structure", accession, tag="v1")

        if accession == "P31749":
            ligand_pointer = _artifact_ref("ligand", accession)
            feature_records.append(
                FeatureCacheEntry(
                    cache_id=f"feature-ligand-{accession}",
                    feature_family="ligand",
                    cache_version="v1",
                    source_refs=(
                        FeatureCacheSourceRef(
                            source_name="ligand",
                            source_record_id=f"bindingdb:{accession}",
                            manifest_id=cohort["manifest_id"],
                            planning_id=planning_ref,
                        ),
                    ),
                    canonical_ids=(f"protein:{accession}",),
                    join_status="joined",
                    artifact_pointers=(
                    FeatureCacheArtifactPointer(
                        artifact_kind="feature_matrix",
                        pointer=ligand_pointer,
                        source_name="ligand",
                        source_record_id=f"bindingdb:{accession}",
                        planning_id=planning_ref,
                        ),
                    ),
                )
            )
            available_artifacts[ligand_pointer] = _artifact_payload("ligand", accession, tag="v1")

    pair_record = ProteinProteinSummaryRecord(
        summary_id="pair:4HHB:protein_protein",
        protein_a_ref="protein:P69905",
        protein_b_ref="protein:P68871",
        interaction_type="protein complex",
        interaction_id="4HHB",
        interaction_refs=("4HHB",),
        organism_name="Homo sapiens",
        taxon_id=9606,
        physical_interaction=True,
        join_status="joined",
        context=SummaryRecordContext(
            provenance_pointers=(
                SummaryProvenancePointer(
                    provenance_id="ppi:4HHB:2026-03-22",
                    source_name="IntAct",
                    source_record_id="4HHB",
                    release_version="2026-03-22",
                    release_date="2026-03-22",
                ),
            ),
            storage_notes=("live-derived pair sidecar for the benchmark probe",),
        ),
    )
    ppi_representation = build_ppi_representation(
        (pair_record,),
        representation_id="ppi-live-4hhb-2026-03-22",
        library_id="ppi-live-corpus-2026-03-22",
        source_manifest_id="ppi:live-smoke:2026-03-22",
        provenance=("docs/reports/ppi_live_smoke_2026_03_22.md",),
    )

    package_manifest = PackageManifest(
        package_id="real-data-benchmark-full-2026-03-22",
        selected_examples=tuple(examples),
        raw_manifests=(
            PackageManifestRawManifest(
                source_name="benchmark-cohort",
                raw_manifest_id=cohort["manifest_id"],
                raw_manifest_ref=str(COHORT_MANIFEST).replace("\\", "/"),
                release_version="2026-03-22",
                planning_index_ref="planning/real-data-benchmark-full-2026-03-22",
                notes=("frozen 12-accession benchmark cohort",),
            ),
        ),
        planning_index_refs=("planning/real-data-benchmark-full-2026-03-22",),
        materialization=PackageManifestMaterialization(
            split_name="frozen-cohort",
            split_artifact_id="split-labels-2026-03-22",
            materialization_run_id="full-benchmark-run-2026-03-22",
            materialization_mode="selective",
            package_version="2026-03-22",
            package_state="frozen",
            materialized_at="2026-03-22T00:00:00Z",
            published_at="2026-03-22T00:00:00Z",
            notes=("benchmark harness prepared from frozen cohort",),
        ),
        provenance=(
            str(COHORT_MANIFEST).replace("\\", "/"),
            str(SPLIT_LABELS).replace("\\", "/"),
            "docs/reports/real_data_benchmark_rerun.md",
            "runs/real_data_benchmark/results/live_inputs.json",
        ),
        notes=("full benchmark harness from frozen 12-accession cohort",),
    )

    planning_index = PlanningIndexSchema(records=tuple(planning_entries))
    canonical_store = CanonicalStore(records=tuple(canonical_records))
    feature_cache = FeatureCacheCatalog(records=tuple(feature_records))
    embedding_cache = EmbeddingCacheCatalog(records=tuple(embedding_records))
    return package_manifest, planning_index, canonical_store, feature_cache, embedding_cache, available_artifacts, ppi_representation


def _base_manifest(
    cohort: dict[str, Any],
    split_labels: dict[str, Any],
    *,
    command: str,
    prepare_command: str,
) -> dict[str, Any]:
    split_counts = split_labels["counts"]
    return {
        "manifest_id": "full-benchmark-run-2026-03-22",
        "task_id": "P6-T013",
        "date": "2026-03-22",
        "status": "prepared",
        "runtime_surface": "training/multimodal/runtime.py",
        "command": command,
        "prepare_command": prepare_command,
        "results_dir": str(FULL_RESULTS_DIR).replace("\\", "/"),
        "inputs": {
            "cohort_manifest": str(COHORT_MANIFEST).replace("\\", "/"),
            "split_labels": str(SPLIT_LABELS).replace("\\", "/"),
            "benchmark_manifest": str(BENCHMARK_MANIFEST).replace("\\", "/"),
            "benchmark_runbook": str(BENCHMARK_RUNBOOK).replace("\\", "/"),
            "benchmark_checklist": str(BENCHMARK_CHECKLIST).replace("\\", "/"),
            "frozen_cohort_count": cohort["target_size"],
            "split_counts": split_counts,
            "live_smoke_reports": [str(path).replace("\\", "/") for path in LIVE_SMOKE_REPORTS],
            "rerun_report": str(FULL_RERUN_REPORT).replace("\\", "/"),
        },
        "execution": {
            "mode": "partial-then-resume",
            "attempted": False,
            "first_pass_limit": 6,
            "requested_modalities": list(REQUESTED_MODALITIES),
            "checkpoint_path": str(CHECKPOINT_PATH).replace("\\", "/"),
        },
        "outputs": {
            "run_summary": str(RUN_SUMMARY_PATH).replace("\\", "/"),
            "checkpoint_summary": str(CHECKPOINT_SUMMARY_PATH).replace("\\", "/"),
            "live_inputs": str(LIVE_INPUTS_PATH).replace("\\", "/"),
            "log": str(LOG_PATH).replace("\\", "/"),
        },
        "limitations": [
            "local prototype runtime uses surrogate modality embeddings",
            "checkpoint resume is keyed by example identity",
            "ppi sidecar is present only on the hemoglobin pair",
        ],
        "blocker_categories": [],
    }


def _summarize_result(result: Any) -> dict[str, Any]:
    return {
        "run_id": result.checkpoint.run_id,
        "checkpoint_tag": result.checkpoint.checkpoint_tag,
        "checkpoint_ref": result.checkpoint.checkpoint_ref,
        "checkpoint_path": result.checkpoint.checkpoint_path,
        "processed_examples": result.checkpoint.processed_examples,
        "completed_example_ids": list(result.checkpoint.completed_example_ids),
        "processable_example_ids": list(result.checkpoint.processable_example_ids),
        "plan_backend_ready": result.plan.status.backend_ready,
        "plan_blocker": None if result.plan.status.blocker is None else result.plan.status.blocker.reason,
        "state_phase": result.state.phase,
        "loss_history": list(result.checkpoint.loss_history),
        "available_modalities": list(result.example_results[0].fusion_result.available_modalities)
        if result.example_results
        else [],
    }


def _write_logs(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the real-data benchmark harness.")
    parser.add_argument("--prepare-only", action="store_true", help="Write the run manifest and stop.")
    parser.add_argument("--first-pass-limit", type=int, default=6, help="Examples to process before resuming.")
    parser.add_argument("--deterministic-seed", type=int, default=19)
    parser.add_argument("--learning-rate", type=float, default=0.1)
    parser.add_argument("--fusion-dim", type=int, default=8)
    parser.add_argument("--checkpoint-path", type=Path, default=CHECKPOINT_PATH)
    args = parser.parse_args()

    cohort = _read_json(COHORT_MANIFEST)
    split_labels = _read_json(SPLIT_LABELS)
    FULL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (FULL_RESULTS_DIR / "checkpoints").mkdir(parents=True, exist_ok=True)
    (FULL_RESULTS_DIR / "logs").mkdir(parents=True, exist_ok=True)

    prepare_command = "python scripts/run_full_benchmark.py --prepare-only"
    attempt_command = "python scripts/run_full_benchmark.py"
    run_manifest = _base_manifest(
        cohort,
        split_labels,
        command=attempt_command,
        prepare_command=prepare_command,
    )
    _write_json(RUN_MANIFEST_PATH, run_manifest)

    if args.prepare_only:
        return 0

    package_manifest, planning_index, canonical_store, feature_cache, embedding_cache, available_artifacts, ppi_representation = _build_runtime_inputs(
        cohort,
        split_labels,
    )
    storage_runtime = integrate_storage_runtime(
        package_manifest,
        planning_index=planning_index,
        canonical_store=canonical_store,
        feature_cache=feature_cache,
        embedding_cache=embedding_cache,
        available_artifacts=available_artifacts,
        materialization_run_id="full-benchmark-run-2026-03-22",
        materialized_at=datetime.now(tz=UTC),
        package_version="2026-03-22",
        package_state="frozen",
        split_name="frozen-cohort",
        split_artifact_id="split-labels-2026-03-22",
        published_at=datetime.now(tz=UTC),
        provenance_refs=("scripts/run_full_benchmark.py",),
        notes=("full benchmark harness materialization",),
    )
    first_pass = execute_multimodal_training(
        storage_runtime,
        ppi_representation=ppi_representation,
        checkpoint_path=args.checkpoint_path,
        deterministic_seed=args.deterministic_seed,
        learning_rate=args.learning_rate,
        max_examples=args.first_pass_limit,
        provenance=("scripts/run_full_benchmark.py",),
        notes=("first-pass partial run",),
    )
    resumed = execute_multimodal_training(
        storage_runtime,
        ppi_representation=ppi_representation,
        checkpoint_path=args.checkpoint_path,
        deterministic_seed=args.deterministic_seed,
        learning_rate=args.learning_rate,
        resume=True,
        provenance=("scripts/run_full_benchmark.py",),
        notes=("resumed full run",),
    )

    _write_json(
        LIVE_INPUTS_PATH,
        {
            "task_id": "P6-T013",
            "cohort_manifest": str(COHORT_MANIFEST).replace("\\", "/"),
            "split_labels": str(SPLIT_LABELS).replace("\\", "/"),
            "cohort": cohort["cohort"],
            "requested_modalities": list(REQUESTED_MODALITIES),
            "probe": None,
        },
    )
    _write_json(
        CHECKPOINT_SUMMARY_PATH,
        {
            "first_checkpoint": first_pass.checkpoint.to_dict(),
            "resumed_checkpoint": resumed.checkpoint.to_dict(),
        },
    )
    _write_json(
        RUN_SUMMARY_PATH,
        {
            "benchmark_task": "P6-T013",
            "cohort_status": "frozen_12_accession_run_complete_on_prototype_runtime",
            "runtime_surface": "local prototype runtime with surrogate modality embeddings and identity-safe resume continuity",
            "selected_accession_count": len(cohort["cohort"]),
            "split_counts": split_labels["counts"],
            "first_run": _summarize_result(first_pass),
            "resumed_run": _summarize_result(resumed),
            "summary_library": {
                "record_count": resumed.example_results[0].fusion_result.available_count if resumed.example_results else 0,
            },
            "remaining_gaps": [
                "The runtime is still a local prototype, not the production multimodal trainer stack.",
                "PPI evidence is attached as a sidecar only for the hemoglobin pair and does not widen the training corpus.",
                "The full benchmark remains bounded by the frozen in-tree cohort and live-derived evidence available today.",
            ],
        },
    )
    _write_logs(
        LOG_PATH,
        [
            "P6-T013 full benchmark harness",
            f"cohort_manifest={COHORT_MANIFEST.as_posix()}",
            f"split_labels={SPLIT_LABELS.as_posix()}",
            f"checkpoint_path={args.checkpoint_path.as_posix()}",
            "first_pass=6 examples",
            "resume=completed",
            "runtime_surface=local prototype runtime with surrogate modality embeddings and identity-safe resume continuity",
        ],
    )

    run_manifest.update(
        {
            "status": "completed_on_prototype_runtime",
            "execution": {
                "mode": "partial-then-resume",
                "attempted": True,
                "first_pass_limit": args.first_pass_limit,
                "requested_modalities": list(REQUESTED_MODALITIES),
                "checkpoint_path": str(args.checkpoint_path).replace("\\", "/"),
                "first_run_processed_examples": first_pass.checkpoint.processed_examples,
                "resumed_run_processed_examples": resumed.checkpoint.processed_examples,
                "checkpoint_resumes": 1,
                "checkpoint_writes": 2,
                "resume_continuity": "identity-safe",
                "final_status": resumed.state.phase,
            },
            "outputs": {
                "run_summary": str(RUN_SUMMARY_PATH).replace("\\", "/"),
                "checkpoint_summary": str(CHECKPOINT_SUMMARY_PATH).replace("\\", "/"),
                "live_inputs": str(LIVE_INPUTS_PATH).replace("\\", "/"),
                "log": str(LOG_PATH).replace("\\", "/"),
            },
            "limitations": [
                "local prototype runtime uses surrogate modality embeddings",
                "checkpoint resume is keyed by example identity",
                "ppi sidecar is present only on the hemoglobin pair",
            ],
            "blocker_categories": [],
        }
    )
    _write_json(RUN_MANIFEST_PATH, run_manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
