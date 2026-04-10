from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.export_duplicate_cleanup_delete_ready_first_batch_manifest import (
    build_duplicate_cleanup_delete_ready_first_batch_manifest,
    render_markdown,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_build_duplicate_cleanup_delete_ready_first_batch_manifest(tmp_path: Path) -> None:
    first_batch_manifest = {
        "status": "report_only",
        "batch_identity": {
            "batch_size_limit": 1,
            "batch_shape": "one exact-match removal action from same_release_local_copy_duplicates",
            "cohort_name": "same_release_local_copy_duplicates",
            "plan_id": "duplicate-cleanup-dry-run-plan",
            "plan_action_index": 0,
            "action_count": 100,
        },
        "frozen_action": {
            "duplicate_class": "exact_duplicate_same_release",
            "sha256": "00001ec3860210cc78ffa8606b2f316a2bfe4d6130988446c79ffa3b74e7fa00",
            "keeper_path": "data\\raw\\local_copies\\raw\\rcsb\\5I25.json",
            "removal_path": "data\\raw\\local_copies\\raw_rcsb\\5I25.json",
            "reclaimable_bytes": 3116,
            "validation_gates": [
                "exact_sha256_match",
                "no_protected_paths",
                "no_partial_paths",
                "no_latest_surface_rewrites",
            ],
        },
    }
    real_execution_blocker = {
        "answer": {
            "safe_to_execute_today": False,
            "delete_ready_manifest_emitted": False,
        },
        "current_first_batch": {
            "duplicate_class": "exact_duplicate_same_release",
            "sha256": "00001ec3860210cc78ffa8606b2f316a2bfe4d6130988446c79ffa3b74e7fa00",
            "keeper_path": "data\\raw\\local_copies\\raw\\rcsb\\5I25.json",
            "removal_path": "data\\raw\\local_copies\\raw_rcsb\\5I25.json",
            "reclaimable_bytes": 3116,
            "validation_gates": [
                "exact_sha256_match",
                "no_protected_paths",
                "no_partial_paths",
                "no_latest_surface_rewrites",
            ],
        },
        "unmet_conditions": [
            {"rank": 1, "condition_id": "mutation_authorization_missing"},
            {"rank": 2, "condition_id": "approval_boundary_not_recorded"},
        ],
    }
    verification_contract = {
        "post_mutation_verification_contract": {
            "minimum_checks": [
                {"rank": 1, "check": "Refresh the inventory after mutation."},
                {"rank": 2, "check": "Reconcile the approved delta."},
            ]
        },
        "acceptance_standard": {
            "status": "not_yet_passable",
            "summary": "future destructive cleanup can only be accepted if the final filesystem state matches exactly.",
            "what_success_requires": ["approved files were removed and nothing else was removed"],
        },
    }

    payload = build_duplicate_cleanup_delete_ready_first_batch_manifest(
        first_batch_manifest,
        real_execution_blocker,
        verification_contract,
    )

    assert payload["status"] == "report_only"
    assert payload["surface_state"]["delete_enabled"] is False
    assert payload["surface_state"]["safe_to_execute_today"] is False
    assert payload["delete_ready_manifest"]["delete_ready_manifest_emitted"] is True
    assert payload["delete_ready_manifest"]["batch_size_limit"] == 1
    assert payload["delete_ready_manifest"]["cohort_name"] == "same_release_local_copy_duplicates"
    assert payload["real_execution_blocker_alignment"]["delete_ready_manifest_emitted"] is False
    assert payload["validation"]["status"] == "passed"
    assert len(payload["post_delete_verification_contract_scaffold"]["minimum_checks"]) == 2

    markdown = render_markdown(payload)
    assert "# Duplicate Cleanup Delete-Ready First Batch Manifest" in markdown
    assert "Post-Delete Verification Scaffold" in markdown
    assert "same_release_local_copy_duplicates" in markdown


def test_export_duplicate_cleanup_delete_ready_first_batch_manifest_cli(tmp_path: Path) -> None:
    first_batch_manifest = {
        "status": "report_only",
        "batch_identity": {
            "batch_size_limit": 1,
            "batch_shape": "one exact-match removal action from same_release_local_copy_duplicates",
            "cohort_name": "same_release_local_copy_duplicates",
            "plan_id": "duplicate-cleanup-dry-run-plan",
            "plan_action_index": 0,
            "action_count": 100,
        },
        "frozen_action": {
            "duplicate_class": "exact_duplicate_same_release",
            "sha256": "00001ec3860210cc78ffa8606b2f316a2bfe4d6130988446c79ffa3b74e7fa00",
            "keeper_path": "data\\raw\\local_copies\\raw\\rcsb\\5I25.json",
            "removal_path": "data\\raw\\local_copies\\raw_rcsb\\5I25.json",
            "reclaimable_bytes": 3116,
            "validation_gates": [
                "exact_sha256_match",
                "no_protected_paths",
                "no_partial_paths",
                "no_latest_surface_rewrites",
            ],
        },
    }
    blocker = {
        "answer": {
            "safe_to_execute_today": False,
            "delete_ready_manifest_emitted": False,
        },
        "current_first_batch": {
            "duplicate_class": "exact_duplicate_same_release",
            "sha256": "00001ec3860210cc78ffa8606b2f316a2bfe4d6130988446c79ffa3b74e7fa00",
            "keeper_path": "data\\raw\\local_copies\\raw\\rcsb\\5I25.json",
            "removal_path": "data\\raw\\local_copies\\raw_rcsb\\5I25.json",
            "reclaimable_bytes": 3116,
            "validation_gates": [
                "exact_sha256_match",
                "no_protected_paths",
                "no_partial_paths",
                "no_latest_surface_rewrites",
            ],
        },
        "unmet_conditions": [],
    }
    verification_contract = {
        "post_mutation_verification_contract": {
            "minimum_checks": [
                {"rank": 1, "check": "Refresh the inventory after mutation."},
            ]
        },
        "acceptance_standard": {"status": "not_yet_passable"},
    }

    first_batch_path = tmp_path / "p86.json"
    blocker_path = tmp_path / "p87.json"
    contract_path = tmp_path / "p64.json"
    output_json = tmp_path / "p90.json"
    output_md = tmp_path / "p90.md"
    first_batch_path.write_text(json.dumps(first_batch_manifest), encoding="utf-8")
    blocker_path.write_text(json.dumps(blocker), encoding="utf-8")
    contract_path.write_text(json.dumps(verification_contract), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(
                REPO_ROOT
                / "scripts"
                / "export_duplicate_cleanup_delete_ready_first_batch_manifest.py"
            ),
            "--first-batch-manifest",
            str(first_batch_path),
            "--real-execution-blocker",
            str(blocker_path),
            "--post-delete-verification-contract",
            str(contract_path),
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
    assert payload["delete_ready_manifest"]["delete_ready_manifest_emitted"] is True
    assert payload["truth_boundary"]["delete_enabled"] is False
    assert payload["truth_boundary"]["mutation_allowed"] is False
    assert "delete_ready_manifest_surface" in output_md.read_text(encoding="utf-8")
