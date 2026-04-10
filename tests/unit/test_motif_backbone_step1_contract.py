from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_motif_backbone_step1_contract_keeps_scope_to_interpro_prosite_and_local_pfam() -> None:
    status_path = REPO_ROOT / "artifacts" / "status" / "p46_motif_backbone_step1_contract.json"
    report_path = REPO_ROOT / "docs" / "reports" / "p46_motif_backbone_step1_contract.md"

    status = json.loads(status_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")

    assert status["status"] == "implementation_ready"
    assert status["summary"]["joinable_backbone_source_count"] == 3
    assert status["summary"]["output_surface_count"] == 3
    assert status["summary"]["blocked_future_lane_count"] == 2
    assert status["readiness"]["implementation_ready"] is True
    assert status["readiness"]["payload_captured"] is False
    assert status["readiness"]["verdict"] == "step1_contract_ready"

    source_names = [source["source_name"] for source in status["source_backbone"]]
    assert source_names == ["interpro", "pfam", "prosite"]
    assert status["emission_order"] == [
        "ProteinSummaryRecord.context.domain_references",
        "ProteinSummaryRecord.context.motif_references",
        "ProteinSummaryRecord.context.provenance_pointers",
    ]
    assert status["source_backbone"][0]["emit_first"] is True
    assert status["source_backbone"][1]["emit_first"] is True
    assert status["source_backbone"][2]["emit_first"] is True
    assert "UniProt accession" in status["required_joins"]["interpro"]
    assert "span_start" in status["required_joins"]["pfam"]
    assert "PDOC accession" in status["required_joins"]["prosite"]
    assert "ELM" in status["truth_boundaries"][1]
    assert "MegaMotifBase" in status["truth_boundaries"][2]

    assert "domain_references" in report
    assert "motif_references" in report
    assert "provenance_pointers" in report
    assert "InterPro" in report
    assert "PROSITE" in report
    assert "Pfam" in report
    assert "ELM" in report
    assert "MegaMotifBase" in report
