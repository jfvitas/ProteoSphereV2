from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN_SUMMARY = ROOT / "runs" / "real_data_benchmark" / "full_results" / "run_summary.json"
CHECKPOINT_SUMMARY = (
    ROOT / "runs" / "real_data_benchmark" / "full_results" / "checkpoint_summary.json"
)
METRICS_SUMMARY = ROOT / "runs" / "real_data_benchmark" / "full_results" / "metrics_summary.json"
REPORT = ROOT / "docs" / "reports" / "p19_training_envelopes.md"


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_training_envelopes_are_repeatable_and_resume_stable() -> None:
    run_summary = _read_json(RUN_SUMMARY)
    metrics_summary = _read_json(METRICS_SUMMARY)
    split_counts = run_summary["split_counts"]  # type: ignore[index]
    first_run = run_summary["first_run"]  # type: ignore[index]
    resumed_run = run_summary["resumed_run"]  # type: ignore[index]
    metrics_loss_summary = metrics_summary["loss_summary"]  # type: ignore[index]
    cohort_summary = metrics_summary["cohort"]  # type: ignore[index]
    runtime_summary = metrics_summary["runtime"]  # type: ignore[index]

    assert run_summary["cohort_status"] == "frozen_12_accession_run_complete_on_prototype_runtime"
    assert run_summary["selected_accession_count"] == 12
    assert split_counts == {
        "resolved": 12,
        "test": 2,
        "total": 12,
        "train": 8,
        "unresolved": 0,
        "val": 2,
    }
    assert run_summary["runtime_surface"] == (
        "local prototype runtime with surrogate modality embeddings and "
        "identity-safe resume continuity"
    )

    assert runtime_summary["checkpoint_resumes"] == 1
    assert runtime_summary["checkpoint_writes"] == 2
    assert runtime_summary["resume_continuity"] == {
        "declared": "identity-safe",
        "processed_example_delta": 6,
        "same_checkpoint_path": True,
        "same_checkpoint_ref": True,
        "same_processed_example_ids": True,
    }
    assert first_run["checkpoint_ref"] == resumed_run["checkpoint_ref"]
    assert first_run["checkpoint_path"] == resumed_run["checkpoint_path"]
    assert first_run["processed_examples"] == 6
    assert resumed_run["processed_examples"] == 12
    assert first_run["completed_example_ids"] == [
        "P69905",
        "P68871",
        "P04637",
        "P31749",
        "Q9NZD4",
        "Q2TAC2",
    ]
    assert resumed_run["completed_example_ids"] == [
        "P69905",
        "P68871",
        "P04637",
        "P31749",
        "Q9NZD4",
        "Q2TAC2",
        "P00387",
        "P02042",
        "P02100",
        "P69892",
        "P09105",
        "Q9UCM0",
    ]
    assert first_run["loss_history"] == [
        0.4182014703584182,
        0.00414239629369404,
        0.0014039822489337003,
        0.004468375670382288,
        0.004625745748011499,
        0.0005759156567932949,
    ]
    assert resumed_run["loss_history"] == [
        0.4182014703584182,
        0.00414239629369404,
        0.0014039822489337003,
        0.004468375670382288,
        0.004625745748011499,
        0.0005759156567932949,
        0.006825779341999685,
        0.0028791988351548614,
        0.19415306271289642,
        0.006477222253648755,
        0.0016413822351332762,
        0.0009405410993406097,
    ]
    assert cohort_summary["split_counts"]["train"] == 8  # type: ignore[index]
    assert cohort_summary["split_counts"]["val"] == 2  # type: ignore[index]
    assert cohort_summary["split_counts"]["test"] == 2  # type: ignore[index]
    assert cohort_summary["unresolved_count"] == 0
    assert cohort_summary["cross_split_duplicates"] == []

    assert first_run["run_id"] == resumed_run["run_id"] == "multimodal-run:c6ff74a7fb07cdcf"
    assert first_run["checkpoint_tag"] == resumed_run["checkpoint_tag"]
    assert metrics_loss_summary["first_run"]["mean"] == 0.07223631432937218  # type: ignore[index]
    assert metrics_loss_summary["resumed_run"]["mean"] == 0.053861256037867226  # type: ignore[index]
    assert metrics_loss_summary["resumed_run"]["mean"] < metrics_loss_summary[
        "first_run"
    ]["mean"]  # type: ignore[index]
    threshold = metrics_loss_summary["first_run"]["mean"] * 0.8  # type: ignore[index]
    assert metrics_loss_summary["resumed_run"]["mean"] <= threshold  # type: ignore[index]
    assert metrics_loss_summary["first_run"]["count"] == 6  # type: ignore[index]
    assert metrics_loss_summary["resumed_run"]["count"] == 12  # type: ignore[index]
    assert metrics_loss_summary["first_run"]["min"] == metrics_loss_summary[
        "resumed_run"
    ]["min"]  # type: ignore[index]
    assert metrics_loss_summary["first_run"]["max"] == metrics_loss_summary[
        "resumed_run"
    ]["max"]  # type: ignore[index]

    report = REPORT.read_text(encoding="utf-8")
    assert "repeatable checkpoint identity" in report
    assert "resume stability" in report
    assert "production-grade or weeklong-soak claim" in report
