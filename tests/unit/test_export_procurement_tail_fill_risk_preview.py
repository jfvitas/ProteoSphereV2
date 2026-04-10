from __future__ import annotations

from scripts.export_procurement_tail_fill_risk_preview import (
    build_procurement_tail_fill_risk_preview,
)


def test_tail_fill_risk_reports_zero_before_completion() -> None:
    payload = build_procurement_tail_fill_risk_preview(
        {
            "summary": {"free_bytes": 100},
            "rows": [
                {"estimated_hours_to_completion_at_recent_rate": 4.0},
                {"estimated_hours_to_completion_at_recent_rate": 6.0},
            ],
        },
        {
            "summary": {
                "recent_growth_bytes_per_second": 10.0,
                "estimated_hours_to_zero_free_at_recent_rate": 3.0,
            }
        },
    )

    assert payload["summary"]["risk_state"] == "zero_before_completion"
    assert payload["summary"]["slowest_completion_hours"] == 6.0


def test_tail_fill_risk_reports_completion_before_zero() -> None:
    payload = build_procurement_tail_fill_risk_preview(
        {
            "summary": {"free_bytes": 100},
            "rows": [{"estimated_hours_to_completion_at_recent_rate": 2.0}],
        },
        {
            "summary": {
                "recent_growth_bytes_per_second": 10.0,
                "estimated_hours_to_zero_free_at_recent_rate": 5.0,
            }
        },
    )

    assert payload["summary"]["risk_state"] == "completion_before_zero"
