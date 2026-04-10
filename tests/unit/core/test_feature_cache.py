from __future__ import annotations

from datetime import date, datetime

import pytest

from core.storage.feature_cache import (
    FeatureCacheArtifactPointer,
    FeatureCacheCatalog,
    FeatureCacheCoverage,
    FeatureCacheEntry,
    FeatureCacheSourceRef,
    validate_feature_cache_payload,
)


def test_feature_cache_entry_normalizes_and_serializes() -> None:
    entry = FeatureCacheEntry(
        cache_id=" seq-emb:uniprot:P69905 ",
        feature_family=" sequence_embedding ",
        cache_version=" v2 ",
        source_refs=(
            FeatureCacheSourceRef(
                source_name=" UniProt ",
                source_record_id=" P69905 ",
                manifest_id=" uniprot:2026_03:download ",
                planning_id=" plan:prot:P69905 ",
                source_locator=" https://example.org/uniprot/P69905 ",
                source_keys={"accession": " P69905 "},
            ),
            FeatureCacheSourceRef(
                source_name=" UniProt ",
                source_record_id=" P69905 ",
                manifest_id="uniprot:2026_03:download",
                planning_id="plan:prot:P69905",
                source_locator="https://example.org/uniprot/P69905",
                source_keys={"accession": "P69905"},
            ),
        ),
        canonical_ids=(" canon:P69905 ", "canon:P69905", "uniprot:P69905"),
        join_status=" Joined ",
        join_confidence=0.85,
        coverage=(
            FeatureCacheCoverage(
                coverage_kind=" source ",
                label=" UniProt release ",
                coverage_state=" present ",
                source_names=(" UniProt ", "UniProt"),
                notes=(" release-pinned ", "release-pinned"),
                confidence=1.0,
            ),
            FeatureCacheCoverage(
                coverage_kind=" modality ",
                label=" embeddings ",
                coverage_state=" partial ",
                source_names=("sequence",),
                notes=(" derived ",),
                confidence=0.5,
            ),
        ),
        artifact_pointers=(
            FeatureCacheArtifactPointer(
                artifact_kind=" embedding ",
                pointer=" cache/features/P69905.vec ",
                selector=" sequence_embedding ",
                source_name=" UniProt ",
                source_record_id=" P69905 ",
                planning_id=" plan:prot:P69905 ",
                notes=(" derived-from:uniprot ", "derived-from:uniprot"),
            ),
        ),
        integrity_fields=(" sha256:abc123 ", "sha256:abc123", "size=2048"),
        metadata={
            "retrieved_at": datetime(2026, 3, 22, 14, 15, 30),
            "release_date": date(2026, 3, 22).isoformat(),
        },
    )

    assert entry.cache_id == "seq-emb:uniprot:P69905"
    assert entry.feature_family == "sequence_embedding"
    assert entry.cache_version == "v2"
    assert entry.source_names == ("UniProt",)
    assert entry.source_manifest_ids == ("uniprot:2026_03:download",)
    assert entry.planning_ids == ("plan:prot:P69905",)
    assert entry.canonical_ids == ("canon:P69905", "uniprot:P69905")
    assert entry.join_status == "joined"
    assert entry.join_confidence == 0.85
    assert entry.integrity_fields == ("sha256:abc123", "size=2048")
    assert entry.metadata["retrieved_at"] == "2026-03-22T14:15:30"
    assert entry.metadata["release_date"] == "2026-03-22"

    payload = entry.to_dict()
    assert payload["cache_id"] == "seq-emb:uniprot:P69905"
    assert payload["source_names"] == ["UniProt"]
    assert payload["source_manifest_ids"] == ["uniprot:2026_03:download"]
    assert payload["planning_ids"] == ["plan:prot:P69905"]
    assert payload["canonical_ids"] == ["canon:P69905", "uniprot:P69905"]
    assert payload["artifact_pointers"][0]["planning_id"] == "plan:prot:P69905"


def test_feature_cache_entry_preserves_provenance_distinct_source_refs() -> None:
    entry = FeatureCacheEntry(
        cache_id="seq-emb:uniprot:P69905",
        feature_family="sequence_embedding",
        cache_version="v2",
        source_refs=(
            FeatureCacheSourceRef(
                source_name="UniProt",
                source_record_id="P69905",
                manifest_id="uniprot:2026_03:download",
                planning_id="plan:prot:P69905",
                source_locator="https://example.org/uniprot/P69905",
                source_keys={"accession": "P69905"},
            ),
            FeatureCacheSourceRef(
                source_name="UniProt",
                source_record_id="P69905",
                manifest_id="uniprot:2026_03:download",
                planning_id="plan:prot:P69905",
                source_locator="https://mirror.example.org/uniprot/P69905",
                source_keys={"accession": "P69905", "mirror": "true"},
            ),
        ),
    )

    assert len(entry.source_refs) == 2
    assert entry.source_refs[0].source_locator == "https://example.org/uniprot/P69905"
    assert entry.source_refs[1].source_locator == "https://mirror.example.org/uniprot/P69905"
    assert entry.source_refs[0].source_keys != entry.source_refs[1].source_keys
    assert entry.to_dict()["source_refs"][0]["source_locator"] == "https://example.org/uniprot/P69905"
    assert entry.to_dict()["source_refs"][1]["source_locator"] == "https://mirror.example.org/uniprot/P69905"


def test_validate_feature_cache_payload_accepts_aliases_and_round_trips() -> None:
    catalog = validate_feature_cache_payload(
        {
            "schema_version": 1,
            "entries": [
                {
                    "id": "ligand-summary:bindingdb:brd4",
                    "family": "ligand_summary",
                    "version": "2026.03",
                    "sources": [
                        {
                            "source": "BindingDB",
                            "record_id": "Reactant_set_id:42",
                            "source_manifest_id": "bindingdb:2026.03:scrape",
                            "plan_id": "plan:ligand:brd4",
                            "url": "https://example.org/bindingdb/42",
                        }
                    ],
                    "canonical_id": "canon:brd4",
                    "status": "linked",
                    "confidence": 0.6,
                    "coverage_slices": [
                        {
                            "axis": "source",
                            "name": "BindingDB release",
                            "state": "indexed",
                            "sources": ["BindingDB"],
                        },
                        {
                            "axis": "modality",
                            "name": "ligand_summary",
                            "state": "present",
                            "sources": ["ligand"],
                        },
                    ],
                    "materialization_pointers": [
                        {
                            "kind": "table",
                            "path": "cache/features/ligand-summary/brd4.parquet",
                            "selection": "target:BRD4",
                            "source": "BindingDB",
                            "record_id": "Reactant_set_id:42",
                            "notes": ["precomputed"],
                        }
                    ],
                    "checksums": ["sha256:def456"],
                    "annotations": {"source_release": "2026.03"},
                }
            ],
        }
    )

    record = catalog.get("ligand-summary:bindingdb:brd4")
    assert record is not None
    assert record.cache_version == "2026.03"
    assert record.join_status == "joined"
    assert record.canonical_ids == ("canon:brd4",)
    assert record.source_manifest_ids == ("bindingdb:2026.03:scrape",)
    assert record.planning_ids == ("plan:ligand:brd4",)
    assert record.coverage[0].coverage_state == "present"
    assert record.artifact_pointers[0].artifact_kind == "table"
    assert record.metadata["source_release"] == "2026.03"

    rebuilt = FeatureCacheCatalog.from_dict(catalog.to_dict())
    assert rebuilt.to_dict()["record_count"] == 1
    assert rebuilt.get("ligand-summary:bindingdb:brd4") == record


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {
                "cache_id": "",
                "feature_family": "sequence_embedding",
                "cache_version": "v1",
                "source_refs": (
                    FeatureCacheSourceRef(
                        source_name="UniProt",
                        source_record_id="P69905",
                        manifest_id="uniprot:2026_03:download",
                    ),
                ),
            },
            "cache_id",
        ),
        (
            {
                "cache_id": "seq-emb",
                "feature_family": "sequence_embedding",
                "cache_version": "",
                "source_refs": (
                    FeatureCacheSourceRef(
                        source_name="UniProt",
                        source_record_id="P69905",
                        manifest_id="uniprot:2026_03:download",
                    ),
                ),
            },
            "cache_version",
        ),
        (
            {
                "cache_id": "seq-emb",
                "feature_family": "sequence_embedding",
                "cache_version": "v1",
                "source_refs": (),
            },
            "source_refs must not be empty",
        ),
        (
            {
                "cache_id": "seq-emb",
                "feature_family": "sequence_embedding",
                "cache_version": "v1",
                "source_refs": (
                    FeatureCacheSourceRef(
                        source_name="UniProt",
                        source_record_id="P69905",
                        manifest_id="uniprot:2026_03:download",
                    ),
                ),
                "join_status": "bogus",
            },
            "unsupported join_status",
        ),
    ],
)
def test_feature_cache_entry_rejects_invalid_input(kwargs, message) -> None:
    with pytest.raises((ValueError, TypeError), match=message):
        FeatureCacheEntry(**kwargs)


def test_feature_cache_catalog_rejects_duplicate_cache_ids() -> None:
    source_ref = FeatureCacheSourceRef(
        source_name="UniProt",
        source_record_id="P69905",
        manifest_id="uniprot:2026_03:download",
    )
    with pytest.raises(ValueError, match="duplicate cache_id"):
        FeatureCacheCatalog(
            records=(
                FeatureCacheEntry(
                    cache_id="cache:one",
                    feature_family="sequence_embedding",
                    cache_version="v1",
                    source_refs=(source_ref,),
                ),
                FeatureCacheEntry(
                    cache_id="cache:one",
                    feature_family="sequence_embedding",
                    cache_version="v1",
                    source_refs=(source_ref,),
                ),
            )
        )
