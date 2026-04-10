from __future__ import annotations

from connectors.rcsb.parsers import RCSBEntityRecord
from connectors.uniprot.parsers import UniProtSequenceRecord
from normalization.mapping.mmseqs2_chain_alignment import (
    map_chain_sequence_to_uniprot,
    map_entity_chains_to_uniprot,
)


def test_map_chain_sequence_resolves_best_non_exact_alignment() -> None:
    query_sequence = "MKTAYIAKQRQISFVKSHFSRQ"
    resolved = map_chain_sequence_to_uniprot(
        query_sequence,
        [
            _make_uniprot("P_GOOD", "GGMKTAYIAKQRQISFVKSHFNRQAA"),
            _make_uniprot("P_BAD", "YYYYYYYYYYYYYYYYYYYYYYYYYY"),
        ],
        pdb_id="1ABC",
        entity_id="1",
        chain_id="A",
    )

    assert resolved.status == "resolved"
    assert resolved.resolved_accession == "P_GOOD"
    assert resolved.reason == "alignment_resolved"
    assert resolved.alignment_backend == "local_smith_waterman_fallback"
    assert resolved.candidates[0].identity > 0.9
    assert resolved.candidates[0].query_coverage == 1.0
    assert resolved.candidates[0].alignment_backend == "local_smith_waterman_fallback"
    assert resolved.candidates[1].query_coverage < 0.1
    assert resolved.to_dict()["alignment_backend"] == "local_smith_waterman_fallback"
    assert resolved.to_dict()["candidates"][0]["alignment_backend"] == (
        "local_smith_waterman_fallback"
    )


def test_map_chain_sequence_marks_tied_top_hits_as_ambiguous() -> None:
    ambiguous = map_chain_sequence_to_uniprot(
        "ACDEFGHIKLMNPQRSTVWY",
        [
            _make_uniprot("P_ONE", "ACDEFGHIKLMNPQRSTVWY"),
            _make_uniprot("P_TWO", "ACDEFGHIKLMNPQRSTVWY"),
        ],
        chain_id="A",
    )

    assert ambiguous.status == "ambiguous"
    assert ambiguous.resolved_accession is None
    assert ambiguous.reason == "ambiguous_top_alignment"
    assert ambiguous.alignment_backend == "local_smith_waterman_fallback"
    assert [candidate.accession for candidate in ambiguous.candidates[:2]] == ["P_ONE", "P_TWO"]
    assert ambiguous.candidates[0].alignment_backend == "local_smith_waterman_fallback"


def test_map_chain_sequence_preserves_noncanonical_symbols_in_query_length() -> None:
    unresolved = map_chain_sequence_to_uniprot(
        "ACD-1",
        [
            _make_uniprot("P_MATCH", "ACD"),
        ],
        chain_id="A",
    )

    assert unresolved.status == "unresolved"
    assert unresolved.resolved_accession is None
    assert unresolved.reason == "no_alignment_passed_thresholds"
    assert unresolved.query_sequence_length == 5
    assert unresolved.alignment_backend == "local_smith_waterman_fallback"
    assert unresolved.candidates[0].query_coverage < 0.9
    assert unresolved.candidates[0].alignment_backend == "local_smith_waterman_fallback"


def test_map_chain_sequence_preserves_explicit_unresolved_when_no_hit_passes_thresholds() -> None:
    unresolved = map_chain_sequence_to_uniprot(
        "ACDEFGHIKLMNPQRSTVWY",
        [
            _make_uniprot("P_LOW_1", "YYYYYYYYYYYYYYYYYYYY"),
            _make_uniprot("P_LOW_2", "CCCCCCCCCCCCCCCCCCCC"),
        ],
        chain_id="A",
        provided_uniprot_ids=("P_LOW_1",),
    )

    assert unresolved.status == "unresolved"
    assert unresolved.resolved_accession is None
    assert unresolved.reason == "no_alignment_passed_thresholds"
    assert unresolved.provided_uniprot_ids == ("P_LOW_1",)
    assert unresolved.candidates[0].is_reference_hint is True
    assert unresolved.alignment_backend == "local_smith_waterman_fallback"


def test_map_entity_chains_uses_alignment_evidence_for_each_chain() -> None:
    entity = RCSBEntityRecord(
        pdb_id="2XYZ",
        entity_id="7",
        description="Example entity",
        polymer_type="Protein",
        sequence="MKTAYIAKQRQISFVKSHFSRQ",
        sequence_length=22,
        chain_ids=("A", "B"),
        uniprot_ids=("P_HINT",),
        organism_names=("Escherichia coli",),
        taxonomy_ids=("562",),
    )

    mappings = map_entity_chains_to_uniprot(
        entity,
        [
            _make_uniprot("P_HINT", "PPPPPPPPPPPPPPPPPPPPPP"),
            _make_uniprot("P_ALIGN", "TTMKTAYIAKQRQISFVKSHFSRQAA"),
        ],
    )

    assert [mapping.chain_id for mapping in mappings] == ["A", "B"]
    assert all(mapping.status == "resolved" for mapping in mappings)
    assert all(mapping.resolved_accession == "P_ALIGN" for mapping in mappings)
    assert all(mapping.provided_uniprot_ids == ("P_HINT",) for mapping in mappings)
    assert all(mapping.alignment_backend == "local_smith_waterman_fallback" for mapping in mappings)
    assert mappings[0].candidates[1].is_reference_hint is True


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
