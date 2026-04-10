from __future__ import annotations

import json
from pathlib import Path

from execution.materialization.packet_gap_execution_plan import (
    build_packet_gap_execution_plan,
    render_markdown,
)
from scripts.export_packet_gap_execution_plan import main


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str = "evidence") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_dashboard(path: Path) -> None:
    _write_json(
        path,
        {
            "generated_at": "2026-03-23T18:05:37.474312+00:00",
            "summary": {
                "packet_count": 12,
                "packet_deficit_count": 5,
                "total_missing_modality_count": 7,
            },
            "source_fix_candidates": [
                {
                    "source_ref": "ligand:P00387",
                    "missing_modality_count": 1,
                    "affected_packet_count": 1,
                    "missing_modalities": ["ligand"],
                    "packet_ids": ["packet-P00387"],
                    "packet_accessions": ["P00387"],
                },
                {
                    "source_ref": "ligand:P09105",
                    "missing_modality_count": 1,
                    "affected_packet_count": 1,
                    "missing_modalities": ["ligand"],
                    "packet_ids": ["packet-P09105"],
                    "packet_accessions": ["P09105"],
                },
                {
                    "source_ref": "ligand:Q2TAC2",
                    "missing_modality_count": 1,
                    "affected_packet_count": 1,
                    "missing_modalities": ["ligand"],
                    "packet_ids": ["packet-Q2TAC2"],
                    "packet_accessions": ["Q2TAC2"],
                },
                {
                    "source_ref": "ligand:Q9NZD4",
                    "missing_modality_count": 1,
                    "affected_packet_count": 1,
                    "missing_modalities": ["ligand"],
                    "packet_ids": ["packet-Q9NZD4"],
                    "packet_accessions": ["Q9NZD4"],
                },
                {
                    "source_ref": "ligand:Q9UCM0",
                    "missing_modality_count": 1,
                    "affected_packet_count": 1,
                    "missing_modalities": ["ligand"],
                    "packet_ids": ["packet-Q9UCM0"],
                    "packet_accessions": ["Q9UCM0"],
                },
                {
                    "source_ref": "ppi:Q9UCM0",
                    "missing_modality_count": 1,
                    "affected_packet_count": 1,
                    "missing_modalities": ["ppi"],
                    "packet_ids": ["packet-Q9UCM0"],
                    "packet_accessions": ["Q9UCM0"],
                },
                {
                    "source_ref": "structure:Q9UCM0",
                    "missing_modality_count": 1,
                    "affected_packet_count": 1,
                    "missing_modalities": ["structure"],
                    "packet_ids": ["packet-Q9UCM0"],
                    "packet_accessions": ["Q9UCM0"],
                },
            ],
        },
    )


def _write_local_ligand_source_map(path: Path) -> None:
    _write_json(
        path,
        {
            "entries": [
                {
                    "accession": "P00387",
                    "classification": "bulk_assay_actionable",
                    "recommended_next_action": "ingest_local_bulk_assay",
                    "biolip_pdb_ids": ["1UMK"],
                    "chembl_hits": [{"chembl_id": "CHEMBL2146"}],
                    "bindingdb_hits": [],
                    "alphafold_hits": [{"entry_id": "AF-P00387-F1-model_v6"}],
                },
                {
                    "accession": "P09105",
                    "classification": "structure_companion_only",
                    "recommended_next_action": "hold_for_ligand_acquisition",
                    "biolip_pdb_ids": [],
                    "chembl_hits": [],
                    "bindingdb_hits": [],
                    "alphafold_hits": [{"entry_id": "AF-P09105-F1-model_v6"}],
                },
                {
                    "accession": "Q2TAC2",
                    "classification": "structure_companion_only",
                    "recommended_next_action": "hold_for_ligand_acquisition",
                    "biolip_pdb_ids": [],
                    "chembl_hits": [],
                    "bindingdb_hits": [],
                    "alphafold_hits": [{"entry_id": "AF-Q2TAC2-F1-model_v6"}],
                },
            ]
        },
    )


def test_build_packet_gap_execution_plan_ranks_local_work_before_fresh_acquisition(
    tmp_path: Path,
) -> None:
    dashboard_path = tmp_path / "artifacts" / "status" / "packet_deficit_dashboard.json"
    local_map_path = tmp_path / "artifacts" / "status" / "local_ligand_source_map.json"
    source_hunt = tmp_path / "docs" / "reports" / "p26_packet_deficit_source_hunt.md"
    q9ucm0_brief = tmp_path / "docs" / "reports" / "q9ucm0_acquisition_brief_2026_03_23.md"
    q9ucm0_checklist = tmp_path / "docs" / "reports" / "q9ucm0_acquisition_checklist_2026_03_23.md"
    q9ucm0_structure = (
        tmp_path / "docs" / "reports" / "q9ucm0_structure_gap_local_investigation_2026_03_23.md"
    )
    p00387_brief = tmp_path / "docs" / "reports" / "p00387_local_chembl_rescue.md"

    _write_dashboard(dashboard_path)
    _write_local_ligand_source_map(local_map_path)
    _write_text(source_hunt, "Q9NZD4 has local 1Z8U bound_objects.")
    _write_text(q9ucm0_brief, "Q9UCM0 remains unresolved for structure, ppi, and ligand.")
    _write_text(q9ucm0_checklist, "Q9UCM0 needs fresh acquisition.")
    _write_text(q9ucm0_structure, "Q9UCM0 has no local structure rescue.")
    _write_text(p00387_brief, "CHEMBL2146 with 93 activities.")

    payload = build_packet_gap_execution_plan(
        dashboard_path=dashboard_path,
        local_ligand_source_map_path=local_map_path,
        evidence_artifact_paths=(
            source_hunt,
            q9ucm0_brief,
            q9ucm0_checklist,
            q9ucm0_structure,
            p00387_brief,
        ),
    )

    assert payload["summary"] == {
        "ranked_source_ref_count": 7,
        "quick_local_extraction_count": 2,
        "local_bulk_assay_extraction_count": 2,
        "fresh_acquisition_blocker_count": 3,
        "dashboard_source_fix_candidate_count": 7,
        "dashboard_packet_count": 12,
        "dashboard_packet_deficit_count": 5,
        "dashboard_total_missing_modality_count": 7,
    }
    assert [item["source_ref"] for item in payload["ranked_items"]] == [
        "ligand:Q9NZD4",
        "ligand:P00387",
        "ligand:P09105",
        "ligand:Q2TAC2",
        "structure:Q9UCM0",
        "ppi:Q9UCM0",
        "ligand:Q9UCM0",
    ]
    assert payload["ranked_items"][0]["work_class"] == "quick_local_extraction"
    assert payload["ranked_items"][1]["local_ligand_source_map"]["classification"] == (
        "bulk_assay_actionable"
    )
    assert payload["ranked_items"][4]["work_class"] == "fresh_acquisition_blocker"
    assert payload["ranked_items"][-1]["next_action"].startswith(
        "Treat ligand acquisition as downstream"
    )

    markdown = render_markdown(payload)
    assert "# Packet Gap Execution Plan" in markdown
    assert "`ligand:Q9NZD4`" in markdown
    assert "fresh acquisition blockers" in markdown.lower()


def test_main_writes_packet_gap_execution_plan_outputs(tmp_path: Path, capsys) -> None:
    dashboard_path = tmp_path / "artifacts" / "status" / "packet_deficit_dashboard.json"
    local_map_path = tmp_path / "artifacts" / "status" / "local_ligand_source_map.json"
    output_path = tmp_path / "artifacts" / "status" / "packet_gap_execution_plan.json"
    markdown_path = tmp_path / "docs" / "reports" / "packet_gap_execution_plan.md"
    q9ucm0_brief = tmp_path / "docs" / "reports" / "q9ucm0_acquisition_brief_2026_03_23.md"

    _write_dashboard(dashboard_path)
    _write_local_ligand_source_map(local_map_path)
    _write_text(q9ucm0_brief, "Q9UCM0 requires fresh acquisition.")

    exit_code = main(
        [
            "--dashboard",
            str(dashboard_path),
            "--local-ligand-source-map",
            str(local_map_path),
            "--evidence-artifact",
            str(q9ucm0_brief),
            "--output",
            str(output_path),
            "--markdown",
            str(markdown_path),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert "Packet gap execution plan exported" in captured.out
    assert payload["status"] == "planning_only"
    assert payload["summary"]["ranked_source_ref_count"] == 7
    assert markdown_path.exists()
