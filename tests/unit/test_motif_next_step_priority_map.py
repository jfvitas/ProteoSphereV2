from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_motif_next_step_priority_map_ranks_backbone_elm_then_mega_motifbase() -> None:
    status_path = REPO_ROOT / "artifacts" / "status" / "p45_motif_next_step_priority_map.json"
    report_path = REPO_ROOT / "docs" / "reports" / "p45_motif_next_step_priority_map.md"

    status = json.loads(status_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")

    assert status["status"] == "priority_ready"
    assert status["summary"]["current_backbone_source_count"] == 3
    assert status["summary"]["partial_import_source_count"] == 1
    assert status["summary"]["future_only_source_count"] == 2
    assert status["summary"]["release_grade_ready"] is False

    ranks = [step["rank"] for step in status["priority_steps"]]
    titles = [step["title"] for step in status["priority_steps"]]
    assert ranks == [1, 2, 3]
    assert "InterPro" in titles[0]
    assert "ELM" in titles[1]
    assert "MegaMotifBase" in titles[2]

    assert "motivated_proteins remains future-only" in status["overall_blockers"][2]
    assert "PF accession" in status["priority_steps"][0]["source_specific_fields"]
    assert "ELME accession" in status["priority_steps"][1]["source_specific_fields"]
    assert "page/query fingerprint" in status["priority_steps"][2]["source_specific_fields"]
    assert "uniprot_accession" in status["priority_steps"][0]["corroboration_fields"]
    assert "organism" in status["priority_steps"][1]["corroboration_fields"]
    assert "source_page_url_or_query_fingerprint" in status["priority_steps"][2]["corroboration_fields"]

    assert "InterPro" in report
    assert "PROSITE" in report
    assert "Pfam" in report
    assert "ELM" in report
    assert "MegaMotifBase" in report
    assert "motivated_proteins" in report
