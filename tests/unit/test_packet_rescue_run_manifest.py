from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.export_packet_rescue_run_manifest import build_packet_rescue_run_manifest, main


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_build_packet_rescue_run_manifest_preserves_order_and_provenance(tmp_path: Path) -> None:
    priority_path = tmp_path / "p32_packet_rescue_priority.json"
    _write_json(
        priority_path,
        {
            "artifact_id": "p32_packet_rescue_priority",
            "schema_id": "proteosphere-p32-packet-rescue-priority-2026-03-30",
            "generated_at": "2026-03-30T19:12:24.2170081Z",
            "dashboard_summary": {
                "packet_deficit_count": 2,
                "modality_deficit_counts": {"ligand": 2},
            },
            "source_availability": {"chembl": "present", "bindingdb": "present"},
            "bindingdb_snapshot_behavior": [],
            "canonical_presence": [],
            "priority_ranking": [
                {
                    "rank": 2,
                    "accession": "Q9UCM0",
                    "canonical_id": "protein:Q9UCM0",
                    "packet_status": "partial",
                    "missing_modalities": ["structure", "ligand", "ppi"],
                    "recommended_routes": [
                        {
                            "rank": 1,
                            "modality": "structure",
                            "route": "AlphaFold DB explicit accession probe",
                            "sources": ["alphafold_db"],
                            "confidence": "high",
                            "why": "structure first",
                        },
                        {
                            "rank": 2,
                            "modality": "structure",
                            "route": "RCSB/PDBe best-structures re-probe",
                            "sources": ["rcsb_pdbe"],
                            "confidence": "medium_high",
                            "why": "fallback",
                        },
                    ],
                },
                {
                    "rank": 1,
                    "accession": "P00387",
                    "canonical_id": "protein:P00387",
                    "packet_status": "partial",
                    "missing_modalities": ["ligand"],
                    "recommended_routes": [
                        {
                            "rank": 1,
                            "modality": "ligand",
                            "route": "ChEMBL rescue brief",
                            "sources": ["chembl"],
                            "confidence": "high",
                            "why": "best local route",
                        },
                        {
                            "rank": 2,
                            "modality": "ligand",
                            "route": "BindingDB direct accession probe",
                            "sources": ["bindingdb"],
                            "confidence": "low",
                            "why": "fallback",
                        },
                    ],
                },
            ],
        },
    )

    manifest = build_packet_rescue_run_manifest(priority_path=priority_path)

    assert manifest["status"] == "planning_only"
    assert manifest["current_deficit_accessions"] == ["P00387", "Q9UCM0"]
    assert manifest["manifest_summary"] == {
        "accession_count": 2,
        "step_count": 4,
        "primary_step_count": 2,
        "fallback_step_count": 2,
    }
    assert manifest["accession_plans"][0]["accession"] == "P00387"
    assert manifest["accession_plans"][0]["primary_route"]["route"] == "ChEMBL rescue brief"
    assert manifest["accession_plans"][0]["fallback_routes"][0]["sources"] == ["bindingdb"]
    assert manifest["accession_plans"][1]["primary_route"]["modality"] == "structure"
    assert manifest["manifest_steps"][0]["step_id"] == "rescue-01-01"
    assert manifest["manifest_steps"][0]["kind"] == "primary"
    assert manifest["manifest_steps"][0]["provenance"]["source_priority_route_rank"] == 1
    assert manifest["manifest_steps"][1]["kind"] == "fallback"
    assert manifest["manifest_steps"][1]["provenance"]["source_priority_route_count"] == 2
    assert manifest["source_priority_summary"]["source_availability"]["chembl"] == "present"


def test_build_packet_rescue_run_manifest_fails_closed_on_missing_required_sections(
    tmp_path: Path,
) -> None:
    priority_path = tmp_path / "broken_priority.json"
    _write_json(
        priority_path,
        {
            "artifact_id": "broken",
            "schema_id": "proteosphere-p32-packet-rescue-priority-2026-03-30",
            "generated_at": "2026-03-30T19:12:24.2170081Z",
            "dashboard_summary": {},
            "source_availability": {},
        },
    )

    with pytest.raises(ValueError, match="priority artifact missing required sequence"):
        build_packet_rescue_run_manifest(priority_path=priority_path)


def test_main_writes_manifest_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    priority_path = tmp_path / "priority.json"
    output_path = tmp_path / "out" / "manifest.json"
    _write_json(
        priority_path,
        {
            "artifact_id": "p32_packet_rescue_priority",
            "schema_id": "proteosphere-p32-packet-rescue-priority-2026-03-30",
            "generated_at": "2026-03-30T19:12:24.2170081Z",
            "dashboard_summary": {"packet_deficit_count": 1},
            "source_availability": {"chembl": "present"},
            "bindingdb_snapshot_behavior": [],
            "canonical_presence": [],
            "priority_ranking": [
                {
                    "rank": 1,
                    "accession": "P00387",
                    "canonical_id": "protein:P00387",
                    "packet_status": "partial",
                    "missing_modalities": ["ligand"],
                    "recommended_routes": [
                        {
                            "rank": 1,
                            "modality": "ligand",
                            "route": "ChEMBL rescue brief",
                            "sources": ["chembl"],
                            "confidence": "high",
                            "why": "best local route",
                        }
                    ],
                }
            ],
        },
    )

    exit_code = main(["--priority", str(priority_path), "--output", str(output_path)])

    assert exit_code == 0
    assert output_path.is_file()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["current_deficit_accessions"] == ["P00387"]
    assert payload["manifest_summary"]["step_count"] == 1
    assert "Packet rescue run manifest exported" in capsys.readouterr().out
