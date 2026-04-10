from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_motif_backbone_validation_contract_requires_the_expected_surfaces_and_evidence() -> None:
    status_path = REPO_ROOT / "artifacts" / "status" / "p48_motif_backbone_validation_contract.json"
    report_path = REPO_ROOT / "docs" / "reports" / "p48_motif_backbone_validation_contract.md"

    status = json.loads(status_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")

    assert status["status"] == "validation_contract_ready"
    assert status["readiness"]["validation_contract_ready"] is True
    assert status["readiness"]["payload_captured"] is False
    assert status["readiness"]["check_count"] == 5
    assert status["readiness"]["verdict"] == "motif_backbone_validation_contract_ready"

    assert set(status["surface_requirements"]) == {
        "domain_references",
        "motif_references",
        "provenance_pointers",
    }
    assert status["surface_requirements"]["domain_references"]["allowed_sources"] == [
        "InterPro",
        "Pfam",
    ]
    assert status["surface_requirements"]["motif_references"]["allowed_sources"] == [
        "PROSITE",
    ]
    assert status["surface_requirements"]["provenance_pointers"]["allowed_sources"] == [
        "InterPro",
        "Pfam",
        "PROSITE",
    ]

    check_ids = [check["check_id"] for check in status["validation_checks"]]
    assert check_ids == [
        "domain_surface_shape",
        "motif_surface_shape",
        "provenance_surface_shape",
        "evidence_alignment",
        "truth_boundary_exclusion",
    ]

    assert "InterPro" in report
    assert "PROSITE" in report
    assert "Pfam" in report
    assert "Do not accept ELM in this step." in report
    assert "Do not accept MegaMotifBase in this step." in report
    assert "Pass Criteria" in report
