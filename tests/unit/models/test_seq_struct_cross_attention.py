from __future__ import annotations

from types import SimpleNamespace

import pytest

from features.esm2_embeddings import ProteinEmbeddingResult
from models.multimodal.seq_struct_cross_attention import (
    DEFAULT_SEQ_STRUCT_CROSS_ATTENTION_DIM,
    DEFAULT_SEQ_STRUCT_CROSS_ATTENTION_MODEL,
    SeqStructCrossAttentionBaseline,
    cross_attend_sequence_structure,
)
from models.multimodal.structure_encoder import StructureEmbeddingResult


def test_cross_attention_baseline_forward_pass_from_feature_bundle() -> None:
    model = SeqStructCrossAttentionBaseline(attention_dim=3)
    bundle = SimpleNamespace(
        sequence_embedding=_sequence_embedding(),
        structure_embedding=_structure_embedding(),
        provenance={"bundle": "unit-test"},
    )

    result = model.forward(bundle, provenance={"request_id": "cross-attn-001"})

    assert result.model_name == DEFAULT_SEQ_STRUCT_CROSS_ATTENTION_MODEL
    assert result.attention_dim == 3
    assert result.modalities == ("sequence", "structure")
    assert result.available_modalities == ("sequence", "structure")
    assert result.missing_modalities == ()
    assert result.coverage == pytest.approx(1.0)
    assert result.is_complete is True
    assert result.sequence_token_ids == ("1", "2", "3")
    assert result.structure_token_ids == ("atom", "residue")
    assert result.sequence_attention_weights[0] == pytest.approx((0.5, 0.5))
    assert result.sequence_attention_weights[1] == pytest.approx((0.5, 0.5))
    assert result.sequence_attention_weights[2] == pytest.approx((0.5, 0.5))
    assert len(result.structure_attention_weights) == 2
    assert result.sequence_context_embedding == pytest.approx((1.0, 0.0, 0.0))
    assert len(result.structure_context_embedding) == 3
    assert len(result.fused_embedding) == 3
    assert result.metrics["coverage"] == pytest.approx(1.0)
    assert result.metrics["sequence_token_count"] == pytest.approx(3.0)
    assert result.metrics["structure_token_count"] == pytest.approx(2.0)
    assert result.provenance["bundle"] == "unit-test"
    assert result.provenance["request_id"] == "cross-attn-001"
    assert result.provenance["sequence_model_name"] == "sequence-test"
    assert result.provenance["structure_model_name"] == "structure-test"
    assert result.provenance["status"] == "ok"
    assert result.to_dict()["sequence_token_ids"] == ["1", "2", "3"]


def test_cross_attention_baseline_masks_queries_and_keys_explicitly() -> None:
    result = cross_attend_sequence_structure(
        sequence_embedding=_sequence_embedding(),
        structure_embedding=_structure_embedding(),
        sequence_token_mask=(True, False, True),
        structure_token_mask=(True, False),
        provenance={"request_id": "cross-attn-002"},
        attention_dim=3,
    )

    assert result.available_modalities == ("sequence", "structure")
    assert result.sequence_token_mask == (True, False, True)
    assert result.structure_token_mask == (True, False)
    assert result.sequence_attention_weights[0] == pytest.approx((1.0, 0.0))
    assert result.sequence_attention_weights[1] == pytest.approx((0.0, 0.0))
    assert result.sequence_attention_weights[2] == pytest.approx((1.0, 0.0))
    assert result.structure_attention_weights[0][1] == pytest.approx(0.0)
    assert result.structure_attention_weights[1] == pytest.approx((0.0, 0.0, 0.0))
    assert result.metrics["sequence_masked_count"] == pytest.approx(1.0)
    assert result.metrics["structure_masked_count"] == pytest.approx(1.0)
    assert result.metrics["sequence_masked_fraction"] == pytest.approx(1.0 / 3.0)
    assert result.metrics["structure_masked_fraction"] == pytest.approx(0.5)
    assert result.provenance["request_id"] == "cross-attn-002"
    assert result.provenance["status"] == "ok"


def test_cross_attention_baseline_reports_degraded_state_when_one_side_is_missing() -> None:
    result = cross_attend_sequence_structure(
        sequence_embedding=_sequence_embedding(),
        provenance={"request_id": "cross-attn-003"},
        attention_dim=DEFAULT_SEQ_STRUCT_CROSS_ATTENTION_DIM,
    )

    assert result.available_modalities == ("sequence",)
    assert result.missing_modalities == ("structure",)
    assert result.sequence_attention_weights == ((), (), ())
    assert result.structure_attention_weights == ()
    assert result.coverage == pytest.approx(0.5)
    assert result.provenance["status"] == "degraded"


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
        pooled_embedding=(1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0),
        cls_embedding=(1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0),
        provenance={"backend": "sequence-test"},
    )


def _structure_embedding() -> StructureEmbeddingResult:
    return StructureEmbeddingResult(
        pdb_id="1ABC",
        model_name="structure-test",
        embedding_dim=3,
        token_ids=("atom", "residue"),
        token_embeddings=((1.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
        pooled_embedding=(1.0, 0.0, 0.0),
        graph_kinds=("atom", "residue"),
        source="graph-summary",
        frozen=True,
        provenance={"backend": "structure-test"},
    )
