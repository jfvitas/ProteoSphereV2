from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_motif_gap_resolution_status_distinguishes_imported_vs_external_gaps() -> None:
    status_path = REPO_ROOT / "artifacts" / "status" / "p38_motif_gap_resolution_status.json"
    report_path = REPO_ROOT / "docs" / "reports" / "p38_motif_gap_resolution_note.md"

    status = json.loads(status_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")

    assert status["status"] == "attention"
    assert status["summary"]["source_count"] == 3
    assert status["summary"]["satisfiable_from_imported_content_count"] == 1
    assert status["summary"]["true_external_gap_count"] == 2

    elm = next(source for source in status["sources"] if source["source_name"] == "elm")
    mega = next(
        source for source in status["sources"] if source["source_name"] == "mega_motif_base"
    )
    motivated = next(
        source for source in status["sources"] if source["source_name"] == "motivated_proteins"
    )

    assert elm["resolution"] == "satisfiable_from_imported_content"
    assert elm["imported_content_paths"] == [
        "data/raw/protein_data_scope_seed/elm/elm_classes.tsv",
        "data/raw/protein_data_scope_seed/elm/elm_interaction_domains.tsv",
    ]
    assert mega["resolution"] == "true_external_gap"
    assert motivated["resolution"] == "true_external_gap"
    assert mega["evidence_paths"][0] == "artifacts/status/source_coverage_matrix.json"
    assert motivated["evidence_paths"][0] == "artifacts/status/source_coverage_matrix.json"

    assert "already-imported source whose current shape can be satisfied" in report
    assert "mega_motif_base" in report
    assert "motivated_proteins" in report
    assert "true external gap" in report
