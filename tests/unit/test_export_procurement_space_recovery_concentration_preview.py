from __future__ import annotations

from scripts.export_procurement_space_recovery_concentration_preview import (
    build_procurement_space_recovery_concentration_preview,
)


def test_concentration_preview_reports_top1_dominant() -> None:
    payload = build_procurement_space_recovery_concentration_preview(
        {
            "summary": {"total_ranked_reclaim_gib": 10.0},
            "rows": [
                {"filename": "a.bin", "reclaim_gib_if_removed": 6.0},
                {"filename": "b.bin", "reclaim_gib_if_removed": 2.0},
                {"filename": "c.bin", "reclaim_gib_if_removed": 2.0},
            ],
        }
    )

    assert payload["summary"]["concentration_state"] == "top1_dominant"
    assert payload["summary"]["top1_reclaim_fraction"] == 0.6


def test_concentration_preview_reports_distributed_lane() -> None:
    payload = build_procurement_space_recovery_concentration_preview(
        {
            "summary": {"total_ranked_reclaim_gib": 10.0},
            "rows": [
                {"filename": "a.bin", "reclaim_gib_if_removed": 2.0},
                {"filename": "b.bin", "reclaim_gib_if_removed": 2.0},
                {"filename": "c.bin", "reclaim_gib_if_removed": 2.0},
                {"filename": "d.bin", "reclaim_gib_if_removed": 2.0},
                {"filename": "e.bin", "reclaim_gib_if_removed": 2.0},
            ],
        }
    )

    assert payload["summary"]["concentration_state"] == "distributed_lane"
