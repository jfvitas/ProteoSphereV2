from __future__ import annotations

from connectors.rcsb.parsers import RCSBEntityRecord
from connectors.uniprot.parsers import UniProtSequenceRecord
from normalization.mapping.chain_ambiguity import (
    map_chain_sequence_preserving_ambiguity,
    map_entity_chains_preserving_ambiguity,
)


def test_preserves_multiple_exact_candidates_as_ambiguous() -> None:
    mapping = map_chain_sequence_preserving_ambiguity(
        "ACDEFGHIK",
        [
            _make_uniprot("P_ONE", "ACDEFGHIK"),
            _make_uniprot("P_TWO", "ACDEFGHIK"),
            _make_uniprot("P_OTHER", "YYYYYYYYY"),
        ],
        pdb_id="1ABC",
        entity_id="1",
        chain_id="A",
    )

    assert mapping.status == "ambiguous"
    assert mapping.resolved_accession is None
    assert mapping.reason == "multiple_exact_sequence_matches"
    assert [candidate.accession for candidate in mapping.candidates[:2]] == ["P_ONE", "P_TWO"]
    assert mapping.candidates[0].source_backends == (
        "exact_sequence_match",
        "local_smith_waterman_fallback",
    )
    assert mapping.to_dict()["candidates"][0]["source_backends"] == [
        "exact_sequence_match",
        "local_smith_waterman_fallback",
    ]


def test_preserves_alignment_ambiguity_when_exact_match_is_absent() -> None:
    mapping = map_chain_sequence_preserving_ambiguity(
        "ACDEFGHIKLMNPQRSTVWY",
        [
            _make_uniprot("P_ONE", "ACDEFGHIKLMNPQRSTVWY"),
            _make_uniprot("P_TWO", "ACDEFGHIKLMNPQRSTVWY"),
        ],
        chain_id="A",
    )

    assert mapping.status == "ambiguous"
    assert mapping.resolved_accession is None
    assert mapping.reason == "multiple_exact_sequence_matches"
    assert [candidate.accession for candidate in mapping.candidates[:2]] == ["P_ONE", "P_TWO"]
    assert all(
        "local_smith_waterman_fallback" in candidate.source_backends
        or candidate.source_backends == ("exact_sequence_match",)
        for candidate in mapping.candidates
    )


def test_entity_mapping_preserves_ambiguity_for_each_chain() -> None:
    entity = RCSBEntityRecord(
        pdb_id="2XYZ",
        entity_id="7",
        description="Example entity",
        polymer_type="Protein",
        sequence="ACDEFGHIK",
        sequence_length=9,
        chain_ids=("A", "B"),
        uniprot_ids=("P_HINT",),
        organism_names=("Test organism",),
        taxonomy_ids=("9606",),
    )

    mappings = map_entity_chains_preserving_ambiguity(
        entity,
        [
            _make_uniprot("P_ONE", "ACDEFGHIK"),
            _make_uniprot("P_TWO", "ACDEFGHIK"),
        ],
    )

    assert [mapping.chain_id for mapping in mappings] == ["A", "B"]
    assert all(mapping.status == "ambiguous" for mapping in mappings)
    assert all(mapping.resolved_accession is None for mapping in mappings)
    assert all(mapping.provided_uniprot_ids == ("P_HINT",) for mapping in mappings)


def test_preserves_alignment_backend_provenance_in_candidates() -> None:
    mapping = map_chain_sequence_preserving_ambiguity(
        "MKTAYIAKQRQISFVKSHFSRQ",
        [
            _make_uniprot("P_GOOD", "GGMKTAYIAKQRQISFVKSHFNRQAA"),
            _make_uniprot("P_BAD", "YYYYYYYYYYYYYYYYYYYYYYYYYY"),
        ],
        chain_id="A",
    )

    assert mapping.status == "resolved"
    assert mapping.resolved_accession == "P_GOOD"
    assert mapping.reason == "alignment_resolved"
    assert mapping.candidates[0].source_backends == (
        "exact_sequence_match",
        "local_smith_waterman_fallback",
    )
    assert mapping.to_dict()["candidates"][0]["source_backends"] == [
        "exact_sequence_match",
        "local_smith_waterman_fallback"
    ]


def _make_uniprot(accession: str, sequence: str) -> UniProtSequenceRecord:
    return UniProtSequenceRecord(
        accession=accession,
        entry_name=f"{accession}_ENTRY",
        protein_name=f"{accession} protein",
        organism_name="Test organism",
        gene_names=(),
        reviewed=True,
        sequence=sequence,
        sequence_length=len(sequence),
        source_format="test",
    )
