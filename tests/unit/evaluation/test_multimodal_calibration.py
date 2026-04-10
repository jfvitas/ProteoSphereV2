from __future__ import annotations

import pytest

from evaluation.multimodal.calibration import (
    DEFAULT_MULTIMODAL_CALIBRATION_ID,
    MultimodalCalibrationReport,
    summarize_multimodal_calibration,
)


def test_summarize_multimodal_calibration_flags_underconfident_outputs() -> None:
    report = summarize_multimodal_calibration(
        (
            _calibration_payload(
                available_modalities=("sequence", "structure", "ligand"),
                missing_modalities=(),
                confidence=0.25,
                uncertainty=0.75,
            ),
        ),
        provenance={"audit": "unit-test"},
    )

    assert isinstance(report, MultimodalCalibrationReport)
    assert report.metrics_id == DEFAULT_MULTIMODAL_CALIBRATION_ID
    assert report.example_count == 1
    assert report.calibrated_count == 0
    assert report.underconfident_count == 1
    assert report.overconfident_count == 0
    assert report.confidence_quality_mean == pytest.approx(0.25)
    assert report.uncertainty_quality_mean == pytest.approx(0.25)
    assert report.confidence_mae == pytest.approx(0.75)
    assert report.uncertainty_mae == pytest.approx(0.75)
    assert report.examples[0].calibration_judgment == "underconfident"
    assert report.examples[0].confidence_quality == pytest.approx(0.25)
    assert report.examples[0].uncertainty_quality == pytest.approx(0.25)
    assert report.provenance["audit"] == "unit-test"
    assert report.to_dict()["example_count"] == 1


def test_summarize_multimodal_calibration_flags_overconfident_outputs() -> None:
    report = summarize_multimodal_calibration(
        (
            _calibration_payload(
                available_modalities=("sequence", "structure"),
                missing_modalities=("ligand",),
                confidence=0.95,
                uncertainty=0.05,
            ),
        )
    )

    assert report.example_count == 1
    assert report.calibrated_count == 0
    assert report.underconfident_count == 0
    assert report.overconfident_count == 1
    assert report.examples[0].calibration_judgment == "overconfident"
    assert report.examples[0].confidence_quality == pytest.approx(0.7166666667)
    assert report.examples[0].uncertainty_quality == pytest.approx(0.7166666667)
    assert report.confidence_bias_mean == pytest.approx(0.2833333333)
    assert report.uncertainty_bias_mean == pytest.approx(-0.2833333333)


def test_summarize_multimodal_calibration_rejects_inconsistent_payloads() -> None:
    with pytest.raises(ValueError, match="complementary"):
        summarize_multimodal_calibration(
            (
                _calibration_payload(
                    available_modalities=("sequence", "structure", "ligand"),
                    missing_modalities=(),
                    confidence=0.8,
                    uncertainty=0.1,
                ),
            )
        )


def _calibration_payload(
    *,
    available_modalities: tuple[str, ...],
    missing_modalities: tuple[str, ...],
    confidence: float,
    uncertainty: float,
) -> dict[str, object]:
    modalities = ("sequence", "structure", "ligand")
    return {
        "model_name": "multimodal-uncertainty-baseline-v1",
        "fusion_model_name": "multimodal-fusion-baseline-v1",
        "modalities": modalities,
        "available_modalities": available_modalities,
        "missing_modalities": missing_modalities,
        "confidence": confidence,
        "uncertainty": uncertainty,
        "metrics": {
            "coverage": len(available_modalities) / float(len(modalities)),
            "available_count": float(len(available_modalities)),
            "missing_count": float(len(missing_modalities)),
        },
        "source_kind": "multimodal_uncertainty_baseline",
        "frozen": True,
        "provenance": {"backend": "unit-test"},
    }
