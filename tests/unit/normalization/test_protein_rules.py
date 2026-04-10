from __future__ import annotations

from normalization.conflicts.protein_rules import merge_protein_records


def test_merge_protein_records_resolves_clean_merge() -> None:
    result = merge_protein_records(
        [
            {
                "uniprot_id": " p12345 ",
                "sequence": "ACDEFG",
                "organism": "Homo sapiens",
                "protein_name": "Example protein",
                "source": "UniProt",
                "provenance_refs": ["src:uniprot:1"],
            },
            {
                "accession": "P12345",
                "sequence": "ACDEFG",
                "organism": "Homo sapiens",
                "description": "Example protein from source B",
                "source": "curated",
                "provenance_refs": ["src:curated:2"],
            },
        ]
    )

    assert result.status == "resolved"
    assert result.is_resolved
    assert result.primary_accession == "P12345"
    assert result.canonical_protein is not None
    assert result.canonical_protein.accession == "P12345"
    assert result.canonical_protein.sequence == "ACDEFG"
    assert result.provenance_refs == ("src:uniprot:1", "src:curated:2")
    assert result.conflicts == ()


def test_merge_protein_records_flags_direct_sequence_conflict() -> None:
    result = merge_protein_records(
        [
            {
                "accession": "P12345",
                "sequence": "ACDEFG",
                "organism": "Homo sapiens",
                "provenance_refs": ["src:one"],
            },
            {
                "accession": "P12345",
                "sequence": "ACDEFA",
                "organism": "Homo sapiens",
                "provenance_refs": ["src:two"],
            },
        ]
    )

    assert result.status == "conflict"
    assert result.canonical_protein is None
    assert result.primary_accession == "P12345"
    assert result.conflicts[0].kind == "sequence_mismatch"
    assert result.conflicts[0].observed_values == ("ACDEFG", "ACDEFA")
    assert result.provenance_refs == ("src:one", "src:two")


def test_merge_protein_records_preserves_metadata_ambiguity() -> None:
    result = merge_protein_records(
        [
            {
                "accession": "P12345",
                "sequence": "ACDEFG",
                "organism": "Homo sapiens",
                "protein_name": "Alpha protein",
                "aliases": ["alpha", "shared"],
                "provenance_refs": ["src:one"],
            },
            {
                "accession": "P12345",
                "sequence": "ACDEFG",
                "organism": "Homo sapiens",
                "protein_name": "Beta protein",
                "aliases": ["beta", "shared"],
                "provenance_refs": ["src:two"],
            },
        ]
    )

    assert result.status == "ambiguous"
    assert result.canonical_protein is not None
    assert result.canonical_protein.accession == "P12345"
    assert result.canonical_protein.sequence == "ACDEFG"
    assert result.alternative_values["name"] == ("Alpha protein", "Beta protein")
    assert result.canonical_protein.aliases == ("alpha", "shared", "beta")
    assert result.conflicts == ()


def test_merge_protein_records_exposes_input_provenance_on_result_records() -> None:
    result = merge_protein_records(
        [
            {
                "accession": "P12345",
                "sequence": "ACDEFG",
                "organism": "Homo sapiens",
                "source": "UniProt",
                "provenance_refs": ["src:uniprot:1"],
            },
            {
                "accession": "P12345",
                "sequence": "ACDEFG",
                "organism": "Homo sapiens",
                "source": "Manual curation",
                "provenance": ["src:manual:2", "src:manual:2"],
            },
        ]
    )

    assert result.status == "resolved"
    assert [record.provenance_refs for record in result.records] == [
        ("src:uniprot:1",),
        ("src:manual:2",),
    ]
    assert result.provenance_refs == ("src:uniprot:1", "src:manual:2")
