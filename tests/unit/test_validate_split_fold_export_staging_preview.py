from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_validate_split_fold_export_staging_preview(tmp_path: Path) -> None:
    staging_contract = {
        "staging_surface": {
            "stage_id": "run_scoped_fold_export_staging",
            "surface_id": "split_fold_export_staging_preview",
        },
        "staging_manifest_schema": {
            "required_values": {
                "gate_id": "cv_fold_export_unlock_gate",
                "gate_surface": "split_engine_input_preview",
                "gate_status": "blocked_pending_unlock",
                "candidate_row_count": 1889,
                "assignment_count": 1889,
                "split_group_counts": {"train": 1, "val": 1, "test": 9},
                "row_level_split_counts": {"train": 1440, "val": 266, "test": 183},
                "blocked_reasons": [
                    "fold_export_ready=false",
                    "cv_folds_materialized=false",
                    "final_split_committed=false",
                ],
            }
        },
    }
    staging_preview = {
        "status": "blocked_report_emitted",
        "stage": {
            "stage_id": "run_scoped_fold_export_staging",
            "surface_id": "split_fold_export_staging_preview",
            "run_scoped_only": True,
        },
        "gate_binding": {
            "gate_id": "cv_fold_export_unlock_gate",
            "gate_surface": "split_engine_input_preview",
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
            "blocked": True,
            "blocked_reasons": [
                "fold_export_ready=false",
                "cv_folds_materialized=false",
                "final_split_committed=false",
            ],
            "validation_status": "aligned",
            "dry_run_validation_status": "aligned",
            "dry_run_issue_count": 0,
        },
        "truth_boundary": {
            "run_scoped_only": True,
            "cv_fold_export_unlocked": False,
            "cv_folds_materialized": False,
            "final_split_committed": False,
        },
    }
    gate_preview = {
        "validation_snapshot": {
            "dry_run_validation_status": "aligned",
            "largest_groups": [
                {"linked_group_id": "protein:P04637", "split_name": "train", "entity_count": 1440}
            ]
        }
    }
    gate_validation = {
        "status": "aligned",
        "validation": {
            "dry_run_validation_status": "aligned",
            "dry_run_issue_count": 0,
        },
    }
    split_engine_input_preview = {
        "assignment_binding": {
            "candidate_row_count": 1889,
            "assignment_count": 1889,
        }
    }

    contract_path = tmp_path / "contract.json"
    staging_preview_path = tmp_path / "staging_preview.json"
    gate_preview_path = tmp_path / "gate_preview.json"
    gate_validation_path = tmp_path / "gate_validation.json"
    input_path = tmp_path / "input.json"
    output_json = tmp_path / "staging_validation.json"
    output_md = tmp_path / "staging_validation.md"
    contract_path.write_text(json.dumps(staging_contract), encoding="utf-8")
    staging_preview_path.write_text(json.dumps(staging_preview), encoding="utf-8")
    gate_preview_path.write_text(json.dumps(gate_preview), encoding="utf-8")
    gate_validation_path.write_text(json.dumps(gate_validation), encoding="utf-8")
    input_path.write_text(json.dumps(split_engine_input_preview), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "validate_split_fold_export_staging_preview.py"),
            "--staging-contract",
            str(contract_path),
            "--split-fold-export-staging-preview",
            str(staging_preview_path),
            "--split-fold-export-gate-preview",
            str(gate_preview_path),
            "--split-fold-export-gate-validation",
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
    assert payload["status"] == "aligned"
    assert payload["validation"]["gate_status"] == "blocked_pending_unlock"
    assert payload["validation"]["issues"] == []
    assert payload["truth_boundary"]["cv_fold_export_unlocked"] is False
    assert "Split Fold Export Staging Validation" in output_md.read_text(encoding="utf-8")
