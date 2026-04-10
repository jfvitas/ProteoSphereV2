from __future__ import annotations

from core.library.summary_record import ProteinProteinSummaryRecord, SummaryRecordContext
from models.multimodal.ligand_encoder import encode_smiles
from models.multimodal.pair_ligand_context import (
    DEFAULT_PAIR_LIGAND_CONTEXT_DIM,
    DEFAULT_PAIR_LIGAND_CONTEXT_MODEL,
    PairLigandContext,
    build_pair_ligand_context,
)


def _pair_record() -> ProteinProteinSummaryRecord:
    return ProteinProteinSummaryRecord(
        summary_id="pair:P69905:P68871",
        protein_a_ref="protein:P69905",
        protein_b_ref="protein:P68871",
        interaction_type="protein complex",
        interaction_id="4HHB",
        interaction_refs=("4HHB",),
        evidence_refs=("IntAct:EBI-1",),
        organism_name="Homo sapiens",
        taxon_id=9606,
        physical_interaction=True,
        directionality="undirected",
        evidence_count=1,
        confidence=0.95,
        join_status="joined",
        join_reason="canonical pair anchor",
        context=SummaryRecordContext(storage_notes=("unit-test",)),
        notes=("frozen benchmark pair",),
    )


def test_pair_ligand_context_fuses_pair_and_ligand_modalities() -> None:
    pair = _pair_record()
    ligand = encode_smiles(
        "CCO",
        name="Ethanol",
        provenance={"run_id": "lig-001"},
    )

    result = build_pair_ligand_context(
        pair_context=pair,
        ligand_embedding=ligand,
        provenance={"request_id": "pair-ligand-fusion"},
    )

    assert result.model_name == DEFAULT_PAIR_LIGAND_CONTEXT_MODEL
    assert result.context_dim == DEFAULT_PAIR_LIGAND_CONTEXT_DIM
    assert result.modalities == ("pair", "ligand")
    assert result.available_modalities == ("pair", "ligand")
    assert result.missing_modalities == ()
    assert result.is_complete is True
    assert result.coverage == 1.0
    assert result.modality_weights == {"pair": 0.5, "ligand": 0.5}
    assert result.modality_token_counts["pair"] > 0
    assert result.modality_token_counts["ligand"] > 0
    assert len(result.fused_embedding) == DEFAULT_PAIR_LIGAND_CONTEXT_DIM
    assert len(result.feature_vector) == len(result.feature_names)
    assert result.metrics["coverage"] == 1.0
    assert result.metrics["pair_token_count"] == float(result.modality_token_counts["pair"])
    assert result.metrics["ligand_token_count"] == float(result.modality_token_counts["ligand"])
    assert result.provenance["request_id"] == "pair-ligand-fusion"
    assert result.provenance["pair_summary_id"] == pair.summary_id
    assert result.provenance["protein_a_ref"] == "protein:P69905"
    assert result.provenance["ligand_canonical_id"] == ligand.canonical_id
    assert result.provenance.get("ligand_id") is None
    assert result.provenance["modality_sources"] == {
        "pair": "protein_protein_summary",
        "ligand": ligand.source,
    }
    assert result.provenance["modality_models"]["ligand"] == ligand.model_name


def test_pair_ligand_context_keeps_missing_ligand_explicit() -> None:
    pair = _pair_record()

    result = PairLigandContext().fuse(pair_context=pair)

    assert result.available_modalities == ("pair",)
    assert result.missing_modalities == ("ligand",)
    assert result.is_complete is False
    assert result.modality_weights == {"pair": 1.0, "ligand": 0.0}
    assert result.modality_token_counts["pair"] > 0
    assert result.modality_token_counts["ligand"] == 0
    assert result.metrics["coverage"] == 0.5
    assert result.metrics["missing_count"] == 1.0
    assert result.provenance["pair_summary_id"] == pair.summary_id
    assert result.to_dict()["missing_modalities"] == ["ligand"]
