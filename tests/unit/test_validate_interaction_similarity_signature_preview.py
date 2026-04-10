from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_validate_interaction_similarity_signature_preview(tmp_path: Path) -> None:
    preview_json = tmp_path / "interaction_similarity_signature_preview.json"
    validation_json = tmp_path / "interaction_similarity_signature_validation.json"
    validation_md = tmp_path / "interaction_similarity_signature_validation.md"
    bundle_manifest = tmp_path / "bundle_manifest.json"

    preview_json.write_text(
        json.dumps(
            {
                "artifact_id": "interaction_similarity_signature_preview",
                "schema_id": "proteosphere-interaction-similarity-signature-preview-2026-04-02",
                "status": "complete",
                "row_count": 2,
                "rows": [
                    {
                        "signature_id": "interaction_similarity:P69905",
                        "protein_ref": "protein:P69905",
                        "accession": "P69905",
                        "interaction_similarity_group": "biogrid:present__string:partial_on_disk__intact:unavailable",
                        "candidate_only": True,
                        "biogrid_registry_state": "present",
                        "biogrid_disk_state": "present",
                        "biogrid_matched_row_count": 2,
                        "string_registry_state": "missing",
                        "string_disk_state": "partial_on_disk",
                        "intact_registry_state": "present",
                        "intact_disk_state": "present",
                        "intact_probe_state": "present",
                        "intact_probe_row_count": 5,
                    },
                    {
                        "signature_id": "interaction_similarity:P09105",
                        "protein_ref": "protein:P09105",
                        "accession": "P09105",
                        "interaction_similarity_group": "biogrid:present__string:partial_on_disk__intact:unavailable",
                        "candidate_only": True,
                        "biogrid_registry_state": "present",
                        "biogrid_disk_state": "present",
                        "biogrid_matched_row_count": 1,
                        "string_registry_state": "missing",
                        "string_disk_state": "partial_on_disk",
                        "intact_registry_state": "present",
                        "intact_disk_state": "present",
                        "intact_probe_state": "present",
                        "intact_probe_row_count": 5,
                    },
                ],
                "summary": {
                    "accession_count": 2,
                    "unique_interaction_similarity_group_count": 1,
                    "candidate_only_row_count": 2,
                    "biogrid_matched_row_total": 3,
                    "string_top_level_file_present_count": 1,
                    "string_top_level_file_partial_count": 1,
                    "string_top_level_file_missing_count": 1,
                    "intact_present_count": 2,
                    "source_overlap_accessions": ["P69905", "P09105"],
                },
                "source_surfaces": {
                    "biogrid": {"manifest_state": "present", "disk_state": "present"},
                    "string": {"manifest_state": "missing", "disk_state": "partial_on_disk"},
                    "intact": {"manifest_state": "present", "disk_state": "present"},
                },
                "bundle_alignment": {
                    "bundle_id": "proteosphere-lite",
                    "bundle_status": "preview_generated_verified_assets",
                    "interaction_similarity_signatures_included": False,
                    "interaction_similarity_signatures_record_count": 0,
                },
                "truth_boundary": {
                    "report_only": True,
                    "ready_for_bundle_preview": False,
                    "interaction_family_materialized": False,
                    "direct_interaction_family_claimed": False,
                    "string_family_materialized": False,
                    "intact_pair_evidence_claimed": True,
                    "candidate_only_rows": True,
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    bundle_manifest.write_text(
        json.dumps(
            {
                "bundle_id": "proteosphere-lite",
                "bundle_status": "preview_generated_verified_assets",
                "record_counts": {"interaction_similarity_signatures": 0},
                "table_families": [
                    {
                        "family_name": "interaction_similarity_signatures",
                        "included": False,
                        "record_count": 0,
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "validate_interaction_similarity_signature_preview.py"),
            "--preview-json",
            str(preview_json),
            "--bundle-manifest",
            str(bundle_manifest),
            "--output-json",
            str(validation_json),
            "--output-md",
            str(validation_md),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    payload = json.loads(validation_json.read_text(encoding="utf-8"))
    assert payload["status"] == "aligned"
    assert payload["validation"]["row_count"] == 2
    assert payload["validation"]["candidate_only_accessions"] == ["P69905", "P09105"]
    assert payload["validation"]["bundle_interaction_similarity_signatures_record_count"] == 0
    assert payload["truth_boundary"]["report_only"] is True
    assert payload["truth_boundary"]["bundle_safe_immediately"] is False
    assert "Interaction Similarity Signature Validation" in validation_md.read_text(
        encoding="utf-8"
    )
