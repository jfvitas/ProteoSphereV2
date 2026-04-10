from __future__ import annotations

from types import SimpleNamespace

import pytest

from features.esm2_embeddings import ProteinEmbeddingResult
from models.multimodal.fusion_model import FusionModel, fuse_modalities
from models.multimodal.ligand_encoder import LigandEmbeddingResult
from models.multimodal.structure_encoder import StructureEmbeddingResult


def test_fusion_model_builds_full_modal_fusion_from_feature_bundle() -> None:
    model = FusionModel(fusion_dim=3)
    bundle = SimpleNamespace(
        sequence_embedding=_sequence_embedding(),
        structure_embedding=_structure_embedding(),
        ligand_embedding=_ligand_embedding(),
        provenance={"bundle": "unit-test"},
    )

    result = model.fuse(bundle, provenance={"request_id": "fusion-001"})

    assert result.model_name == "multimodal-fusion-baseline-v1"
    assert result.modalities == ("sequence", "structure", "ligand")
    assert result.available_modalities == ("sequence", "structure", "ligand")
    assert result.missing_modalities == ()
    assert result.available_count == 3
    assert result.missing_count == 0
    assert result.coverage == pytest.approx(1.0)
    assert result.is_complete is True
    assert result.modality_token_counts == {
        "sequence": 3,
        "structure": 2,
        "ligand": 1,
    }
    assert result.modality_token_ids == {
        "sequence": ("1", "2", "3"),
        "structure": ("atom", "residue"),
        "ligand": ("smiles",),
    }
    assert result.modality_weights == {
        "sequence": pytest.approx(1.0 / 3.0),
        "structure": pytest.approx(1.0 / 3.0),
        "ligand": pytest.approx(1.0 / 3.0),
    }
    assert result.fused_embedding == pytest.approx((1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0))
    assert len(result.feature_names) == len(result.feature_vector)
    assert result.feature_names[:5] == (
        "sequence_present",
        "sequence_token_count",
        "sequence_pooled_0",
        "sequence_pooled_1",
        "sequence_pooled_2",
    )
    assert result.feature_names[-3:] == ("fused_0", "fused_1", "fused_2")
    assert result.metrics["coverage"] == pytest.approx(1.0)
    assert result.metrics["feature_vector_length"] == pytest.approx(len(result.feature_vector))
    assert result.provenance["bundle"] == "unit-test"
    assert result.provenance["request_id"] == "fusion-001"
    assert result.provenance["modality_provenance"]["sequence"]["backend"] == "sequence-test"


def test_fusion_model_reports_missing_modalities_and_weights_for_partial_inputs() -> None:
    result = fuse_modalities(
        sequence_embedding=_sequence_embedding(),
        ligand_embedding=_ligand_embedding(),
        provenance={"request_id": "fusion-002"},
        fusion_dim=3,
    )

    assert result.available_modalities == ("sequence", "ligand")
    assert result.missing_modalities == ("structure",)
    assert result.modality_weights == {
        "sequence": pytest.approx(0.5),
        "structure": 0.0,
        "ligand": pytest.approx(0.5),
    }
    assert result.fused_embedding == pytest.approx((0.5, 0.0, 0.5))
    assert result.modality_embeddings["sequence"] == (1.0, 0.0, 0.0)
    assert "structure" not in result.modality_embeddings
    assert result.metrics["available_count"] == pytest.approx(2.0)
    assert result.metrics["missing_count"] == pytest.approx(1.0)
    assert result.metrics["coverage"] == pytest.approx(2.0 / 3.0)


def test_fusion_model_to_dict_is_json_ready() -> None:
    result = FusionModel(fusion_dim=3).fuse(
        sequence_embedding=_sequence_embedding(),
        structure_embedding=_structure_embedding(),
        ligand_embedding=_ligand_embedding(),
    )

    payload = result.to_dict()

    assert payload["modalities"] == ["sequence", "structure", "ligand"]
    assert payload["available_modalities"] == ["sequence", "structure", "ligand"]
    assert payload["missing_modalities"] == []
    assert payload["modality_token_ids"]["sequence"] == ["1", "2", "3"]
    assert payload["modality_embeddings"]["ligand"] == [0.0, 0.0, 1.0]
    assert payload["fused_embedding"] == pytest.approx([1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0])
    assert payload["frozen"] is True
    assert payload["provenance"]["modality_models"]["ligand"] == "ligand-test"


def _sequence_embedding() -> ProteinEmbeddingResult:
    return ProteinEmbeddingResult(
        sequence="ACD",
        model_name="sequence-test",
        embedding_dim=3,
        residue_embeddings=(
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
        ),
        pooled_embedding=(1.0, 0.0, 0.0),
        cls_embedding=(0.0, 0.0, 0.0),
        provenance={"backend": "sequence-test"},
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


def _ligand_embedding() -> LigandEmbeddingResult:
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
        pooled_embedding=(0.0, 0.0, 1.0),
        source_kind="ligand_baseline",
        frozen=True,
        provenance={"backend": "ligand-test"},
    )
