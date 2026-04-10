from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_motif_lane_acquisition_status_matches_current_artifacts() -> None:
    status_path = REPO_ROOT / "artifacts" / "status" / "p37_motif_lane_acquisition_status.json"
    report_path = REPO_ROOT / "docs" / "reports" / "p37_motif_lane_acquisition_note.md"

    status = json.loads(status_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")

    assert status["status"] == "attention"
    assert status["summary"]["source_count"] == 3
    assert status["summary"]["blocked_missing_source_count"] == 2
    assert status["summary"]["alignment_needed_source_count"] == 1

    source_names = [source["source_name"] for source in status["sources"]]
    assert source_names == ["mega_motif_base", "motivated_proteins", "elm"]

    mega = status["sources"][0]
    motivated = status["sources"][1]
    elm = status["sources"][2]

    assert mega["gap_type"] == "blocked_missing"
    assert mega["broad_mirror_status"] == "missing"
    assert motivated["gap_type"] == "blocked_missing"
    assert motivated["broad_mirror_status"] == "missing"
    assert elm["gap_type"] == "alignment_needed"
    assert elm["local_registry_status"] == "partial"
    assert elm["broad_mirror_status"] == "complete"
    assert elm["broad_mirror_present_files"] == [
        "elm_classes.tsv",
        "elm_interaction_domains.tsv",
    ]

    assert "mega_motif_base" in report
    assert "motivated_proteins" in report
    assert "ELM" in report
    assert "elm_classes.tsv" in report
    assert "elm_interaction_domains.tsv" in report
