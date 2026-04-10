from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scripts.build_release_bundle import build_release_bundle
from scripts.rollback_release import RollbackReleaseError, rollback_release_state

ROOT = Path(__file__).resolve().parents[2]
SOURCE_MANIFEST = (
    ROOT / "runs" / "real_data_benchmark" / "full_results" / "release_bundle_manifest.json"
)
RELEASE_RESULTS_ROOT = ROOT / "runs" / "real_data_benchmark" / "full_results"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_release_fixture_tree(source_root: Path, temp_root: Path) -> None:
    source_manifest = _read_json(SOURCE_MANIFEST)
    manifest_path = (
        temp_root
        / "runs"
        / "real_data_benchmark"
        / "full_results"
        / "release_bundle_manifest.json"
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        source_root
        / "runs"
        / "real_data_benchmark"
        / "full_results"
        / "release_bundle_manifest.json",
        manifest_path,
    )

    for section_name in ("release_artifacts", "supporting_artifacts"):
        for entry in source_manifest.get(section_name, []):
            if not isinstance(entry, dict):
                continue
            raw_path = entry.get("path")
            if not raw_path:
                continue
            source_path = source_root / raw_path
            destination_path = temp_root / raw_path
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination_path)


def test_rollback_release_state_restores_paired_manifests_and_artifacts(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / "recovered"
    source_root.mkdir()
    _copy_release_fixture_tree(ROOT, source_root)
    build_release_bundle(
        source_manifest_path=(
            source_root
            / "runs"
            / "real_data_benchmark"
            / "full_results"
            / "release_bundle_manifest.json"
        ),
        output_path=(
            source_root
            / "runs"
            / "real_data_benchmark"
            / "full_results"
            / "versioned_release_bundle_manifest.json"
        ),
        bundle_version="2026.04.03",
    )

    report = rollback_release_state(source_root=source_root, output_root=output_root)

    assert report["status"] == "restored"
    assert report["rollback"]["performed"] is False
    assert report["artifacts"]["missing_count"] == 0
    assert report["artifacts"]["required_missing_count"] == 0
    assert (
        output_root
        / "runs"
        / "real_data_benchmark"
        / "full_results"
        / "release_bundle_manifest.json"
    ).exists()
    assert (
        output_root
        / "runs"
        / "real_data_benchmark"
        / "full_results"
        / "versioned_release_bundle_manifest.json"
    ).exists()
    assert (
        output_root / "rollback_release_report.json"
    ).exists()
    assert _read_json(output_root / "rollback_release_report.json")["status"] == "restored"
    assert (
        output_root / "runs" / "real_data_benchmark" / "full_results" / "schema.json"
    ).exists()


def test_rollback_release_state_blocks_and_cleans_partial_output_after_failed_migration(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / "blocked"
    source_root.mkdir()
    _copy_release_fixture_tree(ROOT, source_root)
    build_release_bundle(
        source_manifest_path=(
            source_root
            / "runs"
            / "real_data_benchmark"
            / "full_results"
            / "release_bundle_manifest.json"
        ),
        output_path=(
            source_root
            / "runs"
            / "real_data_benchmark"
            / "full_results"
            / "versioned_release_bundle_manifest.json"
        ),
        bundle_version="2026.04.03",
    )
    (source_root / "runs" / "real_data_benchmark" / "full_results" / "schema.json").unlink()

    with pytest.raises(RollbackReleaseError, match="unsafe rollback conditions"):
        rollback_release_state(source_root=source_root, output_root=output_root)

    assert output_root.exists() is False
