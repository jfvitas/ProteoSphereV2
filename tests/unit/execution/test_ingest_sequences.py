from __future__ import annotations

from connectors.uniprot.parsers import UniProtSequenceRecord
from core.canonical.registry import CanonicalEntityRegistry
from core.procurement.source_release_manifest import SourceReleaseManifest
from execution.acquire.uniprot_snapshot import UniProtSnapshot, UniProtSnapshotRecord
from execution.ingest.sequences import ingest_sequence_records, ingest_uniprot_snapshot


def _sequence_record(
    accession: str,
    *,
    protein_name: str,
    sequence: str,
    entry_name: str | None = None,
) -> UniProtSequenceRecord:
    return UniProtSequenceRecord(
        accession=accession,
        entry_name=entry_name or f"{accession}_HUMAN",
        protein_name=protein_name,
        organism_name="Homo sapiens",
        gene_names=("ABC",),
        reviewed=True,
        sequence=sequence,
        sequence_length=len(sequence),
        source_format="json",
    )


def _snapshot_record(
    accession: str,
    *,
    protein_name: str,
    sequence: str,
    provenance_id: str,
) -> UniProtSnapshotRecord:
    return UniProtSnapshotRecord(
        accession=accession,
        sequence=_sequence_record(accession, protein_name=protein_name, sequence=sequence),
        release="2026_02",
        release_date="2026-03-01",
        proteome_id="UP000005640",
        proteome_name="Homo sapiens",
        proteome_reference=True,
        proteome_taxon_id=9606,
        provenance={
            "provenance_id": provenance_id,
            "source": {
                "source_name": "UniProt",
                "acquisition_mode": "bulk_download",
            },
            "transformation_step": "sequence_observation",
            "acquired_at": "2026-03-22T12:00:00+00:00",
            "parser_version": "1.0",
            "source_ids": [f"raw/{accession.lower()}.json"],
        },
        raw_entry={"primaryAccession": accession},
    )


def test_ingest_uniprot_snapshot_registers_canonical_proteins_and_preserves_provenance() -> None:
    snapshot = UniProtSnapshot(
        source_release={
            "source_name": "UniProt",
            "release_version": "2026_02",
            "release_date": "2026-03-01",
            "retrieval_mode": "download",
            "source_locator": "https://example.org/uniprot",
        },
        proteome={
            "proteome_id": "UP000005640",
            "proteome_name": "Homo sapiens",
            "proteome_reference": True,
            "proteome_taxon_id": 9606,
        },
        provenance={
            "source_ids": ["raw/uniprot/2026_02/human.json"],
            "acquired_at": "2026-03-22T12:00:00+00:00",
        },
        records=(
            _snapshot_record(
                "P12345",
                protein_name="Example protein",
                sequence="MEEPQSDPSV",
                provenance_id="src-1",
            ),
            _snapshot_record(
                "Q9XYZ1",
                protein_name="Second protein",
                sequence="ACDEFGHIKL",
                provenance_id="src-2",
            ),
        ),
    )
    registry = CanonicalEntityRegistry()
    expected_release = SourceReleaseManifest.from_dict(snapshot.source_release)

    result = ingest_uniprot_snapshot(snapshot, registry=registry)

    assert result.status == "ready"
    assert result.canonical_ids == ("protein:P12345", "protein:Q9XYZ1")
    assert registry.resolve("protein:P12345") is result.canonical_proteins[0]
    assert result.records[0].provenance_record.metadata["source_ids"] == ("raw/p12345.json",)
    assert result.provenance_records[0].metadata["canonical_id"] == "protein:P12345"
    assert result.provenance_records[0].metadata["source_release"]["manifest_id"] == (
        expected_release.manifest_id
    )

    payload = result.to_dict()
    assert payload["canonical_proteins"][0]["accession"] == "P12345"
    assert payload["source_release"]["manifest_id"] == expected_release.manifest_id


def test_ingest_sequence_records_surfaces_sequence_conflicts() -> None:
    result = ingest_sequence_records(
        [
            {
                "accession": "P12345",
                "sequence": "ACDEFG",
                "organism": "Homo sapiens",
                "name": "Example protein",
                "source": "UniProt",
                "provenance": {"source_ids": ["raw/one.json"]},
            },
            {
                "accession": "P12345",
                "sequence": "ACDEFA",
                "organism": "Homo sapiens",
                "name": "Example protein",
                "source": "UniProt",
                "provenance": {"source_ids": ["raw/two.json"]},
            },
        ]
    )

    assert result.status == "unresolved"
    assert result.canonical_proteins == ()
    assert result.outcomes[0].status == "conflict"
    assert result.outcomes[0].merge_result is not None
    assert result.outcomes[0].merge_result.conflicts[0].observed_values == ("ACDEFG", "ACDEFA")
    assert result.unresolved_references[0].reason == "sequence_mismatch"


def test_ingest_sequence_records_preserves_metadata_ambiguity() -> None:
    result = ingest_sequence_records(
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
        ]
    )

    assert result.status == "partial"
    assert result.canonical_ids == ("protein:P12345",)
    assert result.outcomes[0].status == "ambiguous"
    assert result.outcomes[0].alternative_values["name"] == ("Alpha protein", "Beta protein")
    assert result.canonical_proteins[0].name == "Alpha protein"


def test_ingest_sequence_records_marks_missing_accessions_unresolved() -> None:
    result = ingest_sequence_records(
        [
            {
                "sequence": "ACDEFG",
                "organism": "Homo sapiens",
                "name": "Unplaced sequence",
                "source": "UniProt",
            }
        ]
    )

    assert result.status == "unresolved"
    assert result.canonical_proteins == ()
    assert result.outcomes[0].status == "unresolved"
    assert result.unresolved_references[0].reason == "missing_primary_identifier"
