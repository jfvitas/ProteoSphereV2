from __future__ import annotations

from scripts.export_overnight_pending_reconciliation_preview import (
    build_overnight_pending_reconciliation_preview,
)


def test_build_pending_reconciliation_flags_stale_idle_preview_drift() -> None:
    payload = build_overnight_pending_reconciliation_preview(
        queue=[{"id": "A", "status": "done"}, {"id": "B", "status": "blocked"}],
        monitor_snapshot={
            "observed_at": "2026-04-04T02:21:02+00:00",
            "dependency_ready_pending_count": 0,
            "blocked_count": 1,
            "done_count": 10,
            "active_worker_count": 0,
            "ready_count": 0,
        },
        orchestrator_state={
            "active_workers": [],
            "completed_tasks": ["A", "C"],
            "blocked_tasks": ["B"],
            "last_tick_completed_at": "2026-04-04T02:21:02+00:00",
        },
        idle_status_preview={
            "generated_at": "2026-04-04T02:19:56+00:00",
            "queue_summary": {"pending_count": 4, "blocked_count": 1, "active_worker_count": 0},
        },
        wave_advance_preview={
            "post_queue_counts": {"done": 10, "blocked": 1},
            "monitor_summary": {"snapshot": {"observed_at": "2026-04-04T02:19:56+00:00"}},
            "active_worker_count": 0,
        },
    )

    assert payload["summary"]["reconciliation_state"] == "stale_idle_preview_drift_resolved"
    assert payload["summary"]["stale_preview_detected"] is True
    assert payload["summary"]["queue_file_pending_count"] == 0
    assert payload["summary"]["idle_preview_pending_count"] == 4


def test_build_pending_reconciliation_flags_queue_monitor_drift() -> None:
    payload = build_overnight_pending_reconciliation_preview(
        queue=[{"id": "A", "status": "pending"}, {"id": "B", "status": "blocked"}],
        monitor_snapshot={
            "observed_at": "2026-04-04T02:21:02+00:00",
            "dependency_ready_pending_count": 0,
            "blocked_count": 1,
            "done_count": 8,
            "active_worker_count": 0,
            "ready_count": 0,
        },
        orchestrator_state={"active_workers": [], "completed_tasks": [], "blocked_tasks": ["B"]},
        idle_status_preview={"generated_at": "2026-04-04T02:21:03+00:00", "queue_summary": {}},
        wave_advance_preview={"post_queue_counts": {"done": 8, "blocked": 1}},
    )

    assert (
        payload["summary"]["reconciliation_state"]
        == "queue_monitor_pending_drift_requires_review"
    )
    assert payload["summary"]["queue_monitor_pending_drift"] is True
