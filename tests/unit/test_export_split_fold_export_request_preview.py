from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_split_fold_export_request_preview(tmp_path: Path) -> None:
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
                "purpose": "emit a request manifest",
                "must_hold": ["run_scoped_only remains true"],
                "today_status": "blocked today",
            }
        ],
    }
    post_staging_gate_check_preview = {
        "stage": {"stage_id": "cv_fold_export_unlock_gate_check"},
        "gate_check": {
            "gate_status": "blocked_pending_unlock",
            "cv_fold_export_unlocked": False,
        },
        "staging_parity": {
            "staging_status": "blocked_report_emitted",
            "staging_validation_status": "aligned",
        },
        "blocked_report": {
            "blocked_reasons": [
                "fold_export_ready=false",
                "cv_folds_materialized=false",
                "final_split_committed=false",
            ],
            "cv_folds_materialized": False,
            "final_split_committed": False,
        },
    }
    post_staging_gate_check_validation = {
        "status": "aligned",
        "validation": {"issues": []},
    }
    staging_preview = {
        "staging_manifest": {
            "split_group_counts": {"train": 1, "val": 1, "test": 9},
            "row_level_split_counts": {"train": 1440, "val": 266, "test": 183},
            "largest_groups": [
                {"linked_group_id": "protein:P04637", "split_name": "train", "entity_count": 1440}
            ],
        }
    }
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
    gate_check_preview_path = tmp_path / "gate_check_preview.json"
    gate_check_validation_path = tmp_path / "gate_check_validation.json"
    staging_preview_path = tmp_path / "staging_preview.json"
    split_engine_input_path = tmp_path / "split_engine_input.json"
    output_json = tmp_path / "request_preview.json"
    output_md = tmp_path / "request_preview.md"
    contract_path.write_text(json.dumps(impl_order_contract), encoding="utf-8")
    gate_check_preview_path.write_text(
        json.dumps(post_staging_gate_check_preview),
        encoding="utf-8",
    )
    gate_check_validation_path.write_text(
        json.dumps(post_staging_gate_check_validation),
        encoding="utf-8",
    )
    staging_preview_path.write_text(json.dumps(staging_preview), encoding="utf-8")
    split_engine_input_path.write_text(
        json.dumps(split_engine_input_preview),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_split_fold_export_request_preview.py"),
            "--impl-order-contract",
            str(contract_path),
            "--post-staging-gate-check-preview",
            str(gate_check_preview_path),
            "--post-staging-gate-check-validation",
            str(gate_check_validation_path),
            "--staging-preview",
            str(staging_preview_path),
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
    assert payload["status"] == "blocked_report_emitted"
    assert payload["stage"]["stage_id"] == "run_scoped_fold_export_request"
    assert payload["request_binding"]["candidate_row_count"] == 1889
    assert payload["blocked_report"]["blocked"] is True
    assert (
        payload["truth_boundary"]["request_only_no_fold_materialization"] is True
    )
    assert "Split Fold Export Request Preview" in output_md.read_text(encoding="utf-8")
