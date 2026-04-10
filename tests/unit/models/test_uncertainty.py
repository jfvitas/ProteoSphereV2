from __future__ import annotations

import pytest

from features.esm2_embeddings import ProteinEmbeddingResult
from models.multimodal.fusion_model import FusionModel
from models.multimodal.ligand_encoder import LigandEmbeddingResult
from models.multimodal.structure_encoder import StructureEmbeddingResult
from models.multimodal.uncertainty import (
    DEFAULT_UNCERTAINTY_HEAD_MODEL,
    UncertaintyHead,
    estimate_uncertainty,
)


def test_uncertainty_head_scores_complete_fusion_as_low_risk() -> None:
    fusion = FusionModel(fusion_dim=3).fuse(
        sequence_embedding=_sequence_embedding(),
        structure_embedding=_structure_embedding(),
        ligand_embedding=_ligand_embedding(),
    )

    result = estimate_uncertainty(fusion, provenance={"audit": "unit-test"})

    assert result.model_name == DEFAULT_UNCERTAINTY_HEAD_MODEL
    assert result.fusion_model_name == fusion.model_name
    assert result.modalities == ("sequence", "structure", "ligand")
    assert result.available_modalities == ("sequence", "structure", "ligand")
    assert result.missing_modalities == ()
    assert result.coverage == pytest.approx(1.0)
    assert 0.0 < result.uncertainty < 1.0
    assert result.confidence == pytest.approx(1.0 - result.uncertainty)
    assert result.metrics["coverage"] == pytest.approx(1.0)
    assert result.metrics["modality_spread"] > 0.0
    assert result.feature_names == (
        "fusion_coverage",
        "fusion_missing_fraction",
        "fusion_available_count",
        "fusion_missing_count",
        "sequence_weight",
        "structure_weight",
        "ligand_weight",
        "fusion_modality_spread",
        "fusion_fused_norm",
    )
    assert result.feature_vector[0] == pytest.approx(1.0)
    assert result.feature_vector[1] == pytest.approx(0.0)
    assert result.feature_vector[2] == pytest.approx(3.0)
    assert result.feature_vector[3] == pytest.approx(0.0)
    assert result.feature_vector[4:7] == pytest.approx((1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0))
    assert result.provenance["audit"] == "unit-test"
    assert result.provenance["fusion_model_name"] == fusion.model_name


def test_uncertainty_head_increases_when_modalities_are_missing() -> None:
    shared_embedding = _sequence_embedding(
        pooled=(1.0, 0.0, 0.0),
        backend="sequence-shared",
    )
    fusion = FusionModel(fusion_dim=3).fuse(
        sequence_embedding=shared_embedding,
        ligand_embedding=_ligand_embedding(
            pooled=(1.0, 0.0, 0.0),
            backend="ligand-shared",
        ),
    )

    result = UncertaintyHead().evaluate(fusion)

    assert result.available_modalities == ("sequence", "ligand")
    assert result.missing_modalities == ("structure",)
    assert result.coverage == pytest.approx(2.0 / 3.0)
    assert result.uncertainty == pytest.approx(1.0 / 3.0)
    assert result.confidence == pytest.approx(2.0 / 3.0)
    assert result.metrics["modality_spread"] == pytest.approx(0.0)
    assert result.feature_vector[:4] == pytest.approx((2.0 / 3.0, 1.0 / 3.0, 2.0, 1.0))
    assert result.feature_vector[4:7] == pytest.approx((0.5, 0.0, 0.5))


def test_uncertainty_head_to_dict_is_json_ready() -> None:
    fusion = FusionModel(fusion_dim=3).fuse(
        sequence_embedding=_sequence_embedding(),
        structure_embedding=_structure_embedding(),
        ligand_embedding=_ligand_embedding(),
    )

    payload = estimate_uncertainty(fusion, provenance={"audit": "unit-test"}).to_dict()

    assert payload["modalities"] == ["sequence", "structure", "ligand"]
    assert payload["available_modalities"] == ["sequence", "structure", "ligand"]
    assert payload["missing_modalities"] == []
    assert payload["feature_names"] == [
        "fusion_coverage",
        "fusion_missing_fraction",
        "fusion_available_count",
        "fusion_missing_count",
        "sequence_weight",
        "structure_weight",
        "ligand_weight",
        "fusion_modality_spread",
        "fusion_fused_norm",
    ]
    assert payload["feature_vector"] == pytest.approx(
        [
            1.0,
            0.0,
            3.0,
            0.0,
            1.0 / 3.0,
            1.0 / 3.0,
            1.0 / 3.0,
            payload["metrics"]["modality_spread"],
            payload["metrics"]["fused_l2_norm"],
        ]
    )
    assert payload["frozen"] is True
    assert payload["provenance"]["audit"] == "unit-test"
    assert payload["provenance"]["fusion_modalities"] == ["sequence", "structure", "ligand"]


def _sequence_embedding(
    *,
    pooled: tuple[float, float, float] = (1.0, 0.0, 0.0),
    backend: str = "sequence-test",
) -> ProteinEmbeddingResult:
    return ProteinEmbeddingResult(
        sequence="ACD",
        model_name="sequence-test",
        embedding_dim=3,
        residue_embeddings=(
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
        ),
        pooled_embedding=pooled,
        cls_embedding=(0.0, 0.0, 0.0),
        provenance={"backend": backend},
    )


def _structure_embedding() -> StructureEmbeddingResult:
    return StructureEmbeddingResult(
        pdb_id="1ABC",
        model_name="structure-test",
        embedding_dim=3,
        token_ids=("atom", "residue"),
        token_embeddings=((0.0, 1.0, 1.0), (1.0, 0.0, 1.0)),
        pooled_embedding=(0.0, 1.0, 0.0),
        graph_kinds=("atom", "residue"),
        source="graph-summary",
        frozen=True,
        provenance={"backend": "structure-test"},
    )


def _ligand_embedding(
    *,
    pooled: tuple[float, float, float] = (0.0, 0.0, 1.0),
    backend: str = "ligand-test",
) -> LigandEmbeddingResult:
    return LigandEmbeddingResult(
        canonical_id="ligand:test",
        ligand_id="L1",
        name="Test ligand",
        source="ligand-test",
        source_id="L1",
        smiles="CCO",
        inchi=None,
        inchikey=None,
        formula="C2H6O",
        charge=0,
        model_name="ligand-test",
        embedding_dim=3,
        token_ids=("smiles",),
        token_embeddings=((0.5, 0.25, 0.75),),
        pooled_embedding=pooled,
        source_kind="ligand_baseline",
        frozen=True,
        provenance={"backend": backend},
    )
