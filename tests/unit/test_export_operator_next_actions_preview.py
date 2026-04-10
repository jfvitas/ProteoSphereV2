from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_operator_next_actions_preview(tmp_path: Path) -> None:
    ligand_decision = tmp_path / "next_real_ligand_row_decision_preview.json"
    structure_validation = (
        tmp_path / "structure_followup_single_accession_validation_preview.json"
    )
    split_request = tmp_path / "split_fold_export_request_preview.json"
    duplicate_preview = tmp_path / "duplicate_cleanup_first_execution_preview.json"
    duplicate_delete_ready_manifest = (
        tmp_path / "duplicate_cleanup_delete_ready_manifest_preview.json"
    )
    output_json = tmp_path / "operator_next_actions_preview.json"
    output_md = tmp_path / "operator_next_actions_preview.md"

    ligand_decision.write_text(
        json.dumps(
            {
                "selected_accession": "P09105",
                "selected_accession_gate_status": "blocked_pending_acquisition",
                "selected_accession_probe_criteria": {
                    "best_next_action": "Extract the AlphaFold raw model for P09105",
                    "best_next_source": "af/P09105.pdb.gz",
                    "source_classification": "structure_companion_only",
                    "gap_probe_classification": "requires_extraction",
                },
                "fallback_accession": "Q2TAC2",
                "fallback_accession_gate_status": "blocked_pending_acquisition",
                "fallback_trigger_rule": "stay on P09105 until blocker is recorded",
                "current_grounded_accessions": ["P00387"],
                "truth_boundary": {
                    "candidate_only_rows_non_governing": True,
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    structure_validation.write_text(
        json.dumps(
            {
                "status": "aligned",
                "selected_accession": "P31749",
                "deferred_accession": "P04637",
                "candidate_variant_anchor_count": 5,
                "direct_structure_backed_join_certified": False,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    split_request.write_text(
        json.dumps(
            {
                "status": "blocked_report_emitted",
                "stage": {"run_scoped_only": True},
                "truth_boundary": {
                    "cv_fold_export_unlocked": False,
                    "cv_folds_materialized": False,
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    duplicate_preview.write_text(
        json.dumps(
            {
                "execution_status": "not_yet_executable_today",
                "batch_size_limit": 1,
                "duplicate_class": "exact_duplicate_same_release",
                "truth_boundary": {"delete_enabled": False},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    duplicate_delete_ready_manifest.write_text(
        json.dumps(
            {
                "preview_manifest_status": "no_current_valid_batch_requires_refresh",
                "execution_blocked": True,
                "action_count": 0,
                "constraint_checks": {
                    "all_constraints_satisfied_preview": False,
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_operator_next_actions_preview.py"),
            "--ligand-decision",
            str(ligand_decision),
            "--structure-validation",
            str(structure_validation),
            "--split-request",
            str(split_request),
            "--duplicate-preview",
            str(duplicate_preview),
            "--duplicate-delete-ready-manifest",
            str(duplicate_delete_ready_manifest),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["status"] == "complete"
    assert payload["row_count"] == 4
    assert payload["prioritized_actions"][0]["lane"] == "ligand"
    assert payload["prioritized_actions"][0]["accession"] == "P09105"
    assert (
        payload["prioritized_actions"][0]["detail"]["selected_accession_gate_status"]
        == "blocked_pending_acquisition"
    )
    assert (
        payload["prioritized_actions"][0]["detail"]["fallback_accession"] == "Q2TAC2"
    )
    assert payload["prioritized_actions"][1]["accession"] == "P31749"
    assert payload["prioritized_actions"][1]["detail"]["deferred_accession"] == "P04637"
    assert payload["prioritized_actions"][2]["detail"]["request_scope"] is True
    assert payload["prioritized_actions"][3]["detail"]["batch_size_limit"] == 1
    assert payload["prioritized_actions"][3]["detail"]["refresh_required"] is True
    assert payload["truth_boundary"]["report_only"] is True
