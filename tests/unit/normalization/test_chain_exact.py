from __future__ import annotations

from connectors.rcsb.parsers import RCSBEntityRecord
from connectors.uniprot.parsers import UniProtSequenceRecord
from normalization.mapping.chain_exact import (
    map_chain_sequence_exact,
    map_entity_chains_exact,
)


def test_map_chain_sequence_exact_resolves_single_exact_match() -> None:
    resolved = map_chain_sequence_exact(
        "ACDEFGHIK",
        [
            _make_uniprot("P_EXACT", "ACDEFGHIK"),
            _make_uniprot("P_OTHER", "YYYYYYYYY"),
        ],
        pdb_id="1ABC",
        entity_id="1",
        chain_id="A",
    )

    assert resolved.status == "resolved"
    assert resolved.resolved_accession == "P_EXACT"
    assert resolved.reason == "exact_sequence_match"
    assert resolved.alignment_backend == "exact_sequence_match"
    assert resolved.candidates[0].exact_sequence_match is True


def test_map_chain_sequence_exact_prefers_single_reference_hint() -> None:
    resolved = map_chain_sequence_exact(
        "ACDEFGHIK",
        [
            _make_uniprot("P_HINT", "ACDEFGHIK"),
            _make_uniprot("P_OTHER", "ACDEFGHIK"),
        ],
        provided_uniprot_ids=("P_HINT",),
    )

    assert resolved.status == "resolved"
    assert resolved.resolved_accession == "P_HINT"
    assert resolved.reason == "exact_sequence_match_with_reference_hint"
    assert resolved.candidates[0].is_reference_hint is True


def test_map_chain_sequence_exact_marks_multiple_exact_hits_as_ambiguous() -> None:
    ambiguous = map_chain_sequence_exact(
        "ACDEFGHIK",
        [
            _make_uniprot("P_ONE", "ACDEFGHIK"),
            _make_uniprot("P_TWO", "ACDEFGHIK"),
        ],
    )

    assert ambiguous.status == "ambiguous"
    assert ambiguous.resolved_accession is None
    assert ambiguous.reason == "multiple_exact_sequence_matches"


def test_map_chain_sequence_exact_preserves_unresolved_when_no_exact_hit_exists() -> None:
    unresolved = map_chain_sequence_exact(
        "ACDEFGHIK",
        [
            _make_uniprot("P_NEAR", "AACDEFGHIK"),
            _make_uniprot("P_OTHER", "YYYYYYYYY"),
        ],
        provided_uniprot_ids=("P_NEAR",),
    )

    assert unresolved.status == "unresolved"
    assert unresolved.resolved_accession is None
    assert unresolved.reason == "no_exact_sequence_match"
    assert unresolved.provided_uniprot_ids == ("P_NEAR",)


def test_map_entity_chains_exact_reuses_entity_sequence_for_each_chain() -> None:
    entity = RCSBEntityRecord(
        pdb_id="2XYZ",
        entity_id="7",
        description="Example entity",
        polymer_type="Protein",
        sequence="ACDEFGHIK",
        sequence_length=9,
        chain_ids=("A", "B"),
        uniprot_ids=("P_MATCH",),
        organism_names=("Test organism",),
        taxonomy_ids=("9606",),
    )

    mappings = map_entity_chains_exact(
        entity,
        [
            _make_uniprot("P_MATCH", "ACDEFGHIK"),
            _make_uniprot("P_OTHER", "YYYYYYYYY"),
        ],
    )

    assert [mapping.chain_id for mapping in mappings] == ["A", "B"]
    assert all(mapping.status == "resolved" for mapping in mappings)
    assert all(mapping.resolved_accession == "P_MATCH" for mapping in mappings)


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
