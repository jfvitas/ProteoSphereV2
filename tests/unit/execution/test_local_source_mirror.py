from __future__ import annotations

import json
from pathlib import Path

from execution.acquire.local_source_mirror import (
    build_bio_agent_lab_context_registry,
    mirror_local_sources,
    summarize_local_root,
)
from execution.acquire.local_source_registry import build_default_local_source_registry


def test_summarize_local_root_counts_nested_files(tmp_path: Path) -> None:
    root = tmp_path / "source"
    nested = root / "nested"
    nested.mkdir(parents=True)
    (root / "a.txt").write_text("abc", encoding="utf-8")
    (nested / "b.txt").write_text("defgh", encoding="utf-8")

    summary = summarize_local_root(root, sample_limit=1)

    assert summary["exists"] is True
    assert summary["kind"] == "directory"
    assert summary["file_count"] == 2
    assert summary["total_bytes"] == 8
    assert len(summary["sample_files"]) == 1


def test_mirror_local_sources_writes_registry_manifests(tmp_path: Path) -> None:
    storage_root = tmp_path / "bio-agent-lab"
    raw_root = tmp_path / "repo" / "data" / "raw"
    (storage_root / "data" / "catalog").mkdir(parents=True)
    (storage_root / "data_sources" / "uniprot").mkdir(parents=True)
    (storage_root / "data" / "catalog" / "download_manifest.csv").write_text(
        "source\nuniprot\n",
        encoding="utf-8",
    )
    (storage_root / "data_sources" / "uniprot" / "uniprot_sprot.dat.gz").write_text(
        "stub",
        encoding="utf-8",
    )

    summary = mirror_local_sources(
        storage_root=storage_root,
        raw_root=raw_root,
        source_names=("catalog", "uniprot", "string"),
        include_missing=False,
        sample_limit=2,
    )

    assert summary["imported_source_count"] == 2
    assert summary["skipped_source_count"] == 1
    assert summary["skipped_sources"][0]["source_name"] == "string"
    assert summary["authoritative_refresh"] is False
    assert summary["latest_updated"] is False
    assert summary["latest_update_reason"] == "scoped_import_did_not_advance_latest"

    stamp = summary["stamp"]
    catalog_inventory = raw_root / "local_registry" / stamp / "catalog" / "inventory.json"
    uniprot_manifest = raw_root / "local_registry" / stamp / "uniprot" / "manifest.json"
    latest_summary = raw_root / "local_registry_runs" / "LATEST.json"

    assert catalog_inventory.exists()
    assert uniprot_manifest.exists()
    assert latest_summary.exists() is False

    inventory_payload = json.loads(catalog_inventory.read_text(encoding="utf-8"))
    manifest_payload = json.loads(uniprot_manifest.read_text(encoding="utf-8"))

    assert inventory_payload["source_name"] == "catalog"
    assert inventory_payload["present_file_count"] == 1
    assert manifest_payload["source_name"] == "bio-agent-lab/uniprot"
    assert any(
        ref.endswith("uniprot_sprot.dat.gz")
        for ref in manifest_payload["local_artifact_refs"]
    )
    assert any(ref.endswith("inventory.json") for ref in manifest_payload["local_artifact_refs"])


def test_mirror_local_sources_updates_latest_for_authoritative_full_refresh(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "bio-agent-lab"
    raw_root = tmp_path / "repo" / "data" / "raw"
    (storage_root / "data" / "catalog").mkdir(parents=True)
    (storage_root / "data" / "catalog" / "download_manifest.csv").write_text(
        "source\nuniprot\n",
        encoding="utf-8",
    )

    summary = mirror_local_sources(
        storage_root=storage_root,
        raw_root=raw_root,
        sample_limit=2,
    )

    latest_summary = raw_root / "local_registry_runs" / "LATEST.json"
    assert summary["authoritative_refresh"] is True
    assert summary["latest_updated"] is True
    assert summary["latest_update_reason"] == "authoritative_full_refresh"
    assert latest_summary.exists()

    latest_payload = json.loads(latest_summary.read_text(encoding="utf-8"))
    assert latest_payload["stamp"] == summary["stamp"]
    assert latest_payload["latest_updated"] is True


def test_build_bio_agent_lab_context_registry_adds_present_context_folders(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "bio-agent-lab"
    (storage_root / "data" / "processed" / "rcsb").mkdir(parents=True)
    (storage_root / "data" / "qa").mkdir(parents=True)
    (storage_root / "data" / "models").mkdir(parents=True)
    (storage_root / "data" / "packaged").mkdir(parents=True)
    (storage_root / "data" / "prediction").mkdir(parents=True)
    (storage_root / "data" / "raw" / "bindingdb").mkdir(parents=True)
    (storage_root / "data" / "identity").mkdir(parents=True)
    (storage_root / "data" / "external").mkdir(parents=True)
    (storage_root / "data" / "interim").mkdir(parents=True)
    (storage_root / "data" / "raw" / "bindingdb" / "manifest.csv").write_text(
        "source_id\n1\n",
        encoding="utf-8",
    )

    registry = build_bio_agent_lab_context_registry(storage_root)
    default_registry = build_default_local_source_registry(storage_root)

    assert registry.entry_count > default_registry.entry_count
    assert registry.get("processed") is not None
    assert registry.get("qa") is not None
    assert registry.get("models") is not None
    assert registry.get("packaged") is not None
    assert registry.get("prediction") is not None
    assert registry.get("raw") is not None
    assert registry.get("identity") is not None
    assert registry.get("external") is not None
    assert registry.get("interim") is not None

    processed = registry.get("processed")
    packaged = registry.get("packaged")
    raw = registry.get("raw")
    assert processed is not None and processed.status == "present"
    assert processed.category == "derived_training"
    assert processed.load_hints == ("index", "lazy")
    assert packaged is not None and packaged.category == "release_artifact"
    assert raw is not None and raw.category == "metadata"
    assert raw.candidate_roots == (str(storage_root / "data" / "raw"),)


def test_mirror_local_sources_can_target_present_context_folders(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "bio-agent-lab"
    raw_root = tmp_path / "repo" / "data" / "raw"
    (storage_root / "data" / "processed" / "rcsb").mkdir(parents=True)
    (storage_root / "data" / "models").mkdir(parents=True)
    (storage_root / "data" / "qa").mkdir(parents=True)
    (storage_root / "data" / "raw" / "bindingdb").mkdir(parents=True)
    (storage_root / "data" / "processed" / "rcsb" / "state.json").write_text(
        "{}",
        encoding="utf-8",
    )
    (storage_root / "data" / "models" / "model_manifest.json").write_text(
        "{}",
        encoding="utf-8",
    )
    (storage_root / "data" / "qa" / "scenario_test_manifest.json").write_text(
        "{}",
        encoding="utf-8",
    )
    (storage_root / "data" / "raw" / "bindingdb" / "bindingdb.tsv").write_text(
        "id\tvalue\n1\t2\n",
        encoding="utf-8",
    )

    summary = mirror_local_sources(
        storage_root=storage_root,
        raw_root=raw_root,
        source_names=("processed", "models", "qa", "raw"),
        include_missing=False,
        sample_limit=1,
    )

    imported_names = [item["source_name"] for item in summary["imported_sources"]]
    assert imported_names == ["processed", "models", "qa", "raw"]
    assert summary["imported_source_count"] == 4
    assert summary["authoritative_refresh"] is False

    processed = next(
        item for item in summary["imported_sources"] if item["source_name"] == "processed"
    )
    raw = next(item for item in summary["imported_sources"] if item["source_name"] == "raw")
    assert processed["category"] == "derived_training"
    assert processed["present_file_count"] == 1
    assert processed["join_keys"] == []
    assert raw["category"] == "metadata"
    assert raw["present_file_count"] == 1
