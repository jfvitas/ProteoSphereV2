from __future__ import annotations

import pytest

from core.storage.planning_index_schema import (
    PlanningIndexCoverage,
    PlanningIndexEntry,
    PlanningIndexMaterializationPointer,
    PlanningIndexSchema,
    PlanningIndexSourceRecord,
    validate_planning_index_payload,
)


def test_planning_index_entry_normalizes_pinned_source_records_and_lazy_pointers() -> None:
    entry = PlanningIndexEntry(
        planning_id="  protein:P12345  ",
        source_records=(
            PlanningIndexSourceRecord(
                source_name=" UniProt ",
                source_record_id=" p12345 ",
                release_version=" 2026_03 ",
                source_locator=" https://example.org/uniprot ",
                source_keys={"accession": " p12345 ", "taxon": 9606},
            ),
        ),
        canonical_ids=(" protein:P12345 ", "protein:P12345", "canonical:P12345"),
        join_status=" Joined ",
        join_confidence=0.94,
        coverage=(
            PlanningIndexCoverage(
                coverage_kind="source",
                label="UniProt",
                coverage_state="full",
                source_names=(" UniProt ", " UniProt "),
            ),
            PlanningIndexCoverage(
                coverage_kind="modality",
                label="experimental_structure",
                coverage_state="partial",
                notes=(" chain-level mapping only ",),
                confidence=0.6,
            ),
        ),
        lazy_materialization_pointers=(
            PlanningIndexMaterializationPointer(
                materialization_kind="coordinates",
                pointer=" cache/structures/p12345.cif ",
                selector="chain=A",
                source_name="RCSB",
                source_record_id="1ABC",
                notes=("hydrate on selection", "hydrate on selection"),
            ),
        ),
        metadata={"split": "train", "flags": ("source_pinned", True)},
    )

    assert entry.planning_id == "protein:P12345"
    assert entry.source_records[0].source_name == "UniProt"
    assert entry.source_records[0].source_record_id == "p12345"
    assert entry.source_records[0].release_stamp == "2026_03"
    assert entry.canonical_ids == ("protein:P12345", "canonical:P12345")
    assert entry.primary_canonical_id == "protein:P12345"
    assert entry.join_status == "joined"
    assert entry.join_confidence == 0.94
    assert entry.coverage[0].coverage_kind == "source"
    assert entry.coverage[0].coverage_state == "present"
    assert entry.coverage[0].source_names == ("UniProt",)
    assert entry.coverage[1].coverage_kind == "modality"
    assert entry.coverage[1].coverage_state == "partial"
    assert entry.lazy_materialization_pointers[0].materialization_kind == "coordinates"
    assert entry.lazy_materialization_pointers[0].pointer == "cache/structures/p12345.cif"
    assert entry.lazy_materialization_pointers[0].notes == ("hydrate on selection",)
    assert entry.is_pinned_source_backed

    payload = entry.to_dict()
    assert payload["canonical_ids"] == ["protein:P12345", "canonical:P12345"]
    assert payload["canonical_id"] == "protein:P12345"
    assert payload["join_status"] == "joined"
    assert payload["coverage"][1]["coverage_kind"] == "modality"
    assert payload["lazy_materialization_pointers"][0]["pointer"] == "cache/structures/p12345.cif"


def test_planning_index_schema_round_trips_from_dict() -> None:
    schema = PlanningIndexSchema(
        records=(
            PlanningIndexEntry(
                planning_id="emdb:emd-1234",
                source_records=(
                    PlanningIndexSourceRecord(
                        source_name="EMDB",
                        source_record_id="EMD-1234",
                        release_date="2026-03-22",
                        manifest_id="EMDB:2026-03-22:download",
                    ),
                ),
                canonical_ids=("emdb:EMD-1234",),
                join_status="candidate",
                coverage=(
                    PlanningIndexCoverage(
                        coverage_kind="source",
                        label="EMDB",
                        coverage_state="present",
                    ),
                ),
                lazy_materialization_pointers=(
                    PlanningIndexMaterializationPointer(
                        materialization_kind="map",
                        pointer="cache/emdb/emd-1234.map.gz",
                        selector="selected-example",
                    ),
                ),
            ),
        ),
    )

    payload = schema.to_dict()
    rebuilt = validate_planning_index_payload(payload)

    assert rebuilt.schema_version == 1
    assert rebuilt.record_count == 1
    assert rebuilt.get("emdb:emd-1234") is not None
    assert rebuilt.get("emdb:emd-1234").canonical_ids == ("emdb:EMD-1234",)
    assert (
        rebuilt.to_dict()["records"][0]["lazy_materialization_pointers"][0][
            "materialization_kind"
        ]
        == "map"
    )


def test_planning_index_rejects_joined_entry_without_canonical_ids() -> None:
    with pytest.raises(ValueError, match="joined entries require canonical_ids"):
        PlanningIndexEntry(
            planning_id="protein:empty",
            source_records=(
                PlanningIndexSourceRecord(
                    source_name="UniProt",
                    source_record_id="P00000",
                    release_version="2026_03",
                ),
            ),
            join_status="joined",
        )
