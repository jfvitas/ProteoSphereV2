from __future__ import annotations

import json
import shutil
from pathlib import Path

from scripts.restore_runtime_state import DEFAULT_REPORT_NAME, restore_runtime_state

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_restore_fixture_tree(repo_root: Path, temp_root: Path) -> None:
    for rel_path in (
        "tasks/task_queue.json",
        "artifacts/status/orchestrator_state.json",
        "runs/real_data_benchmark/full_results/release_bundle_manifest.json",
        "runs/real_data_benchmark/full_results/run_manifest.json",
        "runs/real_data_benchmark/full_results/run_summary.json",
        "runs/real_data_benchmark/full_results/checkpoint_summary.json",
        "runs/real_data_benchmark/full_results/live_inputs.json",
        "runs/real_data_benchmark/full_results/summary.json",
        "runs/real_data_benchmark/full_results/provenance_table.json",
        "runs/real_data_benchmark/full_results/source_coverage.json",
        "runs/real_data_benchmark/full_results/leakage_audit.json",
        "runs/real_data_benchmark/full_results/metrics_summary.json",
        "runs/real_data_benchmark/full_results/schema.json",
        "runs/real_data_benchmark/full_results/README.md",
        "runs/real_data_benchmark/full_results/checkpoints/full-cohort-trainer.json",
        "runs/real_data_benchmark/full_results/logs/full_rerun_stdout.log",
        "runs/real_data_benchmark/cohort/cohort_manifest.json",
        "runs/real_data_benchmark/cohort/split_labels.json",
        "docs/reports/release_grade_gap_analysis.md",
    ):
        source_path = repo_root / rel_path
        destination_path = temp_root / rel_path
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)


def test_restore_runtime_state_restores_queue_and_release_artifacts(tmp_path: Path) -> None:
    output_root = tmp_path / "restored"
    expected_task_count = len(
        json.loads((REPO_ROOT / "tasks" / "task_queue.json").read_text(encoding="utf-8"))
    )

    report = restore_runtime_state(source_root=REPO_ROOT, output_root=output_root)

    assert report["status"] == "restored"
    assert report["rollback"]["performed"] is False
    assert report["queue"]["task_queue"]["task_count"] == expected_task_count
    assert (
        report["release"]["bundle_manifest"]["bundle_id"]
        == "release-benchmark-bundle-2026-03-22"
    )
    assert report["release"]["missing_count"] == 0
    assert (output_root / "tasks" / "task_queue.json").exists()
    assert (output_root / "artifacts" / "status" / "orchestrator_state.json").exists()
    assert (
        output_root
        / "runs"
        / "real_data_benchmark"
        / "full_results"
        / "run_manifest.json"
    ).exists()
    assert (output_root / DEFAULT_REPORT_NAME).exists()
    assert _read_json(output_root / DEFAULT_REPORT_NAME)["status"] == "restored"


def test_restore_runtime_state_partial_restore_keeps_available_artifacts(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / "partial"
    _copy_restore_fixture_tree(REPO_ROOT, source_root)
    (source_root / "runs" / "real_data_benchmark" / "full_results" / "schema.json").unlink()

    report = restore_runtime_state(
        source_root=source_root,
        output_root=output_root,
        allow_partial=True,
    )

    assert report["status"] == "partial_restore"
    assert report["rollback"]["performed"] is False
    assert report["release"]["required_missing_count"] == 1
    assert any(
        item["role"] == "schema" and item["required"] is True
        for item in report["release"]["missing_artifacts"]
    )
    assert (output_root / "tasks" / "task_queue.json").exists()
    assert (
        output_root
        / "runs"
        / "real_data_benchmark"
        / "full_results"
        / "schema.json"
    ).exists() is False
    assert _read_json(output_root / DEFAULT_REPORT_NAME)["status"] == "partial_restore"


def test_restore_runtime_state_strict_mode_rolls_back_on_required_missing(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / "blocked"
    _copy_restore_fixture_tree(REPO_ROOT, source_root)
    (source_root / "runs" / "real_data_benchmark" / "full_results" / "schema.json").unlink()

    report = restore_runtime_state(source_root=source_root, output_root=output_root)

    assert report["status"] == "blocked"
    assert report["rollback"]["performed"] is True
    assert report["release"]["required_missing_count"] == 1
    assert not output_root.exists()
