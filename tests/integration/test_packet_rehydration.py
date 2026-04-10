from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from core.storage.canonical_store import CanonicalStore, CanonicalStoreRecord
from core.storage.package_manifest import (
    PackageManifest,
    PackageManifestArtifactPointer,
    PackageManifestExample,
    PackageManifestRawManifest,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _package_manifest() -> PackageManifest:
    return PackageManifest(
        package_id="packet-001",
        selected_examples=(
            PackageManifestExample(
                example_id="example-1",
                planning_index_ref="planning/index/example-1",
                source_record_refs=("source-a:1",),
                canonical_ids=("protein:P12345",),
                artifact_pointers=(
                    PackageManifestArtifactPointer(
                        artifact_kind="feature",
                        pointer="artifacts/features/example-1.npy",
                        selector="feature:0",
                        source_name="source-a",
                        source_record_id="source-a:1",
                    ),
                    PackageManifestArtifactPointer(
                        artifact_kind="structure",
                        pointer="artifacts/structures/example-1.cif",
                        selector="structure:0",
                        source_name="source-a",
                        source_record_id="source-a:1",
                    ),
                ),
            ),
        ),
        raw_manifests=(
            PackageManifestRawManifest(
                source_name="source-a",
                raw_manifest_id="raw-source-a-001",
                raw_manifest_ref="raw/source-a/001.json",
                release_version="2026-03-22",
                planning_index_ref="planning/index/example-1",
            ),
        ),
        planning_index_refs=("planning/index/example-1",),
        provenance=("prov:packet-001",),
    )


def _canonical_store() -> CanonicalStore:
    return CanonicalStore(
        records=(
            CanonicalStoreRecord(
                canonical_id="protein:P12345",
                entity_kind="protein",
                canonical_payload={"accession": "P12345"},
            ),
        )
    )


def test_rehydrate_training_packet_cli_materializes_selected_packet(tmp_path: Path) -> None:
    package_manifest_path = tmp_path / "package_manifest.json"
    available_artifacts_path = tmp_path / "available_artifacts.json"
    canonical_store_path = tmp_path / "canonical_store.json"
    output_path = tmp_path / "rehydration_report.json"

    _write_json(package_manifest_path, _package_manifest().to_dict())
    _write_json(
        available_artifacts_path,
        {
            "available_artifacts": {
                "artifacts/features/example-1.npy": {
                    "materialized_ref": "materialized/features/example-1.npy",
                    "checksum": "sha256:feature-1",
                },
                "artifacts/structures/example-1.cif": {
                    "materialized_ref": "materialized/structures/example-1.cif",
                    "checksum": "sha256:structure-1",
                },
            }
        },
    )
    _write_json(canonical_store_path, _canonical_store().to_dict())

    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "rehydrate_training_packet.py"),
            "--package-manifest",
            str(package_manifest_path),
            "--available-artifacts",
            str(available_artifacts_path),
            "--canonical-store",
            str(canonical_store_path),
            "--output",
            str(output_path),
            "--materialization-run-id",
            "rehydrate-run-001",
            "--materialized-at",
            "2026-03-22T12:00:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    report = _read_json(output_path)
    assert report["task_id"] == "P18-T006"
    assert report["status"] == "materialized"
    assert report["materialization_status"] == "materialized"
    assert report["checksum_audit_status"] == "consistent"
    assert report["selected_example_count"] == 1
    assert report["materialized_example_count"] == 1
    assert report["issue_summary"]["materialization_issue_count"] == 0
    assert report["materialization"]["materialization_run_id"] == "rehydrate-run-001"
    assert report["materialization"]["selected_examples"][0]["status"] == "materialized"
    assert (
        report["checksum_audit"]["entries"][0]["materialized_artifact_count"] == 2
    )
    assert report["checksum_audit"]["entries"][0]["missing_artifact_pointers"] == []


def test_rehydrate_training_packet_cli_allows_truthful_partial_rebuild(tmp_path: Path) -> None:
    package_manifest_path = tmp_path / "package_manifest.json"
    available_artifacts_path = tmp_path / "available_artifacts.json"
    canonical_store_path = tmp_path / "canonical_store.json"
    output_path = tmp_path / "rehydration_report.json"

    _write_json(package_manifest_path, _package_manifest().to_dict())
    _write_json(
        available_artifacts_path,
        {
            "available_artifacts": {
                "artifacts/features/example-1.npy": {
                    "materialized_ref": "materialized/features/example-1.npy",
                    "checksum": "sha256:feature-1",
                }
            }
        },
    )
    _write_json(canonical_store_path, _canonical_store().to_dict())

    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "rehydrate_training_packet.py"),
            "--package-manifest",
            str(package_manifest_path),
            "--available-artifacts",
            str(available_artifacts_path),
            "--canonical-store",
            str(canonical_store_path),
            "--output",
            str(output_path),
            "--allow-partial",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    report = _read_json(output_path)
    assert report["status"] == "partial_rehydration"
    assert report["materialization_status"] == "partial"
    assert report["checksum_audit_status"] == "partial"
    assert report["issue_summary"]["materialization_issue_count"] == 1
    assert report["issue_summary"]["missing_artifact_issue_count"] == 1
    assert report["issue_summary"]["missing_artifact_pointer_count"] == 1
    assert report["materialized_example_count"] == 1
    assert report["materialization"]["selected_examples"][0]["status"] == "partial"
    assert (
        report["materialization"]["selected_examples"][0]["issues"][0]["artifact_pointer"]
        == "artifacts/structures/example-1.cif"
    )
    assert report["checksum_audit"]["entries"][0]["packet_state"] == "partial"
    assert report["checksum_audit"]["entries"][0]["missing_artifact_pointers"] == [
        "artifacts/structures/example-1.cif"
    ]


def test_rehydrate_training_packet_cli_fails_closed_when_packet_is_unresolved(
    tmp_path: Path,
) -> None:
    package_manifest_path = tmp_path / "package_manifest.json"
    available_artifacts_path = tmp_path / "available_artifacts.json"
    canonical_store_path = tmp_path / "canonical_store.json"
    output_path = tmp_path / "rehydration_report.json"

    _write_json(package_manifest_path, _package_manifest().to_dict())
    _write_json(available_artifacts_path, {"available_artifacts": {}})
    _write_json(canonical_store_path, _canonical_store().to_dict())

    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "rehydrate_training_packet.py"),
            "--package-manifest",
            str(package_manifest_path),
            "--available-artifacts",
            str(available_artifacts_path),
            "--canonical-store",
            str(canonical_store_path),
            "--output",
            str(output_path),
            "--allow-partial",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1, completed.stderr or completed.stdout
    report = _read_json(output_path)
    assert report["status"] == "unresolved_rehydration"
    assert report["materialization_status"] == "unresolved"
    assert report["checksum_audit_status"] == "partial"
    assert report["materialized_example_count"] == 0
    assert report["issue_summary"]["materialization_issue_count"] == 2
    assert report["issue_summary"]["missing_artifact_issue_count"] == 2
    assert report["checksum_audit"]["entries"][0]["packet_state"] == "unavailable"
    assert report["checksum_audit"]["entries"][0]["missing_artifact_pointers"] == [
        "artifacts/features/example-1.npy",
        "artifacts/structures/example-1.cif",
    ]
