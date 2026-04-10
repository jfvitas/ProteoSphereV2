from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_mega_motifbase_source_fusion_mapping_stays_on_current_backbone() -> None:
    status_path = REPO_ROOT / "artifacts" / "status" / "p44_mega_motifbase_source_fusion_mapping.json"
    report_path = REPO_ROOT / "docs" / "reports" / "p44_mega_motifbase_source_fusion_mapping.md"

    status = json.loads(status_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")

    assert status["status"] == "mapping_ready"
    assert status["summary"]["current_joinable_source_count"] == 4
    assert status["summary"]["current_supporting_family_source_count"] == 2
    assert status["summary"]["future_capture_lane_count"] == 1
    assert status["summary"]["join_spine_fields"] == ["uniprot_accession", "span_start", "span_end"]

    source_names = [source["source_name"] for source in status["current_sources"]]
    assert source_names == ["interpro", "pfam", "prosite", "elm"]
    assert status["current_sources"][0]["corroborates_with"] == ["pfam", "prosite", "elm"]
    assert status["current_sources"][1]["summary_surfaces"] == ["domain_references"]
    assert status["current_sources"][2]["summary_surfaces"] == ["motif_references"]
    assert status["current_sources"][3]["shared_corroboration_fields"] == [
        "uniprot_accession",
        "span_start",
        "span_end",
        "organism",
    ]
    assert status["future_lane"]["source_name"] == "mega_motif_base"
    assert status["future_lane"]["status"] == "capture_pending"
    assert "source-native ids" in status["future_lane"]["source_specific_fields"]
    assert "source_native_id" in status["never_infer"]
    assert "release_version" in status["never_infer"]
    assert "canonical source labels" in status["library_merge_policy"]["non_overwrite_rule"]

    assert "InterPro" in report
    assert "Pfam" in report
    assert "PROSITE" in report
    assert "ELM" in report
    assert "MegaMotifBase" in report
    assert "UniProt accession" in report
