from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.publish_open_source_bundle import (
    DEFAULT_PUBLIC_SUPPORT_ROLES,
    build_open_source_bundle,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCE_MANIFEST = (
    ROOT / "runs" / "real_data_benchmark" / "full_results" / "release_bundle_manifest.json"
)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_manifest_copy(tmp_path: Path, *, mutate_role: str | None = None) -> Path:
    payload = _read_json(SOURCE_MANIFEST)
    if mutate_role is not None:
        for section_name in ("release_artifacts", "supporting_artifacts"):
            for entry in payload.get(section_name, []):
                if isinstance(entry, dict) and entry.get("role") == mutate_role:
                    entry["present"] = False
                    break
    manifest_path = tmp_path / "release_bundle_manifest.json"
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return manifest_path


def test_publish_open_source_bundle_stages_public_artifacts_and_writes_manifest(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "open_source_distribution_bundle"

    payload = build_open_source_bundle(
        source_manifest_path=SOURCE_MANIFEST,
        output_root=output_root,
        bundle_version="2026.04.03",
    )

    output_manifest = output_root / "open_source_distribution_bundle_manifest.json"
    saved = _read_json(output_manifest)
    source_manifest = _read_json(SOURCE_MANIFEST)
    expected_support_count = sum(
        1
        for entry in source_manifest["supporting_artifacts"]
        if entry["role"] in DEFAULT_PUBLIC_SUPPORT_ROLES
    )

    assert payload == saved
    assert payload["bundle_version"] == "2026.04.03"
    assert payload["distribution_tag"] == (
        "open-source-distribution:release-benchmark-bundle-2026-03-22@2026.04.03"
    )
    assert payload["bundle_status"] == "staged_with_checksums"
    assert payload["publication_posture"] == "staged_with_blockers"
    assert payload["release_ready"] is False
    assert payload["missing_required_artifacts"] == []
    assert payload["selected_artifact_count"] == payload["staged_artifact_count"]
    assert payload["selected_release_artifact_count"] == len(source_manifest["release_artifacts"])
    assert payload["selected_support_artifact_count"] == expected_support_count
    assert len(payload["excluded_support_artifacts"]) == (
        len(source_manifest["supporting_artifacts"]) - expected_support_count
    )

    staged_root = output_root / "staged"
    for item in payload["staged_artifacts"]:
        staged_path = Path(item["staged_path"])
        assert staged_path.exists()
        assert staged_path.is_file()
        assert staged_path.is_relative_to(staged_root)
        assert item["sha256"] == _sha256(staged_path)
        assert payload["staged_artifact_sha256_index"][item["tag"]] == item["sha256"]

    schema_item = next(item for item in payload["staged_artifacts"] if item["role"] == "schema")
    assert schema_item["required"] is True
    assert schema_item["visibility"] == "release"
    assert schema_item["path"] == "runs/real_data_benchmark/full_results/schema.json"


def test_publish_open_source_bundle_blocks_on_missing_required_release_artifact(
    tmp_path: Path,
) -> None:
    manifest_path = _write_manifest_copy(tmp_path, mutate_role="schema")

    with pytest.raises(FileNotFoundError, match="missing required public release artifacts"):
        build_open_source_bundle(
            source_manifest_path=manifest_path,
            output_root=tmp_path / "blocked_bundle",
            bundle_version="2026.04.03",
        )

    assert not (tmp_path / "blocked_bundle").exists()


def test_publish_open_source_bundle_blocks_on_missing_public_support_artifact(
    tmp_path: Path,
) -> None:
    manifest_path = _write_manifest_copy(tmp_path, mutate_role="run_summary")

    with pytest.raises(FileNotFoundError, match="missing required public release artifacts"):
        build_open_source_bundle(
            source_manifest_path=manifest_path,
            output_root=tmp_path / "blocked_support_bundle",
            bundle_version="2026.04.03",
        )

    assert not (tmp_path / "blocked_support_bundle").exists()
