from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_ligand_stage1_operator_queue_preview(tmp_path: Path) -> None:
    pilot_preview = tmp_path / "ligand_identity_pilot_preview.json"
    support_preview = tmp_path / "ligand_support_readiness_preview.json"
    output_json = tmp_path / "ligand_stage1_operator_queue_preview.json"
    output_md = tmp_path / "ligand_stage1_operator_queue_preview.md"

    pilot_preview.write_text(
        json.dumps(
            {
                "deferred_accession": "Q9UCM0",
                "deferred_reason": "fresh_acquisition_required",
                "rows": [
                    {
                        "rank": 1,
                        "accession": "P00387",
                        "source_ref": "ligand:P00387",
                        "pilot_role": "lead_anchor",
                        "next_truthful_stage": "ingest_local_bulk_assay",
                    },
                    {
                        "rank": 2,
                        "accession": "Q9NZD4",
                        "source_ref": "ligand:Q9NZD4",
                        "pilot_role": "bridge_rescue_candidate",
                        "next_truthful_stage": (
                            "Ingest the local structure bridge for Q9NZD4 using 1Y01"
                        ),
                    },
                    {
                        "rank": 3,
                        "accession": "P09105",
                        "source_ref": "ligand:P09105",
                        "pilot_role": "support_candidate",
                        "next_truthful_stage": "hold_for_ligand_acquisition",
                    },
                    {
                        "rank": 4,
                        "accession": "Q2TAC2",
                        "source_ref": "ligand:Q2TAC2",
                        "pilot_role": "support_candidate",
                        "next_truthful_stage": "hold_for_ligand_acquisition",
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    support_preview.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "accession": "P00387",
                        "pilot_lane_status": "bulk_assay_actionable",
                        "current_blocker": "support_only_only_no_ligand_rows_materialized",
                    },
                    {
                        "accession": "Q9NZD4",
                        "pilot_lane_status": "rescuable_now",
                        "current_blocker": "bridge_rescue_not_materialized",
                    },
                    {
                        "accession": "P09105",
                        "pilot_lane_status": "structure_companion_only",
                        "current_blocker": "no_local_ligand_evidence_yet",
                    },
                    {
                        "accession": "Q2TAC2",
                        "pilot_lane_status": "structure_companion_only",
                        "current_blocker": "no_local_ligand_evidence_yet",
                    },
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_ligand_stage1_operator_queue_preview.py"),
            "--ligand-identity-pilot-preview",
            str(pilot_preview),
            "--ligand-support-readiness-preview",
            str(support_preview),
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
    assert payload["row_count"] == 4
    assert [row["accession"] for row in payload["ordered_rows"]] == [
        "P00387",
        "Q9NZD4",
        "P09105",
        "Q2TAC2",
    ]
    assert payload["deferred_row"]["accession"] == "Q9UCM0"
    assert payload["truth_boundary"]["report_only"] is True
    assert payload["truth_boundary"]["ligand_rows_materialized"] is False
