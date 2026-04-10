from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_validate_split_fold_export_request_preview(tmp_path: Path) -> None:
    impl_order_contract = {
        "current_live_grounding": {
            "gate_status": "blocked_pending_unlock",
            "dry_run_validation_status": "aligned",
            "candidate_row_count": 1889,
            "assignment_count": 1889,
            "split_group_counts": {"train": 1, "val": 1, "test": 9},
            "row_level_split_counts": {"train": 1440, "val": 266, "test": 183},
        },
        "proposed_implementation_order": [
            {
                "stage_id": "run_scoped_fold_export_request",
                "stage_shape": "request_manifest",
                "today_status": "blocked today",
            }
        ],
    }
    request_preview = {
        "status": "blocked_report_emitted",
        "stage": {
            "stage_id": "run_scoped_fold_export_request",
            "stage_shape": "request_manifest",
            "today_status": "blocked today",
            "run_scoped_only": True,
        },
        "request_binding": {
            "recipe_id": "protein_spine_first_split_recipe_v1",
            "input_artifact": "entity_split_candidate_preview",
            "linked_group_count": 11,
            "candidate_row_count": 1889,
            "assignment_count": 1889,
        },
        "request_manifest_preview": {
            "gate_stage_id": "cv_fold_export_unlock_gate_check",
            "gate_status": "blocked_pending_unlock",
            "staging_status": "blocked_report_emitted",
            "post_staging_validation_status": "aligned",
        },
        "blocked_report": {
            "blocked": True,
            "blocked_reasons": [
                "fold_export_ready=false",
                "cv_folds_materialized=false",
                "final_split_committed=false",
            ],
            "gate_validation_issue_count": 0,
            "cv_fold_export_unlocked": False,
            "cv_folds_materialized": False,
            "final_split_committed": False,
        },
        "live_grounding": {
            "gate_status": "blocked_pending_unlock",
            "candidate_row_count": 1889,
            "assignment_count": 1889,
            "split_group_counts": {"train": 1, "val": 1, "test": 9},
            "row_level_split_counts": {"train": 1440, "val": 266, "test": 183},
        },
        "truth_boundary": {
            "run_scoped_only": True,
            "cv_fold_export_unlocked": False,
            "cv_folds_materialized": False,
            "final_split_committed": False,
        },
    }
    post_staging_gate_check_preview = {
        "stage": {"stage_id": "cv_fold_export_unlock_gate_check"},
        "gate_check": {"gate_status": "blocked_pending_unlock"},
        "staging_parity": {"staging_status": "blocked_report_emitted"},
    }
    post_staging_gate_check_validation = {"status": "aligned"}
    split_engine_input_preview = {
        "assignment_binding": {
            "group_row_count": 11,
            "candidate_row_count": 1889,
            "assignment_count": 1889,
        },
        "recipe_binding": {
            "recipe_id": "protein_spine_first_split_recipe_v1",
            "input_artifact": "entity_split_candidate_preview",
        },
    }

    contract_path = tmp_path / "contract.json"
    request_preview_path = tmp_path / "request_preview.json"
    gate_check_preview_path = tmp_path / "gate_check_preview.json"
    gate_check_validation_path = tmp_path / "gate_check_validation.json"
    split_engine_input_path = tmp_path / "split_engine_input.json"
    output_json = tmp_path / "request_validation.json"
    output_md = tmp_path / "request_validation.md"
    contract_path.write_text(json.dumps(impl_order_contract), encoding="utf-8")
    request_preview_path.write_text(json.dumps(request_preview), encoding="utf-8")
    gate_check_preview_path.write_text(
        json.dumps(post_staging_gate_check_preview),
        encoding="utf-8",
    )
    gate_check_validation_path.write_text(
        json.dumps(post_staging_gate_check_validation),
        encoding="utf-8",
    )
    split_engine_input_path.write_text(
        json.dumps(split_engine_input_preview),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "validate_split_fold_export_request_preview.py"),
            "--impl-order-contract",
            str(contract_path),
            "--request-preview",
            str(request_preview_path),
            "--post-staging-gate-check-preview",
            str(gate_check_preview_path),
            "--post-staging-gate-check-validation",
            str(gate_check_validation_path),
            "--split-engine-input-preview",
            str(split_engine_input_path),
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
    assert payload["status"] == "aligned"
    assert payload["validation"]["gate_status"] == "blocked_pending_unlock"
    assert payload["validation"]["issues"] == []
    assert payload["truth_boundary"]["cv_fold_export_unlocked"] is False
    assert "Split Fold Export Request Validation" in output_md.read_text(encoding="utf-8")
