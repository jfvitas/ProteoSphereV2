from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from scripts.build_operational_readiness_snapshot import (
    build_operational_readiness_snapshot,
    render_markdown,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_build_operational_readiness_snapshot_aggregates_runtime_evidence(tmp_path: Path) -> None:
    queue_path = tmp_path / "tasks" / "task_queue.json"
    state_path = tmp_path / "artifacts" / "status" / "orchestrator_state.json"
    heartbeat_path = tmp_path / "artifacts" / "runtime" / "supervisor.heartbeat.json"
    ledger_path = tmp_path / "artifacts" / "runtime" / "soak_ledger.jsonl"
    benchmark_summary_path = (
        tmp_path / "runs" / "real_data_benchmark" / "full_results" / "summary.json"
    )

    _write_json(
        queue_path,
        [
            {
                "id": "P22-I007",
                "title": "Run weeklong unattended soak validation",
                "status": "dispatched",
                "notes": "Keep open until the ledger covers a real weeklong unattended window.",
                "files": ["docs/reports/p22_weeklong_soak.md"],
            }
        ],
    )
    _write_json(
        state_path,
        {
            "active_workers": [],
            "dispatch_queue": [],
            "review_queue": [],
            "completed_tasks": ["P22-T021"],
            "blocked_tasks": ["P21-T005"],
        },
    )
    _write_json(
        heartbeat_path,
            {
                "status": "healthy",
                "last_heartbeat_at": "2026-03-23T10:45:00+00:00",
                "iteration": 17,
                "phase": "cycle_complete",
            },
    )
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "observed_at": "2026-03-23T10:00:00+00:00",
                        "queue_counts": {
                            "done": 279,
                            "pending": 25,
                            "blocked": 10,
                            "dispatched": 1,
                        },
                        "supervisor_heartbeat": {"status": "unavailable", "age_seconds": None},
                        "truth_boundary": {
                            "prototype_runtime": True,
                            "weeklong_soak_claim_allowed": False,
                        },
                    }
                ),
                json.dumps(
                    {
                        "observed_at": "2026-03-23T10:45:00+00:00",
                        "queue_counts": {
                            "done": 279,
                            "pending": 25,
                            "blocked": 10,
                            "dispatched": 1,
                        },
                        "supervisor_heartbeat": {"status": "healthy", "age_seconds": 5},
                        "truth_boundary": {
                            "prototype_runtime": True,
                            "weeklong_soak_claim_allowed": False,
                        },
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _write_json(
        benchmark_summary_path,
        {
            "status": "blocked_on_release_grade_bar",
        },
    )

    report_path = tmp_path / "docs" / "reports" / "p22_weeklong_soak.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        (
            "This note is a readiness assessment, not a claim that a "
            "weeklong run has already completed."
        ),
        encoding="utf-8",
    )

    snapshot = build_operational_readiness_snapshot(
        queue_path=queue_path,
        state_path=state_path,
        heartbeat_path=heartbeat_path,
        ledger_path=ledger_path,
        benchmark_summary_path=benchmark_summary_path,
        observed_at=datetime(2026, 3, 23, 10, 45, 30, tzinfo=UTC),
    )

    assert snapshot["supervisor"]["status"] == "healthy"
    assert snapshot["supervisor"]["age_seconds"] == 30
    assert snapshot["queue"]["completed_task_count"] == 1
    assert snapshot["queue"]["status_counts"] == {"dispatched": 1}
    assert snapshot["soak_summary"]["observed_window_hours"] == 0.75
    assert snapshot["soak_summary"]["observed_window_progress_ratio"] == 0.0045
    assert snapshot["soak_anomaly"]["incident_count"] == 1
    assert snapshot["queue_drift"]["has_drift"] is True
    assert snapshot["queue_drift"]["status"] == "fresh_drift"
    assert snapshot["queue_drift"]["capture_age_seconds"] == 30
    assert snapshot["queue_drift"]["delta_counts"] == {
        "blocked": -10,
        "done": -279,
        "pending": -25,
    }
    assert snapshot["truth_audit"]["finding_count"] == 0
    assert snapshot["benchmark"]["status"] == "blocked_on_release_grade_bar"
    assert snapshot["release_gate"]["operational_readiness_ready"] is False
    assert snapshot["release_gate"]["blocking_reasons"] == [
        "weeklong_soak_window_incomplete",
        "weeklong_claim_boundary_closed",
        "benchmark_status=blocked_on_release_grade_bar",
    ]


def test_build_operational_readiness_snapshot_detects_queue_drift(tmp_path: Path) -> None:
    queue_path = tmp_path / "tasks" / "task_queue.json"
    state_path = tmp_path / "artifacts" / "status" / "orchestrator_state.json"
    heartbeat_path = tmp_path / "artifacts" / "runtime" / "supervisor.heartbeat.json"
    ledger_path = tmp_path / "artifacts" / "runtime" / "soak_ledger.jsonl"
    benchmark_summary_path = (
        tmp_path / "runs" / "real_data_benchmark" / "full_results" / "summary.json"
    )

    _write_json(
        queue_path,
        [
            {
                "id": "P22-I007",
                "title": "Run weeklong unattended soak validation",
                "status": "dispatched",
                "notes": "",
                "files": [],
            },
            {
                "id": "P22-T024",
                "title": "Build operational readiness snapshot report",
                "status": "done",
                "notes": "",
                "files": [],
            },
        ],
    )
    _write_json(state_path, {"active_workers": [], "dispatch_queue": [], "review_queue": []})
    _write_json(
        heartbeat_path,
        {
            "status": "healthy",
            "last_heartbeat_at": "2026-03-23T10:45:00+00:00",
        },
    )
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(
        json.dumps(
            {
                "observed_at": "2026-03-23T10:45:00+00:00",
                "queue_counts": {"done": 0, "dispatched": 1, "pending": 1},
                "supervisor_heartbeat": {"status": "healthy", "age_seconds": 5},
                "truth_boundary": {
                    "prototype_runtime": True,
                    "weeklong_soak_claim_allowed": False,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _write_json(benchmark_summary_path, {"status": "blocked_on_release_grade_bar"})

    snapshot = build_operational_readiness_snapshot(
        queue_path=queue_path,
        state_path=state_path,
        heartbeat_path=heartbeat_path,
        ledger_path=ledger_path,
        benchmark_summary_path=benchmark_summary_path,
        observed_at=datetime(2026, 3, 23, 10, 45, 30, tzinfo=UTC),
    )

    assert snapshot["queue"]["status_counts"] == {"dispatched": 1, "done": 1}
    assert snapshot["queue_drift"]["has_drift"] is True
    assert snapshot["queue_drift"]["status"] == "fresh_drift"
    assert snapshot["queue_drift"]["capture_age_seconds"] == 30
    assert snapshot["queue_drift"]["delta_counts"] == {"done": 1, "pending": -1}
    assert snapshot["release_gate"]["blocking_reasons"] == [
        "weeklong_soak_window_incomplete",
        "weeklong_claim_boundary_closed",
        "benchmark_status=blocked_on_release_grade_bar",
    ]


def test_build_operational_readiness_snapshot_prefers_fresh_procurement_supervisor_state(
    tmp_path: Path,
) -> None:
    queue_path = tmp_path / "tasks" / "task_queue.json"
    state_path = tmp_path / "artifacts" / "status" / "orchestrator_state.json"
    heartbeat_path = tmp_path / "artifacts" / "runtime" / "supervisor.heartbeat.json"
    procurement_supervisor_state_path = (
        tmp_path / "artifacts" / "runtime" / "procurement_supervisor_state.json"
    )
    ledger_path = tmp_path / "artifacts" / "runtime" / "soak_ledger.jsonl"
    benchmark_summary_path = (
        tmp_path / "runs" / "real_data_benchmark" / "full_results" / "summary.json"
    )

    _write_json(
        queue_path,
        [
            {
                "id": "P22-I007",
                "title": "Run weeklong unattended soak validation",
                "status": "dispatched",
                "notes": "Keep open until the ledger covers a real weeklong unattended window.",
                "files": ["docs/reports/p22_weeklong_soak.md"],
            }
        ],
    )
    _write_json(
        state_path,
        {
            "active_workers": [],
            "dispatch_queue": [],
            "review_queue": [],
            "completed_tasks": [],
            "blocked_tasks": [],
        },
    )
    _write_json(
        heartbeat_path,
        {
            "status": "stale",
            "last_heartbeat_at": "2026-03-23T09:45:00+00:00",
            "iteration": 16,
            "phase": "cycle_complete",
        },
    )
    _write_json(
        procurement_supervisor_state_path,
        {
            "generated_at": "2026-03-23T10:45:10+00:00",
            "status": "running",
            "observation_status": "available",
            "observed_active": [
                {
                    "task_id": "guarded_sources",
                    "pid": 101,
                    "ownership": "observed_only",
                    "command_line": (
                        "python protein_data_scope/download_all_sources.py --tiers guarded"
                    ),
                }
            ],
            "active": [],
            "stale_active": [],
        },
    )
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(
        json.dumps(
            {
                "observed_at": "2026-03-23T10:45:00+00:00",
                "queue_counts": {"dispatched": 1},
                "supervisor_heartbeat": {"status": "healthy", "age_seconds": 5},
                "truth_boundary": {
                    "prototype_runtime": True,
                    "weeklong_soak_claim_allowed": False,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _write_json(benchmark_summary_path, {"status": "blocked_on_release_grade_bar"})

    snapshot = build_operational_readiness_snapshot(
        queue_path=queue_path,
        state_path=state_path,
        heartbeat_path=heartbeat_path,
        procurement_supervisor_state_path=procurement_supervisor_state_path,
        ledger_path=ledger_path,
        benchmark_summary_path=benchmark_summary_path,
        observed_at=datetime(2026, 3, 23, 10, 45, 30, tzinfo=UTC),
    )

    assert snapshot["supervisor"]["status"] == "running"
    assert snapshot["supervisor"]["source"] == "procurement_supervisor_state"
    assert snapshot["supervisor"]["age_seconds"] == 20
    assert snapshot["supervisor_heartbeat"]["status"] == "stale"
    assert snapshot["supervisor_heartbeat"]["age_seconds"] == 3630
    assert snapshot["procurement_supervisor"]["fresh_observation"] is True
    assert snapshot["release_gate"]["operational_readiness_ready"] is False
    assert snapshot["release_gate"]["blocking_reasons"] == [
        "supervisor_status=running",
        "weeklong_soak_window_incomplete",
        "weeklong_claim_boundary_closed",
        "benchmark_status=blocked_on_release_grade_bar",
    ]


def test_render_markdown_surfaces_release_gate() -> None:
    markdown = render_markdown(
        {
            "generated_at": "2026-03-23T10:45:30+00:00",
            "supervisor": {
                "status": "healthy",
                "last_heartbeat_at": "2026-03-23T10:45:00+00:00",
                "age_seconds": 30,
                "iteration": 17,
                "phase": "cycle_complete",
                "source": "heartbeat",
            },
            "supervisor_heartbeat": {
                "status": "healthy",
                "last_heartbeat_at": "2026-03-23T10:45:00+00:00",
                "age_seconds": 30,
                "iteration": 17,
                "phase": "cycle_complete",
            },
            "procurement_supervisor": None,
            "queue": {
                "active_worker_count": 0,
                "dispatch_queue_count": 0,
                "review_queue_count": 0,
                "completed_task_count": 1,
                "blocked_task_count": 1,
                "status_counts": {"dispatched": 1, "done": 1},
            },
            "soak_summary": {
                "entry_count": 2,
                "observed_window_hours": 0.75,
                "observed_window_progress_ratio": 0.0045,
                "remaining_hours_to_weeklong": 167.25,
                "estimated_weeklong_completion_at": "2026-03-30T10:00:00+00:00",
                "healthy_ratio": 0.5,
            },
            "soak_anomaly": {
                "incident_count": 1,
                "incident_status_counts": {"unavailable": 1},
                "longest_healthy_streak": 1,
                "current_healthy_streak": 1,
                "queue_transition_count": 0,
            },
            "queue_drift": {
                "current_queue_counts": {"dispatched": 1, "done": 1},
                "latest_captured_queue_counts": {"dispatched": 1, "pending": 1},
                "latest_captured_at": "2026-03-23T10:45:00+00:00",
                "capture_age_seconds": 30,
                "has_drift": True,
                "status": "fresh_drift",
                "delta_counts": {"done": 1, "pending": -1},
            },
            "truth_audit": {
                "status": "ok",
                "finding_count": 0,
            },
            "benchmark": {"status": "blocked_on_release_grade_bar"},
            "release_gate": {
                "weeklong_claim_allowed": False,
                "weeklong_requirement_met": False,
                "truth_audit_clear": True,
                "operational_readiness_ready": False,
                "blocking_reasons": [
                    "weeklong_soak_window_incomplete",
                    "weeklong_claim_boundary_closed",
                    "benchmark_status=blocked_on_release_grade_bar",
                ],
            },
        }
    )

    assert "# P22 Operational Readiness Snapshot" in markdown
    assert "Drift present: `True`" in markdown
    assert "Drift status: `fresh_drift`" in markdown
    assert "Delta counts: `{'done': 1, 'pending': -1}`" in markdown
    assert (
        "Blocking reasons: `['weeklong_soak_window_incomplete', "
        "'weeklong_claim_boundary_closed', "
        "'benchmark_status=blocked_on_release_grade_bar']`"
    ) in markdown
    assert "Progress ratio: `0.0045`" in markdown
    assert "Operational readiness ready: `False`" in markdown
    assert "not yet strong enough" in markdown
