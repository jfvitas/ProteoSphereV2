from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from scripts.export_overnight_idle_status_preview import (
    build_overnight_idle_status_preview,
    main,
)


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_build_preview_reports_healthy_active() -> None:
    observed_at = datetime(2026, 4, 3, 22, 0, tzinfo=UTC)
    payload = build_overnight_idle_status_preview(
        [{"id": "T1", "status": "ready"}],
        {
            "status": "running",
            "queue_counts": {"ready": 1, "pending": 0, "blocked": 0, "done": 5},
            "ready_count": 1,
            "dependency_ready_pending_count": 0,
            "active_worker_count": 0,
            "dispatch_queue_count": 0,
            "review_queue_count": 0,
            "blocked_count": 0,
            "done_count": 5,
        },
        {
            "status": "attention",
            "summary": {"active_download_count": 2, "remaining_source_count": 2},
        },
        {"status": "running", "observed_active": ["string", "uniprot"], "pending": []},
        {"last_heartbeat_at": observed_at.isoformat()},
        observed_at=observed_at,
    )

    assert payload["idle_state"] == "healthy_active"
    assert payload["queue_summary"]["ready_count"] == 1
    assert any("ready task" in reason for reason in payload["reason_summary"])
    assert payload["next_suggested_action"].startswith("Let the active queue continue")
    assert payload["truth_boundary"]["procurement_tail_awareness_explicit"] is True


def test_build_preview_reports_healthy_queue_drained_with_active_tail() -> None:
    observed_at = datetime(2026, 4, 3, 22, 0, tzinfo=UTC)
    payload = build_overnight_idle_status_preview(
        [],
        {
            "status": "running",
            "queue_counts": {"ready": 0, "pending": 0, "blocked": 0, "done": 12},
            "ready_count": 0,
            "dependency_ready_pending_count": 0,
            "active_worker_count": 0,
            "dispatch_queue_count": 0,
            "review_queue_count": 0,
            "blocked_count": 0,
            "done_count": 12,
        },
        {
            "status": "attention",
            "summary": {
                "active_download_count": 2,
                "remaining_source_count": 2,
                "total_gap_files": 2,
            },
            "remaining_transfer": {
                "top_gap_files": ["protein.links.full.v12.0.txt.gz", "uniref100.xml.gz"]
            },
        },
        {"status": "running", "observed_active": ["string", "uniprot"], "pending": []},
        {"last_heartbeat_at": observed_at.isoformat()},
        observed_at=observed_at,
    )

    assert payload["idle_state"] == "healthy_queue_drained"
    assert payload["queue_summary"]["queue_is_drained"] is True
    assert payload["procurement_tail_awareness"]["active_download_count"] == 2
    assert any(
        "procurement tail still has active downloads" in reason
        for reason in payload["reason_summary"]
    )
    assert "wait for the next replenishment wave" in payload["next_suggested_action"]


def test_build_preview_reports_blocked_waiting() -> None:
    observed_at = datetime(2026, 4, 3, 22, 0, tzinfo=UTC)
    payload = build_overnight_idle_status_preview(
        [{"id": "B1", "status": "blocked"}],
        {
            "status": "running",
            "queue_counts": {"ready": 0, "pending": 0, "blocked": 1, "done": 7},
            "ready_count": 0,
            "dependency_ready_pending_count": 0,
            "active_worker_count": 0,
            "dispatch_queue_count": 0,
            "review_queue_count": 0,
            "blocked_count": 1,
            "done_count": 7,
        },
        {"status": "blocked", "summary": {"active_download_count": 0, "remaining_source_count": 1}},
        {"status": "blocked", "observed_active": [], "pending": ["string"]},
        {"last_heartbeat_at": observed_at.isoformat()},
        observed_at=observed_at,
    )

    assert payload["idle_state"] == "blocked_waiting"
    assert payload["queue_summary"]["blocked_count"] == 1
    assert payload["next_suggested_action"].startswith("Resolve the blocker")


def test_build_preview_reports_stalled_when_heartbeat_is_stale() -> None:
    observed_at = datetime(2026, 4, 3, 22, 0, tzinfo=UTC)
    payload = build_overnight_idle_status_preview(
        [{"id": "R1", "status": "ready"}],
        {
            "status": "running",
            "queue_counts": {"ready": 1, "pending": 0, "blocked": 0, "done": 3},
            "ready_count": 1,
            "dependency_ready_pending_count": 0,
            "active_worker_count": 0,
            "dispatch_queue_count": 0,
            "review_queue_count": 0,
            "blocked_count": 0,
            "done_count": 3,
        },
        {
            "status": "attention",
            "summary": {"active_download_count": 2, "remaining_source_count": 2},
        },
        {"status": "running", "observed_active": ["string", "uniprot"], "pending": []},
        {"last_heartbeat_at": (observed_at - timedelta(hours=1)).isoformat()},
        observed_at=observed_at,
    )

    assert payload["idle_state"] == "stalled_or_attention_needed"
    assert any("heartbeat is stale" in reason.lower() for reason in payload["reason_summary"])
    assert payload["next_suggested_action"].startswith("Refresh the supervisor")


def test_main_writes_default_json(tmp_path: Path) -> None:
    queue_path = tmp_path / "tasks" / "task_queue.json"
    monitor_path = tmp_path / "artifacts" / "runtime" / "monitor_snapshot.json"
    board_path = tmp_path / "artifacts" / "status" / "procurement_status_board.json"
    state_path = tmp_path / "artifacts" / "runtime" / "procurement_supervisor_state.json"
    heartbeat_path = tmp_path / "artifacts" / "runtime" / "supervisor.heartbeat.json"
    output_json = tmp_path / "artifacts" / "status" / "overnight_idle_status_preview.json"
    observed_at = datetime(2026, 4, 3, 22, 0, tzinfo=UTC)

    _write_json(queue_path, [])
    _write_json(
        monitor_path,
        {
            "status": "running",
            "queue_counts": {"ready": 0, "pending": 0, "blocked": 0, "done": 2},
            "ready_count": 0,
            "dependency_ready_pending_count": 0,
            "active_worker_count": 0,
            "dispatch_queue_count": 0,
            "review_queue_count": 0,
            "blocked_count": 0,
            "done_count": 2,
        },
    )
    _write_json(
        board_path,
        {
            "status": "attention",
            "summary": {
                "active_download_count": 2,
                "remaining_source_count": 2,
                "total_gap_files": 2,
            },
            "remaining_transfer": {"top_gap_files": ["protein.links.full.v12.0.txt.gz"]},
        },
    )
    _write_json(state_path, {"status": "running", "observed_active": [], "pending": []})
    _write_json(heartbeat_path, {"last_heartbeat_at": observed_at.isoformat(), "phase": "tick"})

    main(
        [
            "--queue-path",
            str(queue_path),
            "--monitor-path",
            str(monitor_path),
            "--procurement-board-path",
            str(board_path),
            "--supervisor-state-path",
            str(state_path),
            "--heartbeat-path",
            str(heartbeat_path),
            "--output-json",
            str(output_json),
            "--observed-at",
            observed_at.isoformat(),
        ]
    )

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["idle_state"] == "healthy_queue_drained"
    assert payload["procurement_tail_awareness"]["active_download_count"] == 2
    assert payload["status"] == "report_only"
