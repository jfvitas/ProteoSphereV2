from __future__ import annotations

import json
from pathlib import Path

from scripts.summarize_soak_ledger import (
    load_ledger_entries,
    render_markdown,
    summarize_entries,
)


def test_load_ledger_entries_ignores_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "soak_ledger.jsonl"
    path.write_text(
        json.dumps({"observed_at": "2026-03-23T10:00:00+00:00"}) + "\n\n",
        encoding="utf-8",
    )

    entries = load_ledger_entries(path)

    assert len(entries) == 1
    assert entries[0]["observed_at"] == "2026-03-23T10:00:00+00:00"


def test_summarize_entries_counts_heartbeat_mix() -> None:
    entries = [
        {
            "observed_at": "2026-03-23T10:00:00+00:00",
            "queue_counts": {"done": 260, "pending": 25},
            "benchmark_completion_status": "blocked_on_release_grade_bar",
            "truth_boundary": {
                "prototype_runtime": True,
                "weeklong_soak_claim_allowed": False,
            },
            "supervisor_heartbeat": {
                "status": "healthy",
                "age_seconds": 3,
            },
        },
        {
            "observed_at": "2026-03-23T11:00:00+00:00",
            "queue_counts": {"done": 261, "pending": 25, "blocked": 12},
            "benchmark_completion_status": "blocked_on_release_grade_bar",
            "truth_boundary": {
                "prototype_runtime": True,
                "weeklong_soak_claim_allowed": False,
            },
            "supervisor_heartbeat": {
                "status": "stale",
                "age_seconds": 420,
            },
        },
        {
            "observed_at": "2026-03-23T12:30:00+00:00",
            "queue_counts": {"done": 261, "pending": 25, "blocked": 12},
            "benchmark_completion_status": "blocked_on_release_grade_bar",
            "truth_boundary": {
                "prototype_runtime": True,
                "weeklong_soak_claim_allowed": False,
            },
            "supervisor_heartbeat": {
                "status": "unavailable",
                "age_seconds": None,
            },
        },
    ]

    summary = summarize_entries(entries)

    assert summary["entry_count"] == 3
    assert summary["heartbeat_status_counts"] == {
        "healthy": 1,
        "stale": 1,
        "unavailable": 1,
    }
    assert summary["incident_count"] == 2
    assert summary["observed_window_seconds"] == 9000
    assert summary["observed_window_progress_ratio"] == 0.0149
    assert summary["remaining_seconds_to_weeklong"] == 595800
    assert summary["remaining_hours_to_weeklong"] == 165.5
    assert summary["estimated_weeklong_completion_at"] == "2026-03-30T10:00:00+00:00"
    assert summary["max_heartbeat_age_seconds"] == 420
    assert summary["latest_queue_counts"]["done"] == 261
    assert summary["truth_boundary"]["weeklong_requirement_met"] is False
    assert summary["truth_boundary"]["weeklong_soak_claim_allowed"] is False


def test_render_markdown_keeps_truth_boundary_explicit() -> None:
    summary = {
        "entry_count": 2,
        "first_observed_at": "2026-03-23T10:00:00+00:00",
        "last_observed_at": "2026-03-23T11:00:00+00:00",
        "observed_window_seconds": 3600,
        "observed_window_hours": 1.0,
        "remaining_seconds_to_weeklong": 601200,
        "remaining_hours_to_weeklong": 167.0,
        "observed_window_progress_ratio": 0.006,
        "estimated_weeklong_completion_at": "2026-03-30T10:00:00+00:00",
        "heartbeat_status_counts": {"healthy": 2},
        "incident_count": 0,
        "healthy_ratio": 1.0,
        "max_heartbeat_age_seconds": 12,
        "latest_queue_counts": {"done": 261, "pending": 25},
        "queue_high_watermarks": {"done": 261, "pending": 25},
        "latest_benchmark_completion_status": "blocked_on_release_grade_bar",
        "truth_boundary": {
            "prototype_runtime": True,
            "weeklong_soak_claim_allowed": False,
            "weeklong_requirement_seconds": 604800,
            "weeklong_requirement_met": False,
        },
    }

    markdown = render_markdown(summary)

    assert "not a claim that the weeklong soak has already completed" in markdown
    assert "Progress to weeklong threshold: `0.006`" in markdown
    assert "Estimated weeklong threshold at: `2026-03-30T10:00:00+00:00`" in markdown
    assert "Weeklong claim allowed: `False`" in markdown
    assert "Prototype runtime boundary remains active: `True`" in markdown
