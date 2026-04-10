from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.export_duplicate_cleanup_first_execution_batch_manifest import (
    build_duplicate_cleanup_first_execution_batch_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_duplicate_cleanup_first_execution_batch_manifest(tmp_path: Path) -> None:
    checklist = {
        "report_only": True,
        "current_boundary": {
            "mode": "report_only_no_delete",
            "truth_boundary": {
                "report_only": True,
                "delete_enabled": False,
                "latest_surfaces_mutated": False,
            },
        },
        "first_authorized_execution_shape": {
            "batch_size_limit": 1,
            "batch_shape": "one exact-match removal action from same_release_local_copy_duplicates",
            "current_plan_exemplar": {
                "duplicate_class": "exact_duplicate_same_release",
                "sha256": "00001ec3860210cc78ffa8606b2f316a2bfe4d6130988446c79ffa3b74e7fa00",
                "keeper_path": "data\\raw\\local_copies\\raw\\rcsb\\5I25.json",
                "removal_path": "data\\raw\\local_copies\\raw_rcsb\\5I25.json",
                "reclaimable_bytes": 3116,
            },
        },
        "operator_summary": {
            "status": "not_yet_executable_today",
        },
    }
    executor_status = {
        "mode": "report_only_no_delete",
        "status": "usable_with_notes",
        "validation": {"status": "passed"},
    }
    dry_run_plan = {
        "plan_id": "duplicate-cleanup-dry-run-plan",
        "generated_at": "2026-04-01T16:17:47.577796+00:00",
        "allowed_cohorts": [
            "local_archive_equivalents",
            "same_release_local_copy_duplicates",
            "seed_vs_local_copy_duplicates",
        ],
        "action_count": 1,
        "actions": [
            {
                "cohort_name": "same_release_local_copy_duplicates",
                "duplicate_class": "exact_duplicate_same_release",
                "sha256": "00001ec3860210cc78ffa8606b2f316a2bfe4d6130988446c79ffa3b74e7fa00",
                "keeper_path": "data\\raw\\local_copies\\raw\\rcsb\\5I25.json",
                "removal_paths": ["data\\raw\\local_copies\\raw_rcsb\\5I25.json"],
                "reclaimable_bytes": 3116,
                "validation_gates": [
                    "exact_sha256_match",
                    "no_protected_paths",
                    "no_partial_paths",
                    "no_latest_surface_rewrites",
                ],
            }
        ],
    }

    checklist_path = tmp_path / "checklist.json"
    executor_path = tmp_path / "executor.json"
    plan_path = tmp_path / "plan.json"
    output_json = tmp_path / "manifest.json"
    output_md = tmp_path / "manifest.md"
    checklist_path.write_text(json.dumps(checklist), encoding="utf-8")
    executor_path.write_text(json.dumps(executor_status), encoding="utf-8")
    plan_path.write_text(json.dumps(dry_run_plan), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(
                REPO_ROOT
                / "scripts"
                / "export_duplicate_cleanup_first_execution_batch_manifest.py"
            ),
            "--checklist",
            str(checklist_path),
            "--executor-status",
            str(executor_path),
            "--dry-run-plan",
            str(plan_path),
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
    assert payload["status"] == "report_only"
    assert payload["batch_manifest_status"] == "preview_frozen_not_authorized"
    assert payload["batch_identity"]["batch_size_limit"] == 1
    assert payload["frozen_action"]["keeper_path"].endswith("5I25.json")
    assert payload["truth_boundary"]["delete_enabled"] is False
    assert payload["truth_boundary"]["mutation_allowed"] is False
    assert "same_release_local_copy_duplicates" in output_md.read_text(encoding="utf-8")


def test_build_duplicate_cleanup_first_execution_batch_manifest_fails_on_plan_drift() -> None:
    checklist = {
        "report_only": True,
        "current_boundary": {
            "mode": "report_only_no_delete",
            "truth_boundary": {
                "report_only": True,
                "delete_enabled": False,
                "latest_surfaces_mutated": False,
            },
        },
        "first_authorized_execution_shape": {
            "batch_size_limit": 1,
            "batch_shape": "one exact-match removal action from same_release_local_copy_duplicates",
            "current_plan_exemplar": {
                "duplicate_class": "exact_duplicate_same_release",
                "sha256": "00001ec3860210cc78ffa8606b2f316a2bfe4d6130988446c79ffa3b74e7fa00",
                "keeper_path": "data\\raw\\local_copies\\raw\\rcsb\\5I25.json",
                "removal_path": "data\\raw\\local_copies\\raw_rcsb\\5I25.json",
                "reclaimable_bytes": 3116,
            },
        },
        "operator_summary": {
            "status": "not_yet_executable_today",
        },
    }
    executor_status = {
        "mode": "report_only_no_delete",
        "status": "usable_with_notes",
        "validation": {"status": "passed"},
    }
    dry_run_plan = {
        "plan_id": "duplicate-cleanup-dry-run-plan",
        "generated_at": "2026-04-01T16:17:47.577796+00:00",
        "allowed_cohorts": [
            "local_archive_equivalents",
            "same_release_local_copy_duplicates",
            "seed_vs_local_copy_duplicates",
        ],
        "action_count": 1,
        "actions": [
            {
                "cohort_name": "same_release_local_copy_duplicates",
                "duplicate_class": "exact_duplicate_same_release",
                "sha256": "drifted",
                "keeper_path": "data\\raw\\local_copies\\raw\\rcsb\\DIFF.json",
                "removal_paths": ["data\\raw\\local_copies\\raw_rcsb\\DIFF.json"],
                "reclaimable_bytes": 1,
                "validation_gates": [
                    "exact_sha256_match",
                    "no_protected_paths",
                    "no_partial_paths",
                    "no_latest_surface_rewrites",
                ],
            }
        ],
    }

    payload = build_duplicate_cleanup_first_execution_batch_manifest(
        checklist,
        executor_status,
        dry_run_plan,
    )

    assert payload["batch_manifest_status"] == "blocked"
    assert payload["validation"]["status"] == "failed"
    assert payload["plan_alignment"]["first_action_matches_exemplar"] is False
    assert "plan_first_action_mismatch" in payload["validation"]["errors"]
