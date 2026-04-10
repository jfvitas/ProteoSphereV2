from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from scripts.post_tail_runner_support import (
        python_step,
        read_json,
        run_steps,
        write_json,
    )
except ModuleNotFoundError:  # pragma: no cover
    from post_tail_runner_support import python_step, read_json, run_steps, write_json

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = REPO_ROOT / "artifacts" / "runtime" / "post_tail_completion_state.json"
DEFAULT_LEDGER_PATH = REPO_ROOT / "artifacts" / "runtime" / "post_tail_completion_ledger.jsonl"
DEFAULT_SUMMARY_PATH = REPO_ROOT / "artifacts" / "status" / "post_tail_completion_summary.json"
DEFAULT_UNIREF_SOURCE = Path(r"C:\Users\jfvit\Downloads\uniref100.xml.gz")
DEFAULT_UNIREF_DEST = Path(
    r"C:\CSTEMP\ProteoSphereV2_overflow\protein_data_scope_seed\uniprot\uniref100.xml.gz"
)
DEFAULT_EXPANSION_BACKLOG = (
    REPO_ROOT / "docs" / "reports" / "procurement_expansion_inventory_2026_04_05.md"
)


def _validation_payload(state: dict[str, Any]) -> dict[str, Any]:
    validate_step = ((state.get("steps") or {}).get("validate_operator_state") or {})
    output_excerpt = str(validate_step.get("output_excerpt") or "").strip()
    if not output_excerpt:
        return {"status": "unknown"}
    try:
        return json.loads(output_excerpt)
    except json.JSONDecodeError:
        return {"status": "unknown", "raw": output_excerpt[-2000:]}


def build_post_tail_completion_summary(state: dict[str, Any]) -> dict[str, Any]:
    source_completion = read_json(
        REPO_ROOT / "artifacts" / "status" / "procurement_source_completion_preview.json"
    )
    corpus = read_json(
        REPO_ROOT / "artifacts" / "status" / "seed_plus_neighbors_structured_corpus_preview.json"
    )
    multimodal = read_json(
        REPO_ROOT / "artifacts" / "status" / "training_set_multimodal_sidecar_preview.json"
    )
    validation = _validation_payload(state)
    source_index = source_completion.get("source_completion_index") or {}
    uniprot = source_index.get("uniprot") or {}
    string_entry = source_index.get("string") or {}

    steps = state.get("steps") or {}
    executed_step_count = sum(
        1 for step in steps.values() if isinstance(step, dict) and step.get("status") == "completed"
    )
    failed_step_count = sum(
        1 for step in steps.values() if isinstance(step, dict) and step.get("status") == "failed"
    )

    return {
        "artifact_id": "post_tail_completion_summary",
        "schema_id": "proteosphere-post-tail-completion-summary-2026-04-05",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "completed" if failed_step_count == 0 else "failed",
        "summary": {
            "executed_step_count": executed_step_count,
            "failed_step_count": failed_step_count,
            "string_completion_status": source_completion.get("string_completion_status"),
            "uniprot_completion_status": source_completion.get("uniprot_completion_status"),
            "canonical_corpus_row_count": (corpus.get("summary") or {}).get("row_count"),
            "strict_governing_training_view_count": (multimodal.get("summary") or {}).get(
                "strict_governing_training_view_count"
            ),
            "validation_status": validation.get("status"),
        },
        "uniref_placement": {
            "authoritative_path": (uniprot.get("primary_live_path") or "").replace("\\", "/"),
            "completed_off_primary_root": uniprot.get("completed_off_primary_root"),
            "authority_note": uniprot.get("authority_note"),
            "fallback_source_path": str(DEFAULT_UNIREF_SOURCE).replace("\\", "/"),
            "expected_overflow_path": str(DEFAULT_UNIREF_DEST).replace("\\", "/"),
        },
        "source_completion_states": {
            "string": {
                "status": string_entry.get("completion_status"),
                "authority_note": string_entry.get("authority_note"),
                "primary_live_path": string_entry.get("primary_live_path"),
            },
            "uniprot": {
                "status": uniprot.get("completion_status"),
                "authority_note": uniprot.get("authority_note"),
                "primary_live_path": uniprot.get("primary_live_path"),
            },
        },
        "next_phase_backlog": {
            "inventory_report": str(DEFAULT_EXPANSION_BACKLOG).replace("\\", "/"),
            "downloads_deferred_until_external_drive": True,
        },
        "restart_hint": state.get("restart_hint"),
        "validation": validation,
    }


def _completion_steps(
    *,
    uniref_source: Path,
    uniref_dest: Path,
) -> list[Any]:
    return [
        python_step(
            "execute_post_tail_unlock",
            "Finalize UniRef placement and refresh procurement truth.",
            "scripts/run_post_tail_unlock.py",
            args=[
                "--execute",
                "--resume",
                "--allow-c-overflow-authority",
                "--uniref-source",
                str(uniref_source),
                "--uniref-dest",
                str(uniref_dest),
            ],
            expected_outputs=[
                "artifacts/status/post_tail_unlock_execution_preview.json",
                "artifacts/status/procurement_source_completion_preview.json",
                "artifacts/status/procurement_tail_freeze_gate_preview.json",
            ],
        ),
        python_step(
            "refresh_source_coverage_matrix",
            "Refresh the source coverage matrix after tail completion.",
            "scripts/export_source_coverage_matrix.py",
            expected_outputs=["artifacts/status/source_coverage_matrix.json"],
        ),
        python_step(
            "refresh_scrape_readiness_registry",
            "Refresh the scrape readiness registry after tail completion.",
            "scripts/export_scrape_readiness_registry_preview.py",
            expected_outputs=["artifacts/status/scrape_readiness_registry_preview.json"],
        ),
        python_step(
            "refresh_overnight_queue_backlog",
            "Refresh the overnight queue backlog with stale-runtime filtering.",
            "scripts/export_overnight_queue_backlog_preview.py",
            expected_outputs=["artifacts/status/overnight_queue_backlog_preview.json"],
        ),
        python_step(
            "refresh_pdbbind_registry",
            "Refresh the local PDBbind registry preview.",
            "scripts/export_pdbbind_registry_preview.py",
            expected_outputs=["artifacts/status/pdbbind_registry_preview.json"],
        ),
        python_step(
            "refresh_pdbbind_validation",
            "Refresh the local PDBbind validation preview.",
            "scripts/export_pdbbind_validation_preview.py",
            expected_outputs=["artifacts/status/pdbbind_validation_preview.json"],
        ),
        python_step(
            "refresh_elm_support",
            "Refresh the accession-scoped ELM support preview.",
            "scripts/export_elm_support_preview.py",
            expected_outputs=["artifacts/status/elm_support_preview.json"],
        ),
        python_step(
            "refresh_elm_support_validation",
            "Refresh the accession-scoped ELM support validation preview.",
            "scripts/export_elm_support_validation_preview.py",
            expected_outputs=["artifacts/status/elm_support_validation_preview.json"],
        ),
        python_step(
            "refresh_sabio_support",
            "Refresh the accession-scoped SABIO-RK support preview.",
            "scripts/export_sabio_rk_support_preview.py",
            expected_outputs=["artifacts/status/sabio_rk_support_preview.json"],
        ),
        python_step(
            "refresh_sabio_support_validation",
            "Refresh the accession-scoped SABIO-RK support validation preview.",
            "scripts/validate_sabio_rk_support_preview.py",
            expected_outputs=["artifacts/status/sabio_rk_support_validation.json"],
        ),
        python_step(
            "materialize_string_interaction",
            "Refresh the STRING interaction materialization preview.",
            "scripts/export_string_interaction_materialization_preview.py",
            expected_outputs=["artifacts/status/string_interaction_materialization_preview.json"],
        ),
        python_step(
            "refresh_ligand_row_materialization",
            "Refresh the lightweight ligand row materialization preview.",
            "scripts/export_ligand_row_materialization_preview.py",
            expected_outputs=["artifacts/status/ligand_row_materialization_preview.json"],
        ),
        python_step(
            "refresh_ligand_support_readiness",
            "Refresh the ligand support readiness preview.",
            "scripts/export_ligand_support_readiness_preview.py",
            expected_outputs=["artifacts/status/ligand_support_readiness_preview.json"],
        ),
        python_step(
            "refresh_ligand_identity_core_materialization",
            "Refresh the ligand identity-core materialization preview.",
            "scripts/export_ligand_identity_core_materialization_preview.py",
            expected_outputs=["artifacts/status/ligand_identity_core_materialization_preview.json"],
        ),
        python_step(
            "refresh_training_set_eligibility",
            "Refresh the training set eligibility matrix preview.",
            "scripts/export_training_set_eligibility_matrix_preview.py",
            expected_outputs=["artifacts/status/training_set_eligibility_matrix_preview.json"],
        ),
        python_step(
            "refresh_split_engine_input",
            "Refresh the split-engine input preview.",
            "scripts/export_split_engine_input_preview.py",
            expected_outputs=["artifacts/status/split_engine_input_preview.json"],
        ),
        python_step(
            "materialize_split_fold_export",
            "Materialize the run-scoped split fold export preview.",
            "scripts/export_split_fold_export_materialization_preview.py",
            expected_outputs=["artifacts/status/split_fold_export_materialization_preview.json"],
        ),
        python_step(
            "refresh_split_engine_input_post_fold_export",
            "Refresh the split-engine input preview after fold export materialization.",
            "scripts/export_split_engine_input_preview.py",
            expected_outputs=["artifacts/status/split_engine_input_preview.json"],
        ),
        python_step(
            "refresh_split_fold_export_gate",
            "Refresh the split fold export gate preview.",
            "scripts/export_split_fold_export_gate_preview.py",
            expected_outputs=["artifacts/status/split_fold_export_gate_preview.json"],
        ),
        python_step(
            "validate_split_fold_export_gate",
            "Validate the split fold export gate preview.",
            "scripts/validate_split_fold_export_gate_preview.py",
            expected_outputs=["artifacts/status/split_fold_export_gate_validation.json"],
        ),
        python_step(
            "refresh_split_fold_export_staging",
            "Refresh the split fold export staging preview.",
            "scripts/export_split_fold_export_staging_preview.py",
            expected_outputs=["artifacts/status/split_fold_export_staging_preview.json"],
        ),
        python_step(
            "validate_split_fold_export_staging",
            "Validate the split fold export staging preview.",
            "scripts/validate_split_fold_export_staging_preview.py",
            expected_outputs=["artifacts/status/split_fold_export_staging_validation.json"],
        ),
        python_step(
            "refresh_split_post_staging_gate_check",
            "Refresh the split post-staging gate check preview.",
            "scripts/export_split_post_staging_gate_check_preview.py",
            expected_outputs=["artifacts/status/split_post_staging_gate_check_preview.json"],
        ),
        python_step(
            "validate_split_post_staging_gate_check",
            "Validate the split post-staging gate check preview.",
            "scripts/validate_split_post_staging_gate_check_preview.py",
            expected_outputs=["artifacts/status/split_post_staging_gate_check_validation.json"],
        ),
        python_step(
            "refresh_split_fold_export_request",
            "Refresh the split fold export request preview.",
            "scripts/export_split_fold_export_request_preview.py",
            expected_outputs=["artifacts/status/split_fold_export_request_preview.json"],
        ),
        python_step(
            "validate_split_fold_export_request",
            "Validate the split fold export request preview.",
            "scripts/validate_split_fold_export_request_preview.py",
            expected_outputs=["artifacts/status/split_fold_export_request_validation.json"],
        ),
        python_step(
            "refresh_package_readiness",
            "Refresh the package readiness preview.",
            "scripts/export_package_readiness_preview.py",
            expected_outputs=["artifacts/status/package_readiness_preview.json"],
        ),
        python_step(
            "refresh_training_set_readiness",
            "Refresh the training set readiness preview.",
            "scripts/export_training_set_readiness_preview.py",
            expected_outputs=["artifacts/status/training_set_readiness_preview.json"],
        ),
        python_step(
            "refresh_uniref_cluster_materialization_plan",
            "Refresh the UniRef cluster materialization plan.",
            "scripts/export_uniref_cluster_materialization_plan_preview.py",
            expected_outputs=["artifacts/status/uniref_cluster_materialization_plan_preview.json"],
        ),
        python_step(
            "refresh_uniref_cluster_context",
            "Refresh the UniRef cluster context from local post-tail authority.",
            "scripts/export_uniref_cluster_context_preview.py",
            expected_outputs=["artifacts/status/uniref_cluster_context_preview.json"],
        ),
        python_step(
            "refresh_evolutionary_snapshot",
            "Build the accession-scoped evolutionary snapshot preview.",
            "scripts/export_evolutionary_snapshot_preview.py",
            expected_outputs=["artifacts/status/evolutionary_snapshot_preview.json"],
        ),
        python_step(
            "refresh_sequence_redundancy_guard",
            "Refresh the sequence redundancy guard preview.",
            "scripts/export_sequence_redundancy_guard_preview.py",
            expected_outputs=["artifacts/status/sequence_redundancy_guard_preview.json"],
        ),
        python_step(
            "refresh_scrape_gap_matrix",
            "Refresh the scrape gap matrix after UniRef completion.",
            "scripts/export_scrape_gap_matrix_preview.py",
            expected_outputs=["artifacts/status/scrape_gap_matrix_preview.json"],
        ),
        python_step(
            "refresh_scrape_execution_wave",
            "Refresh the scrape execution wave preview.",
            "scripts/export_scrape_execution_wave_preview.py",
            expected_outputs=["artifacts/status/scrape_execution_wave_preview.json"],
        ),
        python_step(
            "refresh_seed_plus_neighbors_corpus",
            "Rebuild the seed-plus-neighbors structured corpus preview.",
            "scripts/export_seed_plus_neighbors_structured_corpus_preview.py",
            expected_outputs=["artifacts/status/seed_plus_neighbors_structured_corpus_preview.json"],
        ),
        python_step(
            "refresh_seed_plus_neighbors_entity_resolution",
            "Refresh the seed-plus-neighbors entity resolution sidecar.",
            "scripts/export_seed_plus_neighbors_entity_resolution_preview.py",
            expected_outputs=["artifacts/status/seed_plus_neighbors_entity_resolution_preview.json"],
        ),
        python_step(
            "refresh_baseline_sidecar",
            "Refresh the baseline training sidecar.",
            "scripts/export_seed_plus_neighbors_baseline_sidecar_preview.py",
            expected_outputs=["artifacts/status/training_set_baseline_sidecar_preview.json"],
        ),
        python_step(
            "refresh_multimodal_sidecar",
            "Refresh the multimodal training sidecar.",
            "scripts/export_seed_plus_neighbors_multimodal_sidecar_preview.py",
            expected_outputs=["artifacts/status/training_set_multimodal_sidecar_preview.json"],
        ),
        python_step(
            "refresh_training_packet_summary",
            "Refresh the training packet summary preview.",
            "scripts/export_training_packet_summary_preview.py",
            expected_outputs=["artifacts/status/training_packet_summary_preview.json"],
        ),
        python_step(
            "refresh_training_packet_completeness",
            "Refresh the packet completeness matrix.",
            "scripts/export_training_packet_completeness_matrix_preview.py",
            expected_outputs=["artifacts/status/training_packet_completeness_matrix_preview.json"],
        ),
        python_step(
            "refresh_training_split_alignment_recheck",
            "Refresh the training split alignment recheck.",
            "scripts/export_training_split_alignment_recheck_preview.py",
            expected_outputs=["artifacts/status/training_split_alignment_recheck_preview.json"],
        ),
        python_step(
            "refresh_training_packet_materialization_queue",
            "Refresh the packet materialization queue preview.",
            "scripts/export_training_packet_materialization_queue_preview.py",
            expected_outputs=["artifacts/status/training_packet_materialization_queue_preview.json"],
        ),
        python_step(
            "refresh_final_structured_dataset_bundle",
            "Export the versioned final structured dataset bundle.",
            "scripts/export_final_structured_dataset_bundle.py",
            expected_outputs=[
                "artifacts/status/final_structured_dataset_bundle_preview.json",
                "data/reports/final_structured_datasets/LATEST.json",
            ],
        ),
        python_step(
            "refresh_benchmark_provenance",
            "Refresh the benchmark provenance table.",
            "scripts/emit_benchmark_provenance.py",
            expected_outputs=["runs/real_data_benchmark/full_results/provenance_table.json"],
        ),
        python_step(
            "refresh_release_corpus_ledger",
            "Refresh the release corpus evidence ledger.",
            "scripts/emit_release_corpus_ledger.py",
            expected_outputs=[
                "runs/real_data_benchmark/full_results/release_corpus_evidence_ledger.json"
            ],
        ),
        python_step(
            "refresh_release_bundle_manifest",
            "Refresh the versioned release bundle manifest.",
            "scripts/build_release_bundle.py",
            expected_outputs=[
                "runs/real_data_benchmark/full_results/versioned_release_bundle_manifest.json"
            ],
        ),
        python_step(
            "refresh_release_cards",
            "Publish conservative release cards from current release evidence.",
            "scripts/publish_release_cards.py",
            expected_outputs=[
                "runs/real_data_benchmark/full_results/release_cards_manifest.json"
            ],
        ),
        python_step(
            "refresh_release_runtime_qualification",
            "Refresh the frozen-v1 runtime qualification preview.",
            "scripts/export_release_runtime_qualification_preview.py",
            expected_outputs=["artifacts/status/release_runtime_qualification_preview.json"],
        ),
        python_step(
            "refresh_release_governing_sufficiency",
            "Refresh the frozen-v1 governing sufficiency preview.",
            "scripts/export_release_governing_sufficiency_preview.py",
            expected_outputs=["artifacts/status/release_governing_sufficiency_preview.json"],
        ),
        python_step(
            "refresh_release_accession_evidence_pack",
            "Refresh the frozen-v1 accession evidence pack preview.",
            "scripts/export_release_accession_evidence_pack_preview.py",
            expected_outputs=["artifacts/status/release_accession_evidence_pack_preview.json"],
        ),
        python_step(
            "refresh_release_reporting_completeness",
            "Refresh the frozen-v1 reporting completeness preview.",
            "scripts/export_release_reporting_completeness_preview.py",
            expected_outputs=["artifacts/status/release_reporting_completeness_preview.json"],
        ),
        python_step(
            "refresh_release_blocker_resolution_board",
            "Refresh the frozen-v1 blocker resolution board preview.",
            "scripts/export_release_blocker_resolution_board_preview.py",
            expected_outputs=["artifacts/status/release_blocker_resolution_board_preview.json"],
        ),
        python_step(
            "refresh_procurement_external_drive_mount",
            "Refresh the external-drive mount preview for the deferred v2 wave.",
            "scripts/export_procurement_external_drive_mount_preview.py",
            expected_outputs=["artifacts/status/procurement_external_drive_mount_preview.json"],
        ),
        python_step(
            "refresh_procurement_expansion_storage_budget",
            "Refresh the deferred v2 expansion storage budget preview.",
            "scripts/export_procurement_expansion_storage_budget_preview.py",
            expected_outputs=["artifacts/status/procurement_expansion_storage_budget_preview.json"],
        ),
        python_step(
            "refresh_procurement_expansion_wave",
            "Refresh the deferred v2 expansion procurement wave preview.",
            "scripts/export_procurement_expansion_wave_preview.py",
            expected_outputs=["artifacts/status/procurement_expansion_wave_preview.json"],
        ),
        python_step(
            "refresh_missing_scrape_family_contracts",
            "Refresh the deferred missing scrape-family contracts preview.",
            "scripts/export_missing_scrape_family_contracts_preview.py",
            expected_outputs=["artifacts/status/missing_scrape_family_contracts_preview.json"],
        ),
        python_step(
            "refresh_release_grade_readiness",
            "Refresh the release-grade readiness preview.",
            "scripts/export_release_grade_readiness_preview.py",
            expected_outputs=["artifacts/status/release_grade_readiness_preview.json"],
        ),
        python_step(
            "refresh_release_runtime_maturity",
            "Refresh the release runtime maturity preview.",
            "scripts/export_release_runtime_maturity_preview.py",
            expected_outputs=["artifacts/status/release_runtime_maturity_preview.json"],
        ),
        python_step(
            "refresh_release_source_coverage_depth",
            "Refresh the release source coverage depth preview.",
            "scripts/export_release_source_coverage_depth_preview.py",
            expected_outputs=["artifacts/status/release_source_coverage_depth_preview.json"],
        ),
        python_step(
            "refresh_release_provenance_depth",
            "Refresh the release provenance depth preview.",
            "scripts/export_release_provenance_depth_preview.py",
            expected_outputs=["artifacts/status/release_provenance_depth_preview.json"],
        ),
        python_step(
            "refresh_release_grade_runbook",
            "Refresh the release-grade runbook preview.",
            "scripts/export_release_grade_runbook_preview.py",
            expected_outputs=["artifacts/status/release_grade_runbook_preview.json"],
        ),
        python_step(
            "refresh_release_accession_closure_matrix",
            "Refresh the release accession closure matrix preview.",
            "scripts/export_release_accession_closure_matrix_preview.py",
            expected_outputs=["artifacts/status/release_accession_closure_matrix_preview.json"],
        ),
        python_step(
            "refresh_release_accession_action_queue",
            "Refresh the release accession action queue preview.",
            "scripts/export_release_accession_action_queue_preview.py",
            expected_outputs=["artifacts/status/release_accession_action_queue_preview.json"],
        ),
        python_step(
            "refresh_release_promotion_gate",
            "Refresh the release promotion gate preview.",
            "scripts/export_release_promotion_gate_preview.py",
            expected_outputs=["artifacts/status/release_promotion_gate_preview.json"],
        ),
        python_step(
            "refresh_release_source_fix_followup_batch",
            "Refresh the release source-fix follow-up batch preview.",
            "scripts/export_release_source_fix_followup_batch_preview.py",
            expected_outputs=["artifacts/status/release_source_fix_followup_batch_preview.json"],
        ),
        python_step(
            "refresh_release_candidate_promotion",
            "Refresh the release candidate promotion preview.",
            "scripts/export_release_candidate_promotion_preview.py",
            expected_outputs=["artifacts/status/release_candidate_promotion_preview.json"],
        ),
        python_step(
            "refresh_release_grade_closure_queue",
            "Refresh the ranked release-grade closure queue preview.",
            "scripts/export_release_grade_closure_queue_preview.py",
            expected_outputs=["artifacts/status/release_grade_closure_queue_preview.json"],
        ),
        python_step(
            "refresh_operator_dashboard",
            "Refresh the operator dashboard.",
            "scripts/export_operator_dashboard.py",
            expected_outputs=["runs/real_data_benchmark/full_results/operator_dashboard.json"],
        ),
        python_step(
            "validate_operator_state",
            "Validate the operator state against the pinned contract.",
            "scripts/validate_operator_state.py",
            args=["--json"],
        ),
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the resumable post-tail completion wave."
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--allow-c-overflow-authority", action="store_true")
    parser.add_argument("--uniref-source", type=Path, default=DEFAULT_UNIREF_SOURCE)
    parser.add_argument("--uniref-dest", type=Path, default=DEFAULT_UNIREF_DEST)
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--ledger-path", type=Path, default=DEFAULT_LEDGER_PATH)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.execute:
        raise SystemExit("Use --execute to run the post-tail completion wave.")
    if not args.allow_c_overflow_authority:
        raise SystemExit("--allow-c-overflow-authority is required for execute mode.")

    state, _ = run_steps(
        runner_name="post_tail_completion_wave",
        steps=_completion_steps(
            uniref_source=args.uniref_source,
            uniref_dest=args.uniref_dest,
        ),
        state_path=args.state_path,
        ledger_path=args.ledger_path,
        resume=args.resume,
    )
    summary = build_post_tail_completion_summary(state)
    write_json(args.summary_output, summary)
    print(args.summary_output)


if __name__ == "__main__":
    main()
