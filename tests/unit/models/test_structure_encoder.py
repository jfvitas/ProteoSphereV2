from __future__ import annotations

from types import SimpleNamespace

import pytest

from features.structure_graphs import (
    AtomGraph,
    AtomNode,
    GraphEdge,
    ResidueGraph,
    ResidueNode,
)
from models.multimodal.structure_encoder import (
    DEFAULT_STRUCTURE_ENCODER_DIM,
    DEFAULT_STRUCTURE_ENCODER_MODEL,
    StructureEncoder,
    encode_structure,
)


def test_structure_encoder_summarizes_single_graph_deterministically() -> None:
    graph = _structure_graphs()["atom"]

    result = encode_structure(graph, provenance={"request_id": "single-graph"})

    assert result.model_name == DEFAULT_STRUCTURE_ENCODER_MODEL
    assert result.pdb_id == "1ABC"
    assert result.token_ids == ("graph",)
    assert result.graph_kinds == ("atom",)
    assert result.graph_count == 1
    assert len(result.token_embeddings[0]) == DEFAULT_STRUCTURE_ENCODER_DIM
    assert len(result.pooled_embedding) == DEFAULT_STRUCTURE_ENCODER_DIM
    assert result.provenance["request_id"] == "single-graph"
    assert result.provenance["graph_count"] == 1
    assert result.provenance["graph_names"] == ["graph"]
    assert result.to_dict()["graph_count"] == 1


def test_structure_encoder_accepts_bundle_style_structure_graphs() -> None:
    encoder = StructureEncoder(embedding_dim=4)
    bundle = SimpleNamespace(
        structure_graphs=_structure_graphs(),
        provenance={"bundle": "yes"},
    )

    result = encoder.encode(bundle, provenance={"request_id": "bundle-test"})

    assert result.pdb_id == "1ABC"
    assert result.token_ids == ("atom", "residue")
    assert result.graph_kinds == ("atom", "residue")
    assert result.graph_count == 2
    assert all(len(row) == 4 for row in result.token_embeddings)
    assert len(result.pooled_embedding) == 4
    assert result.provenance["bundle"] == "yes"
    assert result.provenance["request_id"] == "bundle-test"
    assert result.provenance["graph_names"] == ["atom", "residue"]
    assert result.provenance["graph_provenance"]["atom"]["entry_title"] == "unit-test"


def test_structure_encoder_marks_mixed_pdb_bundles_explicitly() -> None:
    encoder = StructureEncoder()
    bundle = {
        "structure_graphs": _structure_graphs(residue_pdb_id="2XYZ"),
        "provenance": {"bundle": "mixed"},
    }

    result = encoder.encode(bundle)

    assert result.pdb_id == "mixed"
    assert result.provenance["pdb_id_is_ambiguous"] is True
    assert result.provenance["pdb_id_candidates"] == ["1ABC", "2XYZ"]
    assert result.provenance["graph_count"] == 2


def test_structure_encoder_rejects_empty_graph_inputs() -> None:
    encoder = StructureEncoder()

    with pytest.raises(ValueError, match="at least one graph"):
        encoder.encode({})


def _structure_graphs(*, residue_pdb_id: str = "1ABC") -> dict[str, AtomGraph | ResidueGraph]:
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
                provenance={"kind": "atom"},
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
                provenance={"kind": "atom"},
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
        pdb_id=residue_pdb_id,
        nodes=(
            ResidueNode(
                residue_key="A:1",
                pdb_id=residue_pdb_id,
                chain_id="A",
                residue_name="ALA",
                residue_number=1,
                sequence_position=1,
                one_letter_code="A",
                provenance={"kind": "residue"},
            ),
            ResidueNode(
                residue_key="B:1",
                pdb_id=residue_pdb_id,
                chain_id="B",
                residue_name="ASP",
                residue_number=1,
                sequence_position=1,
                one_letter_code="D",
                provenance={"kind": "residue"},
            ),
        ),
        edges=(
            GraphEdge(source="A:1", target="B:1", kind="sequence_adjacent"),
            GraphEdge(source="A:1", target="B:1", kind="spatial_contact", weight=4.0),
        ),
        provenance={"entry_title": "unit-test"},
    )
    return {"atom": atom_graph, "residue": residue_graph}
