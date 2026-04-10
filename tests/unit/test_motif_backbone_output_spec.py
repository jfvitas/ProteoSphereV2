from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_motif_backbone_output_spec_defines_the_first_three_surfaces() -> None:
    status_path = REPO_ROOT / "artifacts" / "status" / "p47_motif_backbone_output_spec.json"
    report_path = REPO_ROOT / "docs" / "reports" / "p47_motif_backbone_output_spec.md"

    status = json.loads(status_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")

    assert status["status"] == "spec_ready"
    assert status["readiness"]["spec_ready"] is True
    assert status["readiness"]["payload_captured"] is False
    assert status["readiness"]["output_surface_count"] == 3
    assert status["readiness"]["verdict"] == "motif_backbone_output_spec_ready"

    surface_names = [surface["surface_name"] for surface in status["surfaces"]]
    assert surface_names == [
        "domain_references",
        "motif_references",
        "provenance_pointers",
    ]

    domain_fields = status["surfaces"][0]["top_level_fields"]
    motif_fields = status["surfaces"][1]["top_level_fields"]
    provenance_fields = status["surfaces"][2]["top_level_fields"]

    assert domain_fields == motif_fields
    assert provenance_fields == [
        "provenance_id",
        "source_name",
        "source_record_id",
        "release_version",
        "release_date",
        "acquired_at",
        "checksum",
        "join_status",
        "notes",
    ]

    assert status["surfaces"][0]["field_contracts"][0]["value"] == "domain_reference"
    assert status["surfaces"][1]["field_contracts"][0]["value"] == "motif_reference"
    assert status["surfaces"][2]["field_contracts"][7]["value"] == "joined"

    assert "InterPro" in report
    assert "PROSITE" in report
    assert "Pfam" in report
    assert "provenance_pointers" in report
    assert "Do not add ELM in this step." in report
    assert "Do not add MegaMotifBase in this step." in report
