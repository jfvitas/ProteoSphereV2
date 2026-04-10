from __future__ import annotations

import json

from core.storage.canonical_store import CanonicalStore, CanonicalStoreRecord
from core.storage.package_manifest import (
    PackageManifest,
    PackageManifestArtifactPointer,
    PackageManifestExample,
    PackageManifestRawManifest,
)
from execution.materialization.packet_checksum_audit import (
    PacketChecksumAuditResult,
    audit_packet_checksum_payload,
    audit_packet_checksums,
)
from execution.materialization.selective_materializer import materialize_selected_examples


def _package_manifest(*, canonical_id: str = "protein:P12345") -> PackageManifest:
    return PackageManifest(
        package_id="package-001",
        selected_examples=(
            PackageManifestExample(
                example_id="example-1",
                planning_index_ref="planning/index/example-1",
                source_record_refs=("source-a:1",),
                canonical_ids=(canonical_id,),
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
            PackageManifestExample(
                example_id="example-2",
                planning_index_ref="planning/index/example-2",
                source_record_refs=("source-b:1",),
                canonical_ids=("protein:P67890",),
                artifact_pointers=(
                    PackageManifestArtifactPointer(
                        artifact_kind="feature",
                        pointer="artifacts/features/example-2.npy",
                        selector="feature:0",
                        source_name="source-b",
                        source_record_id="source-b:1",
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
                source_locator="https://example.test/source-a",
                planning_index_ref="planning/index/example-1",
            ),
        ),
        planning_index_refs=("planning/index/example-1", "planning/index/example-2"),
        provenance=("prov:package",),
        notes=("package notes",),
    )


def _canonical_store() -> CanonicalStore:
    return CanonicalStore(
        records=(
            CanonicalStoreRecord(
                canonical_id="protein:P12345",
                entity_kind="protein",
                canonical_payload={"accession": "P12345"},
                provenance_refs=("prov:protein",),
            ),
            CanonicalStoreRecord(
                canonical_id="protein:P67890",
                entity_kind="protein",
                canonical_payload={"accession": "P67890"},
                provenance_refs=("prov:protein-2",),
            ),
        ),
    )


def _clean_result() -> PacketChecksumAuditResult:
    selective_result = materialize_selected_examples(
        _package_manifest(),
        available_artifacts={
            "artifacts/features/example-1.npy": {
                "materialized_ref": "materialized/features/example-1.npy",
                "checksum": "sha256:feature-1",
                "provenance_refs": ("prov:feature-1",),
            },
            "artifacts/structures/example-1.cif": "materialized/structures/example-1.cif",
            "artifacts/features/example-2.npy": "materialized/features/example-2.npy",
        },
        canonical_store=_canonical_store(),
        materialization_run_id="run-001",
        materialized_at="2026-03-22T12:00:00Z",
    )
    return audit_packet_checksums(_package_manifest(), selective_result)


def test_audit_packet_checksums_records_deterministic_identity_and_round_trips() -> None:
    audit = _clean_result()

    assert audit.status == "consistent"
    assert audit.entry_count == 2
    assert audit.summary["consistent_count"] == 2
    assert audit.summary["partial_count"] == 0
    assert audit.summary["drifted_count"] == 0

    by_example = {entry.example_id: entry for entry in audit.entries}
    assert by_example["example-1"].packet_state == "consistent"
    assert by_example["example-1"].drift_state == "unavailable"
    assert by_example["example-1"].expected_artifact_count == 2
    assert by_example["example-1"].materialized_artifact_count == 2
    assert by_example["example-1"].missing_artifact_pointers == ()
    assert by_example["example-2"].packet_state == "consistent"
    assert by_example["example-2"].materialized_artifact_pointers == (
        "artifacts/features/example-2.npy",
    )

    payload = json.loads(json.dumps(audit.to_dict()))
    round_tripped = audit_packet_checksum_payload(payload)
    assert round_tripped.package_manifest_id == audit.package_manifest_id
    assert (
        round_tripped.entries[0].asset_identity_checksum
        == audit.entries[0].asset_identity_checksum
    )


def test_audit_packet_checksums_reports_partial_packets_and_rebuild_drift() -> None:
    reference_audit = _clean_result()
    selective_result = materialize_selected_examples(
        _package_manifest(),
        available_artifacts={
            "artifacts/features/example-1.npy": {
                "materialized_ref": "materialized/features/example-1.npy",
                "checksum": "sha256:feature-1-drifted",
                "provenance_refs": ("prov:feature-1",),
            },
            "artifacts/features/example-2.npy": "materialized/features/example-2.npy",
        },
        canonical_store=_canonical_store(),
    )

    audit = audit_packet_checksums(
        _package_manifest(),
        selective_result,
        reference_audit=reference_audit,
    )

    assert audit.status == "partial"
    assert audit.summary["partial_count"] == 1
    assert audit.summary["drifted_count"] == 1
    assert audit.summary["missing_artifact_count"] == 1

    by_example = {entry.example_id: entry for entry in audit.entries}
    example_1 = by_example["example-1"]
    assert example_1.packet_state == "partial"
    assert example_1.drift_state == "drifted"
    assert example_1.missing_artifact_pointers == ("artifacts/structures/example-1.cif",)
    assert any(issue["kind"] == "partial_packet" for issue in example_1.issues)
    assert any(issue["kind"] == "checksum_drift" for issue in example_1.issues)

    example_2 = by_example["example-2"]
    assert example_2.packet_state == "consistent"
    assert example_2.drift_state == "same"
    assert example_2.missing_artifact_pointers == ()
