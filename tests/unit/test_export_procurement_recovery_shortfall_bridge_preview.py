from __future__ import annotations

from scripts.export_procurement_recovery_shortfall_bridge_preview import (
    build_procurement_recovery_shortfall_bridge_preview,
)


def test_shortfall_bridge_reports_no_bridge_inside_current_universe() -> None:
    payload = build_procurement_recovery_shortfall_bridge_preview(
        {"summary": {"zero_gap_shortfall_gib": 4.0}},
        {
            "summary": {
                "escalation_state": "ranked_duplicate_lane_exhausted",
                "additional_ranked_reclaim_gib": 0.0,
            }
        },
        {"summary": {"review_required_category_count": 0}},
    )

    assert payload["summary"]["bridge_state"] == "no_bridge_inside_current_universe"


def test_shortfall_bridge_reports_manual_review_bridge_possible() -> None:
    payload = build_procurement_recovery_shortfall_bridge_preview(
        {"summary": {"zero_gap_shortfall_gib": 4.0}},
        {
            "summary": {
                "escalation_state": "manual_review_lane_available",
                "additional_ranked_reclaim_gib": 0.0,
            }
        },
        {"summary": {"review_required_category_count": 2}},
    )

    assert payload["summary"]["bridge_state"] == "manual_review_bridge_possible"
