from __future__ import annotations

from pathlib import Path

from core.procurement.source_release_manifest import SourceReleaseManifest
from execution.acquire.biogrid_snapshot import (
    BioGRIDSnapshot,
    BioGRIDSnapshotContract,
    BioGRIDSnapshotResult,
    acquire_biogrid_snapshot,
)


class _FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self._payload


def _fake_opener(expected_url: str, payload: bytes):
    def opener(request, timeout=None):
        assert request.full_url == expected_url
        assert request.headers["User-agent"] == "ProteoSphereV2-BioGRIDSnapshot/0.1"
        assert timeout == 30.0
        return _FakeResponse(payload)

    return opener


def test_acquire_biogrid_snapshot_uses_local_artifact_and_preserves_metadata(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "biogrid.tsv"
    source_file.write_text(
        "#BioGRID Interaction ID\tBioGRID ID A\tBioGRID ID B\n"
        "12345\tBGI:1\tBGI:2\n"
        "12346\tBGI:3\tBGI:4\n",
        encoding="utf-8",
    )

    manifest = SourceReleaseManifest(
        source_name="BioGRID",
        release_version="5.0.255",
        release_date="2026-03-01",
        retrieval_mode="download",
        local_artifact_refs=(str(source_file),),
        provenance=("BioGRID release archive",),
        reproducibility_metadata=("sha256:seed",),
    )

    result = acquire_biogrid_snapshot(manifest, acquired_on="2026-03-22T00:00:00+00:00")

    assert isinstance(result, BioGRIDSnapshotResult)
    assert result.status == "ok"
    assert result.reason == "biogrid_snapshot_acquired"
    assert result.succeeded is True
    assert isinstance(result.contract, BioGRIDSnapshotContract)
    assert isinstance(result.snapshot, BioGRIDSnapshot)
    assert result.contract.snapshot_id == manifest.manifest_id
    assert result.snapshot.content_source.startswith("local_artifact:")
    assert result.snapshot.record_count == 2
    assert result.snapshot.header == (
        "BioGRID Interaction ID",
        "BioGRID ID A",
        "BioGRID ID B",
    )
    assert result.snapshot.records[0] == ("12345", "BGI:1", "BGI:2")
    assert result.snapshot.content_sha256
    assert result.provenance["source"] == "BioGRID"
    assert result.provenance["content_source"].startswith("local_artifact:")
    assert result.provenance["record_count"] == 2
    assert result.provenance["parser_version"] == "biogrid-tabular-text-v1"

    payload = result.to_dict()
    assert payload["manifest"]["manifest_id"] == manifest.manifest_id
    assert payload["manifest"]["release_version"] == "5.0.255"
    assert payload["snapshot"]["record_count"] == 2


def test_acquire_biogrid_snapshot_blocks_without_artifact_or_source_locator() -> None:
    manifest = {
        "source_name": "BioGRID",
        "release_version": "5.0.255",
        "release_date": "2026-03-01",
        "retrieval_mode": "download",
        "provenance": ["release-note"],
    }

    result = acquire_biogrid_snapshot(manifest)

    assert result.status == "blocked"
    assert result.reason == "biogrid_manifest_needs_source_locator_or_local_artifact_refs"
    assert result.contract is not None
    assert result.snapshot is None
    assert result.provenance["availability"] == "blocked"
    assert result.provenance["blocker_reason"] == result.reason


def test_acquire_biogrid_snapshot_reports_empty_remote_payload_as_unavailable() -> None:
    manifest = SourceReleaseManifest(
        source_name="BioGRID",
        release_version="5.0.255",
        release_date="2026-03-01",
        retrieval_mode="download",
        source_locator="https://example.org/biogrid.tsv",
        provenance=("release-note",),
    )

    result = acquire_biogrid_snapshot(
        manifest,
        opener=_fake_opener("https://example.org/biogrid.tsv", b""),
        acquired_on="2026-03-22T00:00:00+00:00",
    )

    assert result.status == "unavailable"
    assert result.reason == "biogrid_empty_payload"
    assert result.contract is not None
    assert result.snapshot is None
    assert result.provenance["availability"] == "unavailable"
    assert result.provenance["content_source"] == "source_locator:https://example.org/biogrid.tsv"
    assert result.provenance["record_count"] == 0


def test_acquire_biogrid_snapshot_blocks_on_source_mismatch() -> None:
    manifest = SourceReleaseManifest(
        source_name="BindingDB",
        release_version="2026Q1",
        release_date="2026-03-01",
        retrieval_mode="download",
        source_locator="https://example.org/biogrid.tsv",
    )

    result = acquire_biogrid_snapshot(manifest)

    assert result.status == "blocked"
    assert result.reason == "biogrid_manifest_source_mismatch"
    assert result.contract is None
    assert result.snapshot is None
    assert result.provenance["availability"] == "blocked"
