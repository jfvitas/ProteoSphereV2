from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_data_inventory import build_inventory_audit, render_inventory_markdown


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_build_inventory_audit_summarizes_raw_local_and_canonical(tmp_path: Path) -> None:
    bootstrap_summary = tmp_path / "data" / "raw" / "bootstrap_runs" / "LATEST.json"
    local_registry_summary = tmp_path / "data" / "raw" / "local_registry_runs" / "LATEST.json"
    canonical_summary = tmp_path / "data" / "canonical" / "LATEST.json"

    _write_json(
        bootstrap_summary,
        {
            "generated_at": "2026-03-23T00:00:00+00:00",
            "accessions": ["P12345"],
            "results": [
                {
                    "source": "intact",
                    "status": "ok",
                    "downloaded_files": ["data/raw/intact/run/P12345/P12345.txt"],
                    "manifest": {
                        "manifest_id": "IntAct:test",
                        "release_version": "2026-03-23",
                        "retrieval_mode": "api",
                        "source_locator": "https://ebi.example/intact",
                    },
                },
                {
                    "source": "uniprot",
                    "status": "ok",
                    "downloaded_files": ["data/raw/uniprot/run/P12345/P12345.json"],
                    "manifest": {
                        "manifest_id": "UniProt:test",
                        "release_version": "2026-03-23",
                        "retrieval_mode": "api",
                        "source_locator": "https://rest.uniprot.org/uniprotkb",
                    },
                }
            ],
        },
    )
    _write_json(
        local_registry_summary,
        {
            "generated_at": "2026-03-23T00:10:00+00:00",
            "stamp": "20260323T001000Z",
            "imported_source_count": 2,
            "selected_source_count": 2,
            "imported_sources": [
                {
                    "source_name": "bindingdb",
                    "status": "present",
                    "category": "assays",
                    "present_file_count": 10,
                    "present_total_bytes": 1024,
                    "inventory_path": "data/raw/local_registry/run/bindingdb/inventory.json",
                    "manifest_path": "data/raw/local_registry/run/bindingdb/manifest.json",
                    "load_hints": ["preload"],
                    "join_keys": ["uniprot_accession"],
                },
                {
                    "source_name": "string",
                    "status": "missing",
                    "category": "ppi",
                    "present_file_count": 0,
                    "present_total_bytes": 0,
                    "load_hints": ["lazy"],
                    "join_keys": ["string_id"],
                },
            ],
        },
    )
    _write_json(
        canonical_summary,
        {
            "created_at": "2026-03-23T00:20:00+00:00",
            "status": "ready",
            "reason": "all_manifest_driven_lanes_resolved",
            "run_id": "raw-bootstrap-canonical-test",
            "record_counts": {
                "protein": 1,
                "ligand": 2,
                "assay": 3,
                "structure": 1,
                "store_total": 7,
            },
            "unresolved_counts": {
                "sequence_conflicts": 0,
                "sequence_unresolved_references": 0,
                "structure_conflicts": 0,
                "structure_unresolved_references": 0,
                "assay_conflicts": 0,
                "assay_unresolved_cases": 0,
            },
            "sequence_result": {"status": "ready", "canonical_proteins": [{}]},
            "structure_result": {"status": "resolved", "canonical_records": [{}]},
            "assay_result": {"status": "resolved", "canonical_assays": [{}, {}, {}]},
            "canonical_store": {
                "records": [
                    {"entity_kind": "protein"},
                    {"entity_kind": "ligand"},
                    {"entity_kind": "ligand"},
                    {"entity_kind": "assay"},
                    {"entity_kind": "assay"},
                    {"entity_kind": "assay"},
                    {"entity_kind": "structure"},
                ]
            },
            "output_paths": {"latest": "data/canonical/LATEST.json"},
        },
    )

    audit = build_inventory_audit(
        bootstrap_summary_path=bootstrap_summary,
        local_registry_summary_path=local_registry_summary,
        canonical_summary_path=canonical_summary,
    )

    assert audit["raw_online"]["ok_source_count"] == 2
    assert audit["raw_local_registry"]["status_counts"]["present"] == 1
    assert audit["raw_local_registry"]["status_counts"]["missing"] == 1
    assert audit["canonical"]["record_counts"]["assay"] == 3
    assert audit["effective_sources"]["summary"]["snapshot_state_counts"]["healthy"] >= 1
    assert "intact" in [
        name.casefold() for name in audit["effective_sources"]["summary"]["online_only_sources"]
    ]
    markdown = render_inventory_markdown(audit)
    assert "Data Inventory Audit" in markdown
    assert "`bindingdb`" in markdown
    assert "Snapshot health states" in markdown
    assert "Online-only sources" in markdown
