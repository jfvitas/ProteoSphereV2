from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_ligand_support_readiness_preview(tmp_path: Path) -> None:
    support_subslice = {
        "live_grounding": {
            "bundle_ligands_included": False,
            "bundle_ligand_record_count": 0,
            "current_ligand_gap_accessions": [
                "P00387",
                "P09105",
                "Q2TAC2",
                "Q9NZD4",
                "Q9UCM0",
            ],
        },
        "support_only_subslice": {
            "support_accessions": ["P00387", "P09105", "Q2TAC2", "Q9NZD4"],
            "deferred_accessions": ["Q9UCM0"],
        },
    }
    packet_dashboard = {
        "packets": [
            {"accession": "P00387", "status": "partial"},
            {"accession": "P09105", "status": "partial"},
            {"accession": "Q2TAC2", "status": "partial"},
            {"accession": "Q9NZD4", "status": "partial"},
        ]
    }
    local_ligand_source_map = {
        "entries": [
            {
                "accession": "P00387",
                "classification": "bulk_assay_actionable",
                "recommended_next_action": "ingest_local_bulk_assay",
            },
            {
                "accession": "P09105",
                "classification": "structure_companion_only",
                "recommended_next_action": "hold_for_ligand_acquisition",
            },
            {
                "accession": "Q2TAC2",
                "classification": "structure_companion_only",
                "recommended_next_action": "hold_for_ligand_acquisition",
            },
        ]
    }
    local_ligand_gap_probe = {
        "entries": [
            {
                "accession": "Q9NZD4",
                "classification": "rescuable_now",
                "best_next_action": "materialize_local_bridge_ligand_payload",
            }
        ]
    }
    ligand_row_preview = {
        "summary": {
            "grounded_accessions": ["P00387"],
            "candidate_only_accessions": ["Q9NZD4"],
        }
    }

    support_path = tmp_path / "support.json"
    packet_path = tmp_path / "packet.json"
    local_map_path = tmp_path / "local_map.json"
    gap_probe_path = tmp_path / "gap_probe.json"
    ligand_row_preview_path = tmp_path / "ligand_row_preview.json"
    output_json = tmp_path / "ligand_support.json"
    output_md = tmp_path / "ligand_support.md"
    support_path.write_text(json.dumps(support_subslice), encoding="utf-8")
    packet_path.write_text(json.dumps(packet_dashboard), encoding="utf-8")
    local_map_path.write_text(json.dumps(local_ligand_source_map), encoding="utf-8")
    gap_probe_path.write_text(json.dumps(local_ligand_gap_probe), encoding="utf-8")
    ligand_row_preview_path.write_text(json.dumps(ligand_row_preview), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_ligand_support_readiness_preview.py"),
            "--support-subslice",
            str(support_path),
            "--packet-deficit-dashboard",
            str(packet_path),
            "--local-ligand-source-map",
            str(local_map_path),
            "--local-ligand-gap-probe",
            str(gap_probe_path),
            "--ligand-row-preview",
            str(ligand_row_preview_path),
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
    assert payload["summary"]["deferred_accessions"] == ["Q9UCM0"]
    assert payload["summary"]["current_ligand_gap_count"] == 5
    assert payload["summary"]["ligand_readiness_ladder_counts"] == {
        "absent": 1,
        "support-only": 2,
        "candidate-only non-governing": 1,
        "grounded preview-safe": 1,
    }
    rows = {row["accession"]: row for row in payload["rows"]}
    assert rows["P00387"]["ligand_readiness_ladder"] == "grounded preview-safe"
    assert rows["P09105"]["ligand_readiness_ladder"] == "support-only"
    assert rows["Q2TAC2"]["ligand_readiness_ladder"] == "support-only"
    assert rows["Q9NZD4"]["ligand_readiness_ladder"] == "candidate-only non-governing"
    assert payload["summary"]["absent_accessions"] == ["Q9UCM0"]
    assert payload["truth_boundary"]["ligand_rows_materialized"] is False
    assert "Ligand Support Readiness Preview" in output_md.read_text(encoding="utf-8")
