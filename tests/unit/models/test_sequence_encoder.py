from __future__ import annotations

import pytest

from core.canonical.protein import CanonicalProtein
from models.multimodal.sequence_encoder import (
    DEFAULT_SEQUENCE_ENCODER_DIM,
    DEFAULT_SEQUENCE_ENCODER_MODEL,
    SequenceEncoder,
    encode_sequence,
)


def test_sequence_encoder_encodes_canonical_protein_and_preserves_lineage() -> None:
    protein = CanonicalProtein(
        accession=" p12345 ",
        sequence="a c d",
        name=" Example protein ",
        gene_names=("abc1",),
        organism=" Homo sapiens ",
        source="UniProt",
    )
    encoder = SequenceEncoder()

    result = encoder.encode_protein(
        protein,
        provenance={"run_id": "run-001", "source_ids": ["raw/p12345.json"]},
    )

    assert result.sequence == "ACD"
    assert result.model_name == DEFAULT_SEQUENCE_ENCODER_MODEL
    assert result.embedding_dim == DEFAULT_SEQUENCE_ENCODER_DIM
    assert result.source == "sequence_baseline"
    assert result.frozen is True
    assert result.residue_count == 3
    assert len(result.residue_embeddings) == 3
    assert len(result.pooled_embedding) == DEFAULT_SEQUENCE_ENCODER_DIM
    assert result.cls_embedding == result.pooled_embedding
    assert result.provenance["canonical_id"] == "protein:P12345"
    assert result.provenance["accession"] == "P12345"
    assert result.provenance["source_id"] == "P12345"
    assert result.provenance["name"] == "Example protein"
    assert result.provenance["organism"] == "Homo sapiens"
    assert result.provenance["gene_names"] == ["abc1"]
    assert result.provenance["run_id"] == "run-001"
    assert result.provenance["source_ids"] == ["raw/p12345.json"]
    assert result.provenance["encoder"] == DEFAULT_SEQUENCE_ENCODER_MODEL
    assert result.provenance["sequence_length"] == 3

    payload = result.to_dict()
    assert payload["sequence"] == "ACD"
    assert payload["cls_embedding"] == list(result.pooled_embedding)
    assert payload["provenance"]["canonical_id"] == "protein:P12345"


def test_sequence_encoder_reads_nested_canonical_payload_provenance() -> None:
    result = encode_sequence(
        {
            "canonical_payload": {
                "sequence": "ACDE",
                "canonical_id": "protein:P54321",
                "accession": "P54321",
                "name": "Nested example",
                "organism": "Homo sapiens",
                "gene_names": ("XYZ1",),
                "provenance_record": {
                    "provenance_id": "prov-001",
                    "source": {
                        "source_name": "UniProt",
                        "acquisition_mode": "bulk_download",
                    },
                    "transformation_step": "canonicalize_protein",
                    "source_ids": ["raw/p54321.json"],
                },
            }
        }
    )

    assert result.sequence == "ACDE"
    assert result.provenance["provenance_id"] == "prov-001"
    assert result.provenance["canonical_id"] == "protein:P54321"
    assert result.provenance["accession"] == "P54321"
    assert result.provenance["source_ids"] == ["raw/p54321.json"]
    assert result.provenance["gene_names"] == ["XYZ1"]


def test_sequence_encoder_preserves_scalar_gene_names_as_a_single_value() -> None:
    result = encode_sequence(
        {
            "sequence": "ACDE",
            "gene_names": "ABC1",
        }
    )

    assert result.provenance["gene_names"] == ["ABC1"]


def test_sequence_encoder_rejects_invalid_sequence() -> None:
    encoder = SequenceEncoder()

    with pytest.raises(ValueError, match="invalid residue codes"):
        encoder.encode("ACD-1")
