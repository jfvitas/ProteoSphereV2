from __future__ import annotations

from datetime import date, datetime

import pytest

from core.storage.embedding_cache import (
    EmbeddingCacheArtifactPointer,
    EmbeddingCacheCatalog,
    EmbeddingCacheCoverage,
    EmbeddingCacheEntry,
    EmbeddingCacheSourceRef,
    EmbeddingModelIdentity,
    EmbeddingRuntimeIdentity,
    validate_embedding_cache_payload,
)


def test_embedding_cache_entry_normalizes_and_serializes() -> None:
    entry = EmbeddingCacheEntry(
        cache_id=" seq-emb:P12345 ",
        cache_family=" sequence_embedding ",
        cache_version=" v2 ",
        model_identity=EmbeddingModelIdentity(
            model_name=" esm2 ",
            model_version=" 2024.01 ",
            model_metadata={"hidden_size": 1280},
        ),
        runtime_identity=EmbeddingRuntimeIdentity(
            runtime_name=" torch ",
            runtime_version=" 2.4.0 ",
            runtime_metadata={"device": "cuda"},
        ),
        source_refs=(
            EmbeddingCacheSourceRef(
                source_name=" UniProt ",
                source_record_id=" P12345 ",
                manifest_id=" UniProt:2026_03:download ",
                planning_id=" protein:P12345 ",
                provenance_id=" prov-1 ",
                source_locator=" https://example.org/uniprot/P12345 ",
                source_keys={"accession": " P12345 "},
            ),
            EmbeddingCacheSourceRef(
                source_name=" UniProt ",
                source_record_id=" P12345 ",
                manifest_id="UniProt:2026_03:download",
                planning_id="protein:P12345",
                provenance_id="prov-1",
                source_locator="https://example.org/uniprot/P12345",
                source_keys={"accession": "P12345"},
            ),
        ),
        provenance_refs=(" prov-1 ", "prov-1", "prov-2"),
        canonical_ids=(" canon:P12345 ", "canon:P12345", "protein:P12345"),
        join_status=" Joined ",
        join_confidence=0.9,
        coverage=(
            EmbeddingCacheCoverage(
                coverage_kind=" source ",
                label=" UniProt release ",
                coverage_state=" present ",
                source_names=(" UniProt ", "UniProt"),
                notes=(" release-pinned ", "release-pinned"),
                confidence=1.0,
            ),
            EmbeddingCacheCoverage(
                coverage_kind=" modality ",
                label=" sequence_embedding ",
                coverage_state=" partial ",
                source_names=("sequence",),
                notes=(" derived ",),
                confidence=0.5,
            ),
        ),
        artifact_pointers=(
            EmbeddingCacheArtifactPointer(
                artifact_kind=" embedding ",
                pointer=" cache/embeddings/P12345.npy ",
                selector=" protein:P12345 ",
                source_name=" UniProt ",
                source_record_id=" P12345 ",
                planning_id=" protein:P12345 ",
                notes=(" derived-from:uniprot ", "derived-from:uniprot"),
            ),
        ),
        integrity_fields=(" sha256:abc123 ", "sha256:abc123", "size=2048"),
        metadata={
            "retrieved_at": datetime(2026, 3, 22, 14, 15, 30),
            "release_date": date(2026, 3, 22),
        },
    )

    assert entry.cache_id == "seq-emb:P12345"
    assert entry.cache_family == "sequence_embedding"
    assert entry.cache_version == "v2"
    assert entry.model_identity.model_name == "esm2"
    assert entry.model_identity.model_version == "2024.01"
    assert entry.runtime_identity.runtime_name == "torch"
    assert entry.runtime_identity.runtime_version == "2.4.0"
    assert entry.source_names == ("UniProt",)
    assert entry.source_manifest_ids == ("UniProt:2026_03:download",)
    assert entry.planning_index_refs == ("protein:P12345",)
    assert entry.provenance_refs == ("prov-1", "prov-2")
    assert entry.canonical_ids == ("canon:P12345", "protein:P12345")
    assert entry.join_status == "joined"
    assert entry.join_confidence == 0.9
    assert entry.integrity_fields == ("sha256:abc123", "size=2048")
    assert entry.metadata["retrieved_at"] == "2026-03-22T14:15:30"
    assert entry.metadata["release_date"] == "2026-03-22"
    assert entry.is_pinned_source_backed

    payload = entry.to_dict()
    assert payload["cache_id"] == "seq-emb:P12345"
    assert payload["model_identity"]["model_name"] == "esm2"
    assert payload["runtime_identity"]["runtime_version"] == "2.4.0"
    assert payload["source_names"] == ["UniProt"]
    assert payload["source_manifest_ids"] == ["UniProt:2026_03:download"]
    assert payload["planning_index_refs"] == ["protein:P12345"]
    assert payload["artifact_pointers"][0]["planning_id"] == "protein:P12345"


def test_embedding_cache_entry_preserves_provenance_distinct_source_refs() -> None:
    entry = EmbeddingCacheEntry(
        cache_id="seq-emb:P12345",
        cache_family="sequence_embedding",
        cache_version="v2",
        model_identity=EmbeddingModelIdentity(model_name="esm2"),
        runtime_identity=EmbeddingRuntimeIdentity(runtime_name="torch"),
        source_refs=(
            EmbeddingCacheSourceRef(
                source_name="UniProt",
                source_record_id="P12345",
                manifest_id="UniProt:2026_03:download",
                planning_id="protein:P12345",
                provenance_id="prov-1",
                source_locator="https://example.org/uniprot/P12345",
                source_keys={"accession": "P12345"},
            ),
            EmbeddingCacheSourceRef(
                source_name="UniProt",
                source_record_id="P12345",
                manifest_id="UniProt:2026_03:download",
                planning_id="protein:P12345",
                provenance_id="prov-1",
                source_locator="https://mirror.example.org/uniprot/P12345",
                source_keys={"accession": "P12345", "mirror": "true"},
            ),
        ),
    )

    assert len(entry.source_refs) == 2
    assert entry.source_refs[0].source_locator == "https://example.org/uniprot/P12345"
    assert entry.source_refs[1].source_locator == "https://mirror.example.org/uniprot/P12345"
    assert entry.source_refs[0].source_keys != entry.source_refs[1].source_keys
    assert entry.to_dict()["source_refs"][0]["source_locator"] == "https://example.org/uniprot/P12345"
    assert entry.to_dict()["source_refs"][1]["source_locator"] == "https://mirror.example.org/uniprot/P12345"


def test_validate_embedding_cache_payload_accepts_aliases_and_round_trips() -> None:
    catalog = validate_embedding_cache_payload(
        {
            "schema_version": 1,
            "entries": [
                {
                    "id": "ligand-emb:brd4",
                    "family": "ligand_embedding",
                    "version": "2026.03",
                    "model_identity": {
                        "name": "e5-small",
                        "version": "2024-11",
                        "metadata": {"layers": 12},
                    },
                    "runtime_identity": {
                        "name": "jax",
                        "version": "0.4.26",
                        "metadata": {"platform": "cpu"},
                    },
                    "sources": [
                        {
                            "source": "BindingDB",
                            "record_id": "Reactant_set_id:42",
                            "source_manifest_id": "bindingdb:2026.03:scrape",
                            "plan_id": "plan:ligand:brd4",
                            "provenance": "prov-42",
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
                            "name": "ligand_embedding",
                            "state": "present",
                            "sources": ["ligand"],
                        },
                    ],
                    "materialization_pointers": [
                        {
                            "kind": "vector",
                            "path": "cache/embeddings/ligand/brd4.vec",
                            "selection": "target:BRD4",
                            "source": "BindingDB",
                            "record_id": "Reactant_set_id:42",
                            "planning_id": "plan:ligand:brd4",
                            "notes": ["precomputed"],
                        }
                    ],
                    "checksums": ["sha256:def456"],
                    "annotations": {"source_release": "2026.03"},
                }
            ],
        }
    )

    record = catalog.get("ligand-emb:brd4")
    assert record is not None
    assert record.cache_version == "2026.03"
    assert record.join_status == "joined"
    assert record.canonical_ids == ("canon:brd4",)
    assert record.source_manifest_ids == ("bindingdb:2026.03:scrape",)
    assert record.planning_index_refs == ("plan:ligand:brd4",)
    assert record.coverage[0].coverage_state == "present"
    assert record.artifact_pointers[0].artifact_kind == "vector"
    assert record.provenance_refs == ("prov-42",)
    assert record.metadata["source_release"] == "2026.03"

    rebuilt = EmbeddingCacheCatalog.from_dict(catalog.to_dict())
    assert rebuilt.to_dict()["record_count"] == 1
    assert rebuilt.get("ligand-emb:brd4") == record


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {
                "cache_id": "",
                "cache_family": "sequence_embedding",
                "cache_version": "v1",
                "model_identity": EmbeddingModelIdentity(model_name="esm2"),
                "runtime_identity": EmbeddingRuntimeIdentity(runtime_name="torch"),
                "source_refs": (
                    EmbeddingCacheSourceRef(
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
                "cache_family": "sequence_embedding",
                "cache_version": "",
                "model_identity": EmbeddingModelIdentity(model_name="esm2"),
                "runtime_identity": EmbeddingRuntimeIdentity(runtime_name="torch"),
                "source_refs": (
                    EmbeddingCacheSourceRef(
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
                "cache_family": "sequence_embedding",
                "cache_version": "v1",
                "model_identity": EmbeddingModelIdentity(model_name="esm2"),
                "runtime_identity": EmbeddingRuntimeIdentity(runtime_name="torch"),
                "source_refs": (),
            },
            "source_refs must not be empty",
        ),
        (
            {
                "cache_id": "seq-emb",
                "cache_family": "sequence_embedding",
                "cache_version": "v1",
                "model_identity": EmbeddingModelIdentity(model_name="esm2"),
                "runtime_identity": EmbeddingRuntimeIdentity(runtime_name="torch"),
                "source_refs": (
                    EmbeddingCacheSourceRef(
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
def test_embedding_cache_entry_rejects_invalid_input(kwargs, message) -> None:
    with pytest.raises((ValueError, TypeError), match=message):
        EmbeddingCacheEntry(**kwargs)


def test_embedding_cache_catalog_rejects_duplicate_cache_ids() -> None:
    source_ref = EmbeddingCacheSourceRef(
        source_name="UniProt",
        source_record_id="P69905",
        manifest_id="uniprot:2026_03:download",
    )
    with pytest.raises(ValueError, match="duplicate cache_id"):
        EmbeddingCacheCatalog(
            records=(
                EmbeddingCacheEntry(
                    cache_id="cache:one",
                    cache_family="sequence_embedding",
                    cache_version="v1",
                    model_identity=EmbeddingModelIdentity(model_name="esm2"),
                    runtime_identity=EmbeddingRuntimeIdentity(runtime_name="torch"),
                    source_refs=(source_ref,),
                ),
                EmbeddingCacheEntry(
                    cache_id="cache:one",
                    cache_family="sequence_embedding",
                    cache_version="v1",
                    model_identity=EmbeddingModelIdentity(model_name="esm2"),
                    runtime_identity=EmbeddingRuntimeIdentity(runtime_name="torch"),
                    source_refs=(source_ref,),
                ),
            )
        )
