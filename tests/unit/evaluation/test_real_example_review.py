from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from execution.materialization.training_packet_audit import audit_training_packets

REPO_ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = REPO_ROOT / "runs" / "real_data_benchmark" / "full_results"


def test_audit_training_packets_matches_current_real_results() -> None:
    audit = audit_training_packets(RESULTS_DIR)
    usefulness_review = json.loads(
        (RESULTS_DIR / "usefulness_review.json").read_text(encoding="utf-8")
    )

    assert audit.benchmark_task == "P6-T013"
    assert audit.selected_accession_count == 12
    assert audit.summary["packet_count"] == 12
    assert audit.summary["judgment_counts"]["useful"] == usefulness_review["summary"][
        "judgment_counts"
    ]["useful"]
    assert audit.summary["judgment_counts"]["weak"] == usefulness_review["summary"][
        "judgment_counts"
    ]["weak"]
    assert audit.summary["judgment_counts"]["blocked"] == 0
    assert audit.summary["useful_accessions"] == usefulness_review["summary"]["useful_accessions"]
    assert audit.summary["weak_accessions"] == usefulness_review["summary"]["weak_accessions"]
    assert audit.summary["blocked_accessions"] == []
    assert audit.summary["completeness_counts"]["partial"] == 12

    p69905 = next(packet for packet in audit.packets if packet.accession == "P69905")
    assert p69905.judgment == "useful"
    assert p69905.completeness == "partial"
    assert p69905.present_modalities == ("sequence", "structure")
    assert p69905.supporting_modalities == ("annotation", "pathway")
    assert p69905.missing_modalities == ("ligand", "ppi")
    assert any(
        "checkpoint_coverage.first_checkpoint_index=1" in pointer
        for pointer in p69905.provenance_pointers
    )
    assert any("live_source_smoke" in pointer for pointer in p69905.provenance_pointers)

    p68871 = next(packet for packet in audit.packets if packet.accession == "P68871")
    assert p68871.judgment == "weak"
    assert p68871.mixed_evidence is True
    assert p68871.present_modalities == ("sequence", "ppi")
    assert p68871.missing_modalities == ("structure", "ligand")
    assert "runs/real_data_benchmark/results/live_inputs.json" in p68871.provenance_pointers

    payload = audit.to_dict()
    assert json.dumps(payload)
    assert payload["summary"]["packet_count"] == 12


def test_evaluate_real_examples_cli_json_output() -> None:
    command = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "evaluate_real_examples.py"),
        "--json",
    ]
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    payload = json.loads(result.stdout)

    assert payload["benchmark_task"] == "P6-T013"
    assert payload["summary"]["judgment_counts"]["useful"] == 1
    assert payload["summary"]["judgment_counts"]["weak"] == 11
    assert payload["summary"]["blocked_accessions"] == []
