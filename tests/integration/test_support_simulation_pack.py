"""Support simulation pack integration coverage."""

# ruff: noqa: I001

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNBOOK_PATH = REPO_ROOT / "docs" / "runbooks" / "support_simulation_pack.md"


def test_support_simulation_pack_exists_and_is_nonempty() -> None:
    assert RUNBOOK_PATH.exists(), "support simulation pack runbook is missing"
    content = RUNBOOK_PATH.read_text(encoding="utf-8")

    assert content.strip(), "support simulation pack runbook is empty"
    assert "report-only" in content
    assert "install" in content
    assert "packet" in content
    assert "benchmark" in content
    assert "recovery" in content


def test_support_simulation_pack_covers_all_incident_classes() -> None:
    content = RUNBOOK_PATH.read_text(encoding="utf-8").lower()

    required_sections = (
        "install incident",
        "packet incident",
        "benchmark incident",
        "recovery incident",
    )
    for section in required_sections:
        assert section in content, f"missing runbook section: {section}"


def test_support_simulation_pack_keeps_truth_boundaries_explicit() -> None:
    content = RUNBOOK_PATH.read_text(encoding="utf-8")

    required_phrases = (
        "runtime maturity remains prototype-level",
        "source coverage depth",
        "provenance and reporting depth",
        "assembled_with_blockers",
        "summary-only",
        "lineage-aware and fail closed",
    )
    for phrase in required_phrases:
        assert phrase in content, f"missing truth-boundary phrase: {phrase}"


def test_support_simulation_pack_lists_support_evidence_and_ownership() -> None:
    content = RUNBOOK_PATH.read_text(encoding="utf-8")

    required_evidence = (
        "install_bootstrap_state.json",
        "packet_deficit_dashboard.json",
        "release_bundle_manifest.json",
        "release_support_manifest.json",
        "P23-T003.json",
        "P23-T004.json",
    )
    required_ownership = (
        "Install/bootstrap owner",
        "Packet owner",
        "Benchmark owner",
        "Recovery owner",
        "Operator owner",
    )

    for item in required_evidence:
        assert item in content, f"missing evidence reference: {item}"
    for item in required_ownership:
        assert item in content, f"missing ownership label: {item}"
