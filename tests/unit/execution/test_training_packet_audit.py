from __future__ import annotations

import json
from pathlib import Path

from execution.materialization.training_packet_audit import (
    audit_training_packet_payload,
    audit_training_packets,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = REPO_ROOT / "runs" / "real_data_benchmark" / "full_results"


def test_audit_training_packets_scores_real_benchmark_artifacts() -> None:
    result = audit_training_packets(RESULTS_DIR)
    payload = result.to_dict()
    by_accession = {packet["accession"]: packet for packet in payload["packets"]}

    assert payload["benchmark_task"] == "P6-T013"
    assert payload["selected_accession_count"] == 12
    assert payload["requested_modalities"] == ["sequence", "structure", "ligand", "ppi"]
    assert payload["summary"]["packet_count"] == 12
    assert payload["summary"]["judgment_counts"] == {
        "useful": 1,
        "weak": 11,
        "blocked": 0,
    }
    assert by_accession["P69905"]["judgment"] == "useful"
    assert by_accession["P69905"]["planning_index_ref"] == "planning/P69905"
    assert by_accession["P69905"]["canonical_id"] == "protein:P69905"
    assert by_accession["P69905"]["leakage_key"] == "P69905"
    assert by_accession["P69905"]["missing_modalities"] == ["ligand", "ppi"]
    assert "planning/P69905" in by_accession["P69905"]["provenance_pointers"]
    assert by_accession["P68871"]["judgment"] == "weak"
    assert "ppi" in by_accession["P68871"]["present_modalities"]
    assert by_accession["P09105"]["split"] == "test"
    assert by_accession["P09105"]["missing_modalities"] == ["structure", "ligand", "ppi"]


def test_audit_training_packet_payload_round_trips() -> None:
    payload = audit_training_packets(RESULTS_DIR).to_dict()
    round_tripped = audit_training_packet_payload(payload)

    assert round_tripped.selected_accession_count == 12
    assert round_tripped.summary["packet_count"] == 12
    assert round_tripped.packets[0].row_index == 1
    assert round_tripped.packets[-1].row_index == 12
    assert json.loads(json.dumps(round_tripped.to_dict()))["benchmark_task"] == "P6-T013"
