from __future__ import annotations

import json
from pathlib import Path

import pytest

from execution.materialization.structure_packet_enricher import (
    StructureCoordinatePayload,
    StructurePacketEnrichmentEntry,
    StructurePacketEnrichmentResult,
    enrich_structure_packets,
)


def _sample_slice_payload() -> dict[str, object]:
    return {
        "task_id": "P14-I007",
        "results_dir": "runs/real_data_benchmark/full_results",
        "direct_evidence": [
            {
                "accession": "P12345",
                "canonical_id": "protein:P12345",
                "split": "train",
                "bucket": "rich_coverage",
                "judgment": "weak",
                "evidence_mode": "direct_live_smoke",
                "lane_depth": 1,
                "source_lanes": ["UniProt"],
                "present_modalities": ["sequence"],
                "missing_modalities": ["structure"],
                "coverage_notes": ["single-lane coverage"],
            },
            {
                "accession": "P23456",
                "canonical_id": "protein:P23456",
                "split": "val",
                "bucket": "moderate_coverage",
                "judgment": "weak",
                "evidence_mode": "in_tree_live_snapshot",
                "lane_depth": 1,
                "source_lanes": ["UniProt"],
                "present_modalities": ["sequence"],
                "missing_modalities": ["structure"],
                "coverage_notes": ["single-lane coverage"],
            },
            {
                "accession": "P34567",
                "canonical_id": "protein:P34567",
                "split": "test",
                "bucket": "sparse_or_control",
                "judgment": "weak",
                "evidence_mode": "live_verified_accession",
                "lane_depth": 1,
                "source_lanes": ["UniProt"],
                "present_modalities": ["sequence"],
                "missing_modalities": ["structure"],
                "coverage_notes": ["single-lane coverage"],
            },
        ],
        "structure_bridge_targets": {
            "P12345": ["1ABC"],
            "P23456": ["2DEF"],
            "P34567": [],
        },
        "structure_bridge_result": {
            "records": [
                {
                    "accession": "P12345",
                    "source_record_id": "P12345:1ABC",
                    "pdb_id": "1ABC",
                    "bridge_state": "positive_hit",
                    "bridge_kind": "bridge_only",
                    "evidence_refs": ["https://example.test/1ABC"],
                },
                {
                    "accession": "P23456",
                    "source_record_id": "P23456:2DEF",
                    "pdb_id": "2DEF",
                    "bridge_state": "positive_hit",
                    "bridge_kind": "bridge_only",
                    "evidence_refs": ["https://example.test/2DEF"],
                },
            ]
        },
    }


def test_enrich_structure_packets_distinguishes_states_and_round_trips(tmp_path: Path) -> None:
    root = tmp_path / "rcsb"
    root.mkdir()
    (root / "1ABC.json").write_text(
        json.dumps(
            {
                "task_type": "protein_protein",
                "source_record_id": "1ABC",
                "pdb_id": "1ABC",
                "uniprot_ids": ["P12345"],
                "structure_file_cif_path": "/tmp/1ABC.cif",
            }
        ),
        encoding="utf-8",
    )
    (root / "2DEF.json").write_bytes(b"")

    result = enrich_structure_packets(
        _sample_slice_payload(),
        coordinate_payload_roots=[tmp_path],
        include_unbridged=True,
    )

    assert result.source_task_id == "P14-I007"
    assert result.source_accession_count == 3
    assert result.bridge_positive_accession_count == 2
    assert result.status == "partial"
    assert result.packet_complete_accession_count == 1
    assert result.materialized_accession_count == 1
    assert result.bridge_only_accession_count == 1
    assert result.unavailable_accession_count == 1
    assert result.selected_accessions == ("P12345", "P23456", "P34567")
    assert result.bridge_positive_accessions == ("P12345", "P23456")

    materialized = next(entry for entry in result.entries if entry.accession == "P12345")
    assert materialized.packet_state == "packet_complete"
    assert materialized.coordinate_payloads[0].payload_state == "available"
    assert materialized.coordinate_payloads[0].payload_data["pdb_id"] == "1ABC"
    assert materialized.coordinate_payloads[0].payload_sha256 is not None
    assert materialized.source_record_refs == ("P12345:1ABC",)
    assert materialized.evidence_refs == ("https://example.test/1ABC",)

    bridge_only = next(entry for entry in result.entries if entry.accession == "P23456")
    assert bridge_only.packet_state == "bridge_only"
    assert bridge_only.coordinate_payloads[0].payload_state == "empty"
    assert bridge_only.issues[0].kind == "empty_coordinate_payload"

    unavailable = next(entry for entry in result.entries if entry.accession == "P34567")
    assert unavailable.packet_state == "unavailable"
    assert unavailable.coordinate_payloads == ()
    assert unavailable.issues[0].kind == "unbridged_accession"

    result_dict = result.to_dict()
    round_tripped = StructurePacketEnrichmentResult.from_dict(result_dict)
    assert round_tripped.selected_accessions == result.selected_accessions
    assert round_tripped.entries[0].coordinate_payloads[0].payload_state in {"available", "empty"}
    assert result_dict["packet_complete_accession_count"] == result.packet_complete_accession_count
    assert result_dict["bridge_positive_accessions"] == ["P12345", "P23456"]


def test_enrich_structure_packets_marks_fully_materialized_packets_complete(
    tmp_path: Path,
) -> None:
    root = tmp_path / "rcsb"
    root.mkdir()
    (root / "1ABC.json").write_text(
        json.dumps(
            {
                "task_type": "protein_protein",
                "source_record_id": "1ABC",
                "pdb_id": "1ABC",
                "uniprot_ids": ["P12345"],
            }
        ),
        encoding="utf-8",
    )

    payload = {
        "task_id": "P15-T002",
        "results_dir": "runs/real_data_benchmark/full_results",
        "direct_evidence": [
            {
                "accession": "P12345",
                "canonical_id": "protein:P12345",
                "split": "train",
                "bucket": "rich_coverage",
                "judgment": "useful",
                "evidence_mode": "direct_live_smoke",
                "lane_depth": 2,
                "source_lanes": ["UniProt", "RCSB/PDBe bridge"],
                "present_modalities": ["sequence", "structure"],
                "missing_modalities": ["ppi"],
                "coverage_notes": ["bridge-positive packet"],
            }
        ],
        "structure_bridge_targets": {"P12345": ["1ABC"]},
        "structure_bridge_result": {
            "records": [
                {
                    "accession": "P12345",
                    "source_record_id": "P12345:1ABC",
                    "pdb_id": "1ABC",
                    "bridge_state": "positive_hit",
                    "bridge_kind": "bridge_only",
                    "evidence_refs": ["https://example.test/1ABC"],
                }
            ]
        },
    }

    result = enrich_structure_packets(payload, coordinate_payload_roots=[tmp_path])

    assert result.status == "packet_complete"
    assert result.packet_complete_accession_count == 1
    assert result.bridge_only_accession_count == 0
    assert result.entries[0].packet_state == "packet_complete"
    assert result.entries[0].packet_complete_payload_count == 1
    assert result.to_dict()["status"] == "packet_complete"


def test_enrich_structure_packets_uses_real_p14_bridge_targets_when_available() -> None:
    mirror_root = Path(r"C:\Users\jfvit\Documents\bio-agent-lab\data\processed\rcsb")
    if not mirror_root.exists():
        pytest.skip("local RCSB processed mirror is unavailable")

    source_path = Path("runs/real_data_benchmark/full_results/protein_depth_candidate_slice.json")
    result = enrich_structure_packets(source_path, coordinate_payload_roots=[mirror_root])

    assert result.source_task_id == "P14-I007"
    assert result.source_accession_count == 12
    assert result.bridge_positive_accession_count == 9
    assert result.packet_complete_accession_count == 4
    assert result.materialized_accession_count == 4
    assert result.bridge_only_accession_count == 5
    assert result.unavailable_accession_count == 0
    assert result.status == "partial"
    assert set(result.bridge_positive_accessions) == {
        "P69905",
        "P68871",
        "P04637",
        "P31749",
        "Q9NZD4",
        "P00387",
        "P02042",
        "P02100",
        "P69892",
    }

    entries = {entry.accession: entry for entry in result.entries}
    assert entries["P69905"].packet_state == "packet_complete"
    assert entries["P69905"].coordinate_payloads[0].pdb_id == "1BAB"
    assert entries["P69905"].coordinate_payloads[0].payload_state == "available"
    assert entries["P69905"].coordinate_payloads[0].payload_data["source_record_id"] == "1BAB"
    assert entries["P02042"].packet_state == "bridge_only"
    assert entries["P02042"].coordinate_payloads[0].payload_state == "empty"
    assert entries["P02100"].packet_state == "bridge_only"
    assert entries["P02100"].coordinate_payloads[0].payload_state == "empty"

    assert all(isinstance(entry, StructurePacketEnrichmentEntry) for entry in result.entries)
    assert all(
        isinstance(payload, StructureCoordinatePayload)
        for payload in entries["P69905"].coordinate_payloads
    )
