from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from statistics import fmean
from typing import Any

from models.multimodal.fusion_model import FusionModelResult

DEFAULT_MULTIMODAL_METRICS_ID = "multimodal-metrics"


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _mean_or_zero(values: Iterable[float]) -> float:
    values = tuple(float(value) for value in values)
    if not values:
        return 0.0
    return fmean(values)


@dataclass(frozen=True, slots=True)
class MultimodalExampleMetrics:
    example_index: int
    model_name: str
    fusion_dim: int
    modalities: tuple[str, ...]
    available_modalities: tuple[str, ...]
    missing_modalities: tuple[str, ...]
    available_count: int
    missing_count: int
    coverage: float
    complete: bool
    fused_l2_norm: float
    feature_vector_length: int
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "example_index": self.example_index,
            "model_name": self.model_name,
            "fusion_dim": self.fusion_dim,
            "modalities": list(self.modalities),
            "available_modalities": list(self.available_modalities),
            "missing_modalities": list(self.missing_modalities),
            "available_count": self.available_count,
            "missing_count": self.missing_count,
            "coverage": self.coverage,
            "complete": self.complete,
            "fused_l2_norm": self.fused_l2_norm,
            "feature_vector_length": self.feature_vector_length,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class MultimodalMetrics:
    metrics_id: str
    model_name: str
    fusion_dim: int
    modalities: tuple[str, ...]
    example_count: int
    complete_count: int
    partial_count: int
    coverage_mean: float
    coverage_min: float
    coverage_max: float
    complete_rate: float
    available_count_mean: float
    missing_count_mean: float
    fused_l2_norm_mean: float
    fused_l2_norm_min: float
    fused_l2_norm_max: float
    feature_vector_length_mean: float
    modality_coverage: dict[str, float]
    example_metrics: tuple[MultimodalExampleMetrics, ...]
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metrics_id": self.metrics_id,
            "model_name": self.model_name,
            "fusion_dim": self.fusion_dim,
            "modalities": list(self.modalities),
            "example_count": self.example_count,
            "complete_count": self.complete_count,
            "partial_count": self.partial_count,
            "coverage_mean": self.coverage_mean,
            "coverage_min": self.coverage_min,
            "coverage_max": self.coverage_max,
            "complete_rate": self.complete_rate,
            "available_count_mean": self.available_count_mean,
            "missing_count_mean": self.missing_count_mean,
            "fused_l2_norm_mean": self.fused_l2_norm_mean,
            "fused_l2_norm_min": self.fused_l2_norm_min,
            "fused_l2_norm_max": self.fused_l2_norm_max,
            "feature_vector_length_mean": self.feature_vector_length_mean,
            "modality_coverage": dict(self.modality_coverage),
            "example_metrics": [metric.to_dict() for metric in self.example_metrics],
            "provenance": dict(self.provenance),
        }


def _example_metric(
    result: FusionModelResult,
    *,
    example_index: int,
) -> MultimodalExampleMetrics:
    available_modalities = tuple(result.available_modalities)
    missing_modalities = tuple(result.missing_modalities)
    coverage = float(result.coverage)
    fused_l2_norm = float(sum(value * value for value in result.fused_embedding) ** 0.5)
    feature_vector_length = len(result.feature_vector)
    provenance = {
        "source_kind": result.source_kind,
        "model_name": result.model_name,
        "available_count": result.available_count,
        "missing_count": result.missing_count,
    }
    provenance.update(dict(result.provenance))
    return MultimodalExampleMetrics(
        example_index=example_index,
        model_name=result.model_name,
        fusion_dim=result.fusion_dim,
        modalities=tuple(result.modalities),
        available_modalities=available_modalities,
        missing_modalities=missing_modalities,
        available_count=result.available_count,
        missing_count=result.missing_count,
        coverage=coverage,
        complete=result.is_complete,
        fused_l2_norm=fused_l2_norm,
        feature_vector_length=feature_vector_length,
        provenance=provenance,
    )


def summarize_multimodal_metrics(
    results: Iterable[FusionModelResult],
    *,
    metrics_id: str = DEFAULT_MULTIMODAL_METRICS_ID,
    provenance: dict[str, Any] | None = None,
) -> MultimodalMetrics:
    materialized = tuple(results)
    if not materialized:
        raise ValueError("results must contain at least one FusionModelResult")
    if not all(isinstance(result, FusionModelResult) for result in materialized):
        raise TypeError("results must contain FusionModelResult objects")

    first = materialized[0]
    for result in materialized[1:]:
        if result.model_name != first.model_name:
            raise ValueError("results must share the same model_name")
        if result.fusion_dim != first.fusion_dim:
            raise ValueError("results must share the same fusion_dim")
        if result.modalities != first.modalities:
            raise ValueError("results must share the same modality contract")

    example_metrics = tuple(
        _example_metric(result, example_index=index)
        for index, result in enumerate(materialized, start=1)
    )
    coverage_values = tuple(metric.coverage for metric in example_metrics)
    available_counts = tuple(metric.available_count for metric in example_metrics)
    missing_counts = tuple(metric.missing_count for metric in example_metrics)
    fused_norms = tuple(metric.fused_l2_norm for metric in example_metrics)
    feature_lengths = tuple(metric.feature_vector_length for metric in example_metrics)
    complete_count = sum(1 for metric in example_metrics if metric.complete)
    modality_coverage = {
        modality: sum(
            1 for result in materialized if modality in result.available_modalities
        )
        / float(len(materialized))
        for modality in first.modalities
    }

    provenance_payload: dict[str, Any] = {}
    if provenance is not None:
        provenance_payload.update(provenance)
    provenance_payload.update(
        {
            "source_model_name": first.model_name,
            "fusion_dim": first.fusion_dim,
            "modalities": list(first.modalities),
            "example_count": len(materialized),
        }
    )

    return MultimodalMetrics(
        metrics_id=_clean_text(metrics_id) or DEFAULT_MULTIMODAL_METRICS_ID,
        model_name=first.model_name,
        fusion_dim=first.fusion_dim,
        modalities=first.modalities,
        example_count=len(materialized),
        complete_count=complete_count,
        partial_count=len(materialized) - complete_count,
        coverage_mean=_mean_or_zero(coverage_values),
        coverage_min=min(coverage_values),
        coverage_max=max(coverage_values),
        complete_rate=complete_count / float(len(materialized)),
        available_count_mean=_mean_or_zero(available_counts),
        missing_count_mean=_mean_or_zero(missing_counts),
        fused_l2_norm_mean=_mean_or_zero(fused_norms),
        fused_l2_norm_min=min(fused_norms),
        fused_l2_norm_max=max(fused_norms),
        feature_vector_length_mean=_mean_or_zero(feature_lengths),
        modality_coverage=modality_coverage,
        example_metrics=example_metrics,
        provenance=provenance_payload,
    )


__all__ = [
    "DEFAULT_MULTIMODAL_METRICS_ID",
    "MultimodalExampleMetrics",
    "MultimodalMetrics",
    "summarize_multimodal_metrics",
]
