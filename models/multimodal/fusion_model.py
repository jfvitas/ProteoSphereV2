from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from math import sqrt
from typing import Any

from features.esm2_embeddings import ProteinEmbeddingResult
from models.multimodal.ligand_encoder import LigandEmbeddingResult
from models.multimodal.structure_encoder import StructureEmbeddingResult

DEFAULT_FUSION_MODEL = "multimodal-fusion-baseline-v1"
DEFAULT_FUSION_DIM = 8
DEFAULT_MODALITY_ORDER = ("sequence", "structure", "ligand")


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _json_ready(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


def _coerce_provenance(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError("provenance must be a mapping")
    return _json_ready(dict(value))


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


def _project_vector(values: Sequence[float], *, width: int) -> tuple[float, ...]:
    numbers = [float(value) for value in values]
    if width < 1:
        raise ValueError("fusion_dim must be >= 1")
    if not numbers:
        return tuple(0.0 for _ in range(width))
    if len(numbers) == width:
        return tuple(numbers)

    mean_value = sum(numbers) / len(numbers)
    min_value = min(numbers)
    max_value = max(numbers)
    l2_value = sqrt(sum(value * value for value in numbers))
    summary = [mean_value, min_value, max_value, l2_value, numbers[0], numbers[-1]]
    while len(summary) < width:
        summary.append(mean_value)
    return tuple(summary[:width])


def _vector_norm(values: Sequence[float]) -> float:
    return sqrt(sum(float(value) * float(value) for value in values))


def _weighted_mean(
    rows: Sequence[Sequence[float]],
    weights: Sequence[float],
) -> tuple[float, ...]:
    if not rows:
        return ()
    if len(rows) != len(weights):
        raise ValueError("weights must align with rows")
    width = len(rows[0])
    totals = [0.0] * width
    total_weight = 0.0
    for row, weight in zip(rows, weights, strict=True):
        if len(row) != width:
            raise ValueError("embedding rows must share a common width")
        total_weight += float(weight)
        for index, value in enumerate(row):
            totals[index] += float(value) * float(weight)
    if total_weight <= 0.0:
        return tuple(0.0 for _ in range(width))
    return tuple(total / total_weight for total in totals)


def _payload_value(payload: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]
    return None


def _mapping_or_attributes(value: Any, *keys: str) -> Any:
    if isinstance(value, Mapping):
        for key in keys:
            if key in value:
                return value[key]
        return None
    for key in keys:
        if hasattr(value, key):
            return getattr(value, key)
    return None


def _token_ids_for_sequence(embedding: ProteinEmbeddingResult) -> tuple[str, ...]:
    return tuple(str(index) for index in range(1, embedding.residue_count + 1))


def _coerce_modality_embedding(
    modality: str,
    value: (
        ProteinEmbeddingResult
        | StructureEmbeddingResult
        | LigandEmbeddingResult
        | Mapping[str, Any]
        | Any
    ),
) -> dict[str, Any]:
    if value is None:
        return {
            "present": False,
            "token_ids": (),
            "token_count": 0,
            "pooled_embedding": (),
            "provenance": {},
            "source": None,
            "model_name": None,
        }

    provenance = _coerce_provenance(_mapping_or_attributes(value, "provenance"))
    source = _clean_text(_mapping_or_attributes(value, "source")) or None
    model_name = _clean_text(_mapping_or_attributes(value, "model_name")) or None

    if modality == "sequence":
        residue_embeddings = _mapping_or_attributes(value, "residue_embeddings")
        pooled_embedding = _mapping_or_attributes(value, "pooled_embedding")
        if residue_embeddings is None or pooled_embedding is None:
            raise TypeError(
                "sequence embeddings must expose residue_embeddings and pooled_embedding"
            )
        normalized_residue_embeddings = tuple(
            tuple(float(item) for item in row) for row in residue_embeddings
        )
        if not normalized_residue_embeddings:
            raise ValueError("sequence embedding must contain at least one residue embedding")
        token_ids = (
            _token_ids_for_sequence(value)
            if isinstance(value, ProteinEmbeddingResult)
            else tuple(str(index) for index in range(1, len(normalized_residue_embeddings) + 1))
        )
        pooled = tuple(float(item) for item in pooled_embedding)
        return {
            "present": True,
            "token_ids": token_ids,
            "token_count": len(token_ids),
            "pooled_embedding": pooled,
            "provenance": provenance,
            "source": source,
            "model_name": model_name,
        }

    token_ids = _mapping_or_attributes(value, "token_ids")
    token_embeddings = _mapping_or_attributes(value, "token_embeddings")
    pooled_embedding = _mapping_or_attributes(value, "pooled_embedding")
    if token_ids is None or token_embeddings is None or pooled_embedding is None:
        raise TypeError(
            f"{modality} embeddings must expose token_ids, token_embeddings, and pooled_embedding"
        )

    normalized_token_ids = tuple(str(item) for item in token_ids)
    normalized_token_embeddings = tuple(
        tuple(float(item) for item in row) for row in token_embeddings
    )
    if not normalized_token_embeddings:
        raise ValueError(f"{modality} embedding must contain at least one token embedding")

    return {
        "present": True,
        "token_ids": normalized_token_ids,
        "token_count": len(normalized_token_ids),
        "pooled_embedding": tuple(float(item) for item in pooled_embedding),
        "provenance": provenance,
        "source": source,
        "model_name": model_name,
    }


@dataclass(frozen=True, slots=True)
class FusionModelResult:
    model_name: str
    fusion_dim: int
    modalities: tuple[str, ...]
    available_modalities: tuple[str, ...]
    missing_modalities: tuple[str, ...]
    modality_token_ids: dict[str, tuple[str, ...]]
    modality_token_counts: dict[str, int]
    modality_embeddings: dict[str, tuple[float, ...]]
    modality_weights: dict[str, float]
    fused_embedding: tuple[float, ...]
    feature_names: tuple[str, ...]
    feature_vector: tuple[float, ...]
    metrics: dict[str, float]
    source_kind: str = "multimodal_fusion_baseline"
    frozen: bool = True
    provenance: dict[str, object] = field(default_factory=dict)

    @property
    def available_count(self) -> int:
        return len(self.available_modalities)

    @property
    def missing_count(self) -> int:
        return len(self.missing_modalities)

    @property
    def coverage(self) -> float:
        if not self.modalities:
            return 0.0
        return self.available_count / float(len(self.modalities))

    @property
    def is_complete(self) -> bool:
        return self.missing_count == 0

    def to_dict(self) -> dict[str, object]:
        return {
            "model_name": self.model_name,
            "fusion_dim": self.fusion_dim,
            "modalities": list(self.modalities),
            "available_modalities": list(self.available_modalities),
            "missing_modalities": list(self.missing_modalities),
            "modality_token_ids": {
                key: list(value) for key, value in self.modality_token_ids.items()
            },
            "modality_token_counts": dict(self.modality_token_counts),
            "modality_embeddings": {
                key: list(value) for key, value in self.modality_embeddings.items()
            },
            "modality_weights": dict(self.modality_weights),
            "fused_embedding": list(self.fused_embedding),
            "feature_names": list(self.feature_names),
            "feature_vector": list(self.feature_vector),
            "metrics": dict(self.metrics),
            "source_kind": self.source_kind,
            "frozen": self.frozen,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class FusionModel:
    model_name: str = DEFAULT_FUSION_MODEL
    fusion_dim: int = DEFAULT_FUSION_DIM
    source_kind: str = "multimodal_fusion_baseline"
    modalities: tuple[str, ...] = DEFAULT_MODALITY_ORDER

    def __post_init__(self) -> None:
        model_name = _clean_text(self.model_name)
        source_kind = _clean_text(self.source_kind)
        modalities = tuple(
            modality
            for modality in (_clean_text(name) for name in self.modalities)
            if modality
        )
        if not model_name:
            raise ValueError("model_name must be a non-empty string")
        if self.fusion_dim < 1:
            raise ValueError("fusion_dim must be >= 1")
        if not modalities:
            raise ValueError("modalities must contain at least one modality name")
        invalid_modalities = sorted(
            modality for modality in modalities if modality not in DEFAULT_MODALITY_ORDER
        )
        if invalid_modalities:
            raise ValueError(
                "modalities must be drawn from: " + ", ".join(DEFAULT_MODALITY_ORDER)
            )
        object.__setattr__(self, "model_name", model_name)
        object.__setattr__(self, "source_kind", source_kind or "multimodal_fusion_baseline")
        object.__setattr__(self, "modalities", modalities)

    def fuse(
        self,
        feature_bundle: Any | None = None,
        *,
        sequence_embedding: ProteinEmbeddingResult | Mapping[str, Any] | Any | None = None,
        structure_embedding: StructureEmbeddingResult | Mapping[str, Any] | Any | None = None,
        ligand_embedding: LigandEmbeddingResult | Mapping[str, Any] | Any | None = None,
        provenance: Mapping[str, Any] | None = None,
    ) -> FusionModelResult:
        bundle_provenance: dict[str, Any] = {}
        if feature_bundle is not None:
            if isinstance(feature_bundle, Mapping):
                bundle_provenance = _coerce_provenance(_payload_value(feature_bundle, "provenance"))
            else:
                bundle_provenance = _coerce_provenance(
                    _mapping_or_attributes(feature_bundle, "provenance")
                )
            if sequence_embedding is None:
                sequence_embedding = _mapping_or_attributes(feature_bundle, "sequence_embedding")
            if structure_embedding is None:
                structure_embedding = _mapping_or_attributes(feature_bundle, "structure_embedding")
            if ligand_embedding is None:
                ligand_embedding = _mapping_or_attributes(feature_bundle, "ligand_embedding")

        summaries = {
            "sequence": _coerce_modality_embedding("sequence", sequence_embedding),
            "structure": _coerce_modality_embedding("structure", structure_embedding),
            "ligand": _coerce_modality_embedding("ligand", ligand_embedding),
        }
        available_modalities = tuple(
            modality for modality in self.modalities if summaries[modality]["present"]
        )
        if not available_modalities:
            raise ValueError("at least one modality embedding must be provided")
        missing_modalities = tuple(
            modality for modality in self.modalities if modality not in available_modalities
        )

        modality_embeddings: dict[str, tuple[float, ...]] = {}
        modality_token_ids: dict[str, tuple[str, ...]] = {}
        modality_token_counts: dict[str, int] = {}
        modality_weights: dict[str, float] = {
            modality: 0.0 for modality in self.modalities
        }
        for modality in self.modalities:
            summary = summaries[modality]
            modality_token_ids[modality] = tuple(summary["token_ids"])
            modality_token_counts[modality] = int(summary["token_count"])
            if summary["present"]:
                modality_embeddings[modality] = _project_vector(
                    summary["pooled_embedding"],
                    width=self.fusion_dim,
                )

        active_embeddings = [modality_embeddings[modality] for modality in available_modalities]
        active_weight = 1.0 / float(len(active_embeddings))
        for modality in available_modalities:
            modality_weights[modality] = active_weight

        fused_embedding = _weighted_mean(
            active_embeddings,
            [modality_weights[modality] for modality in available_modalities],
        )

        feature_names: list[str] = []
        feature_vector: list[float] = []
        for modality in self.modalities:
            summary = summaries[modality]
            feature_names.append(f"{modality}_present")
            feature_vector.append(1.0 if summary["present"] else 0.0)
            feature_names.append(f"{modality}_token_count")
            feature_vector.append(float(summary["token_count"]))
            default_embedding = (0.0,) * self.fusion_dim
            for index, value in enumerate(modality_embeddings.get(modality, default_embedding)):
                feature_names.append(f"{modality}_pooled_{index}")
                feature_vector.append(float(value))

        for index, value in enumerate(fused_embedding):
            feature_names.append(f"fused_{index}")
            feature_vector.append(float(value))

        metrics = {
            "available_count": float(len(available_modalities)),
            "missing_count": float(len(missing_modalities)),
            "coverage": float(len(available_modalities)) / float(len(self.modalities)),
            "feature_vector_length": float(len(feature_vector)),
            "fused_l2_norm": float(_vector_norm(fused_embedding)),
        }

        provenance_payload = dict(bundle_provenance)
        if provenance is not None:
            provenance_payload.update(_coerce_provenance(provenance))
        provenance_payload.update(
            {
                "encoder": self.model_name,
                "source_kind": self.source_kind,
                "modalities": list(self.modalities),
                "available_modalities": list(available_modalities),
                "missing_modalities": list(missing_modalities),
                "modality_provenance": {
                    modality: dict(summaries[modality]["provenance"])
                    for modality in self.modalities
                    if summaries[modality]["present"]
                },
                "modality_sources": {
                    modality: summaries[modality]["source"]
                    for modality in self.modalities
                    if summaries[modality]["present"]
                },
                "modality_models": {
                    modality: summaries[modality]["model_name"]
                    for modality in self.modalities
                    if summaries[modality]["present"]
                },
                "fusion_dim": self.fusion_dim,
            }
        )

        return FusionModelResult(
            model_name=self.model_name,
            fusion_dim=self.fusion_dim,
            modalities=self.modalities,
            available_modalities=available_modalities,
            missing_modalities=missing_modalities,
            modality_token_ids=modality_token_ids,
            modality_token_counts=modality_token_counts,
            modality_embeddings=modality_embeddings,
            modality_weights=modality_weights,
            fused_embedding=fused_embedding,
            feature_names=tuple(feature_names),
            feature_vector=tuple(feature_vector),
            metrics=metrics,
            source_kind=self.source_kind,
            frozen=True,
            provenance=provenance_payload,
        )


def fuse_modalities(
    feature_bundle: Any | None = None,
    *,
    model_name: str = DEFAULT_FUSION_MODEL,
    fusion_dim: int = DEFAULT_FUSION_DIM,
    source_kind: str = "multimodal_fusion_baseline",
    modalities: Sequence[str] = DEFAULT_MODALITY_ORDER,
    sequence_embedding: ProteinEmbeddingResult | Mapping[str, Any] | Any | None = None,
    structure_embedding: StructureEmbeddingResult | Mapping[str, Any] | Any | None = None,
    ligand_embedding: LigandEmbeddingResult | Mapping[str, Any] | Any | None = None,
    provenance: Mapping[str, Any] | None = None,
) -> FusionModelResult:
    return FusionModel(
        model_name=model_name,
        fusion_dim=fusion_dim,
        source_kind=source_kind,
        modalities=tuple(modalities),
    ).fuse(
        feature_bundle,
        sequence_embedding=sequence_embedding,
        structure_embedding=structure_embedding,
        ligand_embedding=ligand_embedding,
        provenance=provenance,
    )


__all__ = [
    "DEFAULT_FUSION_DIM",
    "DEFAULT_FUSION_MODEL",
    "DEFAULT_MODALITY_ORDER",
    "FusionModel",
    "FusionModelResult",
    "fuse_modalities",
]
