from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.schema_migrate import SchemaMigrationError, migrate_schema_file

ROOT = Path(__file__).resolve().parents[2]
SOURCE_ARTIFACT = ROOT / "artifacts" / "status" / "summary_library_inventory.json"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_schema_migrate_upgrades_pinned_summary_inventory_forward(tmp_path: Path) -> None:
    output_path = tmp_path / "summary_library_inventory.schema_v2.json"

    report = migrate_schema_file(
        SOURCE_ARTIFACT,
        output_path,
        target_schema_version=2,
    )
    saved = _read_json(output_path)
    source = _read_json(SOURCE_ARTIFACT)

    assert report["status"] == "upgraded"
    assert report["safe_upgrade"] is True
    assert report["upgrade_policy"] == "forward_only"
    assert report["source_schema_version"] == 1
    assert report["target_schema_version"] == 2
    assert report["applied_migrations"] == ["schema_version 1 -> 2"]
    assert report["current_schema_version"] == 2
    assert report["input_sha256"] != report["output_sha256"]

    assert saved["schema_version"] == 2
    assert saved["schema_version_history"] == [1, 2]
    assert saved["schema_migration"]["status"] == "upgraded"
    assert saved["schema_migration"]["safe_upgrade"] is True
    assert saved["schema_migration"]["upgrade_policy"] == "forward_only"
    assert saved["schema_migration"]["source_schema_version"] == 1
    assert saved["schema_migration"]["target_schema_version"] == 2

    assert saved["library_id"] == source["library_id"]
    assert saved["source_manifest_id"] == source["source_manifest_id"]
    assert saved["record_count"] == source["record_count"]
    assert saved["record_type_counts"] == source["record_type_counts"]
    assert saved["join_status_counts"] == source["join_status_counts"]
    assert saved["storage_tier_counts"] == source["storage_tier_counts"]


def test_schema_migrate_rejects_unsupported_target_version(tmp_path: Path) -> None:
    output_path = tmp_path / "summary_library_inventory.schema_v3.json"

    with pytest.raises(SchemaMigrationError, match="unsupported target schema_version 3"):
        migrate_schema_file(
            SOURCE_ARTIFACT,
            output_path,
            target_schema_version=3,
        )

    assert not output_path.exists()
