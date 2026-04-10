from __future__ import annotations

from scripts.analyze_soak_anomalies import analyze_entries, render_markdown


def test_analyze_entries_tracks_incidents_and_streaks() -> None:
    entries = [
        {
            "observed_at": "2026-03-23T10:00:00+00:00",
            "queue_counts": {"done": 260, "pending": 25},
            "truth_boundary": {"prototype_runtime": True, "weeklong_soak_claim_allowed": False},
            "supervisor_heartbeat": {"status": "unavailable", "age_seconds": None},
        },
        {
            "observed_at": "2026-03-23T10:10:00+00:00",
            "queue_counts": {"done": 260, "pending": 25},
            "truth_boundary": {"prototype_runtime": True, "weeklong_soak_claim_allowed": False},
            "supervisor_heartbeat": {"status": "healthy", "age_seconds": 4},
        },
        {
            "observed_at": "2026-03-23T10:20:00+00:00",
            "queue_counts": {"done": 261, "pending": 24},
            "truth_boundary": {"prototype_runtime": True, "weeklong_soak_claim_allowed": False},
            "supervisor_heartbeat": {"status": "healthy", "age_seconds": 5},
        },
        {
            "observed_at": "2026-03-23T10:30:00+00:00",
            "queue_counts": {"done": 261, "pending": 24},
            "truth_boundary": {"prototype_runtime": True, "weeklong_soak_claim_allowed": False},
            "supervisor_heartbeat": {"status": "stale", "age_seconds": 420},
        },
    ]

    report = analyze_entries(entries)

    assert report["entry_count"] == 4
    assert report["incident_count"] == 2
    assert report["incident_status_counts"] == {"stale": 1, "unavailable": 1}
    assert report["queue_transition_count"] == 1
    assert report["longest_healthy_streak"] == 2
    assert report["current_healthy_streak"] == 0
    assert report["truth_boundary"]["weeklong_soak_claim_allowed"] is False


def test_render_markdown_keeps_claim_boundary_explicit() -> None:
    markdown = render_markdown(
        {
            "entry_count": 3,
            "first_observed_at": "2026-03-23T10:00:00+00:00",
            "last_observed_at": "2026-03-23T11:00:00+00:00",
            "observed_window_hours": 1.0,
            "incident_count": 1,
            "incident_status_counts": {"unavailable": 1},
            "queue_transition_count": 1,
            "longest_healthy_streak": 2,
            "current_healthy_streak": 2,
            "recent_incidents": [
                {
                    "observed_at": "2026-03-23T10:00:00+00:00",
                    "status": "unavailable",
                    "age_seconds": None,
                }
            ],
            "latest_queue_counts": {"done": 265, "pending": 29},
            "truth_boundary": {"prototype_runtime": True, "weeklong_soak_claim_allowed": False},
        }
    )

    assert "does not upgrade the run to a completed weeklong durability claim" in markdown
    assert "Weeklong claim allowed: `False`" in markdown
    assert "Current healthy streak: `2` samples" in markdown
