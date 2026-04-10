from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_split_post_staging_gate_check_preview(tmp_path: Path) -> None:
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
    staging_preview = {
        "status": "blocked_report_emitted",
        "gate_binding": {
            "gate_status": "blocked_pending_unlock",
        },
        "staging_manifest": {
            "candidate_row_count": 1889,
            "assignment_count": 1889,
            "split_group_counts": {"train": 1, "val": 1, "test": 9},
            "row_level_split_counts": {"train": 1440, "val": 266, "test": 183},
            "largest_groups": [
                {"linked_group_id": "protein:P04637", "split_name": "train", "entity_count": 1440}
            ],
        },
        "blocked_report": {
            "dry_run_validation_status": "aligned",
            "dry_run_issue_count": 0,
            "blocked_reasons": [
                "fold_export_ready=false",
                "cv_folds_materialized=false",
                "final_split_committed=false",
            ],
        },
        "truth_boundary": {
            "cv_folds_materialized": False,
            "final_split_committed": False,
        },
    }
    staging_validation = {
        "status": "aligned",
        "validation": {"issues": []},
    }
    gate_preview = {"validation_snapshot": {"dry_run_validation_status": "aligned"}}
    gate_validation = {"validation": {"issues": []}}
    split_engine_input_preview = {
        "assignment_binding": {
            "candidate_row_count": 1889,
            "assignment_count": 1889,
        }
    }

    contract_path = tmp_path / "contract.json"
    staging_preview_path = tmp_path / "staging_preview.json"
    staging_validation_path = tmp_path / "staging_validation.json"
    gate_preview_path = tmp_path / "gate_preview.json"
    gate_validation_path = tmp_path / "gate_validation.json"
    input_path = tmp_path / "input.json"
    output_json = tmp_path / "post_staging_preview.json"
    output_md = tmp_path / "post_staging_preview.md"
    contract_path.write_text(json.dumps(next_stage_contract), encoding="utf-8")
    staging_preview_path.write_text(json.dumps(staging_preview), encoding="utf-8")
    staging_validation_path.write_text(json.dumps(staging_validation), encoding="utf-8")
    gate_preview_path.write_text(json.dumps(gate_preview), encoding="utf-8")
    gate_validation_path.write_text(json.dumps(gate_validation), encoding="utf-8")
    input_path.write_text(json.dumps(split_engine_input_preview), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_split_post_staging_gate_check_preview.py"),
            "--next-stage-contract",
            str(contract_path),
            "--staging-preview",
            str(staging_preview_path),
            "--staging-validation",
            str(staging_validation_path),
            "--gate-preview",
            str(gate_preview_path),
            "--gate-validation",
            str(gate_validation_path),
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
    assert payload["status"] == "blocked_report_emitted"
    assert payload["stage"]["stage_id"] == "cv_fold_export_unlock_gate_check"
    assert payload["gate_check"]["cv_fold_export_unlocked"] is False
    assert payload["staging_parity"]["assignment_count"] == 1889
    assert payload["blocked_report"]["blocked"] is True
    assert "Split Post-Staging Gate Check Preview" in output_md.read_text(encoding="utf-8")
