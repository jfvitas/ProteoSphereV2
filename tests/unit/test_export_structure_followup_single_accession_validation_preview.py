from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_structure_followup_single_accession_validation_preview(
    tmp_path: Path,
) -> None:
    single_preview = tmp_path / "structure_followup_single_accession_preview.json"
    anchor_validation = tmp_path / "structure_followup_anchor_validation.json"
    output_json = tmp_path / "structure_followup_single_accession_validation_preview.json"
    output_md = tmp_path / "structure_followup_single_accession_validation_preview.md"

    single_preview.write_text(
        json.dumps(
            {
                "selected_accession": "P31749",
                "deferred_accession": "P04637",
                "payload_row_count": 1,
                "truth_boundary": {
                    "candidate_only_no_variant_anchor": True,
                    "direct_structure_backed_join_certified": False,
                    "ready_for_operator_preview": True,
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    anchor_validation.write_text(
        json.dumps(
            {
                "status": "aligned",
                "validation": {
                    "validated_row_count": 2,
                    "candidate_variant_anchor_count": 10,
                },
                "validated_rows": [
                    {
                        "accession": "P04637",
                        "recommended_anchor_present_in_best_targets": True,
                        "variant_positions_within_recommended_span": True,
                        "candidate_variant_anchor_count": 5,
                    },
                    {
                        "accession": "P31749",
                        "recommended_anchor_present_in_best_targets": True,
                        "variant_positions_within_recommended_span": True,
                        "candidate_variant_anchor_count": 5,
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(
                REPO_ROOT
                / "scripts"
                / "export_structure_followup_single_accession_validation_preview.py"
            ),
            "--single-accession-preview",
            str(single_preview),
            "--anchor-validation",
            str(anchor_validation),
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
    assert payload["selected_accession"] == "P31749"
    assert payload["deferred_accession"] == "P04637"
    assert payload["candidate_variant_anchor_count_total"] == 10
    assert payload["candidate_variant_anchor_count"] == 5
    assert payload["direct_structure_backed_join_certified"] is False
