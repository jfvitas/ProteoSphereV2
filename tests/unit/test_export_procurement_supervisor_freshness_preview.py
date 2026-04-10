from __future__ import annotations

from datetime import UTC, datetime

from scripts.export_procurement_supervisor_freshness_preview import (
    build_procurement_supervisor_freshness_preview,
)


def test_freshness_preview_marks_legacy_stale_state_as_superseded() -> None:
    payload = build_procurement_supervisor_freshness_preview(
        board={
            "generated_at": "2026-04-03T22:11:43+00:00",
            "procurement_supervisor": {
                "status": "planning",
                "generated_at": "2026-04-03T21:33:40+00:00",
                "active_observed_download_count": 2,
                "observed_active_source": "remaining_transfer_status",
            },
        },
        supervisor_state={
            "generated_at": "2026-04-02T15:13:01+00:00",
            "status": "stale",
            "pending": ["chembl_rnacentral_bulk", "interpro_complexportal_resolver_small"],
            "observed_active": [{"pid": 1}],
            "completed": [{"task_id": "guarded_sources"}],
        },
        heartbeat={
            "last_heartbeat_at": "2026-04-04T02:31:37+00:00",
            "phase": "cycle_complete",
        },
        observed_at=datetime(2026, 4, 4, 2, 32, 0, tzinfo=UTC),
    )

    assert payload["summary"]["freshness_state"] == "legacy_stale_state_superseded"
    assert payload["summary"]["supervisor_heartbeat_fresh"] is True
    assert payload["summary"]["stale_state_superseded_by_board"] is True
    assert payload["summary"]["board_active_observed_download_count"] == 2


def test_freshness_preview_marks_stale_attention_without_fresh_board_and_heartbeat() -> None:
    payload = build_procurement_supervisor_freshness_preview(
        board={
            "generated_at": "2026-04-01T00:00:00+00:00",
            "procurement_supervisor": {
                "status": "idle",
                "generated_at": "2026-04-01T00:00:00+00:00",
                "active_observed_download_count": 0,
                "observed_active_source": "none",
            },
        },
        supervisor_state={
            "generated_at": "2026-04-02T15:13:01+00:00",
            "status": "stale",
            "pending": [],
            "observed_active": [],
            "completed": [],
        },
        heartbeat={},
        observed_at=datetime(2026, 4, 4, 2, 32, 0, tzinfo=UTC),
    )

    assert payload["summary"]["freshness_state"] == "stale_supervisor_state_attention"
    assert payload["summary"]["supervisor_heartbeat_fresh"] is False
    assert payload["summary"]["stale_state_superseded_by_board"] is False
