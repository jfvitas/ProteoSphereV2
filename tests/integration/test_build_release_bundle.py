from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.build_release_bundle import build_release_bundle

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


def test_build_release_bundle_assembles_tagged_manifests_and_checksums(tmp_path: Path) -> None:
    output_path = tmp_path / "versioned_release_bundle_manifest.json"

    payload = build_release_bundle(
        source_manifest_path=SOURCE_MANIFEST,
        output_path=output_path,
        bundle_version="2026.04.03",
    )

    saved = _read_json(output_path)

    assert payload == saved
    assert payload["bundle_version"] == "2026.04.03"
    assert payload["bundle_tag"] == "release-bundle:release-benchmark-bundle-2026-03-22@2026.04.03"
    assert payload["bundle_status"] == "assembled_with_checksums"
    assert payload["source_manifest"]["sha256"] == _sha256(SOURCE_MANIFEST)
    assert payload["missing_required_artifacts"] == []

    tagged_manifests = payload["tagged_manifests"]
    checksum_index = payload["checksums"]["artifact_sha256_index"]
    assert tagged_manifests[0]["tag"] == "source_manifest:release_bundle_manifest"
    assert tagged_manifests[0]["sha256"] == _sha256(SOURCE_MANIFEST)
    assert checksum_index[tagged_manifests[0]["tag"]] == tagged_manifests[0]["sha256"]

    expected_tag_count = (
        1 + len(payload["release_artifacts"]) + len(payload["supporting_artifacts"])
    )
    assert len(tagged_manifests) == expected_tag_count

    schema_entry = next(item for item in tagged_manifests if item["role"] == "schema")
    schema_path = ROOT / schema_entry["path"]
    assert schema_entry["required"] is True
    assert schema_entry["present"] is True
    assert schema_entry["sha256"] == _sha256(schema_path)
    assert checksum_index[schema_entry["tag"]] == schema_entry["sha256"]


def test_build_release_bundle_missing_required_artifacts_fails_closed(tmp_path: Path) -> None:
    manifest_path = tmp_path / "release_bundle_manifest.json"
    payload = _read_json(SOURCE_MANIFEST)
    schema_entry = next(item for item in payload["release_artifacts"] if item["role"] == "schema")
    schema_entry["path"] = str(tmp_path / "missing" / "schema.json")
    schema_entry["present"] = True
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="missing required release artifacts"):
        build_release_bundle(
            source_manifest_path=manifest_path,
            output_path=tmp_path / "out.json",
            bundle_version="2026.04.03",
        )
