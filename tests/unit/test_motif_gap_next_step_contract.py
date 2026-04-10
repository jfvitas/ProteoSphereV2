from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_motif_gap_next_step_contract_stays_focused_on_true_external_gaps() -> None:
    status_path = REPO_ROOT / "artifacts" / "status" / "p39_motif_gap_next_step_contract.json"
    report_path = REPO_ROOT / "docs" / "reports" / "p39_motif_gap_next_step_contract.md"

    status = json.loads(status_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")

    assert status["status"] == "blocked"
    assert status["summary"]["external_gap_count"] == 2
    assert status["summary"]["local_support_source_count"] == 4
    assert status["summary"]["substitute_family_count"] == 5

    gap_names = [gap["source_name"] for gap in status["external_gaps"]]
    assert gap_names == ["mega_motif_base", "motivated_proteins"]
    assert all(gap["status"] == "true_external_gap" for gap in status["external_gaps"])
    assert all("discover the official surface" in step for step in status["execution_order"][:1])
    assert status["substitute_families"][0]["family_name"] == "InterPro"
    assert status["substitute_families"][1]["family_name"] == "PROSITE"
    assert status["substitute_families"][2]["family_name"] == "ELM"
    assert status["substitute_families"][3]["family_name"] == "Pfam"

    assert "mega_motif_base" in report
    assert "motivated_proteins" in report
    assert "PROSITE" in report
    assert "InterPro" in report
    assert "ELM" in report
    assert "Pfam" in report
    assert "RCSB motif search" in report
