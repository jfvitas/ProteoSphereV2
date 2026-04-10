from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_motif_domain_compact_preview_family_is_narrow_and_truth_boundaried() -> None:
    status_path = REPO_ROOT / "artifacts" / "status" / "p89_motif_domain_compact_preview_family.json"
    report_path = REPO_ROOT / "docs" / "reports" / "p89_motif_domain_compact_preview_family.md"

    status = json.loads(status_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")

    assert status["status"] == "report_only"
    assert status["family"]["family_name"] == "motif_domain_compact_preview_family"
    assert status["family"]["namespace_count"] == 3
    assert status["family"]["row_count"] == 55
    assert status["family"]["supporting_record_count"] == 30
    assert status["family"]["reference_kind_counts"] == {"domain": 47, "motif": 8}

    included_namespaces = [item["namespace"] for item in status["family"]["included_namespaces"]]
    assert included_namespaces == ["InterPro", "Pfam", "PROSITE"]

    interpro, pfam, prosite = status["family"]["included_namespaces"]
    assert interpro["source_status"] == "complete"
    assert pfam["source_status"] == "present"
    assert prosite["source_status"] == "complete"

    excluded_namespaces = {item["namespace"]: item for item in status["family"]["excluded_namespaces"]}
    assert excluded_namespaces["ELM"]["source_status"] == "partial"
    assert excluded_namespaces["ELM"]["preview_role"] == "candidate_only_non_governing"

    assert status["bundle_truth_boundary"]["ready_for_bundle_preview"] is True
    assert status["bundle_truth_boundary"]["bundle_preview_ready"] is True
    assert status["bundle_truth_boundary"]["bundle_safe_immediately"] is False

    assert "InterPro" in report
    assert "PROSITE" in report
    assert "Pfam" in report
    assert "ELM" in report
    assert "dictionary preview" in report
    assert "not a new acquisition family" in report
