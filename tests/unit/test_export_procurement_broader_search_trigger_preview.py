from __future__ import annotations

from scripts.export_procurement_broader_search_trigger_preview import (
    build_procurement_broader_search_trigger_preview,
)


def test_broader_search_trigger_reports_immediate() -> None:
    payload = build_procurement_broader_search_trigger_preview(
        {"summary": {"risk_state": "zero_before_completion", "cushion_hours": -2.5}},
        {
            "summary": {
                "bridge_state": "no_bridge_inside_current_universe",
                "zero_gap_shortfall_gib": 4.0,
            }
        },
    )

    assert payload["summary"]["trigger_state"] == "broader_search_immediate"


def test_broader_search_trigger_reports_manual_review_first() -> None:
    payload = build_procurement_broader_search_trigger_preview(
        {"summary": {"risk_state": "zero_before_completion", "cushion_hours": -2.5}},
        {
            "summary": {
                "bridge_state": "manual_review_bridge_possible",
                "zero_gap_shortfall_gib": 4.0,
            }
        },
    )

    assert payload["summary"]["trigger_state"] == "manual_review_before_broader_search"
