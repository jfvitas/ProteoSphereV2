from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MAINTENANCE_RUNBOOK_PATH = REPO_ROOT / "docs" / "runbooks" / "post_release_maintenance.md"

REQUIRED_MAINTENANCE_ARTIFACTS = (
    REPO_ROOT / "docs" / "reports" / "release_program_master_plan.md",
    REPO_ROOT / "docs" / "reports" / "release_artifact_hardening.md",
    REPO_ROOT / "docs" / "reports" / "release_benchmark_bundle.md",
    REPO_ROOT / "docs" / "reports" / "release_grade_gap_analysis.md",
    REPO_ROOT / "docs" / "reports" / "release_provenance_lineage_gap_analysis.md",
    REPO_ROOT / "docs" / "reports" / "release_stabilization_regression.md",
    REPO_ROOT / "docs" / "reports" / "p24_rc_signoff_plan.md",
    REPO_ROOT / "docs" / "reports" / "p24_rc_regression_matrix.md",
    REPO_ROOT / "docs" / "reports" / "p24_governance_pack.md",
    REPO_ROOT / "docs" / "reports" / "p24_ga_signoff_package.md",
    REPO_ROOT / "docs" / "runbooks" / "support_simulation_pack.md",
)


def test_post_release_maintenance_runbook_exists_and_is_report_only() -> None:
    assert MAINTENANCE_RUNBOOK_PATH.exists(), "maintenance runbook is missing"

    content = MAINTENANCE_RUNBOOK_PATH.read_text(encoding="utf-8")
    assert content.strip(), "maintenance runbook is empty"
    assert "report-only" in content
    assert "fail-closed" in content
    assert "post-release maintenance" in content.lower()
    assert "incident rota" in content.lower()
    assert "blocked_on_release_grade_bar" in content


def test_post_release_maintenance_runbook_lists_required_artifacts() -> None:
    content = MAINTENANCE_RUNBOOK_PATH.read_text(encoding="utf-8")

    for artifact in REQUIRED_MAINTENANCE_ARTIFACTS:
        assert artifact.exists(), f"required maintenance artifact is missing: {artifact}"
        assert artifact.name in content, f"missing maintenance artifact reference: {artifact.name}"


def test_post_release_maintenance_runbook_keeps_truth_boundaries_explicit() -> None:
    content = MAINTENANCE_RUNBOOK_PATH.read_text(encoding="utf-8").lower()

    required_phrases = (
        "current posture remains",
        "local prototype",
        "partial downloads",
        "support triage",
        "recovery lane",
        "no scenario claims release authorization",
    )
    for phrase in required_phrases:
        assert phrase in content, f"missing truth-boundary phrase: {phrase}"
