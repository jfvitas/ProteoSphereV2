from __future__ import annotations

import json
from pathlib import Path

from scripts.release_blocker_tracker import build_release_blocker_tracker, main, render_markdown


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_build_release_blocker_tracker_ranks_open_unowned_before_owned_and_closed(
    tmp_path: Path,
) -> None:
    payload = build_release_blocker_tracker(
        release_blockers_payload=[
            {
                "blocker_id": "RB-003",
                "title": "Closed owned blocker",
                "owner": "Sam",
                "closure_state": "closed",
                "severity": "low",
                "priority": "P3",
                "triage_state": "resolved",
            },
            {
                "blocker_id": "RB-001",
                "title": "Open unowned blocker",
                "triage_state": "in_progress",
                "release_blocker": True,
                "severity": "blocker",
                "priority": "P0",
            },
            {
                "blocker_id": "RB-002",
                "title": "Open owned blocker",
                "owner": "Ava",
                "triage_state": "blocked",
                "release_blocker": True,
                "severity": "critical",
                "priority": "P1",
            },
        ]
    )

    assert payload["artifact_id"] == "release_blocker_tracker"
    assert payload["status"] == "report_only"
    assert payload["summary"]["open_blocker_count"] == 2
    assert payload["summary"]["closure_unknown_count"] == 0
    assert payload["summary"]["closed_blocker_count"] == 1
    assert payload["summary"]["owned_count"] == 2
    assert payload["summary"]["unowned_count"] == 1
    assert payload["summary"]["blocked_release_gate"] is True
    assert payload["release_readiness"]["release_claim_allowed"] is False
    assert payload["truth_boundary"]["report_only"] is True
    assert payload["blockers"][0]["blocker_id"] == "RB-001"
    assert payload["blockers"][0]["tracker_status"] == "open_unowned"
    assert payload["blockers"][1]["blocker_id"] == "RB-002"
    assert payload["blockers"][1]["tracker_status"] == "open_owned"
    assert payload["blockers"][2]["blocker_id"] == "RB-003"
    assert payload["blockers"][2]["tracker_status"] == "closed_owned"
    assert payload["blockers"][0]["open_release_blocker"] is True
    assert payload["blockers"][2]["is_closed"] is True

    markdown = render_markdown(payload)
    assert "# Release Blocker Tracker" in markdown
    assert "open_unowned" in markdown
    assert "closed_owned" in markdown


def test_build_release_blocker_tracker_fail_closes_on_conflicting_closure_evidence() -> None:
    payload = build_release_blocker_tracker(
        release_blockers_payload=[
            {
                "blocker_id": "RB-010",
                "title": "Conflicting blocker",
                "release_blocker": True,
                "triage_state": "resolved",
                "severity": "blocker",
                "priority": "P0",
            },
            {
                "blocker_id": "RB-011",
                "title": "Closed blocker",
                "owner": "Maya",
                "closure_state": "closed",
                "triage_state": "resolved",
                "severity": "low",
                "priority": "P3",
            },
        ]
    )

    assert payload["summary"]["closure_unknown_count"] == 1
    ambiguous = payload["blockers"][0]
    assert ambiguous["blocker_id"] == "RB-010"
    assert ambiguous["closure_status"] == "unknown"
    assert ambiguous["is_ambiguous"] is True
    assert ambiguous["conflicting_semantics"] is True
    assert "conflicting open and closed evidence" in ambiguous["closure_reason"]
    assert ambiguous["tracker_status"] == "unknown_unowned"
    assert payload["blockers"][1]["blocker_id"] == "RB-011"
    assert payload["blockers"][1]["closure_status"] == "closed"
    assert payload["summary"]["blocked_release_gate"] is False


def test_main_prefers_dashboard_payload_and_writes_outputs(tmp_path: Path, capsys) -> None:
    dashboard_path = tmp_path / "artifacts" / "status" / "bug_bash_dashboard.json"
    output_json = tmp_path / "artifacts" / "status" / "release_blocker_tracker.json"
    output_md = tmp_path / "docs" / "reports" / "release_blocker_tracker.md"

    _write_json(
        dashboard_path,
        {
            "artifact_id": "bug_bash_dashboard",
            "release_blockers": [
                {
                    "blocker_id": "RB-100",
                    "title": "Dashboard sourced blocker",
                    "owner": "Nia",
                    "triage_state": "triaged",
                    "release_blocker": True,
                    "severity": "critical",
                    "priority": "P1",
                }
            ],
        },
    )

    exit_code = main(
        [
            "--dashboard",
            str(dashboard_path),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(output_json.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert payload["inputs"]["source_mode"] == "dashboard"
    assert payload["summary"]["open_blocker_count"] == 1
    assert payload["summary"]["ownership_status_counts"]["owned"] == 1
    assert output_md.exists()
    assert "# Release Blocker Tracker" in output_md.read_text(encoding="utf-8")
    assert '"artifact_id": "release_blocker_tracker"' in captured.out
