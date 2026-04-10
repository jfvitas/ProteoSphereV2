from __future__ import annotations

from pathlib import Path

from scripts.export_duplicate_cleanup_delete_ready_manifest_preview import (
    build_duplicate_cleanup_delete_ready_manifest_preview,
)


def test_build_duplicate_cleanup_delete_ready_manifest_preview_keeps_report_only_boundary(
    tmp_path: Path,
) -> None:
    keeper = tmp_path / "keeper.json"
    removal = tmp_path / "remove.json"
    keeper.write_text("keeper", encoding="utf-8")
    removal.write_text("removal", encoding="utf-8")

    payload = build_duplicate_cleanup_delete_ready_manifest_preview(
        {
            "plan_id": "duplicate-cleanup-dry-run-plan",
            "actions": [
                {
                    "cohort_name": "same_release_local_copy_duplicates",
                    "duplicate_class": "exact_duplicate_same_release",
                    "keeper_path": str(keeper),
                    "removal_paths": [str(removal)],
                    "sha256": "abc",
                    "reclaimable_bytes": 12,
                    "validation_gates": ["exact_sha256_match"],
                }
            ],
        },
        {"validation": {"status": "passed"}},
        {"answer": {"safe_to_execute_today": False}},
    )

    assert payload["execution_blocked"] is True
    assert payload["delete_batch"]["keeper_path"] == str(keeper)
    assert payload["constraint_checks"]["exact_duplicates_only"] is True
    assert payload["constraint_checks"]["no_partial_paths"] is True
    assert payload["constraint_checks"]["no_latest_json"] is True
    assert payload["constraint_checks"]["checksum_present"] is True
    assert payload["constraint_checks"]["all_constraints_satisfied_preview"] is True
    assert payload["truth_boundary"]["delete_enabled"] is False


def test_build_duplicate_cleanup_delete_ready_manifest_preview_marks_refresh_when_consumed(
) -> None:
    payload = build_duplicate_cleanup_delete_ready_manifest_preview(
        {
            "plan_id": "duplicate-cleanup-dry-run-plan",
            "actions": [
                {
                    "cohort_name": "same_release_local_copy_duplicates",
                    "duplicate_class": "exact_duplicate_same_release",
                    "keeper_path": "missing-keeper",
                    "removal_paths": ["missing-removal"],
                    "sha256": "abc",
                    "reclaimable_bytes": 12,
                    "validation_gates": ["exact_sha256_match"],
                }
            ],
        },
        {"validation": {"status": "passed"}},
        {"answer": {"safe_to_execute_today": False}},
    )

    assert payload["action_count"] == 0
    assert payload["preview_manifest_status"] == "no_current_valid_batch_requires_refresh"
    assert payload["constraint_checks"]["all_constraints_satisfied_preview"] is False
