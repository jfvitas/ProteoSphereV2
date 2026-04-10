from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_mega_motifbase_capture_prep_checklist_requires_explicit_span_accession_and_organism() -> None:
    status_path = REPO_ROOT / "artifacts" / "status" / "p43_mega_motifbase_capture_prep_checklist.json"
    report_path = REPO_ROOT / "docs" / "reports" / "p43_mega_motifbase_capture_prep_checklist.md"

    status = json.loads(status_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")

    assert status["status"] == "capture_prepared"
    assert status["summary"]["motif_reference_target_count"] == 1
    assert status["summary"]["domain_reference_target_count"] == 1
    assert status["summary"]["required_field_count"] == 8
    assert status["summary"]["never_infer_field_count"] == 7
    assert status["readiness"]["capture_prep_ready"] is True
    assert status["readiness"]["payload_captured"] is False
    assert status["readiness"]["library_join_ready"] is False
    assert status["readiness"]["verdict"] == "prep_complete_but_capture_pending"

    assert status["mapping"]["motif_rows"]["summary_surface"] == "ProteinSummaryRecord.context.motif_references"
    assert status["mapping"]["family_rows"]["summary_surface"] == "ProteinSummaryRecord.context.domain_references"
    assert "source_page_url_or_query_fingerprint" in status["required_fields"]
    assert "uniprot_accession_when_joinable" in status["required_fields"]
    assert "span_start_when_joinable" in status["required_fields"]
    assert "span_end_when_joinable" in status["required_fields"]
    assert "organism_when_joinable" in status["required_fields"]
    assert "uniprot_accession" in status["never_infer"]
    assert "residue_span" in status["never_infer"]
    assert "organism" in status["never_infer"]
    assert "release_version" in status["never_infer"]

    assert "ProteinSummaryRecord.context.motif_references" in report
    assert "ProteinSummaryRecord.context.domain_references" in report
    assert "never infer" in report.lower()
    assert "MegaMotifBase" in report
    assert "capture-only" in report
