from __future__ import annotations

from scripts.export_procurement_space_recovery_execution_batch_preview import (
    GIB,
    build_procurement_space_recovery_execution_batch_preview,
)


def test_execution_batch_preview_reports_zero_gap_only_lane() -> None:
    payload = build_procurement_space_recovery_execution_batch_preview(
        {
            "summary": {
                "reclaim_to_zero_bytes": 25 * GIB,
                "reclaim_to_10_gib_buffer_bytes": 35 * GIB,
                "reclaim_to_20_gib_buffer_bytes": 45 * GIB,
            }
        },
        {
            "summary": {"ranked_candidate_count": 2},
            "rows": [
                {
                    "path": "D:/a",
                    "filename": "a.tar.gz",
                    "reason": "duplicate_name_and_size_detected",
                    "safety_tier": "better_candidate",
                    "reclaim_bytes_if_removed": 20 * GIB,
                    "reclaim_gib_if_removed": 20.0,
                    "size_gib": 20.0,
                },
                {
                    "path": "D:/b",
                    "filename": "b.tar.gz",
                    "reason": "duplicate_name_and_size_detected",
                    "safety_tier": "better_candidate",
                    "reclaim_bytes_if_removed": 10 * GIB,
                    "reclaim_gib_if_removed": 10.0,
                    "size_gib": 10.0,
                },
            ],
        },
    )

    assert payload["summary"]["execution_state"] == "zero_gap_batch_available_only"
    assert payload["summary"]["zero_gap_batch_meets_target"] is True
    assert payload["summary"]["buffer_10_gib_batch_meets_target"] is False


def test_execution_batch_preview_handles_empty_candidates() -> None:
    payload = build_procurement_space_recovery_execution_batch_preview(
        {"summary": {}},
        {"summary": {}, "rows": []},
    )

    assert payload["summary"]["execution_state"] == "no_execution_batches_available"
    assert payload["batches"]["zero_gap_batch"]["selected_candidate_count"] == 0
