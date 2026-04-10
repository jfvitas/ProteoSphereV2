from __future__ import annotations

import json
from pathlib import Path

from scripts.export_packet_state_delta_report import (
    build_packet_state_delta_report,
    main,
    render_markdown,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_manifest(
    path: Path,
    *,
    accession: str,
    status: str,
    missing_modalities: list[str],
    present_modalities: list[str],
    artifact_count: int,
    note_count: int,
) -> None:
    _write_json(
        path,
        {
            "accession": accession,
            "status": status,
            "requested_modalities": ["sequence", "structure", "ligand", "ppi"],
            "present_modalities": present_modalities,
            "missing_modalities": missing_modalities,
            "artifacts": [
                {
                    "modality": f"artifact-{index}",
                    "source_ref": f"source:{accession}:{index}",
                }
                for index in range(artifact_count)
            ],
            "notes": [f"note-{index}" for index in range(note_count)],
        },
    )


def _write_delta_inputs(tmp_path: Path) -> dict[str, Path]:
    comparison_path = tmp_path / "artifacts" / "status" / "packet_state_comparison.json"
    packet_deficit_path = tmp_path / "artifacts" / "status" / "packet_deficit_dashboard.json"
    latest_q1impr1 = tmp_path / "latest" / "packet-q1impr1" / "packet_manifest.json"
    freshest_q1impr1 = tmp_path / "freshest" / "packet-q1impr1" / "packet_manifest.json"
    latest_q9nzd4 = tmp_path / "latest" / "packet-q9nzd4" / "packet_manifest.json"
    freshest_q9nzd4 = tmp_path / "freshest" / "packet-q9nzd4" / "packet_manifest.json"
    latest_p00387 = tmp_path / "latest" / "packet-p00387" / "packet_manifest.json"
    freshest_p00387 = tmp_path / "freshest" / "packet-p00387" / "packet_manifest.json"
    latest_q9ucm0 = tmp_path / "latest" / "packet-q9ucm0" / "packet_manifest.json"
    freshest_q9ucm0 = tmp_path / "freshest" / "packet-q9ucm0" / "packet_manifest.json"

    _write_manifest(
        latest_q1impr1,
        accession="Q1IMPR1",
        status="partial",
        missing_modalities=["ligand", "ppi"],
        present_modalities=["sequence", "structure"],
        artifact_count=1,
        note_count=3,
    )
    _write_manifest(
        freshest_q1impr1,
        accession="Q1IMPR1",
        status="partial",
        missing_modalities=["ppi"],
        present_modalities=["sequence", "ligand", "structure"],
        artifact_count=2,
        note_count=1,
    )
    _write_manifest(
        latest_q9nzd4,
        accession="Q9NZD4",
        status="partial",
        missing_modalities=["ligand"],
        present_modalities=["sequence", "structure", "ppi"],
        artifact_count=3,
        note_count=4,
    )
    _write_manifest(
        freshest_q9nzd4,
        accession="Q9NZD4",
        status="partial",
        missing_modalities=["ppi", "structure"],
        present_modalities=["sequence", "ligand"],
        artifact_count=2,
        note_count=5,
    )
    _write_manifest(
        latest_p00387,
        accession="P00387",
        status="partial",
        missing_modalities=["ligand"],
        present_modalities=["sequence", "structure", "ppi"],
        artifact_count=3,
        note_count=4,
    )
    _write_manifest(
        freshest_p00387,
        accession="P00387",
        status="partial",
        missing_modalities=["ligand", "ppi", "structure"],
        present_modalities=["sequence"],
        artifact_count=1,
        note_count=6,
    )
    _write_manifest(
        latest_q9ucm0,
        accession="Q9UCM0",
        status="partial",
        missing_modalities=["ligand", "ppi", "structure"],
        present_modalities=["sequence"],
        artifact_count=1,
        note_count=4,
    )
    _write_manifest(
        freshest_q9ucm0,
        accession="Q9UCM0",
        status="partial",
        missing_modalities=["ligand", "ppi", "structure"],
        present_modalities=["sequence"],
        artifact_count=1,
        note_count=4,
    )

    _write_json(
        comparison_path,
        {
            "generated_at": "2026-03-31T19:42:46.742984+00:00",
            "latest_path": "D:/documents/ProteoSphereV2/data/packages/LATEST.json",
            "freshest_path": (
                "D:/documents/ProteoSphereV2/data/packages/training-packets-20260331T193611Z"
            ),
            "summary": {
                "packet_count": 4,
                "changed_packet_count": 3,
                "improved_packet_count": 1,
                "regressed_packet_count": 2,
                "improved_accessions": ["Q1IMPR1"],
                "regressed_accessions": ["P00387", "Q9NZD4"],
            },
            "packets": [
                {
                    "accession": "Q1IMPR1",
                    "latest_status": "partial",
                    "freshest_status": "partial",
                    "latest_missing_modalities": ["ligand", "ppi"],
                    "freshest_missing_modalities": ["ppi"],
                    "latest_manifest_path": str(latest_q1impr1),
                    "freshest_manifest_path": str(freshest_q1impr1),
                },
                {
                    "accession": "Q9NZD4",
                    "latest_status": "partial",
                    "freshest_status": "partial",
                    "latest_missing_modalities": ["ligand"],
                    "freshest_missing_modalities": ["ppi", "structure"],
                    "latest_manifest_path": str(latest_q9nzd4),
                    "freshest_manifest_path": str(freshest_q9nzd4),
                },
                {
                    "accession": "P00387",
                    "latest_status": "partial",
                    "freshest_status": "partial",
                    "latest_missing_modalities": ["ligand"],
                    "freshest_missing_modalities": ["ligand", "ppi", "structure"],
                    "latest_manifest_path": str(latest_p00387),
                    "freshest_manifest_path": str(freshest_p00387),
                },
                {
                    "accession": "Q9UCM0",
                    "latest_status": "partial",
                    "freshest_status": "partial",
                    "latest_missing_modalities": ["ligand", "ppi", "structure"],
                    "freshest_missing_modalities": ["ligand", "ppi", "structure"],
                    "latest_manifest_path": str(latest_q9ucm0),
                    "freshest_manifest_path": str(freshest_q9ucm0),
                },
            ],
        },
    )

    _write_json(
        packet_deficit_path,
        {
            "generated_at": "2026-03-31T19:36:14.625478+00:00",
            "inputs": {
                "latest_only": True,
                "latest_summary_path": "data/packages/LATEST.json",
                "manifest_count": 4,
                "packet_source_count": 4,
                "packages_root": "data/packages",
            },
            "summary": {
                "packet_count": 4,
                "packet_status_counts": {"partial": 4},
                "complete_packet_count": 0,
                "partial_packet_count": 4,
                "unresolved_packet_count": 0,
                "packet_deficit_count": 4,
                "total_missing_modality_count": 9,
                "modality_deficit_counts": {"ligand": 3, "ppi": 3, "structure": 3},
                "highest_leverage_source_fixes": [
                    {
                        "source_ref": "ligand:Q1IMPR1",
                        "missing_modality_count": 1,
                        "affected_packet_count": 1,
                        "missing_modalities": ["ligand"],
                        "modality_counts": {"ligand": 1},
                        "packet_ids": ["packet-Q1IMPR1"],
                        "packet_accessions": ["Q1IMPR1"],
                    },
                    {
                        "source_ref": "ligand:Q9NZD4",
                        "missing_modality_count": 1,
                        "affected_packet_count": 1,
                        "missing_modalities": ["ligand"],
                        "modality_counts": {"ligand": 1},
                        "packet_ids": ["packet-Q9NZD4"],
                        "packet_accessions": ["Q9NZD4"],
                    },
                    {
                        "source_ref": "ligand:P00387",
                        "missing_modality_count": 1,
                        "affected_packet_count": 1,
                        "missing_modalities": ["ligand"],
                        "modality_counts": {"ligand": 1},
                        "packet_ids": ["packet-P00387"],
                        "packet_accessions": ["P00387"],
                    },
                ],
                "source_fix_candidate_count": 3,
            },
            "packets": [
                {
                    "accession": "Q1IMPR1",
                    "packet_id": "packet-Q1IMPR1",
                    "canonical_id": "protein:Q1IMPR1",
                    "status": "partial",
                    "missing_modality_count": 2,
                    "missing_modalities": ["ligand", "ppi"],
                    "deficit_source_refs": ["ligand:Q1IMPR1", "ppi:Q1IMPR1"],
                    "manifest_path": str(latest_q1impr1),
                    "missing_source_refs": {
                        "ligand": ["ligand:Q1IMPR1"],
                        "ppi": ["ppi:Q1IMPR1"],
                    },
                },
                {
                    "accession": "Q9NZD4",
                    "packet_id": "packet-Q9NZD4",
                    "canonical_id": "protein:Q9NZD4",
                    "status": "partial",
                    "missing_modality_count": 1,
                    "missing_modalities": ["ligand"],
                    "deficit_source_refs": ["ligand:Q9NZD4"],
                    "manifest_path": str(latest_q9nzd4),
                    "missing_source_refs": {
                        "ligand": ["ligand:Q9NZD4"],
                    },
                },
                {
                    "accession": "P00387",
                    "packet_id": "packet-P00387",
                    "canonical_id": "protein:P00387",
                    "status": "partial",
                    "missing_modality_count": 1,
                    "missing_modalities": ["ligand"],
                    "deficit_source_refs": ["ligand:P00387"],
                    "manifest_path": str(latest_p00387),
                    "missing_source_refs": {
                        "ligand": ["ligand:P00387"],
                    },
                },
                {
                    "accession": "Q9UCM0",
                    "packet_id": "packet-Q9UCM0",
                    "canonical_id": "protein:Q9UCM0",
                    "status": "partial",
                    "missing_modality_count": 3,
                    "missing_modalities": ["ligand", "ppi", "structure"],
                    "deficit_source_refs": ["ligand:Q9UCM0", "ppi:Q9UCM0"],
                    "manifest_path": str(latest_q9ucm0),
                    "missing_source_refs": {
                        "ligand": ["ligand:Q9UCM0"],
                        "ppi": ["ppi:Q9UCM0"],
                        "structure": ["structure:Q9UCM0"],
                    },
                },
            ],
        },
    )

    return {
        "comparison_path": comparison_path,
        "packet_deficit_path": packet_deficit_path,
    }


def test_build_packet_state_delta_report_separates_true_fresh_run_changes(
    tmp_path: Path,
) -> None:
    paths = _write_delta_inputs(tmp_path)

    payload = build_packet_state_delta_report(
        comparison_path=paths["comparison_path"],
        packet_deficit_path=paths["packet_deficit_path"],
    )

    assert payload["summary"]["latest_gap_packet_count"] == 4
    assert payload["summary"]["freshest_gap_packet_count"] == 4
    assert payload["summary"]["packet_level_improved_count"] == 1
    assert payload["summary"]["packet_level_regressed_count"] == 2
    assert payload["summary"]["packet_level_unchanged_count"] == 1
    assert payload["summary"]["evidence_layer_improved_count"] == 1
    assert payload["summary"]["evidence_layer_regressed_count"] == 2
    assert payload["summary"]["evidence_layer_unchanged_count"] == 1
    assert payload["summary"]["improved_accessions"] == ["Q1IMPR1"]
    assert payload["summary"]["regressed_accessions"] == ["P00387", "Q9NZD4"]
    assert payload["summary"]["evidence_improved_accessions"] == ["Q1IMPR1"]
    assert payload["summary"]["evidence_regressed_accessions"] == ["Q9NZD4", "P00387"]

    improved_row = payload["packet_level_improvements"][0]
    assert improved_row["accession"] == "Q1IMPR1"
    assert improved_row["delta_kind"] == "improved"
    assert improved_row["delta_gap_count"] == -1
    assert improved_row["evidence_delta_kind"] == "improved"

    regressed_rows = {row["accession"]: row for row in payload["packet_level_regressions"]}
    assert regressed_rows["Q9NZD4"]["delta_kind"] == "regressed"
    assert regressed_rows["Q9NZD4"]["latest_deficit_source_refs"] == ["ligand:Q9NZD4"]
    assert regressed_rows["Q9NZD4"]["freshest_missing_modalities"] == ["ppi", "structure"]
    assert regressed_rows["Q9NZD4"]["evidence_delta_kind"] == "regressed"
    assert regressed_rows["P00387"]["evidence_delta_kind"] == "regressed"

    evidence_rows = {row["accession"]: row for row in payload["lower_layer_evidence_regressions"]}
    assert evidence_rows["Q9NZD4"]["latest_artifact_count"] == 3
    assert evidence_rows["Q9NZD4"]["freshest_artifact_count"] == 2
    assert evidence_rows["P00387"]["latest_artifact_count"] == 3
    assert evidence_rows["P00387"]["freshest_artifact_count"] == 1

    markdown = render_markdown(payload)
    assert "Comparison boundary" in markdown
    assert "Packet-Level Improvements" in markdown
    assert "Packet-Level Regressions" in markdown
    assert "Lower-Layer Evidence Improvements" in markdown
    assert "Lower-Layer Evidence Regressions" in markdown
    assert "Q9NZD4" in markdown
    assert "P00387" in markdown
    assert "fresh-run-improved" in markdown
    assert "fresh-run-regressed" in markdown
    assert "fresh-run-evidence-improved" in markdown
    assert "fresh-run-evidence-regressed" in markdown


def test_main_writes_packet_state_delta_outputs(tmp_path: Path, capsys) -> None:
    paths = _write_delta_inputs(tmp_path)
    output_path = tmp_path / "artifacts" / "status" / "packet_state_delta_report.json"

    exit_code = main(
        [
            "--comparison",
            str(paths["comparison_path"]),
            "--packet-deficit",
            str(paths["packet_deficit_path"]),
            "--output",
            str(output_path),
            "--no-markdown",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert "Packet delta report exported" in captured.out
    assert payload["summary"]["packet_level_improved_count"] == 1
    assert payload["summary"]["packet_level_regressed_count"] == 2
