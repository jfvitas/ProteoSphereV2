from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from features.esm2_embeddings import (
    ESM2UnavailableError,
    ProteinEmbeddingResult,
    embed_sequence,
)
from features.rdkit_descriptors import LigandDescriptorResult
from features.structure_graphs import AtomGraph, ResidueGraph

Scalar = str | int | float | bool
StructureGraphs = Mapping[str, AtomGraph | ResidueGraph]
SequenceEmbedder = Any
XGBoostStylePredictor = Any


@dataclass(frozen=True, slots=True)
class LockdownModelBlocker:
    stage: str
    requested_backend: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "stage": self.stage,
            "requested_backend": self.requested_backend,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class LockdownModelSpec:
    structure_encoder: str
    sequence_encoder: str
    fusion: str
    head: str
    uncertainty_enabled: bool
    source_path: str
    config: dict[str, Scalar]

    def to_dict(self) -> dict[str, object]:
        return {
            "structure_encoder": self.structure_encoder,
            "sequence_encoder": self.sequence_encoder,
            "fusion": self.fusion,
            "head": self.head,
            "uncertainty_enabled": self.uncertainty_enabled,
            "source_path": self.source_path,
            "config": dict(self.config),
        }


@dataclass(frozen=True, slots=True)
class LockdownBackendStatus:
    stage: str
    requested_backend: str
    resolved_backend: str
    backend_ready: bool
    contract_fidelity: str
    provenance: dict[str, object] = field(default_factory=dict)
    blocker: LockdownModelBlocker | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "stage": self.stage,
            "requested_backend": self.requested_backend,
            "resolved_backend": self.resolved_backend,
            "backend_ready": self.backend_ready,
            "contract_fidelity": self.contract_fidelity,
            "provenance": dict(self.provenance),
            "blocker": self.blocker.to_dict() if self.blocker is not None else None,
        }


@dataclass(frozen=True, slots=True)
class StructurePathOutput:
    token_ids: tuple[str, ...]
    token_embeddings: tuple[tuple[float, ...], ...]
    pooled_embedding: tuple[float, ...]
    status: LockdownBackendStatus

    def to_dict(self) -> dict[str, object]:
        return {
            "token_ids": list(self.token_ids),
            "token_embeddings": [list(row) for row in self.token_embeddings],
            "pooled_embedding": list(self.pooled_embedding),
            "status": self.status.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class SequencePathOutput:
    sequence: str
    token_ids: tuple[str, ...]
    token_embeddings: tuple[tuple[float, ...], ...]
    pooled_embedding: tuple[float, ...]
    source_embedding: ProteinEmbeddingResult | None
    status: LockdownBackendStatus

    def to_dict(self) -> dict[str, object]:
        return {
            "sequence": self.sequence,
            "token_ids": list(self.token_ids),
            "token_embeddings": [list(row) for row in self.token_embeddings],
            "pooled_embedding": list(self.pooled_embedding),
            "source_embedding": (
                self.source_embedding.to_dict() if self.source_embedding is not None else None
            ),
            "status": self.status.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class CrossAttentionFusionOutput:
    fused_embedding: tuple[float, ...]
    fused_token_embeddings: tuple[tuple[float, ...], ...]
    attention_matrix: tuple[tuple[float, ...], ...]
    structure_token_ids: tuple[str, ...]
    sequence_token_ids: tuple[str, ...]
    gating_weights: dict[str, float]
    status: LockdownBackendStatus

    def to_dict(self) -> dict[str, object]:
        return {
            "fused_embedding": list(self.fused_embedding),
            "fused_token_embeddings": [list(row) for row in self.fused_token_embeddings],
            "attention_matrix": [list(row) for row in self.attention_matrix],
            "structure_token_ids": list(self.structure_token_ids),
            "sequence_token_ids": list(self.sequence_token_ids),
            "gating_weights": dict(self.gating_weights),
            "status": self.status.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class PredictionTargetOutput:
    name: str
    value: float | None
    uncertainty: float | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "value": self.value,
            "uncertainty": self.uncertainty,
        }


@dataclass(frozen=True, slots=True)
class PredictionHeadOutput:
    feature_names: tuple[str, ...]
    feature_vector: tuple[float, ...]
    predictions: tuple[PredictionTargetOutput, ...]
    status: LockdownBackendStatus

    def to_dict(self) -> dict[str, object]:
        return {
            "feature_names": list(self.feature_names),
            "feature_vector": list(self.feature_vector),
            "predictions": [prediction.to_dict() for prediction in self.predictions],
            "status": self.status.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class LockdownReferenceModelResult:
    spec: LockdownModelSpec
    structure_path: StructurePathOutput
    sequence_path: SequencePathOutput
    fusion: CrossAttentionFusionOutput
    head: PredictionHeadOutput
    blockers: tuple[LockdownModelBlocker, ...]

    @property
    def blocked_stages(self) -> tuple[str, ...]:
        return tuple(blocker.stage for blocker in self.blockers)

    def to_dict(self) -> dict[str, object]:
        return {
            "spec": self.spec.to_dict(),
            "structure_path": self.structure_path.to_dict(),
            "sequence_path": self.sequence_path.to_dict(),
            "fusion": self.fusion.to_dict(),
            "head": self.head.to_dict(),
            "blockers": [blocker.to_dict() for blocker in self.blockers],
        }


def load_lockdown_model_spec(repo_root: str | Path | None = None) -> LockdownModelSpec:
    root = Path(repo_root or Path(__file__).resolve().parents[2]).resolve()
    path = root / "master_handoff_package" / "01_LOCKDOWN_SPEC" / "models" / "default_model.yaml"
    config = _parse_simple_yaml_mapping(path)
    structure_encoder = str(config.get("structure_encoder", "")).strip()
    sequence_encoder = str(config.get("sequence_encoder", "")).strip()
    fusion = str(config.get("fusion", "")).strip()
    head = str(config.get("head", "")).strip()
    if not structure_encoder or not sequence_encoder or not fusion or not head:
        raise ValueError(f"Locked model spec is missing required fields in {path}")
    return LockdownModelSpec(
        structure_encoder=structure_encoder,
        sequence_encoder=sequence_encoder,
        fusion=fusion,
        head=head,
        uncertainty_enabled=bool(config.get("uncertainty", False)),
        source_path=_relative_path(root, path),
        config=config,
    )


class LockdownReferenceModel:
    def __init__(
        self,
        *,
        repo_root: str | Path | None = None,
        sequence_embedder: SequenceEmbedder | None = None,
        xgboost_predictor: XGBoostStylePredictor | None = None,
        fusion_width: int = 6,
    ) -> None:
        self.repo_root = Path(repo_root or Path(__file__).resolve().parents[2]).resolve()
        self.spec = load_lockdown_model_spec(self.repo_root)
        self.sequence_embedder = sequence_embedder or embed_sequence
        self.xgboost_predictor = xgboost_predictor
        self.fusion_width = max(4, int(fusion_width))

    def run(
        self,
        *,
        structure_graphs: StructureGraphs,
        sequence_embedding: ProteinEmbeddingResult | None = None,
        protein_sequence: str | None = None,
        ligand_descriptors: LigandDescriptorResult | None = None,
        target_names: Sequence[str] = ("affinity",),
    ) -> LockdownReferenceModelResult:
        structure_path = self._encode_structure(structure_graphs)
        sequence_path = self._encode_sequence(
            sequence_embedding=sequence_embedding,
            protein_sequence=protein_sequence,
        )
        fusion = self._fuse_modalities(structure_path=structure_path, sequence_path=sequence_path)
        head = self._run_prediction_head(
            structure_path=structure_path,
            sequence_path=sequence_path,
            fusion=fusion,
            ligand_descriptors=ligand_descriptors,
            target_names=target_names,
        )

        blockers = tuple(
            status.blocker
            for status in (
                structure_path.status,
                sequence_path.status,
                fusion.status,
                head.status,
            )
            if status.blocker is not None
        )
        return LockdownReferenceModelResult(
            spec=self.spec,
            structure_path=structure_path,
            sequence_path=sequence_path,
            fusion=fusion,
            head=head,
            blockers=blockers,
        )

    def run_from_feature_bundle(
        self,
        feature_bundle: Any,
        *,
        protein_sequence: str | None = None,
        target_names: Sequence[str] = ("affinity",),
    ) -> LockdownReferenceModelResult:
        structure_graphs = getattr(feature_bundle, "structure_graphs", None)
        if not isinstance(structure_graphs, Mapping):
            raise TypeError("feature_bundle must expose a structure_graphs mapping")
        return self.run(
            structure_graphs=structure_graphs,
            sequence_embedding=getattr(feature_bundle, "sequence_embedding", None),
            protein_sequence=protein_sequence,
            ligand_descriptors=getattr(feature_bundle, "ligand_descriptors", None),
            target_names=target_names,
        )

    def _encode_structure(self, structure_graphs: StructureGraphs) -> StructurePathOutput:
        graph_items = [
            (name, graph)
            for name, graph in sorted(structure_graphs.items())
            if isinstance(graph, (AtomGraph, ResidueGraph))
        ]
        if not graph_items:
            blocker = LockdownModelBlocker(
                stage="structure_encoder",
                requested_backend=self.spec.structure_encoder,
                reason="No extracted structure graphs were provided to the locked model backend.",
            )
            return StructurePathOutput(
                token_ids=(),
                token_embeddings=(),
                pooled_embedding=(),
                status=LockdownBackendStatus(
                    stage="structure_encoder",
                    requested_backend=self.spec.structure_encoder,
                    resolved_backend="unavailable",
                    backend_ready=False,
                    contract_fidelity="missing-input",
                    provenance={"graph_types": []},
                    blocker=blocker,
                ),
            )

        token_ids: list[str] = []
        token_embeddings: list[tuple[float, ...]] = []
        graph_types: list[str] = []
        node_counts: dict[str, int] = {}
        edge_counts: dict[str, int] = {}
        for name, graph in graph_items:
            graph_types.append(name)
            node_counts[name] = len(graph.nodes)
            edge_counts[name] = len(graph.edges)
            token_ids.append(name)
            token_embeddings.append(_graph_to_embedding(graph, width=self.fusion_width))

        return StructurePathOutput(
            token_ids=tuple(token_ids),
            token_embeddings=tuple(token_embeddings),
            pooled_embedding=_mean_rows(token_embeddings),
            status=LockdownBackendStatus(
                stage="structure_encoder",
                requested_backend=self.spec.structure_encoder,
                resolved_backend="local-graph-summary",
                backend_ready=True,
                contract_fidelity="surrogate-shape-compatible",
                provenance={
                    "graph_types": graph_types,
                    "node_counts": node_counts,
                    "edge_counts": edge_counts,
                    "notes": (
                        "A deterministic graph-summary surrogate is used locally until a concrete "
                        "EGNN stack is wired into the repository."
                    ),
                },
            ),
        )

    def _encode_sequence(
        self,
        *,
        sequence_embedding: ProteinEmbeddingResult | None,
        protein_sequence: str | None,
    ) -> SequencePathOutput:
        embedding = sequence_embedding
        if embedding is None and protein_sequence:
            try:
                embedding = self.sequence_embedder(protein_sequence)
            except ESM2UnavailableError as exc:
                blocker = LockdownModelBlocker(
                    stage="sequence_encoder",
                    requested_backend=self.spec.sequence_encoder,
                    reason=str(exc),
                )
                return SequencePathOutput(
                    sequence=str(protein_sequence or ""),
                    token_ids=(),
                    token_embeddings=(),
                    pooled_embedding=(),
                    source_embedding=None,
                    status=LockdownBackendStatus(
                        stage="sequence_encoder",
                        requested_backend=self.spec.sequence_encoder,
                        resolved_backend="unavailable",
                        backend_ready=False,
                        contract_fidelity="missing-backend",
                        provenance={"source": "embed_sequence"},
                        blocker=blocker,
                    ),
                )

        if embedding is None:
            blocker = LockdownModelBlocker(
                stage="sequence_encoder",
                requested_backend=self.spec.sequence_encoder,
                reason="No frozen ESM2 embedding or protein sequence was provided.",
            )
            return SequencePathOutput(
                sequence="",
                token_ids=(),
                token_embeddings=(),
                pooled_embedding=(),
                source_embedding=None,
                status=LockdownBackendStatus(
                    stage="sequence_encoder",
                    requested_backend=self.spec.sequence_encoder,
                    resolved_backend="unavailable",
                    backend_ready=False,
                    contract_fidelity="missing-input",
                    provenance={},
                    blocker=blocker,
                ),
            )

        token_embeddings = tuple(
            _project_vector(row, width=self.fusion_width) for row in embedding.residue_embeddings
        )
        token_ids = tuple(str(index) for index in range(1, len(token_embeddings) + 1))
        pooled_embedding = _project_vector(embedding.pooled_embedding, width=self.fusion_width)
        return SequencePathOutput(
            sequence=embedding.sequence,
            token_ids=token_ids,
            token_embeddings=token_embeddings,
            pooled_embedding=pooled_embedding,
            source_embedding=embedding,
            status=LockdownBackendStatus(
                stage="sequence_encoder",
                requested_backend=self.spec.sequence_encoder,
                resolved_backend=embedding.model_name,
                backend_ready=True,
                contract_fidelity="pretrained-frozen",
                provenance={
                    "source": embedding.source,
                    "frozen": embedding.frozen,
                    "embedding_dim": embedding.embedding_dim,
                    "residue_count": embedding.residue_count,
                    "upstream_provenance": dict(embedding.provenance),
                },
            ),
        )

    def _fuse_modalities(
        self,
        *,
        structure_path: StructurePathOutput,
        sequence_path: SequencePathOutput,
    ) -> CrossAttentionFusionOutput:
        structure_ready = structure_path.status.backend_ready and bool(
            structure_path.token_embeddings
        )
        sequence_ready = sequence_path.status.backend_ready and bool(
            sequence_path.token_embeddings
        )
        gating_weights = _gating_weights(
            structure_ready=structure_ready,
            sequence_ready=sequence_ready,
        )

        if structure_ready and sequence_ready:
            attention_rows: list[tuple[float, ...]] = []
            fused_tokens: list[tuple[float, ...]] = []
            for structure_token in structure_path.token_embeddings:
                scores = tuple(
                    _dot(structure_token, sequence_token) / float(self.fusion_width)
                    for sequence_token in sequence_path.token_embeddings
                )
                weights = _softmax(scores)
                attended_sequence = _weighted_mean(sequence_path.token_embeddings, weights)
                fused_tokens.append(
                    tuple(
                        (left + right) / 2.0
                        for left, right in zip(structure_token, attended_sequence, strict=True)
                    )
                )
                attention_rows.append(weights)

            return CrossAttentionFusionOutput(
                fused_embedding=_mean_rows(fused_tokens),
                fused_token_embeddings=tuple(fused_tokens),
                attention_matrix=tuple(attention_rows),
                structure_token_ids=structure_path.token_ids,
                sequence_token_ids=sequence_path.token_ids,
                gating_weights=gating_weights,
                status=LockdownBackendStatus(
                    stage="fusion",
                    requested_backend=self.spec.fusion,
                    resolved_backend="local-cross-attention",
                    backend_ready=True,
                    contract_fidelity="surrogate-behavioral",
                    provenance={
                        "attention_rows": len(attention_rows),
                        "attention_cols": len(sequence_path.token_ids),
                        "notes": (
                            "This local backend implements deterministic attention-style fusion "
                            "over structure and frozen-sequence embeddings; it is not a trained "
                            "multimodal transformer."
                        ),
                    },
                ),
            )

        available_embeddings = [
            *structure_path.token_embeddings,
            *sequence_path.token_embeddings,
        ]
        blocker = LockdownModelBlocker(
            stage="fusion",
            requested_backend=self.spec.fusion,
            reason=(
                "Cross-attention fusion requires both structure and sequence paths; falling back "
                "to the available modality summaries."
            ),
        )
        return CrossAttentionFusionOutput(
            fused_embedding=_mean_rows(available_embeddings) if available_embeddings else (),
            fused_token_embeddings=tuple(available_embeddings),
            attention_matrix=(),
            structure_token_ids=structure_path.token_ids,
            sequence_token_ids=sequence_path.token_ids,
            gating_weights=gating_weights,
            status=LockdownBackendStatus(
                stage="fusion",
                requested_backend=self.spec.fusion,
                resolved_backend="local-single-modality-fallback",
                backend_ready=False,
                contract_fidelity="degraded-fallback",
                provenance={
                    "structure_ready": structure_ready,
                    "sequence_ready": sequence_ready,
                },
                blocker=blocker,
            ),
        )

    def _run_prediction_head(
        self,
        *,
        structure_path: StructurePathOutput,
        sequence_path: SequencePathOutput,
        fusion: CrossAttentionFusionOutput,
        ligand_descriptors: LigandDescriptorResult | None,
        target_names: Sequence[str],
    ) -> PredictionHeadOutput:
        feature_names, feature_vector = _build_head_features(
            structure_path=structure_path,
            sequence_path=sequence_path,
            fusion=fusion,
            ligand_descriptors=ligand_descriptors,
        )
        targets = tuple(str(name) for name in target_names) or ("affinity",)

        if self.xgboost_predictor is None:
            blocker = LockdownModelBlocker(
                stage="prediction_head",
                requested_backend=self.spec.head,
                reason=(
                    "The repository can materialize the XGBoost-style feature contract, but no "
                    "trained tree backend is wired into the locked reference model."
                ),
            )
            return PredictionHeadOutput(
                feature_names=feature_names,
                feature_vector=feature_vector,
                predictions=tuple(
                    PredictionTargetOutput(name=target, value=None) for target in targets
                ),
                status=LockdownBackendStatus(
                    stage="prediction_head",
                    requested_backend=self.spec.head,
                    resolved_backend="feature-vector-contract-only",
                    backend_ready=False,
                    contract_fidelity="contract-without-trained-backend",
                    provenance={
                        "feature_count": len(feature_names),
                        "uncertainty_enabled": self.spec.uncertainty_enabled,
                    },
                    blocker=blocker,
                ),
            )

        predictor_output = _invoke_predictor(
            self.xgboost_predictor,
            feature_names=feature_names,
            feature_vector=feature_vector,
            target_names=targets,
            uncertainty_enabled=self.spec.uncertainty_enabled,
        )
        predictions = tuple(
            PredictionTargetOutput(
                name=target,
                value=predictor_output["predictions"].get(target),
                uncertainty=predictor_output["uncertainty"].get(target),
            )
            for target in targets
        )
        return PredictionHeadOutput(
            feature_names=feature_names,
            feature_vector=feature_vector,
            predictions=predictions,
            status=LockdownBackendStatus(
                stage="prediction_head",
                requested_backend=self.spec.head,
                resolved_backend=predictor_output["backend_name"],
                backend_ready=True,
                contract_fidelity="predictive-contract",
                provenance={
                    "feature_count": len(feature_names),
                    "uncertainty_enabled": self.spec.uncertainty_enabled,
                    "predictor_provenance": predictor_output["provenance"],
                },
            ),
        )


def run_lockdown_reference_model(
    *,
    structure_graphs: StructureGraphs,
    sequence_embedding: ProteinEmbeddingResult | None = None,
    protein_sequence: str | None = None,
    ligand_descriptors: LigandDescriptorResult | None = None,
    target_names: Sequence[str] = ("affinity",),
    repo_root: str | Path | None = None,
    sequence_embedder: SequenceEmbedder | None = None,
    xgboost_predictor: XGBoostStylePredictor | None = None,
) -> LockdownReferenceModelResult:
    return LockdownReferenceModel(
        repo_root=repo_root,
        sequence_embedder=sequence_embedder,
        xgboost_predictor=xgboost_predictor,
    ).run(
        structure_graphs=structure_graphs,
        sequence_embedding=sequence_embedding,
        protein_sequence=protein_sequence,
        ligand_descriptors=ligand_descriptors,
        target_names=target_names,
    )


def _build_head_features(
    *,
    structure_path: StructurePathOutput,
    sequence_path: SequencePathOutput,
    fusion: CrossAttentionFusionOutput,
    ligand_descriptors: LigandDescriptorResult | None,
) -> tuple[tuple[str, ...], tuple[float, ...]]:
    feature_names: list[str] = []
    feature_values: list[float] = []

    def extend(prefix: str, values: Sequence[float]) -> None:
        for index, value in enumerate(values):
            feature_names.append(f"{prefix}_{index}")
            feature_values.append(float(value))

    extend("structure_pooled", structure_path.pooled_embedding)
    extend("sequence_pooled", sequence_path.pooled_embedding)
    extend("fusion_pooled", fusion.fused_embedding)
    for name, value in sorted(fusion.gating_weights.items()):
        feature_names.append(f"fusion_gate_{name}")
        feature_values.append(float(value))

    if ligand_descriptors is not None:
        for key, value in sorted(ligand_descriptors.descriptors.items()):
            feature_names.append(f"ligand_{key}")
            feature_values.append(float(value))

    return tuple(feature_names), tuple(feature_values)


def _invoke_predictor(
    predictor: XGBoostStylePredictor,
    *,
    feature_names: tuple[str, ...],
    feature_vector: tuple[float, ...],
    target_names: tuple[str, ...],
    uncertainty_enabled: bool,
) -> dict[str, Any]:
    if callable(predictor):
        raw = predictor(
            feature_names=feature_names,
            feature_vector=feature_vector,
            target_names=target_names,
            uncertainty_enabled=uncertainty_enabled,
        )
    elif hasattr(predictor, "predict"):
        raw = predictor.predict(
            feature_names=feature_names,
            feature_vector=feature_vector,
            target_names=target_names,
            uncertainty_enabled=uncertainty_enabled,
        )
    else:
        raise TypeError("xgboost_predictor must be callable or expose a predict(...) method")

    backend_name = getattr(predictor, "backend_name", type(predictor).__name__)
    provenance = getattr(predictor, "provenance", {})

    if isinstance(raw, Mapping) and "predictions" in raw:
        predictions = {
            str(name): _optional_float(value)
            for name, value in dict(raw["predictions"]).items()
        }
        uncertainty = {
            str(name): _optional_float(value)
            for name, value in dict(raw.get("uncertainty", {})).items()
        }
        return {
            "backend_name": str(raw.get("backend_name") or backend_name),
            "predictions": {name: predictions.get(name) for name in target_names},
            "uncertainty": {name: uncertainty.get(name) for name in target_names},
            "provenance": dict(raw.get("provenance", provenance)),
        }

    if isinstance(raw, Mapping):
        predictions = {name: _optional_float(raw.get(name)) for name in target_names}
        return {
            "backend_name": str(backend_name),
            "predictions": predictions,
            "uncertainty": {name: None for name in target_names},
            "provenance": dict(provenance),
        }

    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        values = list(raw)
        if len(values) != len(target_names):
            raise ValueError("Predictor sequence output must align with target_names")
        return {
            "backend_name": str(backend_name),
            "predictions": {
                target: _optional_float(value)
                for target, value in zip(target_names, values, strict=True)
            },
            "uncertainty": {name: None for name in target_names},
            "provenance": dict(provenance),
        }

    if len(target_names) != 1:
        raise ValueError("Scalar predictor outputs are only valid for a single target")
    target = target_names[0]
    return {
        "backend_name": str(backend_name),
        "predictions": {target: _optional_float(raw)},
        "uncertainty": {target: None},
        "provenance": dict(provenance),
    }


def _graph_to_embedding(graph: AtomGraph | ResidueGraph, *, width: int) -> tuple[float, ...]:
    node_count = len(graph.nodes)
    edge_count = len(graph.edges)
    spatial_contacts = sum(1 for edge in graph.edges if edge.kind == "spatial_contact")
    sequential_or_bonded = sum(
        1 for edge in graph.edges if edge.kind in {"bond", "sequence_adjacent", "atom_to_residue"}
    )
    chain_ids = {
        getattr(node, "chain_id", "")
        for node in graph.nodes
        if str(getattr(node, "chain_id", "")).strip()
    }
    base = (
        float(node_count),
        float(edge_count),
        float(spatial_contacts),
        float(sequential_or_bonded),
        float(len(chain_ids)),
        float(edge_count) / float(node_count) if node_count else 0.0,
    )
    return _project_vector(base, width=width)


def _project_vector(values: Sequence[float], *, width: int) -> tuple[float, ...]:
    numbers = [float(value) for value in values]
    if not numbers:
        return ()
    mean_value = sum(numbers) / len(numbers)
    min_value = min(numbers)
    max_value = max(numbers)
    l2_value = math.sqrt(sum(value * value for value in numbers))
    first_value = numbers[0]
    last_value = numbers[-1]
    summary = [
        mean_value,
        min_value,
        max_value,
        l2_value,
        first_value,
        last_value,
    ]
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
            raise ValueError("All rows must share a common width")
        for index, value in enumerate(row):
            totals[index] += float(value)
    return tuple(total / len(rows) for total in totals)


def _weighted_mean(rows: Sequence[Sequence[float]], weights: Sequence[float]) -> tuple[float, ...]:
    if not rows:
        return ()
    if len(rows) != len(weights):
        raise ValueError("weights must align with rows")
    width = len(rows[0])
    totals = [0.0] * width
    total_weight = 0.0
    for row, weight in zip(rows, weights, strict=True):
        if len(row) != width:
            raise ValueError("All rows must share a common width")
        total_weight += float(weight)
        for index, value in enumerate(row):
            totals[index] += float(value) * float(weight)
    if total_weight <= 0.0:
        return tuple(0.0 for _ in range(width))
    return tuple(total / total_weight for total in totals)


def _softmax(values: Sequence[float]) -> tuple[float, ...]:
    if not values:
        return ()
    max_value = max(values)
    exps = [math.exp(float(value) - max_value) for value in values]
    total = sum(exps)
    if total == 0.0:
        return tuple(0.0 for _ in exps)
    return tuple(value / total for value in exps)


def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("dot product inputs must have the same width")
    return sum(float(lval) * float(rval) for lval, rval in zip(left, right, strict=True))


def _gating_weights(*, structure_ready: bool, sequence_ready: bool) -> dict[str, float]:
    if structure_ready and sequence_ready:
        return {"sequence": 0.5, "structure": 0.5}
    if structure_ready:
        return {"sequence": 0.0, "structure": 1.0}
    if sequence_ready:
        return {"sequence": 1.0, "structure": 0.0}
    return {"sequence": 0.0, "structure": 0.0}


def _parse_simple_yaml_mapping(path: Path) -> dict[str, Scalar]:
    config: dict[str, Scalar] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        key, separator, value = line.partition(":")
        if not separator:
            raise ValueError(f"Unsupported YAML line in {path}: {raw_line!r}")
        config[key.strip()] = _parse_scalar(value.strip())
    return config


def _parse_scalar(value: str) -> Scalar:
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if re.fullmatch(r"[+-]?\d+", value):
        return int(value)
    if re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?", value, re.IGNORECASE):
        return float(value)
    return value


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _relative_path(root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")


__all__ = [
    "CrossAttentionFusionOutput",
    "LockdownBackendStatus",
    "LockdownModelBlocker",
    "LockdownModelSpec",
    "LockdownReferenceModel",
    "LockdownReferenceModelResult",
    "PredictionHeadOutput",
    "PredictionTargetOutput",
    "SequencePathOutput",
    "StructurePathOutput",
    "load_lockdown_model_spec",
    "run_lockdown_reference_model",
]
