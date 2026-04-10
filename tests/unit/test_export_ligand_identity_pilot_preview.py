from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_ligand_identity_pilot_preview(tmp_path: Path) -> None:
    pilot_order = {
        "ordering": [
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
                "next_truthful_stage": "bridge_step",
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
            {
                "rank": 5,
                "accession": "Q9UCM0",
                "source_ref": "ligand:Q9UCM0",
                "pilot_role": "deferred_accession",
                "next_truthful_stage": "fresh_acquisition_required",
            },
        ]
    }
    ligand_support = {
        "rows": [
            {
                "accession": "P00387",
                "pilot_lane_status": "bulk_assay_actionable",
                "current_blocker": "support_only",
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
    }
    p00387_payload = {
        "summary": {
            "target_chembl_id": "CHEMBL2146",
            "target_pref_name": "NADH-cytochrome b5 reductase",
            "activity_count_total": 93,
            "rows_emitted": 25,
            "distinct_ligand_count_in_payload": 23,
        },
        "rows": [
            {
                "ligand_chembl_id": "CHEMBL35888",
                "standard_type": "IC50",
                "standard_value": 10840,
                "standard_units": "nM",
            }
        ],
    }
    bridge_payload = {
        "entries": [
            {
                "accession": "Q9NZD4",
                "pdb_id": "1Y01",
                "bridge_state": "ready_now",
                "selected_ligand": {
                    "component_id": "CHK",
                    "component_name": "Cyclitol derivative",
                    "component_role": "primary_binder",
                    "chain_ids": ["B"],
                },
            }
        ]
    }

    order_path = tmp_path / "order.json"
    support_path = tmp_path / "support.json"
    p00387_payload_path = tmp_path / "p00387_payload.json"
    bridge_payload_path = tmp_path / "bridge_payload.json"
    output_json = tmp_path / "pilot.json"
    output_md = tmp_path / "pilot.md"
    order_path.write_text(json.dumps(pilot_order), encoding="utf-8")
    support_path.write_text(json.dumps(ligand_support), encoding="utf-8")
    p00387_payload_path.write_text(json.dumps(p00387_payload), encoding="utf-8")
    bridge_payload_path.write_text(json.dumps(bridge_payload), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_ligand_identity_pilot_preview.py"),
            "--pilot-order",
            str(order_path),
            "--ligand-support",
            str(support_path),
            "--p00387-payload",
            str(p00387_payload_path),
            "--bridge-payload",
            str(bridge_payload_path),
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
    assert payload["row_count"] == 4
    assert payload["rows"][0]["accession"] == "P00387"
    assert payload["rows"][0]["grounded_evidence_kind"] == "local_chembl_bulk_assay_summary"
    assert payload["rows"][0]["grounded_evidence"]["activity_count_total"] == 93
    assert payload["rows"][1]["grounded_evidence_kind"] == "local_structure_bridge_summary"
    assert payload["rows"][1]["grounded_evidence"]["pdb_id"] == "1Y01"
    assert payload["grounded_accessions"] == ["P00387", "Q9NZD4"]
    assert payload["grounded_accession_count"] == 2
    assert payload["deferred_accession"] == "Q9UCM0"
    assert payload["truth_boundary"]["ligand_rows_materialized"] is False
    assert "Ligand Identity Pilot Preview" in output_md.read_text(encoding="utf-8")
