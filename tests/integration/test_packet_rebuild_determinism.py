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


def _clean_available_artifacts() -> dict[str, object]:
    return {
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
    }


def _drifted_available_artifacts() -> dict[str, object]:
    return {
        "available_artifacts": {
            "artifacts/features/example-1.npy": {
                "materialized_ref": "materialized/features/example-1.npy",
                "checksum": "sha256:feature-1-drifted",
            }
        }
    }


def _run_cli(
    *,
    package_manifest_path: Path,
    available_artifacts_path: Path,
    canonical_store_path: Path,
    output_path: Path,
    reference_audit_path: Path | None = None,
    allow_partial: bool = False,
    materialization_run_id: str | None = None,
    materialized_at: str | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
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
    ]
    if reference_audit_path is not None:
        command.extend(["--reference-audit", str(reference_audit_path)])
    if allow_partial:
        command.append("--allow-partial")
    if materialization_run_id is not None:
        command.extend(["--materialization-run-id", materialization_run_id])
    if materialized_at is not None:
        command.extend(["--materialized-at", materialized_at])
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )


def test_packet_rebuild_cli_is_deterministic_for_same_pinned_inputs(tmp_path: Path) -> None:
    package_manifest_path = tmp_path / "package_manifest.json"
    canonical_store_path = tmp_path / "canonical_store.json"
    available_artifacts_path = tmp_path / "available_artifacts.json"
    first_output_path = tmp_path / "rehydration_report_1.json"
    second_output_path = tmp_path / "rehydration_report_2.json"
    reference_audit_path = tmp_path / "reference_audit.json"

    _write_json(package_manifest_path, _package_manifest().to_dict())
    _write_json(canonical_store_path, _canonical_store().to_dict())
    _write_json(available_artifacts_path, _clean_available_artifacts())

    first_run = _run_cli(
        package_manifest_path=package_manifest_path,
        available_artifacts_path=available_artifacts_path,
        canonical_store_path=canonical_store_path,
        output_path=first_output_path,
        materialization_run_id="rehydrate-run-001",
        materialized_at="2026-03-22T12:00:00Z",
    )
    assert first_run.returncode == 0, first_run.stderr or first_run.stdout
    first_report = _read_json(first_output_path)
    _write_json(reference_audit_path, first_report["checksum_audit"])

    second_run = _run_cli(
        package_manifest_path=package_manifest_path,
        available_artifacts_path=available_artifacts_path,
        canonical_store_path=canonical_store_path,
        output_path=second_output_path,
        reference_audit_path=reference_audit_path,
        materialization_run_id="rehydrate-run-002",
        materialized_at="2026-03-22T13:00:00Z",
    )
    assert second_run.returncode == 0, second_run.stderr or second_run.stdout
    second_report = _read_json(second_output_path)

    assert first_report["status"] == "materialized"
    assert second_report["status"] == "materialized"
    assert second_report["checksum_audit_status"] == "consistent"
    assert first_report["materialization"]["materialization_run_id"] == "rehydrate-run-001"
    assert second_report["materialization"]["materialization_run_id"] == "rehydrate-run-002"
    assert (
        first_report["checksum_audit"]["entries"][0]["asset_identity_checksum"]
        == second_report["checksum_audit"]["entries"][0]["asset_identity_checksum"]
    )
    assert second_report["checksum_audit"]["entries"][0]["drift_state"] == "same"
    assert second_report["checksum_audit"]["entries"][0]["packet_state"] == "consistent"


def test_packet_rebuild_cli_surfaces_drift_cases_explicitly(tmp_path: Path) -> None:
    package_manifest_path = tmp_path / "package_manifest.json"
    canonical_store_path = tmp_path / "canonical_store.json"
    clean_available_artifacts_path = tmp_path / "available_artifacts_clean.json"
    drifted_available_artifacts_path = tmp_path / "available_artifacts_drifted.json"
    reference_output_path = tmp_path / "rehydration_report_reference.json"
    drifted_output_path = tmp_path / "rehydration_report_drifted.json"
    reference_audit_path = tmp_path / "reference_audit.json"

    _write_json(package_manifest_path, _package_manifest().to_dict())
    _write_json(canonical_store_path, _canonical_store().to_dict())
    _write_json(clean_available_artifacts_path, _clean_available_artifacts())
    _write_json(drifted_available_artifacts_path, _drifted_available_artifacts())

    reference_run = _run_cli(
        package_manifest_path=package_manifest_path,
        available_artifacts_path=clean_available_artifacts_path,
        canonical_store_path=canonical_store_path,
        output_path=reference_output_path,
    )
    assert reference_run.returncode == 0, reference_run.stderr or reference_run.stdout
    reference_report = _read_json(reference_output_path)
    _write_json(reference_audit_path, reference_report["checksum_audit"])

    drifted_run = _run_cli(
        package_manifest_path=package_manifest_path,
        available_artifacts_path=drifted_available_artifacts_path,
        canonical_store_path=canonical_store_path,
        output_path=drifted_output_path,
        reference_audit_path=reference_audit_path,
        allow_partial=True,
    )
    assert drifted_run.returncode == 0, drifted_run.stderr or drifted_run.stdout
    drifted_report = _read_json(drifted_output_path)

    assert drifted_report["status"] == "partial_rehydration"
    assert drifted_report["materialization_status"] == "partial"
    assert drifted_report["checksum_audit_status"] == "partial"
    assert drifted_report["issue_summary"]["missing_artifact_issue_count"] == 1
    assert drifted_report["issue_summary"]["drifted_count"] == 1
    assert drifted_report["checksum_audit"]["entries"][0]["packet_state"] == "partial"
    assert drifted_report["checksum_audit"]["entries"][0]["drift_state"] == "drifted"
    assert drifted_report["checksum_audit"]["entries"][0]["missing_artifact_pointers"] == [
        "artifacts/structures/example-1.cif"
    ]
