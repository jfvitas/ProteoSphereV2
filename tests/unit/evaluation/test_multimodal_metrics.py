from __future__ import annotations

import pytest

from evaluation.multimodal.metrics import (
    DEFAULT_MULTIMODAL_METRICS_ID,
    MultimodalMetrics,
    summarize_multimodal_metrics,
)
from features.esm2_embeddings import ProteinEmbeddingResult
from models.multimodal.fusion_model import FusionModel
from models.multimodal.ligand_encoder import LigandEmbeddingResult
from models.multimodal.structure_encoder import StructureEmbeddingResult


def test_summarize_multimodal_metrics_reports_conservative_aggregate_values() -> None:
    full_result = _fused_result(
        sequence_embedding=_sequence_embedding(),
        structure_embedding=_structure_embedding(),
        ligand_embedding=_ligand_embedding(),
    )
    partial_result = _fused_result(
        sequence_embedding=_sequence_embedding(),
        ligand_embedding=_ligand_embedding(),
    )

    metrics = summarize_multimodal_metrics(
        (full_result, partial_result),
        provenance={"benchmark": "starter-wave"},
    )

    assert isinstance(metrics, MultimodalMetrics)
    assert metrics.metrics_id == DEFAULT_MULTIMODAL_METRICS_ID
    assert metrics.model_name == full_result.model_name
    assert metrics.fusion_dim == 3
    assert metrics.modalities == ("sequence", "structure", "ligand")
    assert metrics.example_count == 2
    assert metrics.complete_count == 1
    assert metrics.partial_count == 1
    assert metrics.complete_rate == pytest.approx(0.5)
    assert metrics.coverage_mean == pytest.approx((1.0 + (2.0 / 3.0)) / 2.0)
    assert metrics.coverage_min == pytest.approx(2.0 / 3.0)
    assert metrics.coverage_max == pytest.approx(1.0)
    assert metrics.available_count_mean == pytest.approx(2.5)
    assert metrics.missing_count_mean == pytest.approx(0.5)
    assert metrics.modality_coverage == {
        "sequence": pytest.approx(1.0),
        "structure": pytest.approx(0.5),
        "ligand": pytest.approx(1.0),
    }
    assert metrics.example_metrics[0].complete is True
    assert metrics.example_metrics[1].missing_modalities == ("structure",)
    assert metrics.provenance["benchmark"] == "starter-wave"
    assert metrics.provenance["example_count"] == 2
    assert metrics.to_dict()["example_count"] == 2


def test_summarize_multimodal_metrics_rejects_empty_or_mismatched_inputs() -> None:
    full_result = _fused_result(
        sequence_embedding=_sequence_embedding(),
        structure_embedding=_structure_embedding(),
        ligand_embedding=_ligand_embedding(),
    )

    with pytest.raises(ValueError, match="at least one FusionModelResult"):
        summarize_multimodal_metrics(())

    with pytest.raises(ValueError, match="same modality contract"):
        summarize_multimodal_metrics(
            (
                full_result,
                _fused_result(
                    sequence_embedding=_sequence_embedding(),
                    structure_embedding=_structure_embedding(),
                    ligand_embedding=_ligand_embedding(),
                    modalities=("sequence", "ligand"),
                ),
            )
        )


def _fused_result(*, modalities=("sequence", "structure", "ligand"), **kwargs):
    return FusionModel(fusion_dim=3, modalities=modalities).fuse(**kwargs)


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
