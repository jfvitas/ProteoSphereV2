from __future__ import annotations

from scripts.export_overnight_worker_launch_gap_preview import (
    build_overnight_worker_launch_gap_preview,
)


def test_build_worker_launch_gap_preview_reports_no_gap_for_blocked_idle_state() -> None:
    payload = build_overnight_worker_launch_gap_preview(
        queue=[{"id": "A", "status": "done"}, {"id": "B", "status": "blocked"}],
        monitor_snapshot={
            "ready_count": 0,
            "dependency_ready_pending_count": 0,
            "dispatch_queue_count": 0,
            "review_queue_count": 0,
            "active_worker_count": 0,
            "blocked_count": 1,
        },
        orchestrator_state={"active_workers": []},
        idle_status_preview={
            "queue_summary": {"in_flight_count": 0},
            "idle_state": "blocked_waiting",
        },
        heartbeat={"last_heartbeat_at": "2026-04-04T02:21:02+00:00", "phase": "cycle_complete"},
    )

    assert payload["summary"]["launch_gap_state"] == "blocked_or_idle_no_launch_gap"
    assert payload["summary"]["launch_gap_detected"] is False


def test_build_worker_launch_gap_preview_detects_ready_work_without_workers() -> None:
    payload = build_overnight_worker_launch_gap_preview(
        queue=[{"id": "A", "status": "ready"}],
        monitor_snapshot={
            "ready_count": 1,
            "dependency_ready_pending_count": 0,
            "dispatch_queue_count": 0,
            "review_queue_count": 0,
            "active_worker_count": 0,
            "blocked_count": 0,
        },
        orchestrator_state={"active_workers": []},
        idle_status_preview={
            "queue_summary": {"in_flight_count": 1},
            "idle_state": "healthy_active",
        },
        heartbeat={"last_heartbeat_at": "2026-04-04T02:21:02+00:00", "phase": "cycle_complete"},
    )

    assert payload["summary"]["launch_gap_state"] == "launch_gap_present"
    assert payload["summary"]["launch_gap_detected"] is True
