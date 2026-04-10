from __future__ import annotations

import pytest

from core.storage.canonical_store import (
    CanonicalStore,
    CanonicalStoreArtifactPointer,
    CanonicalStoreRecord,
    CanonicalStoreSourceRef,
    validate_canonical_store_payload,
)


def test_canonical_store_normalizes_and_serializes() -> None:
    store = CanonicalStore(
        records=(
            CanonicalStoreRecord(
                canonical_id=" protein:P12345 ",
                entity_kind=" Protein ",
                canonical_payload={
                    "name": "MAPK1",
                    "source_release": {"manifest_id": "UniProt:2026_02:download"},
                },
                source_refs=(
                    CanonicalStoreSourceRef(
                        source_name=" UniProt ",
                        source_record_id=" P12345 ",
                        source_manifest_id=" UniProt:2026_02:download ",
                        planning_index_ref=" planning:index:protein:P12345 ",
                        package_id=" package:train:v1 ",
                        source_locator=" https://example.org/uniprot/P12345 ",
                        source_keys={"accession": " P12345 "},
                    ),
                    CanonicalStoreSourceRef(
                        source_name="UniProt",
                        source_record_id="P12345",
                        source_manifest_id="UniProt:2026_02:download",
                        planning_index_ref="planning:index:protein:P12345",
                        package_id="package:train:v1",
                    ),
                ),
                planning_index_refs=(" planning:index:protein:P12345 ",),
                package_ids=(" package:train:v1 ",),
                artifact_pointers=(
                    CanonicalStoreArtifactPointer(
                        artifact_kind=" structure ",
                        pointer=" cache/structures/p12345.cif ",
                        selector="chain=A",
                        source_name=" RCSB ",
                        source_record_id=" 1ABC ",
                        canonical_id=" protein:P12345 ",
                        planning_index_ref=" planning:index:protein:P12345 ",
                        package_id=" package:train:v1 ",
                        notes=(" hydrate on selection ", "hydrate on selection"),
                    ),
                ),
                aliases=(" uniprot:P12345 ", "protein:P12345"),
                provenance_refs=(
                    " raw:uniprot:P12345 ",
                    "source_release:UniProt:2026_02:download ",
                ),
                notes=(" canonical payload stored once ",),
            ),
        ),
    )

    record = store.records[0]
    source_ref = record.source_refs[0]
    artifact = record.artifact_pointers[0]

    assert store.record_count == 1
    assert store.canonical_ids == ("protein:P12345",)
    assert record.entity_kind == "protein"
    assert record.storage_key == "canonical/protein/protein%3AP12345"
    assert record.source_manifest_ids == ("UniProt:2026_02:download",)
    assert record.source_names == ("UniProt",)
    assert source_ref.storage_key == "sources/UniProt/P12345"
    assert artifact.storage_key == "artifacts/structure/cache/structures/p12345.cif"
    assert record.aliases == ("uniprot:P12345", "protein:P12345")
    assert record.provenance_refs == (
        "raw:uniprot:P12345",
        "source_release:UniProt:2026_02:download",
    )
    assert record.notes == ("canonical payload stored once",)
    assert store.get("protein:P12345") is record
    assert store.get_by_storage_key("canonical/protein/protein%3AP12345") is record

    payload = store.to_dict()
    assert payload["record_count"] == 1
    assert payload["canonical_ids"] == ["protein:P12345"]
    assert payload["records"][0]["storage_key"] == "canonical/protein/protein%3AP12345"
    assert payload["records"][0]["source_refs"][0]["storage_key"] == "sources/UniProt/P12345"
    assert payload["records"][0]["artifact_pointers"][0]["storage_key"] == (
        "artifacts/structure/cache/structures/p12345.cif"
    )


def test_validate_canonical_store_payload_accepts_common_aliases() -> None:
    store = validate_canonical_store_payload(
        {
            "entries": [
                {
                    "id": "ligand:bindingdb:120095",
                    "kind": "ligand",
                    "payload": {
                        "name": "BindingDB ligand 120095",
                        "source_release": {"manifest_id": "BindingDB:2026.02:download"},
                    },
                    "sources": [
                        {
                            "source": "BindingDB",
                            "record_id": "120095",
                            "manifest_id": "BindingDB:2026.02:download",
                            "planning_ref": "planning:index:ligand:120095",
                        }
                    ],
                    "planning_refs": ("planning:index:ligand:120095",),
                    "packages": ("package:train:v1",),
                    "artifacts": [
                        {
                            "kind": "bundle",
                            "path": "cache/packages/package-train-v1.tar",
                            "selection": "selected-examples",
                            "source": "training",
                        }
                    ],
                    "alternative_ids": ("bindingdb:120095",),
                    "provenance": ("raw:bindingdb:120095",),
                }
            ],
        }
    )

    assert store.record_count == 1
    assert store.get("ligand:bindingdb:120095") is not None
    assert store.records[0].entity_kind == "ligand"
    assert store.records[0].artifact_pointers[0].artifact_kind == "bundle"
    assert store.records[0].package_ids == ("package:train:v1",)
    assert store.records[0].planning_index_refs == ("planning:index:ligand:120095",)


def test_canonical_store_record_from_dict_preserves_empty_payload_and_singleton_mappings() -> None:
    record = CanonicalStoreRecord.from_dict(
        {
            "canonical_id": "protein:P12345",
            "entity_kind": "protein",
            "canonical_payload": {},
            "source_refs": {
                "source_name": "UniProt",
                "source_record_id": "P12345",
                "source_manifest_id": "UniProt:2026_02:download",
                "planning_index_ref": "planning:index:protein:P12345",
            },
            "artifact_pointers": {
                "artifact_kind": "structure",
                "pointer": "cache/structures/p12345.cif",
                "source_name": "RCSB",
                "source_record_id": "1ABC",
            },
        }
    )

    assert record.canonical_payload == {}
    assert record.source_refs == (
        CanonicalStoreSourceRef(
            source_name="UniProt",
            source_record_id="P12345",
            source_manifest_id="UniProt:2026_02:download",
            planning_index_ref="planning:index:protein:P12345",
        ),
    )
    assert record.artifact_pointers == (
        CanonicalStoreArtifactPointer(
            artifact_kind="structure",
            pointer="cache/structures/p12345.cif",
            source_name="RCSB",
            source_record_id="1ABC",
        ),
    )

    round_tripped = CanonicalStoreRecord.from_dict(record.to_dict())
    assert round_tripped.canonical_payload == {}
    assert round_tripped.source_refs == record.source_refs
    assert round_tripped.artifact_pointers == record.artifact_pointers


def test_validate_canonical_store_payload_accepts_singleton_entry_mappings() -> None:
    store = validate_canonical_store_payload(
        {
            "entries": {
                "canonical_id": "ligand:bindingdb:120095",
                "kind": "ligand",
                "canonical_payload": {},
                "sources": {
                    "source": "BindingDB",
                    "record_id": "120095",
                    "manifest_id": "BindingDB:2026.02:download",
                },
            },
        }
    )

    assert store.record_count == 1
    assert store.canonical_ids == ("ligand:bindingdb:120095",)
    assert store.records[0].canonical_payload == {}
    assert store.records[0].source_names == ("BindingDB",)
    assert store.records[0].source_record_ids == ("120095",)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {
                "records": (),
            },
            "records must not be empty",
        ),
        (
            {
                "records": (
                    CanonicalStoreRecord(
                        canonical_id="protein:P12345",
                        entity_kind="protein",
                    ),
                    CanonicalStoreRecord(
                        canonical_id="protein:P12345",
                        entity_kind="protein",
                    ),
                ),
            },
            "duplicate canonical_id",
        ),
        (
            {
                "records": (
                    CanonicalStoreRecord(
                        canonical_id="protein:P12345",
                        entity_kind="protein",
                        source_refs=(
                            CanonicalStoreSourceRef(
                                source_name="UniProt",
                                source_record_id="P12345",
                                planning_index_ref="planning:index:protein:P12345",
                            ),
                        ),
                    ),
                ),
                "schema_version": 0,
            },
            "schema_version must be >= 1",
        ),
    ],
)
def test_canonical_store_rejects_invalid_input(kwargs, message) -> None:
    with pytest.raises((ValueError, TypeError), match=message):
        CanonicalStore(**kwargs)
