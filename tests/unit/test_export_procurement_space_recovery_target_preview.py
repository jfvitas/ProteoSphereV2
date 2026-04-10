from __future__ import annotations

from scripts.export_procurement_space_recovery_target_preview import (
    GIB,
    build_procurement_space_recovery_target_preview,
)


def test_space_recovery_target_preview_reports_substantial_need() -> None:
    payload = build_procurement_space_recovery_target_preview(
        {
            "summary": {
                "free_bytes": 10 * GIB,
                "total_remaining_bytes": 30 * GIB,
                "projected_free_after_completion_bytes": -20 * GIB,
            }
        }
    )

    assert payload["summary"]["target_state"] == "substantial_recovery_required"
    assert payload["summary"]["reclaim_to_zero_bytes"] == 20 * GIB
    assert payload["summary"]["reclaim_to_20_gib_buffer_bytes"] == 40 * GIB


def test_space_recovery_target_preview_reports_no_recovery_needed() -> None:
    payload = build_procurement_space_recovery_target_preview(
        {
            "summary": {
                "free_bytes": 50 * GIB,
                "total_remaining_bytes": 10 * GIB,
                "projected_free_after_completion_bytes": 40 * GIB,
            }
        }
    )

    assert payload["summary"]["target_state"] == "no_recovery_required"
    assert payload["summary"]["reclaim_to_zero_bytes"] == 0
