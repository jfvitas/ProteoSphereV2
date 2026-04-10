from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from statistics import fmean
from typing import Any

from models.multimodal.uncertainty import UncertaintyHeadResult

DEFAULT_MULTIMODAL_CALIBRATION_ID = "multimodal-calibration"
_CALIBRATION_TOLERANCE = 0.05
_COMPLEMENT_TOLERANCE = 1e-6


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _mean_or_zero(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return fmean(float(value) for value in values)


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)):
        return (str(value),)
    if not isinstance(value, Sequence):
        value = (value,)
    return tuple(str(item) for item in value)


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


def _mapping_or_attribute(value: Any, *keys: str) -> Any:
    if isinstance(value, Mapping):
        for key in keys:
            if key in value:
                return value[key]
        return None
    for key in keys:
        if hasattr(value, key):
            return getattr(value, key)
    return None


def _coerce_record(value: UncertaintyHeadResult | Mapping[str, Any] | Any) -> dict[str, Any]:
    if isinstance(value, UncertaintyHeadResult):
        payload: dict[str, Any] = {
            "model_name": value.model_name,
            "fusion_model_name": value.fusion_model_name,
            "modalities": value.modalities,
            "available_modalities": value.available_modalities,
            "missing_modalities": value.missing_modalities,
            "confidence": value.confidence,
            "uncertainty": value.uncertainty,
            "metrics": dict(value.metrics),
            "source_kind": value.source_kind,
            "provenance": dict(value.provenance),
        }
        return payload

    if not isinstance(value, Mapping) and not any(
        hasattr(value, key)
        for key in (
            "confidence",
            "uncertainty",
            "available_modalities",
            "missing_modalities",
            "modalities",
        )
    ):
        raise TypeError("records must be UncertaintyHeadResult objects or mappings")

    payload = {
        "model_name": _clean_text(_mapping_or_attribute(value, "model_name")),
        "fusion_model_name": _clean_text(_mapping_or_attribute(value, "fusion_model_name")),
        "modalities": _as_tuple(_mapping_or_attribute(value, "modalities")),
        "available_modalities": _as_tuple(
            _mapping_or_attribute(value, "available_modalities")
        ),
        "missing_modalities": _as_tuple(_mapping_or_attribute(value, "missing_modalities")),
        "confidence": _mapping_or_attribute(value, "confidence"),
        "uncertainty": _mapping_or_attribute(value, "uncertainty"),
        "metrics": dict(_mapping_or_attribute(value, "metrics") or {}),
        "source_kind": _clean_text(_mapping_or_attribute(value, "source_kind")),
        "provenance": _coerce_provenance(_mapping_or_attribute(value, "provenance")),
    }
    return payload


@dataclass(frozen=True, slots=True)
class MultimodalCalibrationExample:
    example_index: int
    model_name: str
    fusion_model_name: str
    modalities: tuple[str, ...]
    available_modalities: tuple[str, ...]
    missing_modalities: tuple[str, ...]
    coverage: float
    target_confidence: float
    target_uncertainty: float
    confidence: float
    uncertainty: float
    confidence_error: float
    uncertainty_error: float
    confidence_quality: float
    uncertainty_quality: float
    calibration_judgment: str
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "example_index": self.example_index,
            "model_name": self.model_name,
            "fusion_model_name": self.fusion_model_name,
            "modalities": list(self.modalities),
            "available_modalities": list(self.available_modalities),
            "missing_modalities": list(self.missing_modalities),
            "coverage": self.coverage,
            "target_confidence": self.target_confidence,
            "target_uncertainty": self.target_uncertainty,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "confidence_error": self.confidence_error,
            "uncertainty_error": self.uncertainty_error,
            "confidence_quality": self.confidence_quality,
            "uncertainty_quality": self.uncertainty_quality,
            "calibration_judgment": self.calibration_judgment,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class MultimodalCalibrationReport:
    metrics_id: str
    model_name: str
    fusion_model_name: str
    modalities: tuple[str, ...]
    example_count: int
    calibrated_count: int
    underconfident_count: int
    overconfident_count: int
    calibrated_rate: float
    confidence_quality_mean: float
    confidence_quality_min: float
    confidence_quality_max: float
    uncertainty_quality_mean: float
    uncertainty_quality_min: float
    uncertainty_quality_max: float
    confidence_mae: float
    uncertainty_mae: float
    confidence_bias_mean: float
    uncertainty_bias_mean: float
    examples: tuple[MultimodalCalibrationExample, ...]
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metrics_id": self.metrics_id,
            "model_name": self.model_name,
            "fusion_model_name": self.fusion_model_name,
            "modalities": list(self.modalities),
            "example_count": self.example_count,
            "calibrated_count": self.calibrated_count,
            "underconfident_count": self.underconfident_count,
            "overconfident_count": self.overconfident_count,
            "calibrated_rate": self.calibrated_rate,
            "confidence_quality_mean": self.confidence_quality_mean,
            "confidence_quality_min": self.confidence_quality_min,
            "confidence_quality_max": self.confidence_quality_max,
            "uncertainty_quality_mean": self.uncertainty_quality_mean,
            "uncertainty_quality_min": self.uncertainty_quality_min,
            "uncertainty_quality_max": self.uncertainty_quality_max,
            "confidence_mae": self.confidence_mae,
            "uncertainty_mae": self.uncertainty_mae,
            "confidence_bias_mean": self.confidence_bias_mean,
            "uncertainty_bias_mean": self.uncertainty_bias_mean,
            "examples": [example.to_dict() for example in self.examples],
            "provenance": dict(self.provenance),
        }


def _validate_record_shape(record: dict[str, Any]) -> tuple[float, float, float]:
    modalities = record["modalities"]
    available_modalities = tuple(
        modality for modality in modalities if modality in record["available_modalities"]
    )
    missing_modalities = tuple(
        modality for modality in modalities if modality not in available_modalities
    )
    if len(available_modalities) + len(missing_modalities) != len(modalities):
        raise ValueError("modalities must partition into available and missing sets")

    confidence = float(record["confidence"])
    uncertainty = float(record["uncertainty"])
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0 and 1")
    if not 0.0 <= uncertainty <= 1.0:
        raise ValueError("uncertainty must be between 0 and 1")
    if abs((confidence + uncertainty) - 1.0) > _COMPLEMENT_TOLERANCE:
        raise ValueError("confidence and uncertainty must be complementary")

    metrics = record["metrics"]
    coverage = (
        float(metrics["coverage"])
        if "coverage" in metrics
        else len(available_modalities) / float(len(modalities))
    )
    if not 0.0 <= coverage <= 1.0:
        raise ValueError("coverage must be between 0 and 1")
    if "coverage" in metrics and abs(float(metrics["coverage"]) - coverage) > _COMPLEMENT_TOLERANCE:
        raise ValueError("coverage does not match the modality counts")
    if (
        "available_count" in metrics
        and abs(float(metrics["available_count"]) - len(available_modalities))
        > _COMPLEMENT_TOLERANCE
    ):
        raise ValueError("available_count does not match the modality counts")
    if (
        "missing_count" in metrics
        and abs(float(metrics["missing_count"]) - len(missing_modalities))
        > _COMPLEMENT_TOLERANCE
    ):
        raise ValueError("missing_count does not match the modality counts")

    target_confidence = coverage
    target_uncertainty = 1.0 - coverage
    confidence_error = confidence - target_confidence
    uncertainty_error = uncertainty - target_uncertainty
    return target_confidence, target_uncertainty, confidence_error, uncertainty_error


def _quality_from_error(error: float) -> float:
    return max(0.0, 1.0 - abs(error))


def _calibration_label(confidence_error: float) -> str:
    if confidence_error < -_CALIBRATION_TOLERANCE:
        return "underconfident"
    if confidence_error > _CALIBRATION_TOLERANCE:
        return "overconfident"
    return "calibrated"


def _example_metric(
    record: dict[str, Any],
    *,
    example_index: int,
) -> MultimodalCalibrationExample:
    target_confidence, target_uncertainty, confidence_error, uncertainty_error = (
        _validate_record_shape(record)
    )
    confidence = float(record["confidence"])
    uncertainty = float(record["uncertainty"])
    modalities = tuple(record["modalities"])
    available_modalities = tuple(
        modality for modality in modalities if modality in record["available_modalities"]
    )
    missing_modalities = tuple(
        modality for modality in modalities if modality not in available_modalities
    )
    coverage = len(available_modalities) / float(len(modalities))
    confidence_quality = _quality_from_error(confidence_error)
    uncertainty_quality = _quality_from_error(uncertainty_error)
    calibration_judgment = _calibration_label(confidence_error)
    provenance = {
        "source_kind": record["source_kind"] or "multimodal_uncertainty_baseline",
        "metrics": dict(record["metrics"]),
    }
    provenance.update(record["provenance"])
    provenance["calibration_judgment"] = calibration_judgment
    return MultimodalCalibrationExample(
        example_index=example_index,
        model_name=record["model_name"],
        fusion_model_name=record["fusion_model_name"],
        modalities=modalities,
        available_modalities=available_modalities,
        missing_modalities=missing_modalities,
        coverage=coverage,
        target_confidence=target_confidence,
        target_uncertainty=target_uncertainty,
        confidence=confidence,
        uncertainty=uncertainty,
        confidence_error=confidence_error,
        uncertainty_error=uncertainty_error,
        confidence_quality=confidence_quality,
        uncertainty_quality=uncertainty_quality,
        calibration_judgment=calibration_judgment,
        provenance=provenance,
    )


def summarize_multimodal_calibration(
    results: Sequence[UncertaintyHeadResult | Mapping[str, Any] | Any],
    *,
    metrics_id: str = DEFAULT_MULTIMODAL_CALIBRATION_ID,
    provenance: Mapping[str, Any] | None = None,
) -> MultimodalCalibrationReport:
    materialized = tuple(results)
    if not materialized:
        raise ValueError("results must contain at least one uncertainty result")

    normalized = tuple(_coerce_record(result) for result in materialized)
    first = normalized[0]
    for record in normalized[1:]:
        if record["model_name"] != first["model_name"]:
            raise ValueError("results must share the same model_name")
        if record["fusion_model_name"] != first["fusion_model_name"]:
            raise ValueError("results must share the same fusion_model_name")
        if record["modalities"] != first["modalities"]:
            raise ValueError("results must share the same modality contract")

    examples = tuple(
        _example_metric(record, example_index=index)
        for index, record in enumerate(normalized, start=1)
    )

    confidence_quality_values = tuple(example.confidence_quality for example in examples)
    uncertainty_quality_values = tuple(example.uncertainty_quality for example in examples)
    confidence_errors = tuple(example.confidence_error for example in examples)
    uncertainty_errors = tuple(example.uncertainty_error for example in examples)
    calibrated_count = sum(
        1 for example in examples if example.calibration_judgment == "calibrated"
    )
    underconfident_count = sum(
        1 for example in examples if example.calibration_judgment == "underconfident"
    )
    overconfident_count = sum(
        1 for example in examples if example.calibration_judgment == "overconfident"
    )

    provenance_payload: dict[str, Any] = {}
    if provenance is not None:
        provenance_payload.update(_coerce_provenance(provenance))
    provenance_payload.update(
        {
            "source_model_name": first["model_name"],
            "fusion_model_name": first["fusion_model_name"],
            "modalities": list(first["modalities"]),
            "example_count": len(examples),
        }
    )

    return MultimodalCalibrationReport(
        metrics_id=_clean_text(metrics_id) or DEFAULT_MULTIMODAL_CALIBRATION_ID,
        model_name=first["model_name"],
        fusion_model_name=first["fusion_model_name"],
        modalities=tuple(first["modalities"]),
        example_count=len(examples),
        calibrated_count=calibrated_count,
        underconfident_count=underconfident_count,
        overconfident_count=overconfident_count,
        calibrated_rate=calibrated_count / float(len(examples)),
        confidence_quality_mean=_mean_or_zero(confidence_quality_values),
        confidence_quality_min=min(confidence_quality_values),
        confidence_quality_max=max(confidence_quality_values),
        uncertainty_quality_mean=_mean_or_zero(uncertainty_quality_values),
        uncertainty_quality_min=min(uncertainty_quality_values),
        uncertainty_quality_max=max(uncertainty_quality_values),
        confidence_mae=_mean_or_zero(tuple(abs(value) for value in confidence_errors)),
        uncertainty_mae=_mean_or_zero(tuple(abs(value) for value in uncertainty_errors)),
        confidence_bias_mean=_mean_or_zero(confidence_errors),
        uncertainty_bias_mean=_mean_or_zero(uncertainty_errors),
        examples=examples,
        provenance=provenance_payload,
    )


__all__ = [
    "DEFAULT_MULTIMODAL_CALIBRATION_ID",
    "MultimodalCalibrationExample",
    "MultimodalCalibrationReport",
    "summarize_multimodal_calibration",
]
