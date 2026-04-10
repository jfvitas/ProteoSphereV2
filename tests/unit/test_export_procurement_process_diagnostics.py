from __future__ import annotations

import json
from pathlib import Path

from scripts.export_procurement_process_diagnostics import (
    build_procurement_process_diagnostics,
    main,
    render_markdown,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_inputs(tmp_path: Path) -> dict[str, Path]:
    download_location_audit_path = (
        tmp_path / "artifacts" / "status" / "download_location_audit_preview.json"
    )
    source_completion_path = (
        tmp_path / "artifacts" / "status" / "procurement_source_completion_preview.json"
    )
    board_path = tmp_path / "artifacts" / "status" / "procurement_status_board.json"
    remaining_transfer_path = (
        tmp_path / "artifacts" / "status" / "broad_mirror_remaining_transfer_status.json"
    )

    _write_json(
        download_location_audit_path,
        {
            "rows": [
                {
                    "source_id": "string",
                    "filename": "protein.links.full.v12.0.txt.gz",
                    "state": "downloaded",
                    "resolved_path": "D:/data/string/protein.links.full.v12.0.txt.gz",
                },
                {
                    "source_id": "uniprot",
                    "filename": "uniref100.xml.gz",
                    "state": "in_process",
                    "resolved_path": "C:/overflow/uniref100.xml.gz.part",
                },
            ]
        },
    )
    _write_json(
        source_completion_path,
        {
            "status": "report_only",
            "string_completion_status": "complete",
            "uniprot_completion_status": "partial",
            "string_completion_ready": True,
            "uniref_completion_ready": False,
            "source_completion": [
                {
                    "source_id": "string",
                    "completion_status": "complete",
                    "completion_ready": True,
                },
                {
                    "source_id": "uniprot",
                    "completion_status": "partial",
                    "completion_ready": False,
                },
            ],
        },
    )
    _write_json(
        board_path,
        {
            "status": "attention",
            "summary": {
                "active_observed_download_count": 2,
                "observed_active_source": "remaining_transfer_status",
            },
            "procurement_supervisor": {
                "status": "planning",
                "observed_active_source": "remaining_transfer_status",
                "active_observed_download_count": 2,
                "active_observed_downloads": [
                    {
                        "task_id": "uniprot",
                        "description": "uniref100.xml.gz",
                        "category": "sequence_reference_backbone",
                        "priority": None,
                        "pid": None,
                        "status": "running",
                        "started_at": "",
                        "filename": "uniref100.xml.gz",
                        "source_name": "UniProt / UniRef / ID Mapping",
                        "gap_kind": "partial",
                    },
                    {
                        "task_id": "string",
                        "description": "protein.links.full.v12.0.txt.gz",
                        "category": "interaction_networks",
                        "priority": None,
                        "pid": None,
                        "status": "running",
                        "started_at": "",
                        "filename": "protein.links.full.v12.0.txt.gz",
                        "source_name": "STRING v12",
                        "gap_kind": "partial",
                    },
                ],
            },
        },
    )
    _write_json(
        remaining_transfer_path,
        {
            "status": "planning",
            "summary": {
                "active_file_count": 2,
                "remaining_source_count": 2,
                "not_yet_started_file_count": 0,
                "total_gap_files": 2,
            },
            "remaining_sources": [
                {
                    "source_id": "uniprot",
                    "source_name": "UniProt / UniRef / ID Mapping",
                    "status": "partial",
                    "coverage_percent": 93.3,
                    "active_file_count": 1,
                },
                {
                    "source_id": "string",
                    "source_name": "STRING v12",
                    "status": "partial",
                    "coverage_percent": 96.2,
                    "active_file_count": 1,
                },
            ],
            "gap_files": [],
        },
    )
    return {
        "audit": download_location_audit_path,
        "source_completion": source_completion_path,
        "board": board_path,
        "remaining": remaining_transfer_path,
    }


def test_build_procurement_process_diagnostics_prefers_source_truth_and_groups_duplicates(
    tmp_path: Path,
) -> None:
    paths = _write_inputs(tmp_path)

    def fake_probe():
        return (
            [
                {
                    "pid": 111,
                    "name": "python.exe",
                    "command_line": (
                        "python protein_data_scope/download_all_sources.py "
                        "--sources uniprot --files uniref100.xml.gz"
                    ),
                    "creation_date": "2026-04-03T21:00:00+00:00",
                },
                {
                    "pid": 222,
                    "name": "python.exe",
                    "command_line": (
                        "python protein_data_scope/download_all_sources.py "
                        "--sources uniprot --files uniref100.xml.gz"
                    ),
                    "creation_date": "2026-04-03T21:00:10+00:00",
                },
                {
                    "pid": 333,
                    "name": "python.exe",
                    "command_line": (
                        "python protein_data_scope/download_all_sources.py "
                        "--sources string --files protein.links.full.v12.0.txt.gz"
                    ),
                    "creation_date": "2026-04-03T21:00:20+00:00",
                },
            ],
            "available",
        )

    payload = build_procurement_process_diagnostics(
        json.loads(paths["audit"].read_text(encoding="utf-8")),
        json.loads(paths["source_completion"].read_text(encoding="utf-8")),
        json.loads(paths["board"].read_text(encoding="utf-8")),
        json.loads(paths["remaining"].read_text(encoding="utf-8")),
        process_probe=fake_probe,
    )

    assert payload["status"] == "attention"
    assert payload["summary"]["authoritative_tail_file_count"] == 1
    assert payload["summary"]["raw_process_table_active_count"] == 3
    assert payload["summary"]["raw_process_table_unique_signature_count"] == 2
    assert payload["summary"]["raw_process_table_duplicate_count"] == 1
    assert payload["summary"]["board_observed_active_source"] == "remaining_transfer_status"
    assert [row["source_id"] for row in payload["authoritative_tail_files"]] == ["uniprot"]
    assert payload["raw_process_table_duplicate_groups"][0]["duplicate_process_count"] == 1
    assert "authoritative tail files" in render_markdown(payload).lower()
    assert "raw duplicate processes" in render_markdown(payload).lower()


def test_main_writes_process_diagnostics_outputs(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    paths = _write_inputs(tmp_path)
    output_json = tmp_path / "artifacts" / "status" / "procurement_process_diagnostics_preview.json"
    output_md = tmp_path / "docs" / "reports" / "procurement_process_diagnostics_preview.md"
    monkeypatch.setattr(
        "scripts.export_procurement_process_diagnostics._probe_live_download_processes",
        lambda: ([], "unavailable"),
    )

    exit_code = main(
        [
            "--download-location-audit",
            str(paths["audit"]),
            "--procurement-source-completion",
            str(paths["source_completion"]),
            "--procurement-status-board",
            str(paths["board"]),
            "--remaining-transfer-status",
            str(paths["remaining"]),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(output_json.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert payload["summary"]["authoritative_tail_file_count"] == 1
    assert output_md.exists()
    assert "Procurement Process Diagnostics Preview" in output_md.read_text(encoding="utf-8")
    assert "raw_process_table_active_count" in captured.out
