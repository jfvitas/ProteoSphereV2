from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_split_fold_export_gate_preview(tmp_path: Path) -> None:
    gate_contract = {
        "fold_export_gate": {
            "gate_id": "cv_fold_export_unlock_gate",
            "gate_surface": "split_engine_input_preview",
            "unlock_intent": "unlock only after dry-run parity is proven",
            "current_state": {
                "ready_for_split_engine_dry_run": True,
                "fold_export_ready": False,
                "cv_folds_materialized": False,
                "final_split_committed": False,
            },
            "required_unlock_conditions": [
                {"condition_id": "dry_run_alignment"},
                {"condition_id": "preview_parity"},
            ],
            "blocked_today_reason": "gate remains closed",
        }
    }
    split_engine_input_preview = {
        "execution_readiness": {
            "next_unlocked_stage": "split_engine_dry_run",
        },
        "assignment_binding": {
            "group_row_count": 3,
            "candidate_row_count": 29,
            "assignment_count": 29,
        },
        "truth_boundary": {
            "cv_folds_materialized": False,
            "final_split_committed": False,
        },
    }
    split_engine_dry_run_validation = {
        "status": "aligned",
        "validation": {
            "issues": [],
            "matches": ["candidate_row_count", "assignment_count"],
            "candidate_row_count": 29,
            "assignment_count": 29,
            "split_group_counts": {"train": 1, "val": 1, "test": 2},
            "row_level_split_counts": {"train": 10, "val": 8, "test": 11},
            "largest_groups": [
                {"linked_group_id": "protein:P04637", "split_name": "train", "entity_count": 10}
            ],
        },
    }

    contract_path = tmp_path / "p68_split_fold_export_gate_contract.json"
    input_path = tmp_path / "split_engine_input_preview.json"
    validation_path = tmp_path / "split_engine_dry_run_validation.json"
    output_json = tmp_path / "split_fold_export_gate_preview.json"
    output_md = tmp_path / "split_fold_export_gate_preview.md"
    contract_path.write_text(json.dumps(gate_contract), encoding="utf-8")
    input_path.write_text(json.dumps(split_engine_input_preview), encoding="utf-8")
    validation_path.write_text(json.dumps(split_engine_dry_run_validation), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_split_fold_export_gate_preview.py"),
            "--gate-contract",
            str(contract_path),
            "--split-engine-input-preview",
            str(input_path),
            "--split-engine-dry-run-validation",
            str(validation_path),
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
    assert payload["status"] == "blocked_pending_unlock"
    assert payload["gate"]["gate_id"] == "cv_fold_export_unlock_gate"
    assert payload["validation_snapshot"]["dry_run_validation_status"] == "aligned"
    assert payload["validation_snapshot"]["candidate_row_count"] == 29
    assert payload["unlock_readiness"]["cv_fold_export_unlocked"] is False
    assert "fold_export_ready=false" in payload["unlock_readiness"]["blocked_reasons"]
    assert "Split Fold Export Gate Preview" in output_md.read_text(encoding="utf-8")
