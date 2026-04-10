from __future__ import annotations

# ruff: noqa: I001

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = REPO_ROOT / "docs" / "reports" / "p25_clean_machine_plan.md"

REQUIRED_ARTIFACTS = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "release_bundle_manifest.json",
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "release_support_manifest.json",
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "release_notes.md",
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
    REPO_ROOT / "docs" / "runbooks" / "post_release_maintenance.md",
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "operator_dashboard.json",
    REPO_ROOT / "artifacts" / "status" / "procurement_status_board.json",
    REPO_ROOT / "artifacts" / "status" / "procurement_tail_freeze_gate_preview.json",
    REPO_ROOT / "artifacts" / "status" / "P25-T001.json",
    REPO_ROOT / "artifacts" / "status" / "P25-T005.json",
)


def test_clean_machine_plan_exists_and_is_report_only() -> None:
    assert PLAN_PATH.exists(), "clean-machine plan is missing"

    content = PLAN_PATH.read_text(encoding="utf-8")
    assert content.strip(), "clean-machine plan is empty"
    assert "report-only" in content
    assert "fail-closed" in content
    assert "blocked_on_release_grade_bar" in content
    assert "clean-machine" in content.lower()
    assert "tagged artifacts" in content.lower()


def test_clean_machine_plan_covers_install_packet_and_benchmark_replay() -> None:
    content = PLAN_PATH.read_text(encoding="utf-8").lower()

    required_phrases = (
        "install replay",
        "packet replay",
        "benchmark replay",
        "released system",
        "rebuild",
        "replay",
    )
    for phrase in required_phrases:
        assert phrase in content, f"missing replay phrase: {phrase}"


def test_clean_machine_plan_lists_required_reproduction_artifacts() -> None:
    content = PLAN_PATH.read_text(encoding="utf-8")

    for artifact in REQUIRED_ARTIFACTS:
        assert artifact.exists(), f"required reproduction artifact is missing: {artifact}"
        assert artifact.name in content, f"missing reproduction artifact reference: {artifact.name}"


def test_clean_machine_plan_keeps_truth_boundaries_explicit() -> None:
    content = PLAN_PATH.read_text(encoding="utf-8").lower()

    required_phrases = (
        "not a claim that release is already authorized",
        "production readiness",
        "missing, stale, or lineage-inconsistent",
        "prototype",
        "release-grade bar",
        "report-only, fail-closed",
    )
    for phrase in required_phrases:
        assert phrase in content, f"missing truth-boundary phrase: {phrase}"
