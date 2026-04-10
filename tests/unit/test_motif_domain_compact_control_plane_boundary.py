from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_motif_domain_compact_control_plane_boundary_stays_nongoverning() -> None:
    status_path = REPO_ROOT / "artifacts" / "status" / "p90_motif_domain_compact_control_plane_boundary.json"
    report_path = REPO_ROOT / "docs" / "reports" / "p90_motif_domain_compact_control_plane_boundary.md"

    status = json.loads(status_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")

    assert status["status"] == "report_only"
    assert status["control_plane_decision"]["should_feed_eligibility"] is False
    assert status["control_plane_decision"]["should_feed_split"] is False
    assert status["control_plane_decision"]["should_feed_leakage_governance"] is False
    assert status["control_plane_decision"]["current_status"] == "library_only"
    assert status["current_boundary"]["governance_role"] == "audit_only"
    assert status["current_boundary"]["split_role"] == "none"
    assert status["current_boundary"]["eligibility_role"] == "none"
    assert status["current_boundary"]["dictionary_rows"]["namespace_count"] == 3
    assert status["current_boundary"]["dictionary_rows"]["row_count"] == 55

    assert status["next_unlock_condition"]["first_truthful_governance_effect"] == "library_only"
    assert (
        status["next_unlock_condition"]["first_truthful_task_effect"]
        == "eligible_for_task only after a task-specific preview says so"
    )

    assert "should not feed eligibility" in report
    assert "should not feed split" in report
    assert "library_only" in report
    assert "task-specific preview" in report
    assert "ELM remains candidate-only" in report
