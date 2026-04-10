from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from itertools import combinations
from math import sqrt
from typing import Any

from models.multimodal.fusion_model import DEFAULT_MODALITY_ORDER, FusionModelResult

DEFAULT_UNCERTAINTY_HEAD_MODEL = "multimodal-uncertainty-baseline-v1"
_SPREAD_WEIGHT = 0.25


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


def _as_float_tuple(values: Any) -> tuple[float, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        return (float(values),)
    if not isinstance(values, Sequence):
        values = (values,)
    return tuple(float(value) for value in values)


def _vector_norm(values: Sequence[float]) -> float:
    return sqrt(sum(float(value) * float(value) for value in values))


def _mean_pairwise_distance(vectors: Sequence[Sequence[float]]) -> float:
    if len(vectors) < 2:
        return 0.0
    distances = []
    for left, right in combinations(vectors, 2):
        if len(left) != len(right):
            raise ValueError("embedding rows must share a common width")
        distances.append(
            sqrt(
                sum(
                    (float(lval) - float(rval)) ** 2
                    for lval, rval in zip(left, right, strict=True)
                )
            )
        )
    return sum(distances) / float(len(distances))


def _normalize_modality_order(values: Sequence[str]) -> tuple[str, ...]:
    order = tuple(_clean_text(value) for value in values if _clean_text(value))
    if not order:
        raise ValueError("modalities must contain at least one modality name")
    invalid = sorted(
        modality for modality in order if modality not in DEFAULT_MODALITY_ORDER
    )
    if invalid:
        raise ValueError("modalities must be drawn from: " + ", ".join(DEFAULT_MODALITY_ORDER))
    return order


def _coerce_fusion_result(
    value: FusionModelResult | Mapping[str, Any] | Any,
) -> dict[str, Any]:
    if isinstance(value, FusionModelResult):
        return {
            "model_name": value.model_name,
            "modalities": value.modalities,
            "available_modalities": value.available_modalities,
            "missing_modalities": value.missing_modalities,
            "modality_weights": dict(value.modality_weights),
            "modality_embeddings": dict(value.modality_embeddings),
            "fused_embedding": value.fused_embedding,
            "provenance": dict(value.provenance),
            "source_kind": value.source_kind,
        }
    if not isinstance(value, Mapping):
        if not any(hasattr(value, key) for key in ("modalities", "available_modalities")):
            raise TypeError("fusion_result must be a FusionModelResult or mapping")
    model_name = _clean_text(_mapping_or_attributes(value, "model_name"))
    model_name = model_name or DEFAULT_UNCERTAINTY_HEAD_MODEL
    modalities = _normalize_modality_order(
        _mapping_or_attributes(value, "modalities") or DEFAULT_MODALITY_ORDER
    )
    available_modalities = tuple(
        str(item)
        for item in (
            _mapping_or_attributes(value, "available_modalities") or ()
        )
    )
    missing_modalities = tuple(
        str(item)
        for item in (
            _mapping_or_attributes(value, "missing_modalities") or ()
        )
    )
    modality_weights = _mapping_or_attributes(value, "modality_weights")
    modality_embeddings = _mapping_or_attributes(value, "modality_embeddings")
    fused_embedding = _mapping_or_attributes(value, "fused_embedding")
    provenance = _coerce_provenance(_mapping_or_attributes(value, "provenance"))
    if modality_weights is None or modality_embeddings is None or fused_embedding is None:
        raise TypeError(
            "fusion_result must expose modality_weights, modality_embeddings, and fused_embedding"
        )
    return {
        "model_name": model_name,
        "modalities": modalities,
        "available_modalities": available_modalities,
        "missing_modalities": missing_modalities,
        "modality_weights": {
            str(key): float(value) for key, value in dict(modality_weights).items()
        },
        "modality_embeddings": {
            str(key): _as_float_tuple(value) for key, value in dict(modality_embeddings).items()
        },
        "fused_embedding": _as_float_tuple(fused_embedding),
        "provenance": provenance,
        "source_kind": _clean_text(_mapping_or_attributes(value, "source_kind"))
        or "multimodal_fusion_baseline",
    }


@dataclass(frozen=True, slots=True)
class UncertaintyHeadResult:
    model_name: str
    fusion_model_name: str
    modalities: tuple[str, ...]
    available_modalities: tuple[str, ...]
    missing_modalities: tuple[str, ...]
    uncertainty: float
    confidence: float
    feature_names: tuple[str, ...]
    feature_vector: tuple[float, ...]
    metrics: dict[str, float]
    source_kind: str = "multimodal_uncertainty_baseline"
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

    def to_dict(self) -> dict[str, object]:
        return {
            "model_name": self.model_name,
            "fusion_model_name": self.fusion_model_name,
            "modalities": list(self.modalities),
            "available_modalities": list(self.available_modalities),
            "missing_modalities": list(self.missing_modalities),
            "uncertainty": self.uncertainty,
            "confidence": self.confidence,
            "feature_names": list(self.feature_names),
            "feature_vector": list(self.feature_vector),
            "metrics": dict(self.metrics),
            "source_kind": self.source_kind,
            "frozen": self.frozen,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class UncertaintyHead:
    model_name: str = DEFAULT_UNCERTAINTY_HEAD_MODEL
    source_kind: str = "multimodal_uncertainty_baseline"

    def __post_init__(self) -> None:
        model_name = _clean_text(self.model_name)
        source_kind = _clean_text(self.source_kind)
        if not model_name:
            raise ValueError("model_name must be a non-empty string")
        object.__setattr__(self, "model_name", model_name)
        object.__setattr__(self, "source_kind", source_kind or "multimodal_uncertainty_baseline")

    def evaluate(
        self,
        fusion_result: FusionModelResult | Mapping[str, Any] | Any,
        *,
        provenance: Mapping[str, Any] | None = None,
    ) -> UncertaintyHeadResult:
        fusion = _coerce_fusion_result(fusion_result)
        modalities = fusion["modalities"]
        available_modalities = tuple(
            modality for modality in modalities if modality in fusion["available_modalities"]
        )
        missing_modalities = tuple(
            modality for modality in modalities if modality not in available_modalities
        )
        if not modalities:
            raise ValueError("fusion_result must describe at least one modality")

        available_count = float(len(available_modalities))
        missing_count = float(len(missing_modalities))
        coverage = available_count / float(len(modalities))
        missing_fraction = 1.0 - coverage
        modality_embeddings = fusion["modality_embeddings"]
        available_embeddings = [
            modality_embeddings[modality]
            for modality in available_modalities
            if modality in modality_embeddings
        ]
        spread = _mean_pairwise_distance(available_embeddings)
        fusion_width = len(fusion["fused_embedding"])
        if fusion_width == 0 and available_embeddings:
            fusion_width = len(available_embeddings[0])
        if fusion_width == 0:
            fusion_width = 1
        normalized_spread = min(spread / sqrt(float(fusion_width)), 1.0)
        uncertainty = min(1.0, max(0.0, missing_fraction + (_SPREAD_WEIGHT * normalized_spread)))
        confidence = 1.0 - uncertainty

        feature_names = (
            "fusion_coverage",
            "fusion_missing_fraction",
            "fusion_available_count",
            "fusion_missing_count",
            *tuple(f"{modality}_weight" for modality in modalities),
            "fusion_modality_spread",
            "fusion_fused_norm",
        )
        feature_vector = (
            coverage,
            missing_fraction,
            available_count,
            missing_count,
            *tuple(float(fusion["modality_weights"].get(modality, 0.0)) for modality in modalities),
            normalized_spread,
            _vector_norm(fusion["fused_embedding"]),
        )

        metrics = {
            "coverage": coverage,
            "missing_fraction": missing_fraction,
            "available_count": available_count,
            "missing_count": missing_count,
            "modality_spread": normalized_spread,
            "fused_l2_norm": _vector_norm(fusion["fused_embedding"]),
            "uncertainty": uncertainty,
            "confidence": confidence,
            "feature_vector_length": float(len(feature_vector)),
        }

        provenance_payload = dict(fusion["provenance"])
        if provenance is not None:
            provenance_payload.update(_coerce_provenance(provenance))
        provenance_payload.update(
            {
                "encoder": self.model_name,
                "source_kind": self.source_kind,
                "fusion_model_name": fusion["model_name"],
                "fusion_modalities": list(modalities),
                "available_modalities": list(available_modalities),
                "missing_modalities": list(missing_modalities),
                "feature_names": list(feature_names),
            }
        )

        return UncertaintyHeadResult(
            model_name=self.model_name,
            fusion_model_name=fusion["model_name"],
            modalities=modalities,
            available_modalities=available_modalities,
            missing_modalities=missing_modalities,
            uncertainty=uncertainty,
            confidence=confidence,
            feature_names=feature_names,
            feature_vector=feature_vector,
            metrics=metrics,
            source_kind=self.source_kind,
            frozen=True,
            provenance=provenance_payload,
        )


def estimate_uncertainty(
    fusion_result: FusionModelResult | Mapping[str, Any] | Any,
    *,
    model_name: str = DEFAULT_UNCERTAINTY_HEAD_MODEL,
    source_kind: str = "multimodal_uncertainty_baseline",
    provenance: Mapping[str, Any] | None = None,
) -> UncertaintyHeadResult:
    return UncertaintyHead(model_name=model_name, source_kind=source_kind).evaluate(
        fusion_result,
        provenance=provenance,
    )


__all__ = [
    "DEFAULT_UNCERTAINTY_HEAD_MODEL",
    "UncertaintyHead",
    "UncertaintyHeadResult",
    "estimate_uncertainty",
]
