from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_validate_split_post_staging_gate_check_preview(tmp_path: Path) -> None:
    next_stage_contract = {
        "current_live_grounding": {
            "gate_id": "cv_fold_export_unlock_gate",
            "gate_surface": "split_engine_input_preview",
            "gate_status": "blocked_pending_unlock",
            "fold_export_ready": False,
        },
        "next_safest_executable_stage": {
            "stage_id": "cv_fold_export_unlock_gate_check",
            "stage_shape": "post_staging_gate_check",
            "today_output": "blocked report only",
        },
    }
    gate_check_preview = {
        "status": "blocked_report_emitted",
        "stage": {
            "stage_id": "cv_fold_export_unlock_gate_check",
            "stage_shape": "post_staging_gate_check",
            "today_output": "blocked report only",
            "run_scoped_only": True,
        },
        "gate_check": {
            "gate_id": "cv_fold_export_unlock_gate",
            "gate_surface": "split_engine_input_preview",
            "gate_status": "blocked_pending_unlock",
            "fold_export_ready": False,
            "cv_fold_export_unlocked": False,
        },
        "staging_parity": {
            "staging_status": "blocked_report_emitted",
            "staging_validation_status": "aligned",
            "dry_run_validation_status": "aligned",
            "candidate_row_count": 1889,
            "assignment_count": 1889,
            "split_group_counts": {"train": 1, "val": 1, "test": 9},
            "row_level_split_counts": {"train": 1440, "val": 266, "test": 183},
            "largest_groups": [
                {"linked_group_id": "protein:P04637", "split_name": "train", "entity_count": 1440}
            ],
        },
        "blocked_report": {
            "blocked": True,
            "blocked_reasons": [
                "fold_export_ready=false",
                "cv_folds_materialized=false",
                "final_split_committed=false",
            ],
            "staging_validation_issue_count": 0,
            "gate_validation_issue_count": 0,
        },
        "input_parity": {
            "input_assignment_count": 1889,
            "input_candidate_row_count": 1889,
            "matches_staging_assignment_count": True,
            "matches_staging_candidate_row_count": True,
        },
        "truth_boundary": {
            "run_scoped_only": True,
            "cv_fold_export_unlocked": False,
            "cv_folds_materialized": False,
            "final_split_committed": False,
        },
    }
    staging_preview = {
        "status": "blocked_report_emitted",
        "staging_manifest": {
            "candidate_row_count": 1889,
            "assignment_count": 1889,
            "split_group_counts": {"train": 1, "val": 1, "test": 9},
            "row_level_split_counts": {"train": 1440, "val": 266, "test": 183},
            "largest_groups": [
                {"linked_group_id": "protein:P04637", "split_name": "train", "entity_count": 1440}
            ],
        },
    }
    staging_validation = {"status": "aligned"}
    gate_preview = {"validation_snapshot": {"dry_run_validation_status": "aligned"}}
    split_engine_input_preview = {
        "assignment_binding": {
            "candidate_row_count": 1889,
            "assignment_count": 1889,
        }
    }

    contract_path = tmp_path / "contract.json"
    preview_path = tmp_path / "preview.json"
    staging_preview_path = tmp_path / "staging_preview.json"
    staging_validation_path = tmp_path / "staging_validation.json"
    gate_preview_path = tmp_path / "gate_preview.json"
    input_path = tmp_path / "input.json"
    output_json = tmp_path / "validation.json"
    output_md = tmp_path / "validation.md"
    contract_path.write_text(json.dumps(next_stage_contract), encoding="utf-8")
    preview_path.write_text(json.dumps(gate_check_preview), encoding="utf-8")
    staging_preview_path.write_text(json.dumps(staging_preview), encoding="utf-8")
    staging_validation_path.write_text(json.dumps(staging_validation), encoding="utf-8")
    gate_preview_path.write_text(json.dumps(gate_preview), encoding="utf-8")
    input_path.write_text(json.dumps(split_engine_input_preview), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "validate_split_post_staging_gate_check_preview.py"),
            "--next-stage-contract",
            str(contract_path),
            "--post-staging-gate-check-preview",
            str(preview_path),
            "--staging-preview",
            str(staging_preview_path),
            "--staging-validation",
            str(staging_validation_path),
            "--gate-preview",
            str(gate_preview_path),
            "--split-engine-input-preview",
            str(input_path),
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
    assert "Split Post-Staging Gate Check Validation" in output_md.read_text(encoding="utf-8")
