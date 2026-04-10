from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.generate_release_notes import build_release_notes

ROOT = Path(__file__).resolve().parents[2]
SOURCE_MANIFEST = (
    ROOT / "runs" / "real_data_benchmark" / "full_results" / "release_bundle_manifest.json"
)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_build_release_notes_carries_blocker_categories_into_both_outputs(
    tmp_path: Path,
) -> None:
    notes_output = tmp_path / "release_notes.md"
    support_output = tmp_path / "release_support_manifest.json"

    payload = build_release_notes(
        source_manifest_path=SOURCE_MANIFEST,
        notes_output_path=notes_output,
        support_output_path=support_output,
        bundle_version="2026.04.03",
    )

    support_manifest = _read_json(support_output)
    source_manifest = _read_json(SOURCE_MANIFEST)

    assert payload["bundle_version"] == "2026.04.03"
    assert payload["bundle_tag"] == "release-notes:release-benchmark-bundle-2026-03-22@2026.04.03"
    assert notes_output.exists()
    assert support_output.exists()
    assert support_manifest["bundle_id"] == source_manifest["bundle_id"]
    assert support_manifest["blocker_categories"] == source_manifest["blocker_categories"]
    assert support_manifest["carry_through"]["blocker_categories"] == source_manifest[
        "blocker_categories"
    ]
    assert support_manifest["carry_through"]["release_status"] == source_manifest["status"]
    assert support_manifest["truth_boundary"] == source_manifest["truth_boundary"]
    assert (
        support_manifest["evidence_artifacts"][0]["tag"]
        == "source_manifest:release_bundle_manifest"
    )
    assert support_manifest["evidence_artifacts"][0]["sha256"] is not None

    notes_text = notes_output.read_text(encoding="utf-8")
    for blocker in source_manifest["blocker_categories"]:
        assert blocker in notes_text
    assert "## Blockers" in notes_text
    assert "## Truth Boundary" in notes_text
    assert "release_support_manifest.json" in notes_text


def test_build_release_notes_fails_closed_on_missing_required_artifact(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "release_bundle_manifest.json"
    payload = _read_json(SOURCE_MANIFEST)
    schema_entry = next(
        item for item in payload["release_artifacts"] if item["role"] == "schema"
    )
    schema_entry["present"] = False
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="missing required release artifacts"):
        build_release_notes(
            source_manifest_path=manifest_path,
            notes_output_path=tmp_path / "notes.md",
            support_output_path=tmp_path / "support.json",
        )
