from __future__ import annotations

import pytest

from execution.assets.structure_cache import (
    StructureCacheAsset,
    StructureCacheCatalog,
    build_structure_cache,
)


def test_build_structure_cache_normalizes_experimental_and_predicted_assets() -> None:
    catalog = build_structure_cache(
        [
            {
                "source_name": "RCSB",
                "asset_kind": "PDB",
                "pointer": "cache/structures/1ABC.pdb",
                "pdb_id": "1abc",
                "entity_id": "1",
                "source_record_id": "1ABC/1",
                "checksum": "sha256:pdb-a",
            },
            {
                "source_name": "PDBe",
                "asset_kind": "pdb",
                "pointer": "mirror/structures/1ABC.pdb",
                "pdb_id": "1ABC",
                "entity_id": "1",
                "source_record_id": "1ABC/1#pdbe",
                "checksum": "sha256:pdb-a",
            },
            {
                "source_name": "RCSB",
                "asset_kind": "mmcif",
                "pointer": "cache/structures/1ABC.cif",
                "pdb_id": "1ABC",
                "assembly_id": "1",
                "source_record_id": "1ABC-1",
                "checksum": "sha256:mmcif-a",
            },
            {
                "source_name": "AlphaFold DB",
                "asset_kind": "alphafold",
                "pointer": "cache/alphafold/P69905.cif",
                "accession": "p69905",
                "model_entity_id": "AF-P69905-F1",
                "sequence_checksum": "SEQ123",
                "source_record_id": "P69905:AF-P69905-F1",
                "checksum": "sha256:af-a",
            },
        ],
        cache_id="structure-cache:test",
        notes=("structural smoke",),
    )

    assert catalog.cache_id == "structure-cache:test"
    assert catalog.entry_count == 3
    assert catalog.hit_count == 3
    assert catalog.miss_count == 0
    assert catalog.checksum_drift_count == 0
    assert catalog.notes == ("structural smoke",)

    pdb_entry = next(entry for entry in catalog.entries if entry.asset_kind == "pdb")
    assert pdb_entry.cache_state == "hit"
    assert pdb_entry.structure_family == "experimental"
    assert pdb_entry.pdb_id == "1ABC"
    assert pdb_entry.source_names == ("RCSB", "PDBe")
    assert pdb_entry.source_record_ids == ("1ABC/1", "1ABC/1#pdbe")
    assert pdb_entry.observed_checksums == ("sha256:pdb-a",)
    assert pdb_entry.reusable is True

    mmcif_entry = next(entry for entry in catalog.entries if entry.asset_kind == "mmcif")
    assert mmcif_entry.cache_state == "hit"
    assert mmcif_entry.structure_family == "experimental"
    assert mmcif_entry.assembly_id == "1"
    assert mmcif_entry.checksum == "sha256:mmcif-a"

    alphafold_entry = next(
        entry for entry in catalog.entries if entry.asset_kind == "alphafold"
    )
    assert alphafold_entry.cache_state == "hit"
    assert alphafold_entry.structure_family == "predicted"
    assert alphafold_entry.accession == "P69905"
    assert alphafold_entry.model_entity_id == "AF-P69905-F1"
    assert alphafold_entry.sequence_checksum == "SEQ123"
    assert alphafold_entry.to_dict()["assets"][0]["source_name"] == "AlphaFold DB"


def test_build_structure_cache_marks_checksum_drift_explicitly() -> None:
    catalog = build_structure_cache(
        [
            {
                "source_name": "AlphaFold DB",
                "asset_kind": "alphafold",
                "pointer": "cache/alphafold/P04637.cif",
                "accession": "P04637",
                "model_entity_id": "AF-P04637-F1",
                "sequence_checksum": "SEQ456",
                "checksum": "sha256:af-a",
            },
            {
                "source_name": "AlphaFold DB",
                "asset_kind": "alphafold",
                "pointer": "cache/alphafold/P04637.cif",
                "accession": "P04637",
                "model_entity_id": "AF-P04637-F1",
                "sequence_checksum": "SEQ456",
                "checksum": "sha256:af-b",
            },
        ]
    )

    assert catalog.entry_count == 1
    assert catalog.checksum_drift_count == 1
    entry = catalog.entries[0]
    assert entry.cache_state == "checksum_drift"
    assert entry.checksum_state == "drift"
    assert entry.checksum is None
    assert entry.observed_checksums == ("sha256:af-a", "sha256:af-b")
    assert entry.reusable is False
    assert "checksum drift detected" in entry.notes


def test_structure_cache_misses_when_checksum_is_absent_and_round_trips() -> None:
    catalog = build_structure_cache(
        [
            {
                "source_name": "RCSB",
                "asset_kind": "mmcif",
                "pointer": "cache/structures/2XYZ.cif",
                "pdb_id": "2xyz",
                "entity_id": "7",
            }
        ],
        cache_id="structure-cache:missing",
    )

    assert catalog.miss_count == 1
    entry = catalog.entries[0]
    assert entry.cache_state == "miss"
    assert entry.checksum_state == "missing"
    assert entry.observed_checksums == ()
    assert entry.checksum is None
    assert entry.reusable is False
    assert "missing checksum" in entry.notes[0]

    round_tripped = StructureCacheCatalog.from_mapping(catalog.to_dict())
    assert round_tripped.cache_id == catalog.cache_id
    assert round_tripped.entry_count == 1
    assert round_tripped.entries[0].cache_state == "miss"


def test_structure_cache_duplicate_same_checksum_stays_truthful() -> None:
    catalog = build_structure_cache(
        [
            {
                "source_name": "RCSB",
                "asset_kind": "mmcif",
                "pointer": "cache/structures/9R2Q.cif",
                "pdb_id": "9R2Q",
                "source_record_id": "P04637:9R2Q",
                "checksum": "sha256:9r2q",
                "notes": ["selected heavy asset"],
            },
            {
                "source_name": "RCSB",
                "asset_kind": "mmcif",
                "pointer": "cache/structures/9R2Q.cif",
                "pdb_id": "9R2Q",
                "source_record_id": "P04637:9R2Q:repeat",
                "checksum": "sha256:9r2q",
                "notes": ["reselected heavy asset"],
            },
        ]
    )

    assert catalog.entry_count == 1
    entry = catalog.entries[0]
    assert entry.cache_state == "hit"
    assert entry.checksum_state == "consistent"
    assert entry.asset_count == 2
    assert "one or more source copies are missing checksums" not in entry.notes
    assert entry.notes == ("selected heavy asset", "reselected heavy asset")


def test_structure_cache_asset_from_mapping_normalizes_aliases() -> None:
    asset = StructureCacheAsset.from_mapping(
        {
            "source": "AlphaFold DB",
            "kind": "alphafold",
            "path": "cache/alphafold/P12345.cif",
            "accession": "p12345",
            "model_id": "AF-P12345-F1",
            "sequenceChecksum": "SEQ789",
            "payload_sha256": "sha256:af-c",
            "notes": ["  reusable  ", "reusable"],
        }
    )

    assert asset.source_name == "AlphaFold DB"
    assert asset.asset_kind == "alphafold"
    assert asset.accession == "P12345"
    assert asset.model_entity_id == "AF-P12345-F1"
    assert asset.sequence_checksum == "SEQ789"
    assert asset.checksum == "sha256:af-c"
    assert asset.notes == ("reusable",)
    assert asset.structure_family == "predicted"


def test_structure_cache_rejects_missing_identity() -> None:
    with pytest.raises(ValueError):
        StructureCacheAsset(
            source_name="RCSB",
            asset_kind="pdb",
            pointer="cache/structures/invalid.pdb",
            checksum="sha256:bad",
        )
