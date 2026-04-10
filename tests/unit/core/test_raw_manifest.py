from __future__ import annotations

from datetime import date, datetime

import pytest

from core.storage.raw_manifest import (
    RawCacheManifest,
    validate_raw_cache_manifest_payload,
)


def test_raw_cache_manifest_normalizes_and_serializes() -> None:
    manifest = RawCacheManifest(
        source_name=" UniProt ",
        release_version=" 2026_03 ",
        release_date=date(2026, 3, 22),
        retrieval_mode=" Download ",
        source_locator=" https://example.org/uniprot ",
        retrieved_at=datetime(2026, 3, 22, 14, 15, 30),
        local_artifact_refs=(
            " cache/raw/uniprot.tsv ",
            "cache/raw/uniprot.tsv",
            "cache/index.json",
        ),
        artifact_refs=(
            " raw://uniprot/export ",
            "raw://uniprot/export",
            "raw://uniprot/header",
        ),
        retrieval_provenance=(" upstream release ", "upstream release", "job:raw-cache"),
        integrity_fields=(" sha256:abc123 ", "sha256:abc123", "size=128KB"),
        rebuild_metadata=(" parser=v1 ", "parser=v1", "scope=allowlist"),
    )

    assert manifest.source_name == "UniProt"
    assert manifest.release_version == "2026_03"
    assert manifest.release_date == "2026-03-22"
    assert manifest.retrieval_mode == "download"
    assert manifest.source_locator == "https://example.org/uniprot"
    assert manifest.retrieved_at == "2026-03-22T14:15:30"
    assert manifest.local_artifact_refs == ("cache/raw/uniprot.tsv", "cache/index.json")
    assert manifest.artifact_refs == ("raw://uniprot/export", "raw://uniprot/header")
    assert manifest.retrieval_provenance == ("upstream release", "job:raw-cache")
    assert manifest.integrity_fields == ("sha256:abc123", "size=128KB")
    assert manifest.rebuild_metadata == ("parser=v1", "scope=allowlist")
    assert manifest.manifest_id == "UniProt:2026_03:download:raw"
    assert manifest.has_release_stamp

    payload = manifest.to_dict()
    assert payload["manifest_id"] == "UniProt:2026_03:download:raw"
    assert payload["local_artifact_refs"] == ["cache/raw/uniprot.tsv", "cache/index.json"]
    assert payload["artifact_refs"] == ["raw://uniprot/export", "raw://uniprot/header"]
    assert payload["retrieval_provenance"] == ["upstream release", "job:raw-cache"]
    assert payload["integrity_fields"] == ["sha256:abc123", "size=128KB"]
    assert payload["rebuild_metadata"] == ["parser=v1", "scope=allowlist"]


def test_validate_raw_cache_manifest_payload_accepts_common_aliases() -> None:
    manifest = validate_raw_cache_manifest_payload(
        {
            "source": "BindingDB",
            "version": "2026.02",
            "date": "2026-02-14",
            "mode": "scrape",
            "url": "https://example.org/bindingdb",
            "retrieved": "2026-02-14T09:30:00",
            "local_paths": ["cache/raw/bindingdb.tsv"],
            "artifacts": ("raw://bindingdb/export",),
            "evidence": ["archive:v2026.02"],
            "checksums": ["sha256:def456"],
            "rebuild": ["parser=v2", "query=target:BRD4"],
        }
    )

    assert manifest.source_name == "BindingDB"
    assert manifest.release_version == "2026.02"
    assert manifest.release_date == "2026-02-14"
    assert manifest.retrieval_mode == "scrape"
    assert manifest.source_locator == "https://example.org/bindingdb"
    assert manifest.retrieved_at == "2026-02-14T09:30:00"
    assert manifest.local_artifact_refs == ("cache/raw/bindingdb.tsv",)
    assert manifest.artifact_refs == ("raw://bindingdb/export",)
    assert manifest.retrieval_provenance == ("archive:v2026.02",)
    assert manifest.integrity_fields == ("sha256:def456",)
    assert manifest.rebuild_metadata == ("parser=v2", "query=target:BRD4")


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
    ],
)
def test_raw_cache_manifest_rejects_invalid_input(kwargs, message) -> None:
    with pytest.raises(ValueError, match=message):
        RawCacheManifest(**kwargs)
