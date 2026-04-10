from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_structure_followup_payload_preview(tmp_path: Path) -> None:
    payload_schema = {
        "payload_scope": {
            "accession": "P31749",
        }
    }
    next_safe_impl_order = {
        "next_safe_target": {
            "accession": "P04637",
        }
    }
    anchor_candidates = {
        "rows": [
            {
                "accession": "P31749",
                "protein_ref": "protein:P31749",
                "recommended_experimental_anchor": {
                    "pdb_id": "7NH5",
                    "chain_id": "A",
                    "coverage": 0.927,
                    "experimental_method": "X-ray diffraction",
                    "resolution": 1.9,
                    "unp_start": 2,
                    "unp_end": 446,
                },
                "candidate_variant_anchors": [
                    {
                        "summary_id": "protein_variant:protein:P31749:K14Q",
                        "variant_signature": "K14Q",
                    }
                ],
            },
            {
                "accession": "P04637",
                "protein_ref": "protein:P04637",
                "recommended_experimental_anchor": {
                    "pdb_id": "9R2Q",
                    "chain_id": "K",
                    "coverage": 1.0,
                    "experimental_method": "Electron Microscopy",
                    "resolution": 3.2,
                    "unp_start": 1,
                    "unp_end": 393,
                },
                "candidate_variant_anchors": [
                    {
                        "summary_id": "protein_variant:protein:P04637:Q5H",
                        "variant_signature": "Q5H",
                    }
                ],
            }
        ]
    }
    anchor_validation = {
        "status": "aligned",
        "validated_rows": [
            {
                "accession": "P31749",
                "recommended_anchor_present_in_best_targets": True,
                "variant_positions_within_recommended_span": True,
                "candidate_variant_anchor_count": 1,
            },
            {
                "accession": "P04637",
                "recommended_anchor_present_in_best_targets": True,
                "variant_positions_within_recommended_span": True,
                "candidate_variant_anchor_count": 1,
            }
        ],
    }

    schema_path = tmp_path / "p69_structure_followup_payload_schema.json"
    impl_order_path = tmp_path / "p72_structure_followup_next_safe_impl_order.json"
    candidates_path = tmp_path / "structure_followup_anchor_candidates.json"
    validation_path = tmp_path / "structure_followup_anchor_validation.json"
    output_json = tmp_path / "structure_followup_payload_preview.json"
    output_md = tmp_path / "structure_followup_payload_preview.md"
    schema_path.write_text(json.dumps(payload_schema), encoding="utf-8")
    impl_order_path.write_text(json.dumps(next_safe_impl_order), encoding="utf-8")
    candidates_path.write_text(json.dumps(anchor_candidates), encoding="utf-8")
    validation_path.write_text(json.dumps(anchor_validation), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_structure_followup_payload_preview.py"),
            "--payload-schema",
            str(schema_path),
            "--next-safe-impl-order",
            str(impl_order_path),
            "--anchor-candidates",
            str(candidates_path),
            "--anchor-validation",
            str(validation_path),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["status"] == "complete"
    assert payload["target_accession"] == "P31749"
    assert payload["payload_accessions"] == ["P31749", "P04637"]
    assert payload["payload_row_count"] == 2
    assert payload["payload_rows"][0]["variant_ref"] == "protein_variant:protein:P31749:K14Q"
    assert payload["payload_rows"][1]["variant_ref"] == "protein_variant:protein:P04637:Q5H"
    assert payload["payload_rows"][0]["structure_id"] == "7NH5"
    assert payload["payload_rows"][1]["structure_id"] == "9R2Q"
    assert payload["validation_context"]["validated_accessions"] == ["P31749", "P04637"]
    assert payload["validation_context"]["candidate_variant_anchor_count_total"] == 2
    assert payload["truth_boundary"]["candidate_only_no_variant_anchor"] is True
    assert "Structure Follow-Up Payload Preview" in output_md.read_text(encoding="utf-8")
