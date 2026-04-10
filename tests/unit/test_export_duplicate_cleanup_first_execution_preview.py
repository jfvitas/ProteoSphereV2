from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_duplicate_cleanup_first_execution_preview(tmp_path: Path) -> None:
    checklist = {
        "first_authorized_execution_shape": {
            "batch_size_limit": 1,
            "batch_shape": "one exact-match removal action",
        }
    }
    delete_ready_manifest = {
        "artifact_id": "duplicate_cleanup_delete_ready_manifest_preview",
        "preview_manifest_status": "no_current_valid_batch_requires_refresh",
        "action_count": 0,
        "delete_batch": {
            "duplicate_class": "",
            "keeper_path": "",
            "removal_paths": [],
            "reclaimable_bytes": 0,
        },
        "truth_boundary": {
            "requires_plan_refresh_when_consumed": True,
        },
    }
    executor_status = {"validation": {"status": "passed"}}

    checklist_path = tmp_path / "checklist.json"
    delete_ready_path = tmp_path / "delete_ready.json"
    executor_path = tmp_path / "executor.json"
    output_json = tmp_path / "preview.json"
    output_md = tmp_path / "preview.md"
    checklist_path.write_text(json.dumps(checklist), encoding="utf-8")
    delete_ready_path.write_text(json.dumps(delete_ready_manifest), encoding="utf-8")
    executor_path.write_text(json.dumps(executor_status), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(
                REPO_ROOT
                / "scripts"
                / "export_duplicate_cleanup_first_execution_preview.py"
            ),
            "--checklist",
            str(checklist_path),
            "--delete-ready-manifest",
            str(delete_ready_path),
            "--executor-status",
            str(executor_path),
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
    assert payload["execution_status"] == "refresh_required_after_consumed_preview_batch"
    assert payload["preview_manifest_status"] == "no_current_valid_batch_requires_refresh"
    assert payload["batch_size_limit"] == 1
    assert payload["duplicate_class"] == ""
    assert payload["refresh_required"] is True
    assert payload["truth_boundary"]["delete_enabled"] is False
    assert "Duplicate Cleanup First Execution Preview" in output_md.read_text(
        encoding="utf-8"
    )
