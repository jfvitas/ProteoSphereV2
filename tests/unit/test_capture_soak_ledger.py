from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from scripts.capture_soak_ledger import append_soak_ledger, build_soak_ledger_entry


def test_build_soak_ledger_entry_marks_healthy_heartbeat() -> None:
    now = datetime(2026, 3, 23, 10, 0, tzinfo=UTC)
    entry = build_soak_ledger_entry(
        monitor_snapshot={
            "queue_counts": {"done": 260, "blocked": 12, "dispatched": 1, "pending": 25},
            "ready_count": 0,
            "dependency_ready_pending_count": 0,
        },
        orchestrator_state={
            "active_workers": [],
            "dispatch_queue": [],
            "review_queue": ["P22-I007"],
            "completed_tasks": ["P21-I008"],
            "blocked_tasks": ["P21-T005"],
            "last_tick_completed_at": "2026-03-23T09:59:59+00:00",
        },
        heartbeat_payload={
            "last_heartbeat_at": (now - timedelta(seconds=30)).isoformat(),
            "stale_after_seconds": 300,
            "iteration": 4,
            "phase": "cycle_complete",
        },
        heartbeat_history_count=7,
        benchmark_summary={"status": "blocked_on_release_grade_bar"},
        benchmark_run_summary={
            "status": "completed_on_prototype_runtime",
            "runtime_surface": "local prototype runtime",
            "remaining_gaps": ["gap-a", "gap-b"],
        },
        observed_at=now,
    )

    assert entry["queue_counts"]["done"] == 260
    assert entry["supervisor_heartbeat"]["status"] == "healthy"
    assert entry["supervisor_heartbeat"]["is_stale"] is False
    assert entry["supervisor_heartbeat"]["age_seconds"] == 30
    assert entry["supervisor_heartbeat_history_count"] == 7
    assert entry["remaining_gap_count"] == 2


def test_append_soak_ledger_writes_unavailable_heartbeat_entry(tmp_path: Path) -> None:
    monitor_path = tmp_path / "artifacts" / "runtime" / "monitor_snapshot.json"
    monitor_path.parent.mkdir(parents=True, exist_ok=True)
    monitor_path.write_text(
        json.dumps(
            {
                "queue_counts": {"done": 260, "blocked": 12, "dispatched": 1, "pending": 25},
                "ready_count": 0,
                "dependency_ready_pending_count": 0,
            }
        ),
        encoding="utf-8",
    )

    state_path = tmp_path / "artifacts" / "status" / "orchestrator_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "active_workers": [],
                "dispatch_queue": [],
                "review_queue": [],
                "completed_tasks": ["P21-I008"],
                "blocked_tasks": ["P21-T005"],
                "last_tick_completed_at": "2026-03-23T09:59:59+00:00",
            }
        ),
        encoding="utf-8",
    )

    benchmark_summary_path = (
        tmp_path / "runs" / "real_data_benchmark" / "full_results" / "summary.json"
    )
    benchmark_summary_path.parent.mkdir(parents=True, exist_ok=True)
    benchmark_summary_path.write_text(
        json.dumps({"status": "blocked_on_release_grade_bar"}),
        encoding="utf-8",
    )

    run_summary_path = benchmark_summary_path.with_name("run_summary.json")
    run_summary_path.write_text(
        json.dumps(
            {
                "status": "completed_on_prototype_runtime",
                "runtime_surface": "local prototype runtime",
                "remaining_gaps": ["gap-a"],
            }
        ),
        encoding="utf-8",
    )

    output_path = tmp_path / "artifacts" / "runtime" / "soak_ledger.jsonl"
    entry = append_soak_ledger(
        output_path=output_path,
        monitor_snapshot_path=monitor_path,
        orchestrator_state_path=state_path,
        heartbeat_path=tmp_path / "artifacts" / "runtime" / "supervisor.heartbeat.json",
        heartbeat_history_path=(
            tmp_path / "artifacts" / "runtime" / "supervisor.heartbeat.history.jsonl"
        ),
        benchmark_summary_path=benchmark_summary_path,
        benchmark_run_summary_path=run_summary_path,
        observed_at=datetime(2026, 3, 23, 10, 0, tzinfo=UTC),
    )

    lines = output_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload == entry
    assert payload["supervisor_heartbeat"]["status"] == "unavailable"
    assert payload["supervisor_heartbeat_history_count"] == 0
    assert payload["benchmark_completion_status"] == "blocked_on_release_grade_bar"


def test_append_soak_ledger_falls_back_to_heartbeat_history(tmp_path: Path) -> None:
    monitor_path = tmp_path / "artifacts" / "runtime" / "monitor_snapshot.json"
    monitor_path.parent.mkdir(parents=True, exist_ok=True)
    monitor_path.write_text(
        json.dumps(
            {
                "queue_counts": {"done": 261, "blocked": 12, "dispatched": 1, "pending": 25},
                "ready_count": 0,
                "dependency_ready_pending_count": 0,
            }
        ),
        encoding="utf-8",
    )

    state_path = tmp_path / "artifacts" / "status" / "orchestrator_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "active_workers": [],
                "dispatch_queue": [],
                "review_queue": [],
                "completed_tasks": ["P22-T007"],
                "blocked_tasks": ["P21-T005"],
                "last_tick_completed_at": "2026-03-23T09:59:59+00:00",
            }
        ),
        encoding="utf-8",
    )

    history_path = tmp_path / "artifacts" / "runtime" / "supervisor.heartbeat.history.jsonl"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    last_heartbeat_at = datetime(2026, 3, 23, 9, 59, 30, tzinfo=UTC)
    history_path.write_text(
        json.dumps(
            {
                "last_heartbeat_at": last_heartbeat_at.isoformat(),
                "stale_after_seconds": 300,
                "iteration": 9,
                "phase": "cycle_complete",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    benchmark_summary_path = (
        tmp_path / "runs" / "real_data_benchmark" / "full_results" / "summary.json"
    )
    benchmark_summary_path.parent.mkdir(parents=True, exist_ok=True)
    benchmark_summary_path.write_text(
        json.dumps({"status": "blocked_on_release_grade_bar"}),
        encoding="utf-8",
    )

    run_summary_path = benchmark_summary_path.with_name("run_summary.json")
    run_summary_path.write_text(
        json.dumps(
            {
                "status": "completed_on_prototype_runtime",
                "runtime_surface": "local prototype runtime",
                "remaining_gaps": ["gap-a"],
            }
        ),
        encoding="utf-8",
    )

    output_path = tmp_path / "artifacts" / "runtime" / "soak_ledger.jsonl"
    entry = append_soak_ledger(
        output_path=output_path,
        monitor_snapshot_path=monitor_path,
        orchestrator_state_path=state_path,
        heartbeat_path=tmp_path / "artifacts" / "runtime" / "supervisor.heartbeat.json",
        heartbeat_history_path=history_path,
        benchmark_summary_path=benchmark_summary_path,
        benchmark_run_summary_path=run_summary_path,
        observed_at=datetime(2026, 3, 23, 10, 0, tzinfo=UTC),
    )

    assert entry["supervisor_heartbeat"]["status"] == "healthy"
    assert entry["supervisor_heartbeat"]["iteration"] == 9
    assert entry["supervisor_heartbeat_history_count"] == 1
