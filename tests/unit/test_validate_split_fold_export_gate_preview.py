from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_validate_split_fold_export_gate_preview(tmp_path: Path) -> None:
    gate_preview = {
        "status": "blocked_pending_unlock",
        "gate": {
            "required_condition_count": 4,
        },
        "validation_snapshot": {
            "dry_run_validation_status": "aligned",
            "dry_run_issue_count": 0,
            "candidate_row_count": 29,
            "assignment_count": 29,
            "split_group_counts": {"train": 1, "val": 1, "test": 2},
            "row_level_split_counts": {"train": 10, "val": 8, "test": 11},
            "largest_groups": [
                {"linked_group_id": "protein:P04637", "split_name": "train", "entity_count": 10}
            ],
        },
        "execution_snapshot": {
            "candidate_row_count": 29,
            "assignment_count": 29,
            "cv_folds_materialized": False,
            "final_split_committed": False,
        },
        "unlock_readiness": {
            "cv_fold_export_unlocked": False,
            "ready_for_fold_export": False,
            "blocked_reasons": [
                "fold_export_ready=false",
                "cv_folds_materialized=false",
                "final_split_committed=false",
            ],
        },
    }
    split_input = {
        "assignment_binding": {
            "candidate_row_count": 29,
            "assignment_count": 29,
        },
        "truth_boundary": {
            "cv_folds_materialized": False,
        },
    }
    dry_run = {
        "status": "aligned",
        "validation": {
            "candidate_row_count": 29,
            "assignment_count": 29,
            "split_group_counts": {"train": 1, "val": 1, "test": 2},
            "row_level_split_counts": {"train": 10, "val": 8, "test": 11},
            "largest_groups": [
                {"linked_group_id": "protein:P04637", "split_name": "train", "entity_count": 10}
            ],
        },
        "truth_boundary": {
            "final_split_committed": False,
        },
    }

    gate_path = tmp_path / "split_fold_export_gate_preview.json"
    input_path = tmp_path / "split_engine_input_preview.json"
    dry_run_path = tmp_path / "split_engine_dry_run_validation.json"
    output_json = tmp_path / "split_fold_export_gate_validation.json"
    output_md = tmp_path / "split_fold_export_gate_validation.md"
    gate_path.write_text(json.dumps(gate_preview), encoding="utf-8")
    input_path.write_text(json.dumps(split_input), encoding="utf-8")
    dry_run_path.write_text(json.dumps(dry_run), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "validate_split_fold_export_gate_preview.py"),
            "--split-fold-export-gate-preview",
            str(gate_path),
            "--split-engine-input-preview",
            str(input_path),
            "--split-engine-dry-run-validation",
            str(dry_run_path),
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
    assert payload["validation"]["candidate_row_count"] == 29
    assert payload["validation"]["dry_run_issue_count"] == 0
    assert payload["truth_boundary"]["cv_fold_export_unlocked"] is False
    assert "Split Fold Export Gate Validation" in output_md.read_text(encoding="utf-8")
