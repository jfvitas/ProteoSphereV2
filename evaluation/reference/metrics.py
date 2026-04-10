from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from statistics import fmean
from typing import Any

from datasets.baseline.schema import BaselineDatasetExample, BaselineDatasetSchema
from models.reference.model import ReferenceExampleSummary, ReferenceModelResult

DEFAULT_REFERENCE_METRICS_ID = "reference-metrics"


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_text_tuple(values: Any) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        values = (values,)
    ordered: dict[str, str] = {}
    for value in values:
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _mean_or_zero(values: Iterable[float]) -> float:
    values = tuple(float(value) for value in values)
    if not values:
        return 0.0
    return fmean(values)


def _json_ready(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class ReferenceExampleMetrics:
    example_index: int
    example_id: str
    protein_accession: str
    feature_modalities: tuple[str, ...]
    label_names: tuple[str, ...]
    split: str | None
    lineage_complete: bool
    requested_coverage: float
    complete_requested_modalities: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "example_index": self.example_index,
            "example_id": self.example_id,
            "protein_accession": self.protein_accession,
            "feature_modalities": list(self.feature_modalities),
            "label_names": list(self.label_names),
            "split": self.split,
            "lineage_complete": self.lineage_complete,
            "requested_coverage": self.requested_coverage,
            "complete_requested_modalities": self.complete_requested_modalities,
        }


@dataclass(frozen=True, slots=True)
class ReferenceMetrics:
    metrics_id: str
    model_name: str
    dataset_contract: str
    dataset_id: str
    schema_version: int
    example_count: int
    requested_modalities: tuple[str, ...]
    available_modalities: tuple[str, ...]
    missing_requested_modalities: tuple[str, ...]
    requested_modality_presence_rate: dict[str, float]
    requested_coverage_mean: float
    requested_coverage_min: float
    requested_coverage_max: float
    complete_requested_example_count: int
    complete_requested_rate: float
    lineage_complete_example_count: int
    lineage_complete_rate: float
    split_counts: dict[str, int]
    example_metrics: tuple[ReferenceExampleMetrics, ...]
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metrics_id": self.metrics_id,
            "model_name": self.model_name,
            "dataset_contract": self.dataset_contract,
            "dataset_id": self.dataset_id,
            "schema_version": self.schema_version,
            "example_count": self.example_count,
            "requested_modalities": list(self.requested_modalities),
            "available_modalities": list(self.available_modalities),
            "missing_requested_modalities": list(self.missing_requested_modalities),
            "requested_modality_presence_rate": dict(self.requested_modality_presence_rate),
            "requested_coverage_mean": self.requested_coverage_mean,
            "requested_coverage_min": self.requested_coverage_min,
            "requested_coverage_max": self.requested_coverage_max,
            "complete_requested_example_count": self.complete_requested_example_count,
            "complete_requested_rate": self.complete_requested_rate,
            "lineage_complete_example_count": self.lineage_complete_example_count,
            "lineage_complete_rate": self.lineage_complete_rate,
            "split_counts": dict(self.split_counts),
            "example_metrics": [metric.to_dict() for metric in self.example_metrics],
            "provenance": dict(self.provenance),
        }


def _coverage_for_example(
    feature_modalities: tuple[str, ...],
    requested_modalities: tuple[str, ...],
) -> tuple[float, bool]:
    if not requested_modalities:
        return 1.0, True
    feature_set = {modality.casefold() for modality in feature_modalities}
    requested_set = [modality.casefold() for modality in requested_modalities]
    present_count = sum(1 for modality in requested_set if modality in feature_set)
    coverage = present_count / float(len(requested_modalities))
    return coverage, present_count == len(requested_modalities)


def _split_key(split: str | None) -> str:
    text = _clean_text(split)
    return text or "unsplit"


def _example_metric_from_summary(
    summary: ReferenceExampleSummary,
    *,
    example_index: int,
    requested_modalities: tuple[str, ...],
) -> ReferenceExampleMetrics:
    requested_coverage, complete_requested_modalities = _coverage_for_example(
        summary.feature_modalities,
        requested_modalities,
    )
    return ReferenceExampleMetrics(
        example_index=example_index,
        example_id=summary.example_id,
        protein_accession=summary.protein_accession,
        feature_modalities=summary.feature_modalities,
        label_names=summary.label_names,
        split=summary.split,
        lineage_complete=summary.lineage_complete,
        requested_coverage=requested_coverage,
        complete_requested_modalities=complete_requested_modalities,
    )


def _example_summaries_from_schema(
    schema: BaselineDatasetSchema,
) -> tuple[ReferenceExampleSummary, ...]:
    summaries = []
    for example in schema.examples:
        if not isinstance(example, BaselineDatasetExample):
            raise TypeError("examples must contain BaselineDatasetExample objects")
        summaries.append(
            ReferenceExampleSummary(
                example_id=example.example_id,
                protein_accession=example.protein_ref.canonical_id,
                feature_modalities=example.feature_modalities,
                label_names=tuple(label.label_name for label in example.labels),
                split=example.split,
                lineage_complete=example.lineage_complete,
            )
        )
    return tuple(summaries)


def _coerce_dataset_like(
    dataset: BaselineDatasetSchema | ReferenceModelResult | Mapping[str, Any],
) -> tuple[
    str,
    str,
    str,
    int,
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[ReferenceExampleSummary, ...],
    dict[str, Any],
]:
    if isinstance(dataset, ReferenceModelResult):
        provenance = {
            "source_kind": "reference_model_result",
            "spec": dataset.spec.to_dict(),
            "status": dataset.status.to_dict(),
        }
        return (
            dataset.spec.model_name,
            dataset.spec.dataset_contract,
            dataset.dataset_id,
            dataset.schema_version,
            dataset.requested_modalities,
            dataset.available_modalities,
            dataset.missing_requested_modalities,
            dataset.example_summaries,
            provenance,
        )

    if isinstance(dataset, BaselineDatasetSchema):
        example_summaries = _example_summaries_from_schema(dataset)
        available_modalities = _normalize_text_tuple(
            modality
            for summary in example_summaries
            for modality in summary.feature_modalities
        )
        requested_modalities = _normalize_text_tuple(dataset.requested_modalities)
        missing_requested_modalities = tuple(
            modality
            for modality in requested_modalities
            if modality.casefold() not in {item.casefold() for item in available_modalities}
        )
        provenance = {
            "source_kind": "baseline_dataset_schema",
            "example_count": dataset.example_count,
            "lineage_complete_example_count": dataset.lineage_complete_example_count,
        }
        return (
            "baseline-reference-model-skeleton",
            "BaselineDatasetSchema",
            dataset.dataset_id,
            dataset.schema_version,
            requested_modalities,
            available_modalities,
            missing_requested_modalities,
            example_summaries,
            provenance,
        )

    if not isinstance(dataset, Mapping):
        raise TypeError(
            "dataset must be a BaselineDatasetSchema, ReferenceModelResult, or mapping"
        )

    if "example_summaries" in dataset:
        example_summaries = tuple(
            ReferenceExampleSummary(
                example_id=_clean_text(item.get("example_id")),
                protein_accession=_clean_text(item.get("protein_accession")),
                feature_modalities=_normalize_text_tuple(item.get("feature_modalities")),
                label_names=_normalize_text_tuple(item.get("label_names")),
                split=(
                    item.get("split")
                    if item.get("split") is None
                    else _clean_text(item.get("split"))
                ),
                lineage_complete=bool(item.get("lineage_complete")),
            )
            for item in tuple(dataset.get("example_summaries") or ())
        )
        requested_modalities = _normalize_text_tuple(dataset.get("requested_modalities"))
        available_modalities = _normalize_text_tuple(dataset.get("available_modalities"))
        if not available_modalities:
            available_modalities = _normalize_text_tuple(
                modality
                for summary in example_summaries
                for modality in summary.feature_modalities
            )
        missing_requested_modalities = _normalize_text_tuple(
            dataset.get("missing_requested_modalities")
        )
        provenance = dict(dataset.get("provenance") or {})
        provenance.setdefault("source_kind", "reference_model_result_mapping")
        return (
            _clean_text(dataset.get("model_name")) or "baseline-reference-model-skeleton",
            _clean_text(dataset.get("dataset_contract")) or "BaselineDatasetSchema",
            _clean_text(dataset.get("dataset_id")),
            int(dataset.get("schema_version", 1)),
            requested_modalities,
            available_modalities,
            missing_requested_modalities,
            example_summaries,
            provenance,
        )

    schema = BaselineDatasetSchema.from_dict(dataset)
    return _coerce_dataset_like(schema)


def summarize_reference_metrics(
    dataset: BaselineDatasetSchema | ReferenceModelResult | Mapping[str, Any],
    *,
    metrics_id: str = DEFAULT_REFERENCE_METRICS_ID,
    provenance: Mapping[str, Any] | None = None,
) -> ReferenceMetrics:
    (
        model_name,
        dataset_contract,
        dataset_id,
        schema_version,
        requested_modalities,
        available_modalities,
        missing_requested_modalities,
        example_summaries,
        inferred_provenance,
    ) = _coerce_dataset_like(dataset)

    if not example_summaries:
        raise ValueError("dataset must contain at least one example")

    example_metrics = tuple(
        _example_metric_from_summary(
            summary,
            example_index=index,
            requested_modalities=requested_modalities,
        )
        for index, summary in enumerate(example_summaries, start=1)
    )
    requested_coverage_values = tuple(
        metric.requested_coverage for metric in example_metrics
    )
    complete_requested_example_count = sum(
        1 for metric in example_metrics if metric.complete_requested_modalities
    )
    lineage_complete_example_count = sum(
        1 for metric in example_metrics if metric.lineage_complete
    )
    split_counts: dict[str, int] = {}
    for metric in example_metrics:
        split_counts[_split_key(metric.split)] = split_counts.get(_split_key(metric.split), 0) + 1
    requested_modality_presence_rate = {
        modality: sum(
            1
            for metric in example_metrics
            if modality.casefold() in {item.casefold() for item in metric.feature_modalities}
        )
        / float(len(example_metrics))
        for modality in requested_modalities
    }

    provenance_payload: dict[str, Any] = dict(inferred_provenance)
    if provenance is not None:
        provenance_payload.update(dict(provenance))
    provenance_payload.update(
        {
            "dataset_contract": dataset_contract,
            "dataset_id": dataset_id,
            "schema_version": schema_version,
            "example_count": len(example_metrics),
            "requested_modalities": list(requested_modalities),
            "available_modalities": list(available_modalities),
        }
    )

    return ReferenceMetrics(
        metrics_id=_clean_text(metrics_id) or DEFAULT_REFERENCE_METRICS_ID,
        model_name=model_name,
        dataset_contract=dataset_contract,
        dataset_id=dataset_id,
        schema_version=schema_version,
        example_count=len(example_metrics),
        requested_modalities=requested_modalities,
        available_modalities=available_modalities,
        missing_requested_modalities=missing_requested_modalities,
        requested_modality_presence_rate=requested_modality_presence_rate,
        requested_coverage_mean=_mean_or_zero(requested_coverage_values),
        requested_coverage_min=min(requested_coverage_values),
        requested_coverage_max=max(requested_coverage_values),
        complete_requested_example_count=complete_requested_example_count,
        complete_requested_rate=complete_requested_example_count / float(len(example_metrics)),
        lineage_complete_example_count=lineage_complete_example_count,
        lineage_complete_rate=lineage_complete_example_count / float(len(example_metrics)),
        split_counts=split_counts,
        example_metrics=example_metrics,
        provenance=provenance_payload,
    )


__all__ = [
    "DEFAULT_REFERENCE_METRICS_ID",
    "ReferenceExampleMetrics",
    "ReferenceMetrics",
    "summarize_reference_metrics",
]
