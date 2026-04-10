from __future__ import annotations

import json
from pathlib import Path

from execution.acquire.corpus_registry import build_corpus_registry


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_build_corpus_registry_emits_rows_from_online_and_local_manifests(tmp_path: Path) -> None:
    bootstrap_summary = tmp_path / "data" / "raw" / "bootstrap_runs" / "LATEST.json"
    local_registry_summary = tmp_path / "data" / "raw" / "local_registry_runs" / "LATEST.json"

    _write_json(
        bootstrap_summary,
        {
            "results": [
                {
                    "source": "IntAct",
                    "status": "ok",
                    "downloaded_files": ["data/raw/intact/run/P04637/P04637.mitab"],
                    "manifest": {
                        "release_version": "2026-03-23",
                        "source_locator": "https://ebi.example/intact",
                    },
                },
                {
                    "source": "PDBBind",
                    "status": "ok",
                    "downloaded_files": [],
                    "manifest": {
                        "release_version": "2026-03-23",
                        "source_locator": "https://pdbbind.example/archive",
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
                    "present_file_count": 6972,
                    "present_total_bytes": 2984467160,
                    "join_keys": ["accession", "inchi_key"],
                    "load_hints": ["index", "lazy"],
                },
                {
                    "source_name": "reactome",
                    "status": "present",
                    "category": "pathway_annotation",
                    "present_file_count": 2,
                    "present_total_bytes": 1024,
                    "join_keys": ["accession", "reactome_id"],
                    "load_hints": ["preload"],
                },
                {
                    "source_name": "biogrid",
                    "status": "missing",
                    "category": "interaction_network",
                    "present_file_count": 0,
                    "present_total_bytes": 0,
                    "join_keys": ["accession"],
                    "load_hints": ["index", "lazy"],
                },
                {
                    "source_name": "catalog",
                    "status": "present",
                    "category": "metadata",
                    "present_file_count": 1,
                    "present_total_bytes": 512,
                    "join_keys": [],
                    "load_hints": ["preload"],
                },
            ]
        },
    )

    registry = build_corpus_registry(
        bootstrap_summary_path=bootstrap_summary,
        local_registry_summary_path=local_registry_summary,
    )

    rows = {row.row_id: row for row in registry.rows}
    assert "pair:intact" in rows
    assert rows["pair:intact"].effective_status == "present"
    assert rows["pair:intact"].available_via == ("online_raw",)
    assert rows["pair:intact"].online_release_version == "2026-03-23"
    assert "online_only" in rows["pair:intact"].notes

    assert "ligand:bindingdb" in rows
    assert rows["ligand:bindingdb"].effective_status == "present"
    assert rows["ligand:bindingdb"].available_via == ("local_registry",)
    assert rows["ligand:bindingdb"].local_join_keys == ("accession", "inchi_key")

    assert "annotation:reactome" in rows
    assert rows["annotation:reactome"].effective_status == "present"
    assert rows["annotation:reactome"].source_category == "pathway_annotation"

    assert "pair:biogrid" in rows
    assert rows["pair:biogrid"].effective_status == "missing"
    assert "no_current_source_copy" in rows["pair:biogrid"].notes

    assert "ligand:pdbbind" in rows
    assert rows["ligand:pdbbind"].effective_status == "partial"
    assert rows["ligand:pdbbind"].online_downloaded_file_count == 0

    assert "metadata:catalog" not in rows
    assert registry.summary["candidate_kind_counts"] == {
        "annotation": 1,
        "ligand": 2,
        "pair": 2,
    }


def test_build_corpus_registry_merges_online_and_local_views_for_same_source(
    tmp_path: Path,
) -> None:
    bootstrap_summary = tmp_path / "data" / "raw" / "bootstrap_runs" / "LATEST.json"
    local_registry_summary = tmp_path / "data" / "raw" / "local_registry_runs" / "LATEST.json"

    _write_json(
        bootstrap_summary,
        {
            "results": [
                {
                    "source": "BindingDB",
                    "status": "ok",
                    "downloaded_files": ["data/raw/bindingdb/run/P31749/P31749.bindingdb.json"],
                    "manifest": {
                        "release_version": "2026-03-23",
                        "source_locator": "https://bindingdb.example/rest",
                    },
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
                    "present_file_count": 10,
                    "present_total_bytes": 2048,
                    "join_keys": ["accession"],
                    "load_hints": ["index"],
                }
            ]
        },
    )

    registry = build_corpus_registry(
        bootstrap_summary_path=bootstrap_summary,
        local_registry_summary_path=local_registry_summary,
    )

    assert len(registry.rows) == 1
    row = registry.rows[0]
    assert row.row_id == "ligand:bindingdb"
    assert row.effective_status == "present"
    assert row.available_via == ("online_raw", "local_registry")
    assert "online_and_local" in row.notes
    assert row.local_present_file_count == 10
    assert row.online_downloaded_file_count == 1
