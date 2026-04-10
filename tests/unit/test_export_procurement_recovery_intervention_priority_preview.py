from __future__ import annotations

from scripts.export_procurement_recovery_intervention_priority_preview import (
    build_procurement_recovery_intervention_priority_preview,
)


def test_intervention_priority_reports_urgent_duplicate_first_review() -> None:
    payload = build_procurement_recovery_intervention_priority_preview(
        {"summary": {"risk_state": "zero_before_completion", "cushion_hours": -3.0}},
        {"summary": {"trigger_state": "ranked_batch_insufficient_escalate"}},
        {"summary": {"safety_state": "duplicate_first_safety_lane_available"}},
        {"summary": {"drift_state": "gap_widening", "current_zero_gap_shortfall_gib": 2.0}},
    )

    assert payload["summary"]["priority_state"] == "urgent_expand_duplicate_first_review"


def test_intervention_priority_reports_monitor_only() -> None:
    payload = build_procurement_recovery_intervention_priority_preview(
        {"summary": {"risk_state": "completion_before_zero", "cushion_hours": 2.0}},
        {"summary": {"trigger_state": "prepare_recovery_review"}},
        {"summary": {"safety_state": "duplicate_first_safety_lane_available"}},
        {"summary": {"drift_state": "gap_flat", "current_zero_gap_shortfall_gib": 1.0}},
    )

    assert payload["summary"]["priority_state"] == "monitor_only"
