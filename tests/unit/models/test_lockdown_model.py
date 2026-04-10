from __future__ import annotations

from types import SimpleNamespace

import pytest

from features.esm2_embeddings import ESM2UnavailableError, ProteinEmbeddingResult
from features.rdkit_descriptors import LigandDescriptorResult
from features.structure_graphs import (
    AtomGraph,
    AtomNode,
    GraphEdge,
    ResidueGraph,
    ResidueNode,
)
from models.reference.lockdown_model import (
    LockdownReferenceModel,
    load_lockdown_model_spec,
)


class _FakeXGBoostPredictor:
    backend_name = "fake-xgboost"
    provenance = {"kind": "unit-test"}

    def predict(
        self,
        *,
        feature_names,
        feature_vector,
        target_names,
        uncertainty_enabled,
    ):
        total = round(sum(feature_vector), 6)
        predictions = {
            target: total + index for index, target in enumerate(target_names, start=1)
        }
        uncertainty = {
            target: round(0.05 * (index + 1), 3) for index, target in enumerate(target_names)
        }
        return {
            "backend_name": self.backend_name,
            "predictions": predictions,
            "uncertainty": uncertainty if uncertainty_enabled else {},
            "provenance": {
                "feature_count": len(feature_names),
                "uncertainty_enabled": uncertainty_enabled,
            },
        }


def test_load_lockdown_model_spec_reads_master_handoff_defaults() -> None:
    spec = load_lockdown_model_spec()

    assert spec.structure_encoder == "EGNN"
    assert spec.sequence_encoder == "ESM2"
    assert spec.fusion == "cross_attention"
    assert spec.head == "xgboost"
    assert spec.uncertainty_enabled is True
    assert spec.source_path == "master_handoff_package/01_LOCKDOWN_SPEC/models/default_model.yaml"


def test_lockdown_reference_model_wires_modalities_and_cross_attention_contract() -> None:
    feature_bundle = SimpleNamespace(
        structure_graphs=_structure_graphs(),
        sequence_embedding=_sequence_embedding(),
        ligand_descriptors=_ligand_descriptors(),
    )
    model = LockdownReferenceModel(xgboost_predictor=_FakeXGBoostPredictor())

    result = model.run_from_feature_bundle(
        feature_bundle,
        target_names=("affinity", "selectivity"),
    )

    assert result.blocked_stages == ()
    assert result.structure_path.status.requested_backend == "EGNN"
    assert result.structure_path.status.resolved_backend == "local-graph-summary"
    assert result.structure_path.status.contract_fidelity == "surrogate-shape-compatible"
    assert result.structure_path.token_ids == ("atom", "residue")

    assert result.sequence_path.sequence == "ACD"
    assert result.sequence_path.source_embedding is not None
    assert result.sequence_path.source_embedding.frozen is True
    assert result.sequence_path.status.contract_fidelity == "pretrained-frozen"
    assert result.sequence_path.token_ids == ("1", "2", "3")

    assert result.fusion.status.requested_backend == "cross_attention"
    assert result.fusion.status.resolved_backend == "local-cross-attention"
    assert result.fusion.status.backend_ready is True
    assert len(result.fusion.attention_matrix) == 2
    assert len(result.fusion.attention_matrix[0]) == 3
    assert result.fusion.gating_weights == {"sequence": 0.5, "structure": 0.5}
    for row in result.fusion.attention_matrix:
        assert sum(row) == pytest.approx(1.0)

    assert result.head.status.requested_backend == "xgboost"
    assert result.head.status.resolved_backend == "fake-xgboost"
    assert result.head.status.backend_ready is True
    assert "ligand_formal_charge" in result.head.feature_names
    assert len(result.head.feature_names) == len(result.head.feature_vector)
    assert [prediction.name for prediction in result.head.predictions] == [
        "affinity",
        "selectivity",
    ]
    assert result.head.predictions[0].value is not None
    assert result.head.predictions[0].uncertainty == pytest.approx(0.05)


def test_lockdown_reference_model_reports_blocked_sequence_and_head_backends() -> None:
    def _missing_esm2(sequence: str) -> ProteinEmbeddingResult:
        raise ESM2UnavailableError(
            f"Frozen ESM2 embeddings are unavailable for sequence length {len(sequence)}."
        )

    model = LockdownReferenceModel(sequence_embedder=_missing_esm2)
    result = model.run(
        structure_graphs=_structure_graphs(),
        protein_sequence="ACD",
        ligand_descriptors=_ligand_descriptors(),
    )

    assert result.structure_path.status.backend_ready is True
    assert result.sequence_path.status.backend_ready is False
    assert result.sequence_path.status.blocker is not None
    assert "unavailable" in result.sequence_path.status.blocker.reason

    assert result.fusion.status.backend_ready is False
    assert result.fusion.status.blocker is not None
    assert result.fusion.gating_weights == {"sequence": 0.0, "structure": 1.0}

    assert result.head.status.backend_ready is False
    assert result.head.status.blocker is not None
    assert all(prediction.value is None for prediction in result.head.predictions)
    assert result.blocked_stages == ("sequence_encoder", "fusion", "prediction_head")


def test_lockdown_reference_model_to_dict_exposes_stable_output_contract_shape() -> None:
    model = LockdownReferenceModel(xgboost_predictor=_FakeXGBoostPredictor())
    result = model.run(
        structure_graphs=_structure_graphs(),
        sequence_embedding=_sequence_embedding(),
        ligand_descriptors=_ligand_descriptors(),
        target_names=("affinity",),
    )

    payload = result.to_dict()

    assert set(payload) == {"spec", "structure_path", "sequence_path", "fusion", "head", "blockers"}
    assert payload["spec"]["uncertainty_enabled"] is True
    assert payload["structure_path"]["status"]["resolved_backend"] == "local-graph-summary"
    assert payload["sequence_path"]["source_embedding"]["frozen"] is True
    assert payload["fusion"]["structure_token_ids"] == ["atom", "residue"]
    assert payload["head"]["predictions"] == [
        {
            "name": "affinity",
            "value": pytest.approx(result.head.predictions[0].value),
            "uncertainty": pytest.approx(result.head.predictions[0].uncertainty),
        }
    ]
    assert payload["blockers"] == []


def _structure_graphs() -> dict[str, AtomGraph | ResidueGraph]:
    atom_graph = AtomGraph(
        pdb_id="1ABC",
        nodes=(
            AtomNode(
                atom_id="A1",
                pdb_id="1ABC",
                chain_id="A",
                residue_key="A:1",
                residue_name="ALA",
                residue_number=1,
                atom_name="CA",
                element="C",
                coordinates=(0.0, 0.0, 0.0),
            ),
            AtomNode(
                atom_id="B1",
                pdb_id="1ABC",
                chain_id="B",
                residue_key="B:1",
                residue_name="ASP",
                residue_number=1,
                atom_name="CA",
                element="C",
                coordinates=(0.0, 0.0, 2.0),
            ),
        ),
        edges=(
            GraphEdge(source="A1", target="A:1", kind="atom_to_residue"),
            GraphEdge(source="B1", target="B:1", kind="atom_to_residue"),
            GraphEdge(source="A1", target="B1", kind="spatial_contact", weight=2.0),
        ),
        provenance={"entry_title": "unit-test"},
    )
    residue_graph = ResidueGraph(
        pdb_id="1ABC",
        nodes=(
            ResidueNode(
                residue_key="A:1",
                pdb_id="1ABC",
                chain_id="A",
                residue_name="ALA",
                residue_number=1,
                sequence_position=1,
                one_letter_code="A",
            ),
            ResidueNode(
                residue_key="B:1",
                pdb_id="1ABC",
                chain_id="B",
                residue_name="ASP",
                residue_number=1,
                sequence_position=1,
                one_letter_code="D",
            ),
        ),
        edges=(
            GraphEdge(source="A:1", target="B:1", kind="spatial_contact", weight=4.0),
        ),
        provenance={"entry_title": "unit-test"},
    )
    return {"atom": atom_graph, "residue": residue_graph}


def _sequence_embedding() -> ProteinEmbeddingResult:
    return ProteinEmbeddingResult(
        sequence="ACD",
        model_name="facebook/esm2_t6_8M_UR50D",
        embedding_dim=3,
        residue_embeddings=(
            (1.0, 0.0, 1.0),
            (0.5, 1.0, 0.5),
            (0.0, 1.0, 1.5),
        ),
        pooled_embedding=(0.5, 2.0 / 3.0, 1.0),
        cls_embedding=(0.1, 0.2, 0.3),
        provenance={"backend": "fake-esm2"},
    )


def _ligand_descriptors() -> LigandDescriptorResult:
    return LigandDescriptorResult(
        smiles="CCO",
        canonical_smiles="CCO",
        descriptors={
            "formal_charge": 0,
            "logp": -0.3,
            "molecular_weight": 46.07,
            "tpsa": 20.23,
        },
        provenance={"backend": "fake-rdkit"},
    )
