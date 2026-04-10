from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_validate_structure_followup_anchor_candidates(tmp_path: Path) -> None:
    anchor_candidates = {
        "row_count": 2,
        "rows": [
            {
                "accession": "P04637",
                "best_experimental_targets": [
                    {
                        "pdb_id": "9R2Q",
                        "chain_id": "K",
                        "unp_start": 1,
                        "unp_end": 393,
                    }
                ],
                "recommended_experimental_anchor": {
                    "pdb_id": "9R2Q",
                    "chain_id": "K",
                    "unp_start": 1,
                    "unp_end": 393,
                },
                "alphafold_primary_model": {"entry_id": "AF-P04637-F1"},
                "candidate_variant_anchors": [
                    {"variant_signature": "Q5H", "variant_position": 5},
                    {"variant_signature": "R248Q", "variant_position": 248},
                ],
                "candidate_variant_anchor_count": 2,
                "variant_position_parse_failures": 1,
            },
            {
                "accession": "P31749",
                "best_experimental_targets": [
                    {
                        "pdb_id": "7NH5",
                        "chain_id": "A",
                        "unp_start": 2,
                        "unp_end": 446,
                    }
                ],
                "recommended_experimental_anchor": {
                    "pdb_id": "7NH5",
                    "chain_id": "A",
                    "unp_start": 2,
                    "unp_end": 446,
                },
                "alphafold_primary_model": {"entry_id": "AF-P31749-F1"},
                "candidate_variant_anchors": [
                    {"variant_signature": "E17K", "variant_position": 17},
                ],
                "candidate_variant_anchor_count": 1,
                "variant_position_parse_failures": 0,
            },
        ],
        "summary": {
            "candidate_accessions": ["P04637", "P31749"],
        },
        "truth_boundary": {
            "direct_structure_backed_join_materialized": False,
        },
    }
    matrix = {
        "summary": {
            "high_priority_accessions": ["P04637", "P31749"],
        }
    }
    anchor_path = tmp_path / "structure_followup_anchor_candidates.json"
    matrix_path = tmp_path / "summary_library_operator_accession_matrix.json"
    output_json = tmp_path / "structure_followup_anchor_validation.json"
    output_md = tmp_path / "structure_followup_anchor_validation.md"
    anchor_path.write_text(json.dumps(anchor_candidates), encoding="utf-8")
    matrix_path.write_text(json.dumps(matrix), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "validate_structure_followup_anchor_candidates.py"),
            "--anchor-candidates",
            str(anchor_path),
            "--operator-accession-matrix",
            str(matrix_path),
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
    assert payload["status"] == "aligned"
    assert payload["validation"]["validated_row_count"] == 2
    assert payload["validation"]["candidate_variant_anchor_count"] == 3
    assert payload["validation"]["issues"] == []
    assert payload["validated_rows"][0]["recommended_anchor"] == "9R2Q:K"
    assert payload["validated_rows"][0]["variant_positions_within_recommended_span"] is True
    assert "Structure Follow-Up Anchor Validation" in output_md.read_text(encoding="utf-8")
