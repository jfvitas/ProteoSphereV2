from __future__ import annotations

from core.procurement.source_release_manifest import SourceReleaseManifest
from execution.indexing.protein_index import build_protein_planning_index
from execution.ingest.sequences import ingest_sequence_records


def _source_release() -> dict[str, object]:
    return {
        "source_name": "UniProt",
        "release_version": "2026_02",
        "release_date": "2026-03-01",
        "retrieval_mode": "download",
        "source_locator": "https://example.org/uniprot",
        "manifest_id": "UniProt:2026_02:download",
    }


def _resolved_records() -> list[dict[str, object]]:
    return [
        {
            "accession": "P12345",
            "sequence": "MEEPQSDPSV",
            "organism": "Homo sapiens",
            "name": "Example protein",
            "source": "UniProt",
            "source_id": "P12345_HUMAN",
            "reviewed": True,
            "provenance": {
                "source_ids": ["raw/uniprot/P12345.json"],
                "raw_payload_pointer": "cache/raw/uniprot/P12345.json",
            },
        }
    ]


def test_build_protein_planning_index_preserves_source_and_lazy_pointers() -> None:
    expected_release = SourceReleaseManifest.from_dict(_source_release())
    ingest_result = ingest_sequence_records(
        _resolved_records(),
        source_release=_source_release(),
    )

    planning_index = build_protein_planning_index(ingest_result)

    assert planning_index.record_count == 1
    entry = planning_index.records[0]
    assert entry.planning_id == "protein:P12345"
    assert entry.join_status == "joined"
    assert entry.canonical_ids == ("protein:P12345",)
    assert entry.source_records[0].source_name == "UniProt"
    assert entry.source_records[0].release_version == "2026_02"
    assert entry.coverage[0].coverage_kind == "source"
    assert entry.coverage[0].coverage_state == "present"
    assert entry.coverage[1].coverage_kind == "modality"
    assert entry.coverage[1].coverage_state == "present"
    assert entry.lazy_materialization_pointers[0].pointer == "cache/raw/uniprot/P12345.json"
    assert entry.lazy_materialization_pointers[0].materialization_kind == "portal_payload"
    assert entry.metadata["canonical_id"] == "protein:P12345"
    assert entry.metadata["source_release"]["manifest_id"] == expected_release.manifest_id


def test_build_protein_planning_index_preserves_ambiguous_join_status() -> None:
    ingest_result = ingest_sequence_records(
        [
            {
                "accession": "P12345",
                "sequence": "ACDEFG",
                "organism": "Homo sapiens",
                "name": "Alpha protein",
                "source": "UniProt",
            },
            {
                "accession": "P12345",
                "sequence": "ACDEFG",
                "organism": "Homo sapiens",
                "name": "Beta protein",
                "source": "UniProt",
            },
        ],
        source_release=_source_release(),
    )

    planning_index = build_protein_planning_index(ingest_result)

    assert planning_index.record_count == 1
    entry = planning_index.records[0]
    assert entry.join_status == "ambiguous"
    assert entry.canonical_ids == ("protein:P12345",)
    assert entry.coverage[1].coverage_state == "present"
    assert entry.lazy_materialization_pointers == ()


def test_build_protein_planning_index_skips_unplaced_records_without_accessions() -> None:
    ingest_result = ingest_sequence_records(
        [
            {
                "sequence": "ACDEFG",
                "organism": "Homo sapiens",
                "name": "Unplaced sequence",
                "source": "UniProt",
            }
        ],
        source_release=_source_release(),
    )

    planning_index = build_protein_planning_index(ingest_result)

    assert planning_index.record_count == 0
