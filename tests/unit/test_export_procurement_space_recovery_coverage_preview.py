from __future__ import annotations

from scripts.export_procurement_space_recovery_coverage_preview import (
    GIB,
    build_procurement_space_recovery_coverage_preview,
)


def test_recovery_coverage_reports_short_ranked_lane() -> None:
    payload = build_procurement_space_recovery_coverage_preview(
        {
            "summary": {
                "reclaim_to_zero_bytes": 5 * GIB,
                "reclaim_to_10_gib_buffer_bytes": 6 * GIB,
                "reclaim_to_20_gib_buffer_bytes": 7 * GIB,
            }
        },
        {
            "batches": {
                "zero_gap_batch": {"cumulative_reclaim_bytes": 4 * GIB},
                "buffer_10_gib_batch": {"cumulative_reclaim_bytes": 4 * GIB},
                "buffer_20_gib_batch": {"cumulative_reclaim_bytes": 4 * GIB},
            }
        },
    )

    assert payload["summary"]["coverage_state"] == "ranked_lane_short_of_zero_gap"
    assert payload["summary"]["zero_gap_coverage_fraction"] == 0.8


def test_recovery_coverage_reports_zero_gap_covered() -> None:
    payload = build_procurement_space_recovery_coverage_preview(
        {
            "summary": {
                "reclaim_to_zero_bytes": 3 * GIB,
                "reclaim_to_10_gib_buffer_bytes": 4 * GIB,
                "reclaim_to_20_gib_buffer_bytes": 5 * GIB,
            }
        },
        {
            "batches": {
                "zero_gap_batch": {"cumulative_reclaim_bytes": 3 * GIB},
                "buffer_10_gib_batch": {"cumulative_reclaim_bytes": 3 * GIB},
                "buffer_20_gib_batch": {"cumulative_reclaim_bytes": 3 * GIB},
            }
        },
    )

    assert payload["summary"]["coverage_state"] == "zero_gap_covered"
    assert payload["summary"]["zero_gap_shortfall_gib"] == 0.0
