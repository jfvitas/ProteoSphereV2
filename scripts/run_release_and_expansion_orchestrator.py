from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from scripts.post_tail_runner_support import (
        python_step,
        run_steps,
        write_json,
    )
    from scripts.release_expansion_support import (
        DEFAULT_EXPANSION_STAGING_ROOT,
        DEFAULT_EXTERNAL_DRIVE_ROOT,
        RELEASE_V1_MODE,
        RELEASE_V2_MODE,
    )
except ModuleNotFoundError:  # pragma: no cover
    from post_tail_runner_support import (
        python_step,
        run_steps,
        write_json,
    )
    from release_expansion_support import (
        DEFAULT_EXPANSION_STAGING_ROOT,
        DEFAULT_EXTERNAL_DRIVE_ROOT,
        RELEASE_V1_MODE,
        RELEASE_V2_MODE,
    )

DEFAULT_STATE_PATH = (
    REPO_ROOT / "artifacts" / "runtime" / "release_expansion_state.json"
)
DEFAULT_LEDGER_PATH = (
    REPO_ROOT / "artifacts" / "runtime" / "release_expansion_ledger.jsonl"
)
DEFAULT_SUMMARY_PATH = (
    REPO_ROOT / "artifacts" / "status" / "release_expansion_orchestrator_summary.json"
)


PHASE_COMMANDS = {
    "close-release-v1": [
        python_step(
            "close_release_v1",
            "Close the frozen v1 release candidate and refresh release-grade surfaces.",
            "scripts/close_release_v1.py",
            args=["--execute"],
            expected_outputs=[
                "runs/real_data_benchmark/full_results/summary.json",
                "artifacts/status/release_blocker_resolution_board_preview.json",
            ],
        )
    ],
    "run-expansion-procurement-wave": [
        python_step(
            "run_expansion_procurement_wave",
            "Run the external-drive expansion procurement wave.",
            "scripts/run_expansion_procurement_wave.py",
            args=["--external-root", str(DEFAULT_EXTERNAL_DRIVE_ROOT)],
            expected_outputs=["artifacts/runtime/expansion_procurement_state.json"],
        ),
        python_step(
            "refresh_external_drive_mount",
            "Refresh the external-drive mount preview.",
            "scripts/export_procurement_external_drive_mount_preview.py",
            args=["--external-root", str(DEFAULT_EXTERNAL_DRIVE_ROOT)],
            expected_outputs=["artifacts/status/procurement_external_drive_mount_preview.json"],
        ),
        python_step(
            "refresh_expansion_storage_budget",
            "Refresh the expansion storage budget preview.",
            "scripts/export_procurement_expansion_storage_budget_preview.py",
            args=["--external-root", str(DEFAULT_EXTERNAL_DRIVE_ROOT)],
            expected_outputs=["artifacts/status/procurement_expansion_storage_budget_preview.json"],
        ),
        python_step(
            "refresh_expansion_wave",
            "Refresh the expansion procurement wave preview.",
            "scripts/export_procurement_expansion_wave_preview.py",
            args=["--external-root", str(DEFAULT_EXTERNAL_DRIVE_ROOT)],
            expected_outputs=["artifacts/status/procurement_expansion_wave_preview.json"],
        ),
        python_step(
            "refresh_operator_dashboard_after_expansion_wave",
            "Refresh the operator dashboard after updating deferred expansion "
            "procurement surfaces.",
            "scripts/export_operator_dashboard.py",
            expected_outputs=["runs/real_data_benchmark/full_results/operator_dashboard.json"],
        ),
    ],
    "implement-missing-scrape-families": [
        python_step(
            "refresh_missing_scrape_family_contracts",
            "Refresh the missing scrape-family contracts preview.",
            "scripts/export_missing_scrape_family_contracts_preview.py",
            expected_outputs=["artifacts/status/missing_scrape_family_contracts_preview.json"],
        ),
        python_step(
            "refresh_scrape_gap_matrix_after_missing_family_contracts",
            "Refresh the scrape gap matrix after pinning the missing-family contracts.",
            "scripts/export_scrape_gap_matrix_preview.py",
            expected_outputs=["artifacts/status/scrape_gap_matrix_preview.json"],
        )
    ],
    "rebuild-expanded-structured-dataset": [
        python_step(
            "refresh_pdbbind_expanded_structured_corpus",
            "Refresh the staged PDBbind-expanded structured corpus preview.",
            "scripts/export_pdbbind_expanded_structured_corpus_preview.py",
            expected_outputs=["artifacts/status/pdbbind_expanded_structured_corpus_preview.json"],
        ),
        python_step(
            "refresh_pdbbind_protein_cohort_graph",
            "Refresh the staged PDBbind protein cohort graph preview.",
            "scripts/export_pdbbind_protein_cohort_graph_preview.py",
            expected_outputs=["artifacts/status/pdbbind_protein_cohort_graph_preview.json"],
        ),
        python_step(
            "refresh_pdb_paper_split_leakage_matrix",
            "Refresh the staged PDB paper split leakage matrix preview.",
            "scripts/export_pdb_paper_split_leakage_matrix_preview.py",
            expected_outputs=[
                "artifacts/status/pdb_paper_split_leakage_matrix_preview.json",
                "artifacts/status/pdb_paper_split_acceptance_gate_preview.json",
            ],
        ),
        python_step(
            "refresh_pdb_paper_split_sequence_signature_audit",
            "Refresh the staged PDB paper split sequence signature audit preview.",
            "scripts/export_pdb_paper_split_sequence_signature_audit_preview.py",
            expected_outputs=[
                "artifacts/status/pdb_paper_split_sequence_signature_audit_preview.json",
            ],
        ),
        python_step(
            "refresh_pdb_paper_split_mutation_audit",
            "Refresh the staged PDB paper split mutation audit preview.",
            "scripts/export_pdb_paper_split_mutation_audit_preview.py",
            expected_outputs=[
                "artifacts/status/pdb_paper_split_mutation_audit_preview.json",
            ],
        ),
        python_step(
            "refresh_pdb_paper_split_structure_state_audit",
            "Refresh the staged PDB paper split structure-state audit preview.",
            "scripts/export_pdb_paper_split_structure_state_audit_preview.py",
            expected_outputs=[
                "artifacts/status/pdb_paper_split_structure_state_audit_preview.json",
            ],
        ),
        python_step(
            "refresh_pdb_paper_dataset_quality_verdict",
            "Refresh the staged PDB paper dataset quality verdict preview.",
            "scripts/export_pdb_paper_dataset_quality_verdict_preview.py",
            expected_outputs=[
                "artifacts/status/pdb_paper_dataset_quality_verdict_preview.json",
            ],
        ),
        python_step(
            "refresh_pdb_paper_split_remediation_plan",
            "Refresh the staged PDB paper split remediation plan preview.",
            "scripts/export_pdb_paper_split_remediation_plan_preview.py",
            expected_outputs=[
                "artifacts/status/pdb_paper_split_remediation_plan_preview.json",
            ],
        ),
        python_step(
            "refresh_external_drive_mount_before_rebuild",
            "Refresh the external-drive mount preview before the deferred v2 rebuild.",
            "scripts/export_procurement_external_drive_mount_preview.py",
            args=["--external-root", str(DEFAULT_EXTERNAL_DRIVE_ROOT)],
            expected_outputs=["artifacts/status/procurement_external_drive_mount_preview.json"],
        ),
        python_step(
            "refresh_expansion_wave_before_rebuild",
            "Refresh the expansion procurement wave before the v2 rebuild.",
            "scripts/export_procurement_expansion_wave_preview.py",
            args=["--external-root", str(DEFAULT_EXTERNAL_DRIVE_ROOT)],
            expected_outputs=["artifacts/status/procurement_expansion_wave_preview.json"],
        ),
        python_step(
            "refresh_missing_scrape_family_contracts_before_rebuild",
            "Refresh the missing scrape-family contracts before the deferred v2 rebuild.",
            "scripts/export_missing_scrape_family_contracts_preview.py",
            expected_outputs=["artifacts/status/missing_scrape_family_contracts_preview.json"],
        ),
        python_step(
            "refresh_operator_dashboard_after_deferred_rebuild",
            "Refresh the operator dashboard after the deferred v2 rebuild planning pass.",
            "scripts/export_operator_dashboard.py",
            expected_outputs=["runs/real_data_benchmark/full_results/operator_dashboard.json"],
        ),
    ],
    "refresh-release-v2-evidence": [
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
            "Refresh the frozen-v1 release accession evidence pack preview.",
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
            "Refresh the release blocker resolution board.",
            "scripts/export_release_blocker_resolution_board_preview.py",
            expected_outputs=["artifacts/status/release_blocker_resolution_board_preview.json"],
        ),
        python_step(
            "refresh_operator_dashboard",
            "Refresh the operator dashboard after release/expansion updates.",
            "scripts/export_operator_dashboard.py",
            expected_outputs=["runs/real_data_benchmark/full_results/operator_dashboard.json"],
        ),
        python_step(
            "validate_operator_state",
            "Validate the operator state after refreshing release-v2 evidence surfaces.",
            "scripts/validate_operator_state.py",
            args=["--json"],
        ),
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the release/expansion orchestrator phase.")
    parser.add_argument("phase", choices=sorted(PHASE_COMMANDS))
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--ledger-path", type=Path, default=DEFAULT_LEDGER_PATH)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    steps = PHASE_COMMANDS[args.phase]
    state, ok = run_steps(
        runner_name=f"release-expansion:{args.phase}",
        steps=steps,
        state_path=args.state_path,
        ledger_path=args.ledger_path,
        resume=args.resume,
    )
    payload = {
        "artifact_id": "release_expansion_orchestrator_summary",
        "generated_at": state.get("updated_at"),
        "phase": args.phase,
        "status": "completed" if ok else "failed",
        "release_mode_v1": RELEASE_V1_MODE,
        "release_mode_v2": RELEASE_V2_MODE,
        "expansion_staging_root": str(DEFAULT_EXPANSION_STAGING_ROOT).replace("\\", "/"),
        "external_drive_root": str(DEFAULT_EXTERNAL_DRIVE_ROOT).replace("\\", "/"),
        "last_successful_step": state.get("last_successful_step"),
        "last_failed_step": state.get("last_failed_step"),
        "restart_hint": state.get("restart_hint"),
    }
    write_json(args.summary_output, payload)
    print(args.summary_output)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
