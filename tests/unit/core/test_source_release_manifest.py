from __future__ import annotations

from datetime import date

import pytest

from core.procurement.source_release_manifest import (
    SourceReleaseManifest,
    validate_source_release_manifest_payload,
)


def test_source_release_manifest_normalizes_and_serializes() -> None:
    manifest = SourceReleaseManifest(
        source_name=" UniProt ",
        release_version=" 2026_03 ",
        release_date=date(2026, 3, 22),
        retrieval_mode=" Download ",
        source_locator=" https://example.org/uniprot ",
        local_artifact_refs=(" cache/uniprot.tsv ", "cache/uniprot.tsv", "cache/index.json"),
        provenance=(" upstream release ", "upstream release", "parser:v1"),
        reproducibility_metadata=(" sha256:abc123 ", "parser=v1", "sha256:abc123"),
    )

    assert manifest.source_name == "UniProt"
    assert manifest.release_version == "2026_03"
    assert manifest.release_date == "2026-03-22"
    assert manifest.retrieval_mode == "download"
    assert manifest.source_locator == "https://example.org/uniprot"
    assert manifest.local_artifact_refs == ("cache/uniprot.tsv", "cache/index.json")
    assert manifest.provenance == ("upstream release", "parser:v1")
    assert manifest.reproducibility_metadata == ("sha256:abc123", "parser=v1")
    assert manifest.manifest_id.startswith("UniProt:2026_03:download:")
    assert manifest.snapshot_fingerprint in manifest.manifest_id
    assert manifest.has_release_stamp

    payload = manifest.to_dict()
    assert payload["manifest_id"] == manifest.manifest_id
    assert payload["snapshot_fingerprint"] == manifest.snapshot_fingerprint
    assert payload["local_artifact_refs"] == ["cache/uniprot.tsv", "cache/index.json"]
    assert payload["provenance"] == ["upstream release", "parser:v1"]
    assert payload["reproducibility_metadata"] == ["sha256:abc123", "parser=v1"]


def test_validate_source_release_manifest_payload_accepts_common_aliases() -> None:
    manifest = validate_source_release_manifest_payload(
        {
            "source": "BindingDB",
            "version": "2026.02",
            "date": "2026-02-14",
            "mode": "scrape",
            "artifact_refs": "cache/raw.html",
            "evidence": ["scrape:run-17"],
            "reproducibility": ["parser=v2", "seed=13", "seed=13"],
        }
    )

    assert manifest.source_name == "BindingDB"
    assert manifest.release_version == "2026.02"
    assert manifest.release_date == "2026-02-14"
    assert manifest.retrieval_mode == "scrape"
    assert manifest.local_artifact_refs == ("cache/raw.html",)
    assert manifest.provenance == ("scrape:run-17",)
    assert manifest.reproducibility_metadata == ("parser=v2", "seed=13")


def test_source_release_manifest_distinguishes_distinct_snapshots_for_same_release() -> None:
    first = SourceReleaseManifest(
        source_name="UniProt",
        release_version="2026_03",
        retrieval_mode="download",
        source_locator="https://example.org/uniprot/release-a",
        local_artifact_refs=("cache/uniprot-a.tsv",),
        provenance=("snapshot:a",),
    )
    second = SourceReleaseManifest(
        source_name="UniProt",
        release_version="2026_03",
        retrieval_mode="download",
        source_locator="https://example.org/uniprot/release-b",
        local_artifact_refs=("cache/uniprot-b.tsv",),
        provenance=("snapshot:b",),
    )

    assert first.manifest_id != second.manifest_id
    assert first.snapshot_fingerprint != second.snapshot_fingerprint
    assert first.manifest_id.startswith("UniProt:2026_03:download:")
    assert second.manifest_id.startswith("UniProt:2026_03:download:")


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {
                "source_name": "",
                "release_version": "2026.03",
                "retrieval_mode": "download",
            },
            "source_name",
        ),
        (
            {
                "source_name": "UniProt",
                "release_version": "",
                "release_date": None,
                "retrieval_mode": "download",
            },
            "release_version or release_date",
        ),
        (
            {
                "source_name": "UniProt",
                "release_version": "2026.03",
                "retrieval_mode": "screen-scrape",
            },
            "unsupported retrieval_mode",
        ),
        (
            {
                "source_name": "UniProt",
                "release_version": "2026.03",
                "release_date": "2026-13-01",
                "retrieval_mode": "download",
            },
            "release_date must be ISO-8601 formatted",
        ),
        (
            {
                "source_name": "UniProt",
                "release_version": "2026.03",
                "retrieval_mode": "screen-scrape",
                "source_locator": "https://example.org/uniprot",
            },
            "unsupported retrieval_mode",
        ),
    ],
)
def test_source_release_manifest_rejects_invalid_input(kwargs, message) -> None:
    with pytest.raises(ValueError, match=message):
        SourceReleaseManifest(**kwargs)
