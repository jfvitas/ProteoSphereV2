from __future__ import annotations

from scripts.export_procurement_recovery_lane_fragility_preview import (
    build_procurement_recovery_lane_fragility_preview,
)


def test_lane_fragility_reports_lead_candidate_covers_shortfall() -> None:
    payload = build_procurement_recovery_lane_fragility_preview(
        {
            "summary": {"total_ranked_reclaim_gib": 10.0},
            "rows": [
                {"filename": "a.bin", "reclaim_gib_if_removed": 6.0},
                {"filename": "b.bin", "reclaim_gib_if_removed": 2.0},
            ],
        },
        {"summary": {"zero_gap_shortfall_gib": 5.0}},
    )

    assert payload["summary"]["fragility_state"] == "lead_candidate_covers_shortfall"


def test_lane_fragility_reports_lane_breaks_without_lead() -> None:
    payload = build_procurement_recovery_lane_fragility_preview(
        {
            "summary": {"total_ranked_reclaim_gib": 10.0},
            "rows": [
                {"filename": "a.bin", "reclaim_gib_if_removed": 4.0},
                {"filename": "b.bin", "reclaim_gib_if_removed": 3.0},
                {"filename": "c.bin", "reclaim_gib_if_removed": 3.0},
            ],
        },
        {"summary": {"zero_gap_shortfall_gib": 7.0}},
    )

    assert payload["summary"]["fragility_state"] == "lane_breaks_without_lead"
