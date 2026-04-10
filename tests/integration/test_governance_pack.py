"""Governance pack integration coverage."""

# ruff: noqa: I001

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE_PACK_PATH = REPO_ROOT / "docs" / "reports" / "p24_governance_pack.md"

REQUIRED_ARTIFACTS = (
    REPO_ROOT / "docs" / "reports" / "release_program_master_plan.md",
    REPO_ROOT / "docs" / "reports" / "release_artifact_hardening.md",
    REPO_ROOT / "docs" / "reports" / "release_benchmark_bundle.md",
    REPO_ROOT / "docs" / "reports" / "release_grade_gap_analysis.md",
    REPO_ROOT / "docs" / "reports" / "release_provenance_lineage_gap_analysis.md",
    REPO_ROOT / "docs" / "reports" / "release_stabilization_regression.md",
    REPO_ROOT / "docs" / "reports" / "p24_rc_signoff_plan.md",
    REPO_ROOT / "docs" / "runbooks" / "support_simulation_pack.md",
)


def test_governance_pack_exists_and_is_report_only() -> None:
    assert GOVERNANCE_PACK_PATH.exists(), "governance pack report is missing"

    content = GOVERNANCE_PACK_PATH.read_text(encoding="utf-8")
    assert content.strip(), "governance pack report is empty"
    assert "report-only" in content
    assert "fail closed" in content
    assert "blocked_on_release_grade_bar" in content
    assert "contribution expectations" in content.lower()
    assert "support expectations" in content.lower()
    assert "maintenance expectations" in content.lower()


def test_governance_pack_lists_required_release_governance_artifacts() -> None:
    content = GOVERNANCE_PACK_PATH.read_text(encoding="utf-8")

    for artifact in REQUIRED_ARTIFACTS:
        assert artifact.exists(), f"required governance artifact is missing: {artifact}"
        assert artifact.name in content, f"missing artifact reference: {artifact.name}"


def test_governance_pack_keeps_truth_boundaries_explicit() -> None:
    content = GOVERNANCE_PACK_PATH.read_text(encoding="utf-8").lower()

    required_phrases = (
        "release remains blocked",
        "contribution-safe",
        "support readiness",
        "maintenance work",
        "current release program",
        "blocker state stays accurate",
    )
    for phrase in required_phrases:
        assert phrase in content, f"missing truth-boundary phrase: {phrase}"
