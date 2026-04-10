from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


COMMAND_MAP = {
    "refresh-procurement-truth": "export_procurement_source_completion_preview.py",
    "execute-scrape-wave": "run_pre_tail_scrape_wave.py",
    "materialize-string-interaction": "export_string_interaction_materialization_preview.py",
    "materialize-string-interaction-lane": "export_string_interaction_materialization_preview.py",
    "compile-cohort": "export_cohort_compiler_preview.py",
    "balance-diagnostics": "export_balance_diagnostics_preview.py",
    "blocker-burndown": "export_training_set_blocker_burndown_preview.py",
    "gate-ladder": "export_training_set_gate_ladder_preview.py",
    "unlock-route": "export_training_set_unlock_route_preview.py",
    "transition-contract": "export_training_set_transition_contract_preview.py",
    "source-fix-batch": "export_training_set_source_fix_batch_preview.py",
    "package-transition-batch": "export_training_set_package_transition_batch_preview.py",
    "package-execution": "export_training_set_package_execution_preview.py",
    "preview-hold-register": "export_training_set_preview_hold_register_preview.py",
    "preview-hold-exit-criteria": "export_training_set_preview_hold_exit_criteria_preview.py",
    "preview-hold-clearance-batch": "export_training_set_preview_hold_clearance_batch_preview.py",
    "modality-gap-register": "export_training_set_modality_gap_register_preview.py",
    "package-blocker-matrix": "export_training_set_package_blocker_matrix_preview.py",
    "scrape-backlog": "export_scrape_backlog_remaining_preview.py",
    "cohort-rationale": "export_cohort_inclusion_rationale_preview.py",
    "gating-evidence": "export_training_set_gating_evidence_preview.py",
    "packet-completeness": "export_training_packet_completeness_matrix_preview.py",
    "split-alignment-recheck": "export_training_split_alignment_recheck_preview.py",
    "packet-materialization-queue": "export_training_packet_materialization_queue_preview.py",
    "packet-summary": "export_training_packet_summary_preview.py",
    "action-queue": "export_training_set_action_queue_preview.py",
    "remediation-plan": "export_training_set_remediation_plan_preview.py",
    "unblock-plan": "export_training_set_unblock_plan_preview.py",
    "plan-package": "export_package_readiness_preview.py",
    "candidate-package": "export_training_set_candidate_package_manifest_preview.py",
    "build-canonical-structured-corpus": "export_seed_plus_neighbors_structured_corpus_preview.py",
    "build-canonical-corpus": "export_seed_plus_neighbors_structured_corpus_preview.py",
    "build-entity-resolution-sidecar": "export_seed_plus_neighbors_entity_resolution_preview.py",
    "build-baseline-sidecar": "export_seed_plus_neighbors_baseline_sidecar_preview.py",
    "build-multimodal-sidecar": "export_seed_plus_neighbors_multimodal_sidecar_preview.py",
    "build-final-structured-dataset-bundle": "export_final_structured_dataset_bundle.py",
    "build-pdbbind-expanded-corpus": "export_pdbbind_expanded_structured_corpus_preview.py",
    "build-pdbbind-protein-cohort-graph": "export_pdbbind_protein_cohort_graph_preview.py",
    "build-pdb-paper-split-leakage-matrix": "export_pdb_paper_split_leakage_matrix_preview.py",
    "build-pdb-paper-sequence-audit": "export_pdb_paper_split_sequence_signature_audit_preview.py",
    "build-pdb-paper-mutation-audit": "export_pdb_paper_split_mutation_audit_preview.py",
    "build-pdb-paper-structure-state-audit": (
        "export_pdb_paper_split_structure_state_audit_preview.py"
    ),
    "build-pdb-paper-quality-verdict": (
        "export_pdb_paper_dataset_quality_verdict_preview.py"
    ),
    "build-pdb-paper-remediation-plan": (
        "export_pdb_paper_split_remediation_plan_preview.py"
    ),
    "release-grade-readiness": "export_release_grade_readiness_preview.py",
    "release-grade-closure-queue": "export_release_grade_closure_queue_preview.py",
    "release-runtime-maturity": "export_release_runtime_maturity_preview.py",
    "release-source-coverage-depth": "export_release_source_coverage_depth_preview.py",
    "release-provenance-depth": "export_release_provenance_depth_preview.py",
    "release-grade-runbook": "export_release_grade_runbook_preview.py",
    "release-accession-closure-matrix": "export_release_accession_closure_matrix_preview.py",
    "release-accession-action-queue": "export_release_accession_action_queue_preview.py",
    "release-promotion-gate": "export_release_promotion_gate_preview.py",
    "release-source-fix-followup-batch": "export_release_source_fix_followup_batch_preview.py",
    "release-candidate-promotion": "export_release_candidate_promotion_preview.py",
    "release-runtime-qualification": "export_release_runtime_qualification_preview.py",
    "release-governing-sufficiency": "export_release_governing_sufficiency_preview.py",
    "release-accession-evidence-pack": "export_release_accession_evidence_pack_preview.py",
    "release-reporting-completeness": "export_release_reporting_completeness_preview.py",
    "release-blocker-resolution-board": "export_release_blocker_resolution_board_preview.py",
    "procurement-external-drive-mount": "export_procurement_external_drive_mount_preview.py",
    "procurement-expansion-wave": "export_procurement_expansion_wave_preview.py",
    "procurement-expansion-storage-budget": (
        "export_procurement_expansion_storage_budget_preview.py"
    ),
    "close-release-v1": "close_release_v1.py",
    "run-expansion-procurement-wave": "run_release_and_expansion_orchestrator.py",
    "implement-missing-scrape-families": "run_release_and_expansion_orchestrator.py",
    "rebuild-expanded-structured-dataset": "run_release_and_expansion_orchestrator.py",
    "refresh-release-v2-evidence": "run_release_and_expansion_orchestrator.py",
    "execute-post-tail-unlock": "run_post_tail_unlock.py",
    "run-final-dataset-wave": "run_post_tail_completion_wave.py",
    "assess-readiness": "export_training_set_readiness_preview.py",
    "split-simulation": "export_split_simulation_preview.py",
    "runbook": "export_training_set_builder_runbook_preview.py",
    "run-post-tail-unlock-dry-run": "run_post_tail_unlock.py",
    "post-tail-unlock-dry-run": "run_post_tail_unlock.py",
    "session": "export_training_set_builder_session_preview.py",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Training-set builder operator CLI.")
    parser.add_argument("command", choices=sorted(COMMAND_MAP))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = REPO_ROOT / "scripts" / COMMAND_MAP[args.command]
    command = [sys.executable, str(target)]
    if args.command == "execute-post-tail-unlock":
        command.extend(["--execute", "--resume", "--allow-c-overflow-authority"])
    elif args.command == "run-final-dataset-wave":
        command.extend(["--execute", "--resume", "--allow-c-overflow-authority"])
    elif args.command == "close-release-v1":
        command.append("--execute")
    elif args.command in {
        "run-expansion-procurement-wave",
        "implement-missing-scrape-families",
        "rebuild-expanded-structured-dataset",
        "refresh-release-v2-evidence",
    }:
        command.extend([args.command, "--resume"])
    result = subprocess.run(command, cwd=REPO_ROOT)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
