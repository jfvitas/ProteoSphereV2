from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.export_provenance_drilldown import build_provenance_drilldown

REPO_ROOT = Path(__file__).resolve().parents[2]


def _copy_fixture_artifacts(temp_root: Path) -> dict[str, Path]:
    results_dir = temp_root / "runs" / "real_data_benchmark" / "full_results"
    results_dir.mkdir(parents=True, exist_ok=True)

    filenames = (
        "provenance_table.json",
        "source_coverage.json",
        "training_packet_audit.json",
        "curated_ppi_candidate_slice.json",
    )
    copied: dict[str, Path] = {}
    for name in filenames:
        source = REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / name
        target = results_dir / name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        copied[name] = target
    return copied


def test_build_provenance_drilldown_includes_entity_pair_and_packet_traces(tmp_path: Path) -> None:
    copied = _copy_fixture_artifacts(tmp_path / "repo")

    payload = build_provenance_drilldown(
        provenance_table_path=copied["provenance_table.json"],
        source_coverage_path=copied["source_coverage.json"],
        packet_audit_path=copied["training_packet_audit.json"],
        curated_ppi_path=copied["curated_ppi_candidate_slice.json"],
    )

    assert payload["exporter_id"] == "provenance-drilldown:v1"
    assert payload["summary"]["entity_trace_count"] == 12
    assert payload["summary"]["packet_trace_count"] == 12
    assert payload["summary"]["pair_trace_count"] >= 12
    assert payload["summary"]["unresolved_lane_count"] >= 1

    entity_accessions = [trace["accession"] for trace in payload["entities"]]
    assert entity_accessions[:4] == ["P69905", "P68871", "P04637", "P31749"]

    p69905 = next(trace for trace in payload["entities"] if trace["accession"] == "P69905")
    assert p69905["trace_kind"] == "entity"
    assert p69905["coverage_snapshot"]["missing_modalities"] == ["ligand", "ppi"]
    assert any(lane["lane_id"] == "entity:P69905:ligand" for lane in p69905["unresolved_lanes"])

    q9u_cm0_pair = next(
        trace
        for trace in payload["pairs"]
        if trace["accession"] == "Q9UCM0" and trace["source_name"] == "IntAct"
    )
    assert q9u_cm0_pair["trace_kind"] == "pair"
    assert q9u_cm0_pair["trace_state"] == "unresolved"
    assert q9u_cm0_pair["empty_state"] == "reachable_empty"
    assert any(lane["lane_kind"] == "pair_empty_hit" for lane in q9u_cm0_pair["unresolved_lanes"])

    p31749_packet = next(
        trace for trace in payload["packets"] if trace["accession"] == "P31749"
    )
    assert p31749_packet["trace_kind"] == "packet"
    assert p31749_packet["completeness"] == "partial"
    assert p31749_packet["missing_modalities"] == ["sequence", "structure", "ppi"]
    assert any(lane["lane_id"] == "packet:P31749:ppi" for lane in p31749_packet["unresolved_lanes"])

    unresolved_lane_ids = {lane["lane_id"] for lane in payload["unresolved_lanes"]}
    assert "entity:P69905:ligand" in unresolved_lane_ids
    assert "packet:P31749:ppi" in unresolved_lane_ids
    assert any(lane_id.startswith("pair:") for lane_id in unresolved_lane_ids)


def test_export_provenance_drilldown_cli_writes_json(tmp_path: Path) -> None:
    copied = _copy_fixture_artifacts(tmp_path / "repo")
    output_path = tmp_path / "drilldown.json"

    command = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "export_provenance_drilldown.py"),
        "--provenance-table",
        str(copied["provenance_table.json"]),
        "--source-coverage",
        str(copied["source_coverage.json"]),
        "--packet-audit",
        str(copied["training_packet_audit.json"]),
        "--curated-ppi",
        str(copied["curated_ppi_candidate_slice.json"]),
        "--output",
        str(output_path),
    ]
    subprocess.run(command, cwd=REPO_ROOT, check=True, capture_output=True, text=True)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["entity_trace_count"] == 12
    assert payload["summary"]["packet_trace_count"] == 12
    assert payload["summary"]["unresolved_lane_count"] >= 1
    assert payload["source_files"]["provenance_table"].endswith(
        "provenance_table.json"
    )
