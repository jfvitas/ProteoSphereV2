from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_motif_scope_completeness_view_reports_real_imported_coverage_and_true_gaps() -> None:
    status_path = REPO_ROOT / "artifacts" / "status" / "p40_motif_scope_completeness_view.json"
    report_path = REPO_ROOT / "docs" / "reports" / "p40_motif_scope_completeness_view.md"

    status = json.loads(status_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")

    assert status["status"] == "not_release_grade"
    assert status["summary"]["imported_motif_source_count"] == 4
    assert status["summary"]["complete_imported_source_count"] == 2
    assert status["summary"]["partial_imported_source_count"] == 1
    assert status["summary"]["genuinely_external_gap_count"] == 2
    assert status["readiness"]["broad_enough_for_backbone"] is True
    assert status["readiness"]["deep_enough_for_release_grade_motif_support"] is False
    assert status["readiness"]["verdict"] == "not_yet_release_grade"

    imported_names = [source["source_name"] for source in status["imported_coverage"]]
    assert imported_names == ["interpro", "prosite", "pfam", "elm"]
    assert status["imported_coverage"][0]["registry_status"] == "complete"
    assert status["imported_coverage"][1]["registry_status"] == "complete"
    assert status["imported_coverage"][2]["registry_status"] == "present"
    assert status["imported_coverage"][3]["registry_status"] == "partial"

    gap_names = [gap["source_name"] for gap in status["external_gaps"]]
    assert gap_names == ["mega_motif_base", "motivated_proteins"]
    assert all(gap["status"] == "true_external_gap" for gap in status["external_gaps"])

    assert "release-grade motif support" in report
    assert "InterPro" in report
    assert "PROSITE" in report
    assert "Pfam" in report
    assert "ELM" in report
    assert "mega_motif_base" in report
    assert "motivated_proteins" in report
