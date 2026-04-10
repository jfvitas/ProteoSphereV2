from __future__ import annotations

import json
from pathlib import Path

from execution.acquire.unified_source_catalog import build_unified_source_catalog


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


def test_build_unified_source_catalog_reconciles_online_and_local_views(tmp_path: Path) -> None:
    bootstrap_summary = tmp_path / "data" / "raw" / "bootstrap_runs" / "LATEST.json"
    local_registry_summary = tmp_path / "data" / "raw" / "local_registry_runs" / "LATEST.json"

    _write_json(
        bootstrap_summary,
        {
            "results": [
                {
                    "source": "intact",
                    "status": "ok",
                    "downloaded_files": ["data/raw/intact/run/P12345/P12345.txt"],
                    "manifest": {
                        "manifest_id": "IntAct:test",
                        "release_version": "2026-03-23",
                        "source_locator": "https://ebi.example/intact",
                    },
                },
                {
                    "source": "pdbbind",
                    "status": "ok",
                    "downloaded_files": [],
                    "manifest": {
                        "manifest_id": "PDBBind:test",
                        "release_version": "2026-03-23",
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
                    "source_name": "intact",
                    "status": "missing",
                    "category": "interaction_network",
                    "present_root_count": 0,
                    "present_file_count": 0,
                    "present_total_bytes": 0,
                    "load_hints": ["index", "lazy"],
                },
                {
                    "source_name": "reactome",
                    "status": "present",
                    "category": "pathway_annotation",
                    "present_root_count": 1,
                    "present_file_count": 2,
                    "present_total_bytes": 1024,
                    "load_hints": ["preload"],
                },
            ]
        },
    )

    catalog = build_unified_source_catalog(
        bootstrap_summary_path=bootstrap_summary,
        local_registry_summary_path=local_registry_summary,
    )

    entries = {entry.source_name.casefold(): entry for entry in catalog.entries}
    assert entries["intact"].effective_status == "present"
    assert entries["intact"].available_via == ("online_raw",)
    assert entries["intact"].facets[0].snapshot_state == "healthy"
    assert entries["intact"].facets[0].drift_state == "new"
    assert "available via online raw snapshot only" in entries["intact"].notes
    assert entries["pdbbind"].effective_status == "partial"
    assert entries["reactome"].effective_status == "present"
    assert entries["reactome"].available_via == ("local_registry",)
    assert entries["reactome"].facets[0].snapshot_state == "healthy"
    assert "intact" in [name.casefold() for name in catalog.summary["online_only_sources"]]
    assert "reactome" in [name.casefold() for name in catalog.summary["local_only_sources"]]


def test_build_unified_source_catalog_surfaces_latest_degradation_and_local_drift(
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
    _write_json(prev_bindingdb_inventory, {"source_name": "bindingdb", "present_file_count": 1})
    _write_json(curr_bindingdb_inventory, {"source_name": "bindingdb", "present_file_count": 2})

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

    catalog = build_unified_source_catalog(
        bootstrap_summary_path=bootstrap_latest,
        local_registry_summary_path=local_latest,
    )

    entries = {entry.source_name.casefold(): entry for entry in catalog.entries}
    alphafold = entries["alphafold"]
    bindingdb = entries["bindingdb"]

    assert alphafold.facets[0].snapshot_state == "degraded"
    assert alphafold.facets[0].drift_state == "regressed"
    assert bindingdb.facets[0].facet_kind == "local_registry"
    assert bindingdb.facets[0].snapshot_state == "healthy"
    assert bindingdb.facets[0].drift_state == "drifted"
    assert bindingdb.drift_state == "drifted"
    assert "latest online snapshot is degraded" in alphafold.notes
    assert "local source fingerprint drift detected" in bindingdb.notes
    assert catalog.summary["snapshot_state_counts"]["degraded"] >= 1
    assert catalog.summary["drift_state_counts"]["drifted"] >= 1
    assert "alphafold" in [name.casefold() for name in catalog.summary["degraded_online_sources"]]
    assert "bindingdb" in [name.casefold() for name in catalog.summary["drifted_local_sources"]]


def test_build_unified_source_catalog_merges_source_families_across_name_variants(
    tmp_path: Path,
) -> None:
    bootstrap_summary = tmp_path / "data" / "raw" / "bootstrap_runs" / "LATEST.json"
    local_registry_summary = tmp_path / "data" / "raw" / "local_registry_runs" / "LATEST.json"

    _write_json(
        bootstrap_summary,
        {
            "results": [
                {
                    "source": "alphafold",
                    "status": "ok",
                    "downloaded_files": ["data/raw/alphafold/run/P12345.prediction.json"],
                    "manifest": {
                        "manifest_id": "AlphaFold:test",
                        "release_version": "2026-03-30",
                        "source_locator": "https://alphafold.example/api",
                    },
                },
                {
                    "source": "rcsb_pdbe",
                    "status": "ok",
                    "downloaded_files": ["data/raw/rcsb_pdbe/run/P12345.best_structures.json"],
                    "manifest": {
                        "manifest_id": "RCSB_PDBe:test",
                        "release_version": "2026-03-30",
                        "source_locator": "https://pdbe.example/api",
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
                    "source_name": "alphafold_db",
                    "status": "present",
                    "category": "structure",
                    "present_root_count": 1,
                    "present_file_count": 2,
                    "present_total_bytes": 2048,
                    "load_hints": ["index", "lazy"],
                },
                {
                    "source_name": "raw_rcsb",
                    "status": "present",
                    "category": "structure",
                    "present_root_count": 1,
                    "present_file_count": 4,
                    "present_total_bytes": 4096,
                    "load_hints": ["index"],
                },
                {
                    "source_name": "structures_rcsb",
                    "status": "present",
                    "category": "structure",
                    "present_root_count": 1,
                    "present_file_count": 6,
                    "present_total_bytes": 8192,
                    "load_hints": ["lazy"],
                },
            ]
        },
    )

    catalog = build_unified_source_catalog(
        bootstrap_summary_path=bootstrap_summary,
        local_registry_summary_path=local_registry_summary,
    )

    entries = {entry.source_name.casefold(): entry for entry in catalog.entries}
    assert "alphafold" in entries
    assert "rcsb_pdbe" in entries
    assert "alphafold_db" not in entries
    assert "raw_rcsb" not in entries
    assert "structures_rcsb" not in entries
    assert set(entries["alphafold"].available_via) == {"online_raw", "local_registry"}
    assert set(entries["rcsb_pdbe"].available_via) == {"online_raw", "local_registry"}
    assert entries["rcsb_pdbe"].facets[1].detail["present_file_count"] == 10
    assert sorted(entries["rcsb_pdbe"].facets[1].detail["source_members"]) == [
        "raw_rcsb",
        "structures_rcsb",
    ]
    assert "alphafold" in [name.casefold() for name in catalog.summary["dual_sources"]]
    assert "rcsb_pdbe" in [name.casefold() for name in catalog.summary["dual_sources"]]
