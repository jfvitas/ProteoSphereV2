from __future__ import annotations

from scripts.export_procurement_recovery_escalation_lane_preview import (
    build_procurement_recovery_escalation_lane_preview,
)


def test_escalation_lane_reports_ranked_duplicate_lane_exhausted() -> None:
    payload = build_procurement_recovery_escalation_lane_preview(
        {"summary": {"ranked_candidate_count": 15, "total_ranked_reclaim_gib": 41.802}},
        {
            "summary": {"execution_state": "insufficient_ranked_capacity"},
            "batches": {"zero_gap_batch": {"cumulative_reclaim_gib": 41.802}},
        },
        {"summary": {"review_required_category_count": 0, "duplicate_first_category_count": 15}},
        {
            "summary": {
                "coverage_state": "ranked_lane_short_of_zero_gap",
                "zero_gap_shortfall_gib": 3.0,
            }
        },
    )

    assert payload["summary"]["escalation_state"] == "ranked_duplicate_lane_exhausted"


def test_escalation_lane_reports_manual_review_available() -> None:
    payload = build_procurement_recovery_escalation_lane_preview(
        {"summary": {"ranked_candidate_count": 15, "total_ranked_reclaim_gib": 41.802}},
        {
            "summary": {"execution_state": "insufficient_ranked_capacity"},
            "batches": {"zero_gap_batch": {"cumulative_reclaim_gib": 41.802}},
        },
        {"summary": {"review_required_category_count": 2, "duplicate_first_category_count": 13}},
        {
            "summary": {
                "coverage_state": "ranked_lane_short_of_zero_gap",
                "zero_gap_shortfall_gib": 3.0,
            }
        },
    )

    assert payload["summary"]["escalation_state"] == "manual_review_lane_available"
