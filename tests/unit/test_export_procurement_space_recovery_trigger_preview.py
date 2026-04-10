from __future__ import annotations

from scripts.export_procurement_space_recovery_trigger_preview import (
    build_procurement_space_recovery_trigger_preview,
)


def test_recovery_trigger_reports_immediate_when_zero_gap_batch_available() -> None:
    payload = build_procurement_space_recovery_trigger_preview(
        {"summary": {"risk_state": "zero_before_completion"}},
        {
            "summary": {
                "execution_state": "zero_gap_batch_available_only",
                "zero_gap_batch_meets_target": True,
            }
        },
        {"summary": {"reclaim_to_zero_gib": 5.0}},
    )

    assert payload["summary"]["trigger_state"] == "recovery_trigger_immediate"


def test_recovery_trigger_reports_escalate_when_ranked_batch_is_short() -> None:
    payload = build_procurement_space_recovery_trigger_preview(
        {"summary": {"risk_state": "zero_before_completion"}},
        {
            "summary": {
                "execution_state": "insufficient_ranked_capacity",
                "zero_gap_batch_meets_target": False,
            }
        },
        {"summary": {"reclaim_to_zero_gib": 42.0}},
    )

    assert payload["summary"]["trigger_state"] == "ranked_batch_insufficient_escalate"
