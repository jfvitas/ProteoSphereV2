from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.export_source_coverage_matrix import build_source_coverage_matrix, render_markdown


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_manifest(path: Path, *, fingerprint: str, source_name: str) -> None:
    _write_json(
        path,
        {
            "manifest_id": f"{source_name}:{fingerprint}",
            "source_name": source_name,
            "release_version": "2026-03-23",
            "retrieval_mode": "download",
            "source_locator": str(path.parent),
            "local_artifact_refs": [str(path.parent)],
            "provenance": ["local_source_mirror", source_name],
            "reproducibility_metadata": ["join_keys=P12345"],
            "snapshot_fingerprint": fingerprint,
        },
    )


def test_build_source_coverage_matrix_merges_online_and_local_views(tmp_path: Path) -> None:
    bootstrap_summary = tmp_path / "data" / "raw" / "bootstrap_runs" / "LATEST.json"
    local_registry_summary = tmp_path / "data" / "raw" / "local_registry_runs" / "LATEST.json"

    _write_json(
        bootstrap_summary,
        {
            "results": [
                {
                    "source": "bindingdb",
                    "status": "ok",
                    "downloaded_files": ["data/raw/bindingdb/P31749.json"],
                    "manifest": {
                        "manifest_id": "BindingDB:test",
                        "release_version": "2026-03-23",
                        "source_locator": "https://bindingdb.example",
                    },
                },
                {
                    "source": "pdbbind",
                    "status": "ok",
                    "downloaded_files": [],
                    "manifest": {
                        "manifest_id": "PDBBind:test",
                        "release_version": "2026-03-23",
                        "source_locator": "https://pdbbind.example",
                    },
                },
            ]
        },
    )
    _write_json(
        local_registry_summary,
        {
            "imported_sources": [
                {
                    "source_name": "bindingdb",
                    "status": "present",
                    "category": "protein_ligand",
                    "present_root_count": 2,
                    "present_file_count": 10,
                    "present_total_bytes": 2048,
                    "load_hints": ["index", "lazy"],
                    "join_keys": ["uniprot_accession"],
                },
                {
                    "source_name": "reactome",
                    "status": "partial",
                    "category": "pathway_annotation",
                    "present_root_count": 1,
                    "present_file_count": 3,
                    "present_total_bytes": 512,
                    "load_hints": ["preload"],
                    "join_keys": ["accession"],
                },
                {
                    "source_name": "biogrid",
                    "status": "missing",
                    "category": "interaction_network",
                    "present_root_count": 0,
                    "present_file_count": 0,
                    "present_total_bytes": 0,
                    "load_hints": ["index"],
                    "join_keys": ["accession"],
                },
            ]
        },
    )

    payload = build_source_coverage_matrix(
        bootstrap_summary_path=bootstrap_summary,
        local_registry_summary_path=local_registry_summary,
    )

    matrix = {row["source_name"].casefold(): row for row in payload["matrix"]}
    assert payload["summary"]["source_count"] == 4
    assert payload["summary"]["status_counts"] == {
        "missing": 1,
        "partial": 2,
        "present": 1,
    }
    assert payload["summary"]["available_via_counts"] == {
        "local_registry": 2,
        "online_raw": 2,
    }
    assert payload["summary"]["present_source_count"] == 1
    assert payload["summary"]["partial_source_count"] == 2
    assert payload["summary"]["missing_source_count"] == 1
    assert payload["summary"]["total_downloaded_files"] == 1
    assert payload["summary"]["total_present_files"] == 13
    assert payload["summary"]["total_present_bytes"] == 2560
    assert matrix["bindingdb"]["effective_status"] == "present"
    assert matrix["bindingdb"]["available_via"] == ["online_raw", "local_registry"]
    assert matrix["bindingdb"]["counts"] == {
        "downloaded_file_count": 1,
        "present_file_count": 10,
        "present_total_bytes": 2048,
    }
    assert matrix["bindingdb"]["planning_signals"]["procurement_gap"] is False
    assert matrix["pdbbind"]["effective_status"] == "partial"
    assert matrix["pdbbind"]["available_via"] == ["online_raw"]
    assert matrix["pdbbind"]["counts"]["downloaded_file_count"] == 0
    assert matrix["biogrid"]["effective_status"] == "missing"
    assert matrix["biogrid"]["available_via"] == []
    assert matrix["biogrid"]["planning_signals"]["procurement_gap"] is True


def test_build_source_coverage_matrix_surfaces_snapshot_health_and_drift(
    tmp_path: Path,
) -> None:
    bootstrap_runs = tmp_path / "data" / "raw" / "bootstrap_runs"
    local_runs = tmp_path / "data" / "raw" / "local_registry_runs"
    bootstrap_latest = bootstrap_runs / "LATEST.json"
    bootstrap_previous = bootstrap_runs / "20260322T235900Z.json"
    local_latest = local_runs / "LATEST.json"
    local_previous = local_runs / "20260322T235900Z.json"

    _write_json(
        bootstrap_previous,
        {
            "results": [
                {
                    "source": "alphafold",
                    "status": "ok",
                    "downloaded_files": ["data/raw/alphafold/P12345.json"],
                    "manifest": {
                        "manifest_id": "AlphaFold:test-prev",
                        "release_version": "2026-03-22",
                        "snapshot_fingerprint": "prev-af",
                    },
                }
            ]
        },
    )
    _write_json(
        bootstrap_latest,
        {
            "results": [
                {
                    "source": "alphafold",
                    "status": "failed",
                    "error": "HTTPError: HTTP Error 404: Not Found",
                    "downloaded_files": [],
                }
            ]
        },
    )

    prev_bindingdb_manifest = local_runs / "20260322T235900Z" / "bindingdb" / "manifest.json"
    curr_bindingdb_manifest = local_runs / "20260323T000100Z" / "bindingdb" / "manifest.json"
    prev_bindingdb_inventory = local_runs / "20260322T235900Z" / "bindingdb" / "inventory.json"
    curr_bindingdb_inventory = local_runs / "20260323T000100Z" / "bindingdb" / "inventory.json"
    _write_manifest(prev_bindingdb_manifest, fingerprint="prev-bdb", source_name="bindingdb")
    _write_manifest(curr_bindingdb_manifest, fingerprint="curr-bdb", source_name="bindingdb")
    _write_json(prev_bindingdb_inventory, {"source_name": "bindingdb"})
    _write_json(curr_bindingdb_inventory, {"source_name": "bindingdb"})

    _write_json(
        local_previous,
        {
            "imported_sources": [
                {
                    "source_name": "bindingdb",
                    "status": "present",
                    "category": "protein_ligand",
                    "present_root_count": 1,
                    "present_file_count": 1,
                    "present_total_bytes": 100,
                    "inventory_path": str(prev_bindingdb_inventory),
                    "manifest_path": str(prev_bindingdb_manifest),
                    "load_hints": ["index"],
                    "join_keys": ["P12345"],
                }
            ]
        },
    )
    _write_json(
        local_latest,
        {
            "imported_sources": [
                {
                    "source_name": "bindingdb",
                    "status": "present",
                    "category": "protein_ligand",
                    "present_root_count": 1,
                    "present_file_count": 2,
                    "present_total_bytes": 200,
                    "inventory_path": str(curr_bindingdb_inventory),
                    "manifest_path": str(curr_bindingdb_manifest),
                    "load_hints": ["index"],
                    "join_keys": ["P12345"],
                }
            ]
        },
    )

    payload = build_source_coverage_matrix(
        bootstrap_summary_path=bootstrap_latest,
        local_registry_summary_path=local_latest,
    )

    matrix = {row["source_name"].casefold(): row for row in payload["matrix"]}
    assert payload["summary"]["snapshot_state_counts"]["degraded"] >= 1
    assert payload["summary"]["drift_state_counts"]["drifted"] >= 1
    assert "alphafold" in [
        name.casefold() for name in payload["summary"]["degraded_online_sources"]
    ]
    assert "bindingdb" in [
        name.casefold() for name in payload["summary"]["drifted_local_sources"]
    ]
    assert matrix["alphafold"]["snapshot_state"] == "degraded"
    assert matrix["alphafold"]["planning_signals"]["snapshot_degraded"] is True
    assert matrix["bindingdb"]["drift_state"] == "drifted"
    assert matrix["bindingdb"]["planning_signals"]["local_fingerprint_drift"] is True
    assert matrix["bindingdb"]["coverage_score"] < 311


def test_render_markdown_surfaces_priority_and_matrix() -> None:
    markdown = render_markdown(
        {
            "generated_at": "2026-03-23T11:00:00+00:00",
            "summary": {
                "source_count": 2,
                "status_counts": {"present": 1, "missing": 1},
                "available_via_counts": {"local_registry": 1, "online_raw": 1},
                "total_downloaded_files": 1,
                "total_present_files": 7,
                "total_present_bytes": 1024,
                "procurement_priority_sources": ["biogrid"],
                "highest_coverage_sources": ["bindingdb"],
            },
            "matrix": [
                {
                    "source_name": "bindingdb",
                    "effective_status": "present",
                    "available_via": ["online_raw", "local_registry"],
                    "coverage_score": 317,
                },
                {
                    "source_name": "biogrid",
                    "effective_status": "missing",
                    "available_via": [],
                    "coverage_score": 0,
                },
            ],
        }
    )

    assert "# Source Coverage Matrix" in markdown
    assert "Priority sources: `biogrid`" in markdown
    assert (
        "`bindingdb` status=`present` snapshot=`unknown` drift=`unknown` "
        "via=`online_raw,local_registry`"
    ) in markdown


def test_export_source_coverage_matrix_cli_writes_json_and_markdown(tmp_path: Path) -> None:
    bootstrap_summary = tmp_path / "data" / "raw" / "bootstrap_runs" / "LATEST.json"
    local_registry_summary = tmp_path / "data" / "raw" / "local_registry_runs" / "LATEST.json"
    output_path = tmp_path / "artifacts" / "status" / "source_coverage_matrix.json"
    markdown_path = tmp_path / "docs" / "reports" / "source_coverage_matrix.md"

    _write_json(
        bootstrap_summary,
        {
            "results": [
                {
                    "source": "bindingdb",
                    "status": "ok",
                    "downloaded_files": ["data/raw/bindingdb/P31749.json"],
                    "manifest": {"manifest_id": "BindingDB:test", "release_version": "2026-03-23"},
                }
            ]
        },
    )
    _write_json(
        local_registry_summary,
        {
            "imported_sources": [
                {
                    "source_name": "bindingdb",
                    "status": "present",
                    "category": "protein_ligand",
                    "present_root_count": 1,
                    "present_file_count": 1,
                    "present_total_bytes": 10,
                    "load_hints": ["index"],
                    "join_keys": ["uniprot_accession"],
                }
            ]
        },
    )

    command = [
        sys.executable,
        str(Path(__file__).resolve().parents[2] / "scripts" / "export_source_coverage_matrix.py"),
        "--bootstrap-summary",
        str(bootstrap_summary),
        "--local-registry-summary",
        str(local_registry_summary),
        "--output",
        str(output_path),
        "--markdown-output",
        str(markdown_path),
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8")

    assert "Source coverage matrix exported:" in result.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["source_count"] == 1
    assert markdown_path.read_text(encoding="utf-8").startswith("# Source Coverage Matrix")
