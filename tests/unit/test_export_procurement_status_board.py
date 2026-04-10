from __future__ import annotations

import json
from pathlib import Path

from scripts.export_procurement_status_board import (
    build_procurement_status_board,
    main,
    render_markdown,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_board_inputs(tmp_path: Path) -> dict[str, Path]:
    broad_mirror_progress_path = tmp_path / "artifacts" / "status" / "broad_mirror_progress.json"
    remaining_transfer_status_path = (
        tmp_path / "artifacts" / "status" / "broad_mirror_remaining_transfer_status.json"
    )
    supervisor_state_path = (
        tmp_path / "artifacts" / "runtime" / "procurement_supervisor_state.json"
    )
    local_registry_summary_path = (
        tmp_path / "artifacts" / "status" / "source_coverage_matrix.json"
    )

    _write_json(
        broad_mirror_progress_path,
        {
            "generated_at": "2026-03-30T22:09:19.726276+00:00",
            "inputs": {
                "manifest_path": "protein_data_scope/sources_manifest.json",
                "seed_root": "data/raw/protein_data_scope_seed",
            },
            "schema_id": "proteosphere-broad-mirror-progress-2026-03-30",
            "status": "complete",
            "summary": {
                "source_count": 4,
                "file_coverage_percent": 37.5,
                "total_expected_files": 8,
                "total_present_files": 3,
                "total_missing_files": 3,
                "total_partial_files": 2,
                "source_status_counts": {
                    "complete": 1,
                    "missing": 1,
                    "partial": 2,
                },
                "complete_source_count": 1,
                "incomplete_source_count": 3,
            },
            "sources": [
                {
                    "source_id": "prosite",
                    "source_name": "PROSITE",
                    "category": "motif",
                    "status": "complete",
                    "priority_rank": 4,
                    "coverage_percent": 100.0,
                    "missing_file_count": 0,
                    "partial_file_count": 0,
                    "representative_missing_files": [],
                    "representative_partial_files": [],
                },
                {
                    "source_id": "reactome",
                    "source_name": "Reactome",
                    "category": "pathways_reactions_complexes",
                    "status": "partial",
                    "priority_rank": 1,
                    "coverage_percent": 50.0,
                    "missing_file_count": 1,
                    "partial_file_count": 0,
                    "representative_missing_files": ["ReactomePathways.txt"],
                    "representative_partial_files": [],
                },
                {
                    "source_id": "string",
                    "source_name": "STRING v12",
                    "category": "interaction_networks",
                    "status": "partial",
                    "priority_rank": 1,
                    "coverage_percent": 0.0,
                    "missing_file_count": 2,
                    "partial_file_count": 2,
                    "representative_missing_files": [
                        "protein.links.full.v12.0.txt.gz",
                        "protein.sequence.embeddings.v12.0.h5",
                    ],
                    "representative_partial_files": [
                        "protein.links.v12.0.txt.gz",
                        "protein.info.v12.0.txt.gz",
                    ],
                },
                {
                    "source_id": "complex_portal",
                    "source_name": "Complex Portal",
                    "category": "complexes",
                    "status": "missing",
                    "priority_rank": 2,
                    "coverage_percent": 0.0,
                    "missing_file_count": 1,
                    "partial_file_count": 0,
                    "representative_missing_files": ["download_landing_page.html"],
                    "representative_partial_files": [],
                },
            ],
            "top_missing_files": [
                {
                    "source_id": "string",
                    "source_name": "STRING v12",
                    "category": "interaction_networks",
                    "priority_rank": 1,
                    "estimated_value": "high",
                    "filename": "protein.links.full.v12.0.txt.gz",
                },
                {
                    "source_id": "reactome",
                    "source_name": "Reactome",
                    "category": "pathways_reactions_complexes",
                    "priority_rank": 1,
                    "estimated_value": "high",
                    "filename": "ReactomePathways.txt",
                },
            ],
            "top_priority_missing_files": [
                {
                    "source_id": "string",
                    "source_name": "STRING v12",
                    "category": "interaction_networks",
                    "priority_rank": 1,
                    "estimated_value": "high",
                    "filename": "protein.links.full.v12.0.txt.gz",
                }
            ],
        },
    )

    _write_json(
        remaining_transfer_status_path,
        {
            "generated_at": "2026-03-31T19:38:13.468063+00:00",
            "schema_id": "proteosphere-broad-mirror-remaining-transfer-status-2026-03-31",
            "status": "planning",
            "summary": {
                "broad_mirror_coverage_percent": 86.4,
                "remaining_source_count": 2,
                "active_file_count": 8,
                "not_yet_started_file_count": 14,
                "active_source_counts": {
                    "string": 4,
                    "uniprot": 4,
                },
                "total_gap_files": 22,
            },
            "sources": [
                {
                    "source_id": "string",
                    "source_name": "STRING v12",
                    "status": "active",
                    "coverage_percent": 81.2,
                    "active_file_count": 4,
                    "not_yet_started_file_count": 8,
                    "priority_rank": 1,
                    "representative_missing_files": [
                        "protein.links.detailed.v12.0.txt.gz",
                        "protein.links.full.v12.0.txt.gz",
                    ],
                    "representative_partial_files": [
                        "protein.links.v12.0.txt.gz",
                    ],
                },
                {
                    "source_id": "uniprot",
                    "source_name": "UniProt / UniRef / ID Mapping",
                    "status": "active",
                    "coverage_percent": 91.7,
                    "active_file_count": 4,
                    "not_yet_started_file_count": 6,
                    "priority_rank": 2,
                    "representative_missing_files": [
                        "uniprot_trembl.xml.gz",
                        "idmapping_selected.tab.gz",
                    ],
                    "representative_partial_files": [
                        "uniprot_trembl.dat.gz",
                    ],
                },
            ],
            "gap_files": [
                {
                    "source_id": "string",
                    "source_name": "STRING v12",
                    "filename": "protein.links.detailed.v12.0.txt.gz",
                    "gap_kind": "missing",
                    "category": "interaction_networks",
                    "priority_rank": 1,
                    "coverage_percent": 81.2,
                },
                {
                    "source_id": "uniprot",
                    "source_name": "UniProt / UniRef / ID Mapping",
                    "filename": "uniprot_trembl.xml.gz",
                    "gap_kind": "missing",
                    "category": "sequence_reference_backbone",
                    "priority_rank": 2,
                    "coverage_percent": 91.7,
                },
            ],
        },
    )

    _write_json(
        supervisor_state_path,
        {
            "generated_at": "2026-03-30T22:19:19.600270+00:00",
            "status": "active",
            "observed_active": [
                {
                    "task_id": "string_download",
                    "description": "Download STRING bulk payload",
                    "priority": 100,
                    "category": "bulk",
                    "pid": 10101,
                    "started_at": "2026-03-30T22:18:12.000000+00:00",
                    "status": "running",
                },
                {
                    "task_id": "reactome_refresh",
                    "description": "Refresh Reactome family payloads",
                    "priority": 90,
                    "category": "bulk",
                    "pid": 10102,
                    "started_at": "2026-03-30T22:18:42.000000+00:00",
                    "status": "running",
                },
            ],
            "active": [
                {
                    "task_id": "stale_fallback_task",
                    "description": "Would be ignored when observed_active exists",
                    "priority": 1,
                    "category": "bulk",
                    "pid": 99999,
                    "started_at": "2026-03-30T22:10:00.000000+00:00",
                    "status": "running",
                }
            ],
            "completed": [
                {
                    "task_id": "prior_wave",
                    "status": "completed",
                }
            ],
            "pending": [],
            "failed": [],
        },
    )

    _write_json(
        local_registry_summary_path,
        {
            "generated_at": "2026-03-30T22:13:29.769475+00:00",
            "inputs": {
                "bootstrap_summary": "data/raw/bootstrap_runs/LATEST.json",
                "local_registry_summary": "data/raw/local_registry_runs/LATEST.json",
            },
            "matrix": [
                {
                    "source_name": "mega_motif_base",
                    "category": "motif",
                    "effective_status": "missing",
                    "coverage_score": 0,
                    "available_via": [],
                    "facet_counts": {
                        "present": 0,
                        "partial": 0,
                        "missing": 1,
                        "degraded": 0,
                        "drifted": 0,
                    },
                    "planning_signals": {"procurement_gap": True},
                },
                {
                    "source_name": "elm",
                    "category": "motif",
                    "effective_status": "partial",
                    "coverage_score": 25,
                    "available_via": ["local_registry"],
                    "facet_counts": {
                        "present": 0,
                        "partial": 1,
                        "missing": 0,
                        "degraded": 0,
                        "drifted": 0,
                    },
                    "planning_signals": {"procurement_gap": True},
                },
                {
                    "source_name": "prosite",
                    "category": "motif",
                    "effective_status": "present",
                    "coverage_score": 100,
                    "available_via": ["local_registry"],
                    "facet_counts": {
                        "present": 1,
                        "partial": 0,
                        "missing": 0,
                        "degraded": 0,
                        "drifted": 0,
                    },
                    "planning_signals": {"procurement_gap": False},
                },
            ],
        },
    )

    return {
        "broad_mirror_progress_path": broad_mirror_progress_path,
        "remaining_transfer_status_path": remaining_transfer_status_path,
        "supervisor_state_path": supervisor_state_path,
        "local_registry_summary_path": local_registry_summary_path,
    }


def test_build_procurement_status_board_combines_live_inputs(tmp_path: Path) -> None:
    paths = _write_board_inputs(tmp_path)

    def unavailable_probe():
        return ([], "unavailable")

    payload = build_procurement_status_board(
        broad_mirror_progress_path=paths["broad_mirror_progress_path"],
        remaining_transfer_status_path=paths["remaining_transfer_status_path"],
        supervisor_state_path=paths["supervisor_state_path"],
        local_registry_summary_path=paths["local_registry_summary_path"],
        process_probe=unavailable_probe,
    )

    assert payload["status"] == "attention"
    assert payload["summary"]["broad_mirror_coverage_percent"] == 37.5
    assert payload["summary"]["source_family_status_counts"] == {
        "complete": 1,
        "missing": 1,
        "partial": 2,
    }
    assert payload["summary"]["active_observed_download_count"] == 8
    assert payload["summary"]["observed_active_source"] == "remaining_transfer_status"
    assert payload["summary"]["local_registry_effective_status_counts"] == {
        "missing": 1,
        "partial": 1,
        "present": 1,
    }
    assert payload["summary"]["top_remaining_gap_count"] == 3
    assert payload["remaining_transfer"]["active_file_count"] == 8
    assert payload["remaining_transfer"]["not_yet_started_file_count"] == 14
    assert payload["remaining_transfer"]["top_gap_files"][0]["filename"] == (
        "protein.links.detailed.v12.0.txt.gz"
    )
    assert payload["top_remaining_gaps"][0]["scope"] == "broad_mirror"
    assert payload["top_remaining_gaps"][0]["source_id"] == "string"
    assert all(row["scope"] == "broad_mirror" for row in payload["top_remaining_gaps"])
    assert payload["broad_mirror"]["top_missing_files"][0]["source_id"] == "string"

    markdown = render_markdown(payload)
    assert "# Procurement Status Board" in markdown
    assert "Broad mirror coverage" in markdown
    assert "Remaining Transfers" in markdown
    assert "Active observed downloads" in markdown
    assert "Active source field" in markdown
    assert "Top remaining filenames" in markdown
    assert "protein.links.detailed.v12.0.txt.gz" in markdown
    assert "`mega_motif_base`" not in markdown


def test_build_procurement_status_board_falls_back_to_active_when_needed(
    tmp_path: Path,
) -> None:
    paths = _write_board_inputs(tmp_path)
    _write_json(
        paths["supervisor_state_path"],
        {
            "generated_at": "2026-03-30T22:19:19.600270+00:00",
            "status": "active",
            "active": [
                {
                    "task_id": "legacy_task",
                    "description": "Legacy active lane",
                    "priority": 10,
                    "category": "bulk",
                    "pid": 10001,
                    "started_at": "2026-03-30T22:18:12.000000+00:00",
                    "status": "running",
                }
            ],
            "completed": [],
            "pending": [],
            "failed": [],
        },
    )

    def unavailable_probe():
        return ([], "unavailable")

    payload = build_procurement_status_board(
        broad_mirror_progress_path=paths["broad_mirror_progress_path"],
        remaining_transfer_status_path=paths["remaining_transfer_status_path"],
        supervisor_state_path=paths["supervisor_state_path"],
        local_registry_summary_path=paths["local_registry_summary_path"],
        process_probe=unavailable_probe,
    )

    assert payload["summary"]["active_observed_download_count"] == 8
    assert payload["summary"]["observed_active_source"] == "remaining_transfer_status"
    assert payload["procurement_supervisor"]["active_observed_downloads"][0]["task_id"] == (
        "string"
    )


def test_build_procurement_status_board_falls_back_to_live_process_table_when_state_is_stale(
    tmp_path: Path,
) -> None:
    paths = _write_board_inputs(tmp_path)
    _write_json(
        paths["supervisor_state_path"],
        {
            "generated_at": "2026-03-30T22:19:19.600270+00:00",
            "status": "idle",
            "active": [],
            "observed_active": [],
            "completed": [],
            "pending": [],
            "failed": [],
        },
    )

    def fake_probe():
        return (
            [
                {
                    "pid": 40404,
                    "name": "python.exe",
                    "command_line": (
                        "python protein_data_scope/download_all_sources.py "
                        "--sources string --dest D:/documents/ProteoSphereV2/data/raw/"
                        "protein_data_scope_seed"
                    ),
                    "creation_date": "2026-03-30T22:20:00+00:00",
                }
            ],
            "available",
        )

    payload = build_procurement_status_board(
        broad_mirror_progress_path=paths["broad_mirror_progress_path"],
        remaining_transfer_status_path=paths["remaining_transfer_status_path"],
        supervisor_state_path=paths["supervisor_state_path"],
        local_registry_summary_path=paths["local_registry_summary_path"],
        process_probe=fake_probe,
    )

    assert payload["summary"]["active_observed_download_count"] == 8
    assert payload["summary"]["observed_active_source"] == "remaining_transfer_status"
    assert payload["procurement_supervisor"]["active_observed_downloads"][0]["filename"] == (
        "protein.links.detailed.v12.0.txt.gz"
    )


def test_build_procurement_status_board_prefers_live_process_table_over_stale_observed_state(
    tmp_path: Path,
) -> None:
    paths = _write_board_inputs(tmp_path)
    _write_json(
        paths["supervisor_state_path"],
        {
            "generated_at": "2026-03-30T22:19:19.600270+00:00",
            "status": "stale",
            "observed_active": [
                {
                    "task_id": "legacy_task",
                    "description": "Legacy observed lane",
                    "priority": 10,
                    "category": "bulk",
                    "pid": 10001,
                    "started_at": "2026-03-30T22:18:12.000000+00:00",
                    "status": "running",
                },
                {
                    "task_id": "legacy_task_2",
                    "description": "Legacy observed lane 2",
                    "priority": 9,
                    "category": "bulk",
                    "pid": 10002,
                    "started_at": "2026-03-30T22:18:22.000000+00:00",
                    "status": "running",
                },
            ],
            "active": [],
            "completed": [],
            "pending": [],
            "failed": [],
        },
    )

    def fake_probe():
        return (
            [
                {
                    "pid": 40404,
                    "name": "python.exe",
                    "command_line": (
                        "python protein_data_scope/download_all_sources.py "
                        "--sources string --dest D:/documents/ProteoSphereV2/data/raw/"
                        "protein_data_scope_seed"
                    ),
                    "creation_date": "2026-03-30T22:20:00+00:00",
                }
            ],
            "available",
        )

    payload = build_procurement_status_board(
        broad_mirror_progress_path=paths["broad_mirror_progress_path"],
        remaining_transfer_status_path=paths["remaining_transfer_status_path"],
        supervisor_state_path=paths["supervisor_state_path"],
        local_registry_summary_path=paths["local_registry_summary_path"],
        process_probe=fake_probe,
    )

    assert payload["summary"]["active_observed_download_count"] == 8
    assert payload["summary"]["observed_active_source"] == "remaining_transfer_status"
    assert payload["procurement_supervisor"]["active_observed_downloads"][0]["filename"] == (
        "protein.links.detailed.v12.0.txt.gz"
    )


def test_main_writes_procurement_status_outputs(tmp_path: Path, capsys) -> None:
    paths = _write_board_inputs(tmp_path)
    output_path = tmp_path / "artifacts" / "status" / "procurement_status_board.json"

    exit_code = main(
        [
            "--broad-mirror-progress",
            str(paths["broad_mirror_progress_path"]),
            "--remaining-transfer-status",
            str(paths["remaining_transfer_status_path"]),
            "--supervisor-state",
            str(paths["supervisor_state_path"]),
            "--local-registry-summary",
            str(paths["local_registry_summary_path"]),
            "--output",
            str(output_path),
            "--no-markdown",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Procurement status board exported" in captured.out
    assert json.loads(output_path.read_text(encoding="utf-8"))["status"] == "attention"


def test_main_writes_fresh_live_download_truth_when_state_is_stale(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    paths = _write_board_inputs(tmp_path)
    _write_json(
        paths["supervisor_state_path"],
        {
            "generated_at": "2026-03-30T22:19:19.600270+00:00",
            "status": "stale",
            "observed_active": [
                {
                    "task_id": "legacy_task",
                    "description": "Legacy observed lane",
                    "priority": 10,
                    "category": "bulk",
                    "pid": 10001,
                    "started_at": "2026-03-30T22:18:12.000000+00:00",
                    "status": "running",
                }
            ],
            "active": [],
            "completed": [],
            "pending": [],
            "failed": [],
        },
    )
    monkeypatch.setattr(
        "scripts.export_procurement_status_board._probe_live_download_processes",
        lambda: (
            [
                {
                    "pid": 50505,
                    "name": "python.exe",
                    "command_line": (
                        "python protein_data_scope/download_all_sources.py "
                        "--sources string --dest D:/documents/ProteoSphereV2/data/raw/"
                        "protein_data_scope_seed"
                    ),
                    "creation_date": "2026-03-30T22:21:00+00:00",
                }
            ],
            "available",
        ),
    )

    output_path = tmp_path / "artifacts" / "status" / "procurement_status_board.json"

    exit_code = main(
        [
            "--broad-mirror-progress",
            str(paths["broad_mirror_progress_path"]),
            "--remaining-transfer-status",
            str(paths["remaining_transfer_status_path"]),
            "--supervisor-state",
            str(paths["supervisor_state_path"]),
            "--local-registry-summary",
            str(paths["local_registry_summary_path"]),
            "--output",
            str(output_path),
            "--no-markdown",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert payload["summary"]["active_observed_download_count"] == 8
    assert (
        payload["procurement_supervisor"]["observed_active_source"]
        == "remaining_transfer_status"
    )
    assert payload["procurement_supervisor"]["active_observed_downloads"][0]["filename"] == (
        "protein.links.detailed.v12.0.txt.gz"
    )
    assert "active=8" in captured.out
