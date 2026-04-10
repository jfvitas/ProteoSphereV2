from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.bug_bash_dashboard import (
    advance_blocker_triage_state,
    build_bug_bash_dashboard,
    main,
    render_markdown,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_inputs(tmp_path: Path) -> dict[str, Path]:
    intake_path = tmp_path / "artifacts" / "status" / "bug_bash_intake.json"
    blockers_path = tmp_path / "artifacts" / "status" / "release_blockers.json"

    _write_json(
        intake_path,
        {
            "bug_bash_items": [
                {
                    "bug_id": "BB-001",
                    "title": "RC signoff text mismatches machine-readable state",
                    "area": "dashboard",
                    "priority": "P1",
                    "severity": "blocker",
                    "release_blocker": True,
                    "triage_state": "new",
                    "triage_events": ["triage", "accept", "start_fix"],
                    "owner": "ops",
                    "source": "rc intake",
                    "notes": ["report-only boundary must stay explicit"],
                },
                {
                    "bug_id": "BB-002",
                    "title": "Release blocker resolved in preview only",
                    "area": "dashboard",
                    "priority": "P2",
                    "severity": "critical",
                    "release_blocker": True,
                    "triage_state": "triaged",
                    "triage_events": ["accept", "resolve"],
                    "owner": "ops",
                    "source": "bug bash",
                    "notes": ["keep report-only truth boundary"],
                },
                {
                    "bug_id": "BB-003",
                    "title": "Non-blocking documentation typo",
                    "area": "docs",
                    "priority": "P3",
                    "severity": "minor",
                    "release_blocker": False,
                    "triage_state": "new",
                    "triage_events": ["triage"],
                    "owner": "docs",
                    "source": "bug bash",
                },
            ],
            "rc_signoff_state": "report_only",
        },
    )
    _write_json(
        blockers_path,
        {
            "release_blockers": [
                {
                    "bug_id": "BB-004",
                    "title": "Unexpected blocker reopened after RC review",
                    "area": "release",
                    "priority": "P0",
                    "severity": "blocker",
                    "release_blocker": True,
                    "triage_state": "resolved",
                    "triage_events": ["reopen", "triage"],
                    "owner": "release",
                    "source": "rc review",
                }
            ]
        },
    )
    return {"intake": intake_path, "blockers": blockers_path}


def test_advance_blocker_triage_state_tracks_allowed_transitions() -> None:
    assert advance_blocker_triage_state("new", "triage") == "triaged"
    assert advance_blocker_triage_state("triaged", "accept") == "accepted"
    assert advance_blocker_triage_state("accepted", "start_fix") == "in_progress"
    assert advance_blocker_triage_state("in_progress", "block") == "blocked"
    assert advance_blocker_triage_state("blocked", "resolve") == "resolved"
    assert advance_blocker_triage_state("resolved", "reopen") == "triaged"


def test_advance_blocker_triage_state_rejects_invalid_transitions() -> None:
    with pytest.raises(ValueError, match="invalid blocker triage transition"):
        advance_blocker_triage_state("resolved", "accept")


def test_build_bug_bash_dashboard_summarizes_blockers_and_truth_boundary(
    tmp_path: Path,
) -> None:
    paths = _write_inputs(tmp_path)

    payload = build_bug_bash_dashboard(
        json.loads(paths["intake"].read_text(encoding="utf-8")),
        json.loads(paths["blockers"].read_text(encoding="utf-8")),
    )

    assert payload["artifact_id"] == "bug_bash_dashboard"
    assert payload["summary"]["intake_count"] == 3
    assert payload["summary"]["release_blocker_count"] == 3
    assert payload["summary"]["open_release_blocker_count"] == 2
    assert payload["summary"]["closed_release_blocker_count"] == 1
    assert payload["summary"]["blocked_on_release_gate"] is True
    assert payload["summary"]["release_gate_state"] == "blocked_pending_open_release_blockers"
    assert payload["truth_boundary"]["report_only"] is True
    assert payload["truth_boundary"]["release_authority"] is False
    assert payload["release_readiness"]["release_claim_allowed"] is False

    state_counts = payload["summary"]["triage_state_counts"]
    assert state_counts["in_progress"] == 1
    assert state_counts["resolved"] == 1
    assert state_counts["triaged"] == 2

    release_blockers = {row["bug_id"]: row for row in payload["release_blockers"]}
    assert release_blockers["BB-001"]["triage_state"] == "in_progress"
    assert release_blockers["BB-002"]["triage_state"] == "resolved"
    assert release_blockers["BB-004"]["triage_state"] == "triaged"
    assert release_blockers["BB-004"]["open_release_blocker"] is True

    markdown = render_markdown(payload)
    assert "# Bug Bash Dashboard" in markdown
    assert "blocked_pending_open_release_blockers" in markdown
    assert "report only" in markdown.lower()


def test_main_writes_machine_readable_outputs(tmp_path: Path, capsys) -> None:
    paths = _write_inputs(tmp_path)
    output = tmp_path / "artifacts" / "status" / "bug_bash_dashboard.json"
    markdown_output = tmp_path / "docs" / "reports" / "bug_bash_dashboard.md"

    exit_code = main(
        [
            "--intake",
            str(paths["intake"]),
            "--release-blockers",
            str(paths["blockers"]),
            "--output",
            str(output),
            "--markdown-output",
            str(markdown_output),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert payload["artifact_id"] == "bug_bash_dashboard"
    assert payload["summary"]["blocked_on_release_gate"] is True
    assert markdown_output.exists()
    assert '"artifact_id": "bug_bash_dashboard"' in captured.out
