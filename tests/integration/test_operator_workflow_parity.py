from __future__ import annotations

from pathlib import Path

from scripts.dataset_design_wizard import build_dataset_design_report
from scripts.export_provenance_drilldown import build_provenance_drilldown
from scripts.review_workspace import build_review_workspace
from scripts.validate_operator_state import validate_operator_state

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_operator_workflow_parity_stays_aligned_with_power_shell_and_winui_handoff() -> None:
    validator = validate_operator_state()
    wizard = build_dataset_design_report()
    workspace = build_review_workspace()
    drilldown = build_provenance_drilldown()

    winui_scope = (REPO_ROOT / "docs" / "reports" / "winui_scope.md").read_text(
        encoding="utf-8"
    )
    winui_readme = (REPO_ROOT / "apps" / "ProteoSphereWinUI" / "README.md").read_text(
        encoding="utf-8"
    )
    parity_report = (REPO_ROOT / "docs" / "reports" / "operator_state_parity.md").read_text(
        encoding="utf-8"
    )

    assert validator["status"] == "ok"
    assert validator["parity"]["completion_status"] == "completed"
    assert validator["parity"]["dashboard_status"] == "completed"
    assert validator["parity"]["release_grade_status"] == "closed_not_release_ready"
    assert validator["parity"]["selected_accession_count"] == 12
    assert validator["parity"]["cohort_size"] == 12
    assert validator["live_state"]["benchmark_release_ready"] is False

    assert wizard["summary"]["proposal_count"] == 12
    assert wizard["summary"]["status_counts"] == {
        "supported": 1,
        "weak": 1,
        "blocked": 10,
    }
    assert wizard["summary"]["scenario_covered_count"] == 5
    assert wizard["summary"]["simulation"]["leakage_collisions"] == []

    assert workspace.scenario_count == 6
    assert workspace.promoted_count == 1
    assert workspace.weak_count == 4
    assert workspace.blocked_count == 1
    assert workspace.batch_state == "blocked"
    assert workspace.operator_recipe_ids == (
        "acceptance-review",
        "packet-triage",
        "benchmark-review",
        "soak-readiness",
        "onboarding",
        "training-set-builder",
        "release-grade-review",
        "external-dataset-assessment",
        "overnight-run-readiness",
    )

    assert drilldown["summary"]["entity_trace_count"] == 12
    assert drilldown["summary"]["pair_trace_count"] == 12
    assert drilldown["summary"]["packet_trace_count"] == 12
    assert drilldown["summary"]["unresolved_lane_count"] == 80
    assert drilldown["summary"]["pair_status_counts"] == {
        "partial": 10,
        "unresolved": 2,
    }

    assert "PowerShell interface" in winui_scope
    assert "Environment Gate" in winui_scope
    assert "missing local `winui` template" in winui_scope
    assert "PowerShell interface" in winui_readme
    assert "not implemented yet" in winui_readme
    assert "fails `dotnet new list winui`" in winui_readme
    assert "validated_with_winui_blocker" in parity_report
    assert "PowerShell surface is the active operator path today" in parity_report
