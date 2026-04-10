from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.tag_release import TagReleaseError, build_tagged_release

ROOT = Path(__file__).resolve().parents[2]
SOURCE_MANIFEST = (
    ROOT / "runs" / "real_data_benchmark" / "full_results" / "release_bundle_manifest.json"
)
SUPPORT_MANIFEST = (
    ROOT / "runs" / "real_data_benchmark" / "full_results" / "release_support_manifest.json"
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


def test_build_tagged_release_pins_manifest_lineage_and_release_identity(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "ga_tagged_release_manifest.json"

    payload = build_tagged_release(
        source_manifest_path=SOURCE_MANIFEST,
        support_manifest_path=SUPPORT_MANIFEST,
        output_path=output_path,
        bundle_version="2026.04.03",
    )

    saved = _read_json(output_path)
    source_manifest = _read_json(SOURCE_MANIFEST)
    support_manifest = _read_json(SUPPORT_MANIFEST)

    assert payload == saved
    assert payload["bundle_id"] == source_manifest["bundle_id"]
    assert payload["bundle_version"] == "2026.04.03"
    assert payload["release_id"] == "release-benchmark-bundle-2026-03-22@2026.04.03"
    assert payload["release_tag"] == "ga-release:release-benchmark-bundle-2026-03-22@2026.04.03"
    assert payload["bundle_tag"] == payload["release_tag"]
    assert payload["release_ready"] is False
    assert payload["release_gate_status"] == source_manifest["status"]
    assert payload["release_posture"] == "tagged_with_blockers"
    assert payload["validation_warnings"] == ["release_not_ready"]
    assert payload["validation_errors"] == []
    assert payload["source_manifest"]["sha256"] == _sha256(SOURCE_MANIFEST)
    assert payload["support_manifest"]["sha256"] == _sha256(SUPPORT_MANIFEST)
    assert payload["support_manifest"]["bundle_tag"] == support_manifest["bundle_tag"]

    manifest_pins = {item["role"]: item for item in payload["manifest_pins"]}
    assert manifest_pins["release_bundle_manifest"]["sha256"] == _sha256(SOURCE_MANIFEST)
    assert manifest_pins["release_support_manifest"]["sha256"] == _sha256(SUPPORT_MANIFEST)
    assert all(item["present"] for item in manifest_pins.values())

    artifact_pins = payload["artifact_pins"]
    assert len(artifact_pins) == len(source_manifest["release_artifacts"]) + len(
        source_manifest["supporting_artifacts"]
    )
    schema_pin = next(item for item in artifact_pins if item["role"] == "schema")
    assert schema_pin["required"] is True
    assert schema_pin["present"] is True
    assert schema_pin["sha256"] is not None
    assert payload["pinned_required_artifacts"] == 1
    assert payload["pin_summary"]["manifest_pin_count"] == 2
    assert payload["pin_summary"]["required_artifact_pin_count"] == 1


def test_build_tagged_release_fails_closed_on_support_lineage_drift(
    tmp_path: Path,
) -> None:
    support_manifest_path = tmp_path / "release_support_manifest.json"
    payload = _read_json(SUPPORT_MANIFEST)
    payload["source_manifest"]["sha256"] = "deadbeef"
    support_manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with pytest.raises(TagReleaseError, match="does not match the source manifest"):
        build_tagged_release(
            source_manifest_path=SOURCE_MANIFEST,
            support_manifest_path=support_manifest_path,
            output_path=tmp_path / "ga_tagged_release_manifest.json",
            bundle_version="2026.04.03",
        )

    assert not (tmp_path / "ga_tagged_release_manifest.json").exists()
