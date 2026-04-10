from __future__ import annotations

import pytest

from connectors.uniprot.parsers import UniProtSequenceRecord
from features.sequence_features import (
    DEFAULT_SEQUENCE_FEATURE_NAMES,
    extract_sequence_features,
    extract_uniprot_sequence_features,
    normalize_protein_sequence,
    residue_class_counts,
    residue_counts,
    residue_fractions,
)


def test_normalize_protein_sequence_rejects_invalid_codes() -> None:
    with pytest.raises(ValueError, match="invalid residue codes"):
        normalize_protein_sequence("ACD1*")


def test_sequence_feature_primitives_compute_counts_fractions_and_classes() -> None:
    sequence = "ACDEFGHIKLMNPQRSTVWY"

    assert residue_counts(sequence)["A"] == 1
    assert residue_counts(sequence)["Y"] == 1
    assert residue_fractions(sequence)["A"] == 0.05
    assert residue_class_counts(sequence) == {
        "hydrophobic": 9,
        "polar": 4,
        "positive": 3,
        "negative": 2,
        "special": 2,
    }

    result = extract_sequence_features(sequence, accession="p12345")

    assert result.accession == "P12345"
    assert result.sequence_length == 20
    assert result.canonical_residue_count == 20
    assert result.ambiguous_residue_count == 0
    assert result.feature_names == DEFAULT_SEQUENCE_FEATURE_NAMES
    assert result.feature_values["fraction_A"] == 0.05
    assert result.feature_values["fraction_hydrophobic"] == 9 / 20
    assert len(result.feature_vector) == len(DEFAULT_SEQUENCE_FEATURE_NAMES)
    assert result.to_dict()["feature_names"][0] == "sequence_length"


def test_extract_sequence_features_tracks_ambiguous_residues_without_overclaiming() -> None:
    result = extract_sequence_features("ABXZ")

    assert result.sequence == "ABXZ"
    assert result.sequence_length == 4
    assert result.canonical_residue_count == 1
    assert result.ambiguous_residue_count == 3
    assert result.ambiguous_residue_counts == {"B": 1, "X": 1, "Z": 1}
    assert result.residue_counts["A"] == 1
    assert result.feature_values["ambiguous_residue_fraction"] == 0.75
    assert result.feature_values["fraction_A"] == 0.25


def test_extract_uniprot_sequence_features_preserves_record_metadata() -> None:
    record = UniProtSequenceRecord(
        accession="P04637",
        entry_name="P53_HUMAN",
        protein_name="Cellular tumor antigen p53",
        organism_name="Homo sapiens",
        gene_names=("TP53",),
        reviewed=True,
        sequence="MEEPQSDPSV",
        sequence_length=10,
        source_format="json",
    )

    result = extract_uniprot_sequence_features(record)

    assert result.accession == "P04637"
    assert result.source == "uniprot_sequence_record"
    assert result.source_format == "json"
    assert result.provenance["entry_name"] == "P53_HUMAN"
    assert result.provenance["reviewed"] is True
    assert result.sequence_length == 10
