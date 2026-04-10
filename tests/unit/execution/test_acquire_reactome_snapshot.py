from __future__ import annotations

from pathlib import Path
from urllib.error import URLError

from execution.acquire.reactome_snapshot import (
    ReactomeSnapshotManifest,
    acquire_reactome_snapshot,
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


def _fake_opener(expected_payloads: dict[str, bytes]):
    def opener(request, timeout=None):
        assert request.headers["User-agent"] == "ProteoSphereV2-ReactomeSnapshot/0.1"
        assert timeout == 30.0
        payload = expected_payloads[request.full_url]
        return _FakeResponse(payload)

    return opener


def test_acquire_reactome_snapshot_downloads_pinned_pathway_and_reaction_assets():
    manifest = ReactomeSnapshotManifest.from_dict(
        {
            "source_name": "Reactome",
            "release_version": "v95",
            "release_date": "2025-12-09",
            "retrieval_mode": "download",
            "source_locator": "https://reactome.org/download-data",
            "assets": [
                {
                    "asset_name": "pathway_information",
                    "asset_url": "https://reactome.org/download/pathway_information.tsv",
                    "asset_kind": "pathway",
                    "stable_ids": ["R-HSA-199420", "R-HSA-199420.3"],
                    "species": "Homo sapiens",
                },
                {
                    "asset_name": "reaction_list",
                    "asset_url": "https://reactome.org/download/reaction_list.tsv",
                    "asset_kind": "reaction",
                    "stable_ids": ["R-HSA-123456"],
                    "species": "Homo sapiens",
                },
            ],
        }
    )

    result = acquire_reactome_snapshot(
        manifest,
        opener=_fake_opener(
            {
                "https://reactome.org/download/pathway_information.tsv": (
                    b"R-HSA-199420\tCell Cycle, Mitotic\n"
                ),
                "https://reactome.org/download/reaction_list.tsv": (
                    b"R-HSA-123456\tCDK activation reaction\n"
                ),
            }
        ),
        acquired_on="2026-03-22",
    )

    assert result.status == "ok"
    assert result.reason == "reactome_snapshot_acquired"
    assert result.succeeded is True
    assert result.manifest.manifest_id == manifest.manifest_id
    assert result.provenance.source == "Reactome"
    assert result.provenance.release_manifest_id == manifest.manifest_id
    assert result.provenance.release_version == "v95"
    assert result.provenance.release_date == "2025-12-09"
    assert result.provenance.retrieval_mode == "download"
    assert result.provenance.source_locator == "https://reactome.org/download-data"
    assert result.provenance.asset_count == 2
    assert result.provenance.stable_ids == (
        "R-HSA-199420",
        "R-HSA-199420.3",
        "R-HSA-123456",
    )
    assert result.assets[0].status == "ok"
    assert result.assets[0].asset_kind == "pathway"
    assert result.assets[0].content_source.startswith("source_locator:")
    assert result.assets[0].source_release_manifest_id == manifest.manifest_id
    assert result.assets[1].status == "ok"
    assert result.assets[1].text.startswith("R-HSA-123456")
    assert result.to_dict()["provenance"]["release_manifest_id"] == manifest.manifest_id


def test_acquire_reactome_snapshot_reports_blocked_manifest_without_network():
    manifest = {
        "source_name": "Reactome",
        "release_version": "v95",
        "release_date": "2025-12-09",
        "retrieval_mode": "download",
        "source_locator": "https://reactome.org/download-data",
        "availability": "blocked",
        "blocked_reason": "quarterly Zenodo snapshot has not been published yet",
    }

    result = acquire_reactome_snapshot(
        manifest,
        opener=_unexpected_opener,
        acquired_on="2026-03-22",
    )

    assert result.status == "blocked"
    assert result.reason == "quarterly Zenodo snapshot has not been published yet"
    assert result.assets == ()
    assert result.provenance.availability == "blocked"
    assert result.provenance.blocker_reason == (
        "quarterly Zenodo snapshot has not been published yet"
    )
    assert result.provenance.asset_count == 0


def test_acquire_reactome_snapshot_marks_empty_asset_as_unavailable():
    manifest = {
        "source_name": "Reactome",
        "release_version": "v95",
        "release_date": "2025-12-09",
        "retrieval_mode": "download",
        "source_locator": "https://reactome.org/download-data",
        "assets": [
            {
                "asset_name": "pathway_information",
                "asset_url": "https://reactome.org/download/pathway_information.tsv",
                "asset_kind": "pathway",
                "stable_ids": ["R-HSA-199420"],
            }
        ],
    }

    result = acquire_reactome_snapshot(
        manifest,
        opener=_fake_opener(
            {"https://reactome.org/download/pathway_information.tsv": b""},
        ),
        acquired_on="2026-03-22",
    )

    assert result.status == "unavailable"
    assert result.reason == "reactome_asset_empty"
    assert result.assets[0].status == "unavailable"
    assert result.assets[0].byte_length == 0
    assert result.provenance.availability == "unavailable"


def test_acquire_reactome_snapshot_uses_local_artifact_for_thin_cohort_accession(
    tmp_path: Path,
) -> None:
    local_asset = tmp_path / "reactome-pathway.tsv"
    local_asset.write_text(
        "R-HSA-199420\tCell Cycle, Mitotic\n",
        encoding="utf-8",
    )

    manifest = {
        "source_name": "Reactome",
        "release_version": "v95",
        "release_date": "2025-12-09",
        "retrieval_mode": "download",
        "source_locator": "https://reactome.org/download-data",
        "assets": [
            {
                "asset_name": "pathway_information",
                "asset_kind": "pathway",
                "stable_ids": ["R-HSA-199420"],
                "species": "Homo sapiens",
                "local_artifact_refs": [str(local_asset)],
            }
        ],
    }

    result = acquire_reactome_snapshot(
        manifest,
        opener=_unexpected_opener,
        acquired_on="2026-03-22",
    )

    assert result.status == "ok"
    assert result.reason == "reactome_snapshot_acquired"
    assert result.assets[0].status == "ok"
    assert result.assets[0].content_source.startswith("local_artifact:")
    assert result.assets[0].text.startswith("R-HSA-199420")
    assert result.provenance.content_sources == (result.assets[0].content_source,)
    assert result.provenance.asset_count == 1


def test_acquire_reactome_snapshot_blocks_non_utf8_local_artifact(tmp_path: Path) -> None:
    local_asset = tmp_path / "reactome-invalid.tsv"
    local_asset.write_bytes(b"\xff\xfe\x00bad-reactome")

    manifest = {
        "source_name": "Reactome",
        "release_version": "v95",
        "release_date": "2025-12-09",
        "retrieval_mode": "download",
        "source_locator": "https://reactome.org/download-data",
        "assets": [
            {
                "asset_name": "pathway_information",
                "asset_kind": "pathway",
                "stable_ids": ["R-HSA-199420"],
                "local_artifact_refs": [str(local_asset)],
            }
        ],
    }

    result = acquire_reactome_snapshot(
        manifest,
        opener=_unexpected_opener,
        acquired_on="2026-03-22",
    )

    assert result.status == "blocked"
    assert result.reason == "reactome_asset_local_decode_failed"
    assert result.assets[0].status == "blocked"
    assert result.assets[0].text == ""
    assert result.assets[0].content_source.startswith("local_artifact:")
    assert result.assets[0].error
    assert result.provenance.availability == "blocked"
    assert result.provenance.blocker_reason == "reactome_asset_local_decode_failed"


def test_acquire_reactome_snapshot_translates_request_failures_into_blockers():
    manifest = {
        "source_name": "Reactome",
        "release_version": "v95",
        "release_date": "2025-12-09",
        "retrieval_mode": "download",
        "source_locator": "https://reactome.org/download-data",
        "assets": [
            {
                "asset_name": "reaction_list",
                "asset_url": "https://reactome.org/download/reaction_list.tsv",
                "asset_kind": "reaction",
                "stable_ids": ["R-HSA-123456"],
            }
        ],
    }

    result = acquire_reactome_snapshot(
        manifest,
        opener=_failing_opener,
        acquired_on="2026-03-22",
    )

    assert result.status == "blocked"
    assert result.reason == "reactome_asset_download_failed"
    assert result.assets[0].status == "blocked"
    assert "network down" in result.assets[0].error
    assert result.provenance.availability == "blocked"


def _unexpected_opener(*args, **kwargs):
    raise AssertionError("network should not be called for blocked manifests")


def _failing_opener(request, timeout=None):
    raise URLError("network down")
