from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_mega_motifbase_acquisition_contract_stays_scrape_only_and_non_inventive() -> None:
    status_path = REPO_ROOT / "artifacts" / "status" / "p42_mega_motifbase_acquisition_contract.json"
    report_path = REPO_ROOT / "docs" / "reports" / "p42_mega_motifbase_acquisition_contract.md"

    status = json.loads(status_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")

    assert status["status"] == "blocked_pending_capture"
    assert status["lane"] == "mega_motif_base"
    assert status["summary"]["current_library_backbone_source_count"] == 3
    assert status["summary"]["partial_support_source_count"] == 1
    assert status["summary"]["target_lane_count"] == 1
    assert status["summary"]["payload_available"] is False

    surfaces = status["source_surface"]["public_entry_points"]
    assert surfaces[0] == "https://caps.ncbs.res.in/MegaMotifbase/"
    assert "download.html" in surfaces[1]
    assert "search.html" in surfaces[2]
    assert "famlist.html" in surfaces[3]
    assert "sflist.html" in surfaces[4]
    assert status["release_pinning"]["surface_mode"] == "scrape_only"
    assert status["release_pinning"]["do_not_fake_download"] is True
    assert "uniprot_accession" in status["normalization_rules"]["required_fields"]
    assert "source_native_id" in status["normalization_rules"]["required_fields"]
    assert status["merge_policy"]["canonical_order"] == [
        "InterPro",
        "PROSITE",
        "Pfam",
        "ELM",
        "MegaMotifBase",
    ]

    assert "No payload is claimed" in report
    assert "MegaMotifBase" in report
    assert "InterPro" in report
    assert "PROSITE" in report
    assert "Pfam" in report
    assert "ELM" in report
