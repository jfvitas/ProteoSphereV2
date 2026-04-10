from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_motif_breadth_action_map_stays_grounded_in_imported_sources_and_true_gaps() -> None:
    status_path = REPO_ROOT / "artifacts" / "status" / "p41_motif_breadth_action_map.json"
    report_path = REPO_ROOT / "docs" / "reports" / "p41_motif_breadth_action_map.md"

    status = json.loads(status_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")

    assert status["status"] == "attention"
    assert status["summary"]["current_library_use_ready_source_count"] == 3
    assert status["summary"]["partial_current_use_source_count"] == 1
    assert status["summary"]["release_grade_breadth_gap_source_count"] == 3
    assert status["readiness"]["current_library_use_ok"] is True
    assert status["readiness"]["release_grade_breadth_ok"] is False
    assert status["readiness"]["verdict"] == "backbone_ready_breadth_blocked"

    backbone_names = [source["source_name"] for source in status["current_library_use"]["backbone_sources"]]
    partial_names = [source["source_name"] for source in status["current_library_use"]["partial_support_sources"]]
    gap_names = [gap["source_name"] for gap in status["breadth_gap_sources"]]

    assert backbone_names == ["interpro", "prosite", "pfam"]
    assert partial_names == ["elm"]
    assert gap_names == ["elm", "mega_motif_base", "motivated_proteins"]
    assert status["breadth_gap_sources"][0]["gap_type"] == "local_import_promotion_needed"
    assert status["breadth_gap_sources"][1]["gap_type"] == "true_external_gap"
    assert status["breadth_gap_sources"][2]["gap_type"] == "true_external_gap"

    assert "InterPro" in report
    assert "PROSITE" in report
    assert "Pfam" in report
    assert "ELM" in report
    assert "mega_motif_base" in report
    assert "motivated_proteins" in report
    assert "release-grade breadth" in report
