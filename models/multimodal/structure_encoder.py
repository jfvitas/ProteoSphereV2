from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from features.structure_graphs import AtomGraph, ResidueGraph

DEFAULT_STRUCTURE_ENCODER_MODEL = "structure-baseline-v1"
DEFAULT_STRUCTURE_ENCODER_DIM = 8
AMBIGUOUS_STRUCTURE_PDB_ID = "mixed"


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _coerce_provenance(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError("provenance must be a mapping")
    return dict(value)


def _project_vector(values: Sequence[float], *, width: int) -> tuple[float, ...]:
    numbers = [float(value) for value in values]
    if width < 1:
        raise ValueError("embedding_dim must be >= 1")
    if not numbers:
        return tuple(0.0 for _ in range(width))
    if len(numbers) == width:
        return tuple(numbers)

    mean_value = sum(numbers) / len(numbers)
    min_value = min(numbers)
    max_value = max(numbers)
    l2_value = sum(value * value for value in numbers) ** 0.5
    summary = [mean_value, min_value, max_value, l2_value, numbers[0], numbers[-1]]
    while len(summary) < width:
        summary.append(mean_value)
    return tuple(summary[:width])


def _mean_rows(rows: Sequence[Sequence[float]]) -> tuple[float, ...]:
    if not rows:
        return ()
    width = len(rows[0])
    totals = [0.0] * width
    for row in rows:
        if len(row) != width:
            raise ValueError("embedding rows must share a common width")
        for index, value in enumerate(row):
            totals[index] += float(value)
    return tuple(total / len(rows) for total in totals)


def _edge_kind_count(graph: AtomGraph | ResidueGraph, *kinds: str) -> int:
    wanted = {kind.casefold() for kind in kinds}
    return sum(1 for edge in graph.edges if edge.kind.casefold() in wanted)


def _node_chain_count(graph: AtomGraph | ResidueGraph) -> int:
    seen: dict[str, None] = {}
    for node in graph.nodes:
        chain_id = _clean_text(getattr(node, "chain_id", ""))
        if chain_id:
            seen.setdefault(chain_id, None)
    return len(seen)


def _degree_summary(graph: AtomGraph | ResidueGraph) -> tuple[float, float]:
    if not graph.nodes:
        return 0.0, 0.0
    degree: dict[str, int] = {}
    for edge in graph.edges:
        degree[edge.source] = degree.get(edge.source, 0) + 1
        degree[edge.target] = degree.get(edge.target, 0) + 1
    if not degree:
        return 0.0, 0.0
    values = list(degree.values())
    return sum(values) / len(graph.nodes), float(max(values))


def _graph_features(graph: AtomGraph | ResidueGraph) -> tuple[float, ...]:
    node_count = len(graph.nodes)
    edge_count = len(graph.edges)
    spatial_contacts = _edge_kind_count(graph, "spatial_contact")
    bonded_or_sequential = _edge_kind_count(graph, "bond", "sequence_adjacent", "atom_to_residue")
    chain_count = _node_chain_count(graph)
    edge_density = float(edge_count) / float(node_count) if node_count else 0.0
    average_degree, max_degree = _degree_summary(graph)
    return (
        float(node_count),
        float(edge_count),
        float(spatial_contacts),
        float(bonded_or_sequential),
        float(chain_count),
        edge_density,
        average_degree,
        max_degree,
    )


def _graph_kind(graph: AtomGraph | ResidueGraph) -> str:
    if isinstance(graph, AtomGraph):
        return "atom"
    if isinstance(graph, ResidueGraph):
        return "residue"
    return type(graph).__name__.replace("Graph", "").lower() or "graph"


def _coerce_graph_mapping(value: Any) -> tuple[dict[str, AtomGraph | ResidueGraph], dict[str, Any]]:
    provenance: dict[str, Any] = {}
    source = value

    if isinstance(value, Mapping):
        provenance = _coerce_provenance(value.get("provenance"))
        if "structure_graphs" in value and isinstance(value["structure_graphs"], Mapping):
            source = value["structure_graphs"]
        elif "graphs" in value and isinstance(value["graphs"], Mapping):
            source = value["graphs"]
    elif hasattr(value, "structure_graphs"):
        structure_graphs = value.structure_graphs
        if not isinstance(structure_graphs, Mapping):
            raise TypeError(
                "value must expose structure_graphs as a mapping of AtomGraph or ResidueGraph"
            )
        source = structure_graphs
        provenance = _coerce_provenance(value.provenance) if hasattr(value, "provenance") else {}
    elif isinstance(value, (AtomGraph, ResidueGraph)):
        source = {"graph": value}
    else:
        raise TypeError(
            "value must be a mapping of structure graphs, a bundle with structure_graphs, "
            "or a single AtomGraph/ResidueGraph"
        )

    graphs: dict[str, AtomGraph | ResidueGraph] = {}
    for key, graph in source.items():
        if not isinstance(graph, (AtomGraph, ResidueGraph)):
            raise TypeError("structure_graphs entries must be AtomGraph or ResidueGraph instances")
        graphs[str(key)] = graph
    if not graphs:
        raise ValueError("structure_graphs must contain at least one graph")
    return graphs, provenance


@dataclass(frozen=True, slots=True)
class StructureEmbeddingResult:
    pdb_id: str
    model_name: str
    embedding_dim: int
    token_ids: tuple[str, ...]
    token_embeddings: tuple[tuple[float, ...], ...]
    pooled_embedding: tuple[float, ...]
    graph_kinds: tuple[str, ...]
    source: str = "graph-summary"
    frozen: bool = True
    provenance: dict[str, object] = field(default_factory=dict)

    @property
    def graph_count(self) -> int:
        return len(self.token_embeddings)

    def to_dict(self) -> dict[str, object]:
        return {
            "pdb_id": self.pdb_id,
            "model_name": self.model_name,
            "embedding_dim": self.embedding_dim,
            "graph_count": self.graph_count,
            "token_ids": list(self.token_ids),
            "token_embeddings": [list(row) for row in self.token_embeddings],
            "pooled_embedding": list(self.pooled_embedding),
            "graph_kinds": list(self.graph_kinds),
            "source": self.source,
            "frozen": self.frozen,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class StructureEncoder:
    model_name: str = DEFAULT_STRUCTURE_ENCODER_MODEL
    embedding_dim: int = DEFAULT_STRUCTURE_ENCODER_DIM
    source: str = "graph_summary"

    def __post_init__(self) -> None:
        model_name = _clean_text(self.model_name)
        if not model_name:
            raise ValueError("model_name must be a non-empty string")
        if self.embedding_dim < 1:
            raise ValueError("embedding_dim must be >= 1")
        object.__setattr__(self, "model_name", model_name)
        object.__setattr__(self, "source", _clean_text(self.source) or "graph_summary")

    def encode(
        self,
        value: Mapping[str, AtomGraph | ResidueGraph] | AtomGraph | ResidueGraph | Any,
        *,
        provenance: Mapping[str, Any] | None = None,
    ) -> StructureEmbeddingResult:
        graphs, inferred_provenance = _coerce_graph_mapping(value)
        graph_items = [(name, graph) for name, graph in sorted(graphs.items())]

        token_ids: list[str] = []
        token_embeddings: list[tuple[float, ...]] = []
        graph_kinds: list[str] = []
        node_counts: dict[str, int] = {}
        edge_counts: dict[str, int] = {}
        graph_provenance: dict[str, Any] = {}

        for name, graph in graph_items:
            token_ids.append(name)
            graph_kind = _graph_kind(graph)
            graph_kinds.append(graph_kind)
            node_counts[name] = len(graph.nodes)
            edge_counts[name] = len(graph.edges)
            graph_provenance[name] = dict(graph.provenance)
            token_embeddings.append(
                _project_vector(_graph_features(graph), width=self.embedding_dim)
            )

        provenance_payload = dict(inferred_provenance)
        if provenance is not None:
            provenance_payload.update(_coerce_provenance(provenance))
        provenance_payload.update(
            {
                "encoder": self.model_name,
                "source": self.source,
                "embedding_dim": self.embedding_dim,
                "graph_count": len(token_ids),
                "graph_kinds": list(graph_kinds),
                "graph_names": list(token_ids),
                "node_counts": node_counts,
                "edge_counts": edge_counts,
                "graph_provenance": graph_provenance,
                "notes": (
                    "Deterministic graph-summary surrogate used until a concrete EGNN encoder "
                    "is wired into the repository."
                ),
            }
        )

        graph_pdb_ids = tuple(
            sorted(
                {
                    _clean_text(getattr(graph, "pdb_id", ""))
                    for _, graph in graph_items
                    if _clean_text(getattr(graph, "pdb_id", ""))
                }
            )
        )
        if len(graph_pdb_ids) == 1:
            pdb_id = graph_pdb_ids[0]
        elif len(graph_pdb_ids) > 1:
            pdb_id = AMBIGUOUS_STRUCTURE_PDB_ID
            provenance_payload["pdb_id_candidates"] = list(graph_pdb_ids)
            provenance_payload["pdb_id_is_ambiguous"] = True
        else:
            pdb_id = "unknown"
            provenance_payload["pdb_id_candidates"] = []
            provenance_payload["pdb_id_is_ambiguous"] = False

        return StructureEmbeddingResult(
            pdb_id=pdb_id,
            model_name=self.model_name,
            embedding_dim=self.embedding_dim,
            token_ids=tuple(token_ids),
            token_embeddings=tuple(token_embeddings),
            pooled_embedding=_mean_rows(token_embeddings),
            graph_kinds=tuple(graph_kinds),
            source=self.source,
            frozen=True,
            provenance=provenance_payload,
        )

    def encode_many(
        self,
        values: Iterable[Mapping[str, AtomGraph | ResidueGraph] | AtomGraph | ResidueGraph | Any],
        *,
        provenance: Mapping[str, Any] | None = None,
    ) -> tuple[StructureEmbeddingResult, ...]:
        return tuple(self.encode(value, provenance=provenance) for value in values)


def encode_structure(
    value: Mapping[str, AtomGraph | ResidueGraph] | AtomGraph | ResidueGraph | Any,
    *,
    model_name: str = DEFAULT_STRUCTURE_ENCODER_MODEL,
    embedding_dim: int = DEFAULT_STRUCTURE_ENCODER_DIM,
    source: str = "graph_summary",
    provenance: Mapping[str, Any] | None = None,
) -> StructureEmbeddingResult:
    return StructureEncoder(
        model_name=model_name,
        embedding_dim=embedding_dim,
        source=source,
    ).encode(value, provenance=provenance)


__all__ = [
    "DEFAULT_STRUCTURE_ENCODER_DIM",
    "DEFAULT_STRUCTURE_ENCODER_MODEL",
    "StructureEmbeddingResult",
    "StructureEncoder",
    "encode_structure",
]
