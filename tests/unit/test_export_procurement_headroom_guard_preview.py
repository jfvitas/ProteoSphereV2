from __future__ import annotations

from scripts.export_procurement_headroom_guard_preview import (
    build_procurement_headroom_guard_preview,
)


def test_headroom_guard_preview_reports_healthy_margin() -> None:
    payload = build_procurement_headroom_guard_preview(
        {
            "summary": {
                "sampled_tail_file_count": 2,
                "total_after_bytes": 1024,
                "aggregate_bytes_per_second": 1.0,
            },
            "rows": [],
        }
    )

    assert payload["summary"]["guard_state"] in {"healthy_headroom", "caution_headroom"}
    assert payload["summary"]["free_bytes"] > 0
    assert payload["summary"]["active_tail_file_count"] == 2


def test_headroom_guard_preview_handles_zero_growth() -> None:
    payload = build_procurement_headroom_guard_preview(
        {
            "summary": {
                "sampled_tail_file_count": 2,
                "total_after_bytes": 2048,
                "aggregate_bytes_per_second": 0.0,
            },
            "rows": [],
        }
    )

    assert payload["summary"]["estimated_hours_to_zero_free_at_recent_rate"] is None
    assert payload["summary"]["active_tail_bytes"] == 2048
