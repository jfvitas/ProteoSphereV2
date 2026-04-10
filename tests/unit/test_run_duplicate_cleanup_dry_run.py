from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_run_duplicate_cleanup_dry_run_emits_status_and_plan(tmp_path: Path) -> None:
    inventory_path = tmp_path / "duplicate_storage_inventory.json"
    status_path = tmp_path / "duplicate_cleanup_status.json"
    inventory_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-01T00:00:00+00:00",
                "summary": {
                    "scanned_root_count": 1,
                    "scanned_file_count": 2,
                    "duplicate_group_count": 1,
                    "duplicate_file_count": 2,
                    "reclaimable_file_count": 1,
                    "reclaimable_bytes": 10,
                    "partial_file_count": 0,
                    "protected_file_count": 0,
                },
                "duplicate_groups": [
                    {
                        "duplicate_class": "exact_duplicate_same_release",
                        "sha256": "abc",
                        "reclaimable": True,
                        "reclaimable_bytes": 10,
                        "files": [
                            {"relative_path": "data\\raw\\local_copies\\foo\\a.txt"},
                            {"relative_path": "data\\raw\\local_copies\\foo\\b.txt"},
                        ],
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    status_path.write_text(
        json.dumps(
            {
                "inventory_summary": {
                    "scanned_root_count": 1,
                    "scanned_file_count": 2,
                    "duplicate_group_count": 1,
                    "duplicate_file_count": 2,
                    "reclaimable_file_count": 1,
                    "reclaimable_bytes": 10,
                    "partial_file_count": 0,
                    "protected_file_count": 0,
                },
                "safe_first_cleanup_cohorts": [
                    {"cohort_name": "same_release_local_copy_duplicates"}
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    plan_json = tmp_path / "plan.json"
    plan_md = tmp_path / "plan.md"
    status_json = tmp_path / "status.json"
    status_md = tmp_path / "status.md"

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "run_duplicate_cleanup_dry_run.py"),
            "--inventory-json",
            str(inventory_path),
            "--status-json",
            str(status_path),
            "--plan-json",
            str(plan_json),
            "--plan-md",
            str(plan_md),
            "--status-output-json",
            str(status_json),
            "--status-output-md",
            str(status_md),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    status_payload = json.loads(status_json.read_text(encoding="utf-8"))
    plan_payload = json.loads(plan_json.read_text(encoding="utf-8"))
    assert status_payload["mode"] == "report_only_no_delete"
    assert status_payload["validation"]["status"] == "passed"
    assert plan_payload["action_count"] == 1
    assert plan_payload["allowed_cohorts"] == ["same_release_local_copy_duplicates"]
