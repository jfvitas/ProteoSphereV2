from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.export_duplicate_storage_inventory import (
    build_duplicate_storage_inventory,
    render_duplicate_storage_inventory_markdown,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_duplicate_inventory_detects_exact_duplicates_across_roots(tmp_path: Path) -> None:
    seed = tmp_path / "data" / "raw" / "protein_data_scope_seed"
    local = tmp_path / "data" / "raw" / "local_copies"
    bootstrap = tmp_path / "data" / "raw" / "bootstrap_runs"

    _write(seed / "bindingdb" / "same.txt", "exact duplicate payload")
    _write(local / "bindingdb" / "same_copy.txt", "exact duplicate payload")
    _write(bootstrap / "run_a.json", json.dumps({"status": "ok"}, sort_keys=True))
    _write(bootstrap / "run_b.json", json.dumps({"status": "ok"}, sort_keys=True))

    payload = build_duplicate_storage_inventory(scan_roots=(seed, local, bootstrap))

    summary = payload["summary"]
    assert summary["duplicate_group_count"] >= 2
    assert summary["reclaimable_file_count"] >= 2
    assert summary["reclaimable_bytes"] > 0

    duplicate_classes = {group["duplicate_class"] for group in payload["duplicate_groups"]}
    assert "exact_duplicate_cross_location" in duplicate_classes
    assert "exact_duplicate_same_release" in duplicate_classes


def test_duplicate_inventory_excludes_partial_and_protected_files(tmp_path: Path) -> None:
    raw = tmp_path / "data" / "raw"
    seed = raw / "protein_data_scope_seed"
    packages = tmp_path / "data" / "packages"
    canonical = tmp_path / "data" / "canonical"

    _write(seed / "string" / "database.schema.v12.0.pdf.part", "partial-content")
    _write(packages / "LATEST.json", '{"status":"ready"}')
    _write(canonical / "LATEST.json", '{"status":"ready"}')
    _write(seed / "bindingdb" / "a.txt", "same payload")
    _write(seed / "bindingdb" / "b.txt", "same payload")

    payload = build_duplicate_storage_inventory(
        scan_roots=(seed, packages, canonical),
    )

    assert payload["summary"]["partial_file_count"] == 1
    protected_paths = {entry["path"].replace("\\", "/") for entry in payload["protected_files"]}
    assert "data/packages/LATEST.json" in protected_paths
    assert "data/canonical/LATEST.json" in protected_paths

    partial_paths = {entry["path"].replace("\\", "/") for entry in payload["partial_files"]}
    assert "data/raw/protein_data_scope_seed/string/database.schema.v12.0.pdf.part" in partial_paths


def test_render_duplicate_storage_inventory_markdown_contains_summary(tmp_path: Path) -> None:
    seed = tmp_path / "data" / "raw" / "protein_data_scope_seed"
    local = tmp_path / "data" / "raw" / "local_copies"
    _write(seed / "a" / "x.bin", "abc")
    _write(local / "a" / "y.bin", "abc")

    payload = build_duplicate_storage_inventory(scan_roots=(seed, local))
    markdown = render_duplicate_storage_inventory_markdown(payload)

    assert "# Duplicate Storage Inventory" in markdown
    assert "Top Reclaimable Groups" in markdown
    assert "reclaimable" in markdown.casefold()
