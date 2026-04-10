from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_RESULTS_DIR = REPO_ROOT / "runs" / "real_data_benchmark" / "full_results"
DEFAULT_RUN_MANIFEST = DEFAULT_RESULTS_DIR / "run_manifest.json"
DEFAULT_RUN_SUMMARY = DEFAULT_RESULTS_DIR / "run_summary.json"
DEFAULT_CHECKPOINT_SUMMARY = DEFAULT_RESULTS_DIR / "checkpoint_summary.json"
DEFAULT_LOG_PATH = DEFAULT_RESULTS_DIR / "logs" / "full_rerun_stdout.log"
DEFAULT_OUTPUT = DEFAULT_RESULTS_DIR / "metrics_summary.json"
DEFAULT_COHORT_MANIFEST = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "cohort" / "cohort_manifest.json"
)
DEFAULT_SPLIT_LABELS = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "cohort" / "split_labels.json"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _loss_summary(losses: Iterable[float]) -> dict[str, Any]:
    values = [float(value) for value in losses]
    if not values:
        return {
            "count": 0,
            "first": None,
            "last": None,
            "min": None,
            "max": None,
            "mean": None,
            "median": None,
            "values": [],
        }
    return {
        "count": len(values),
        "first": values[0],
        "last": values[-1],
        "min": min(values),
        "max": max(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "values": values,
    }


def _compact_checkpoint(checkpoint: dict[str, Any]) -> dict[str, Any]:
    return {
        "checkpoint_path": checkpoint.get("checkpoint_path"),
        "checkpoint_ref": checkpoint.get("checkpoint_ref"),
        "checkpoint_tag": checkpoint.get("checkpoint_tag"),
        "processed_examples": checkpoint.get("processed_examples"),
        "completed_example_ids": checkpoint.get("completed_example_ids", []),
        "processable_example_ids": checkpoint.get("processable_example_ids", []),
        "resumed_from": checkpoint.get("resumed_from"),
        "dataset_signature": checkpoint.get("dataset_signature"),
        "plan_signature": checkpoint.get("plan_signature"),
        "head_bias": checkpoint.get("head_bias"),
        "head_weights_count": len(checkpoint.get("head_weights", [])),
        "loss_summary": _loss_summary(checkpoint.get("loss_history", [])),
        "provenance": checkpoint.get("provenance", {}),
    }


def _load_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def _require_exists(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"missing {label}: {path}")


def _validate_counts(
    *,
    run_manifest: dict[str, Any],
    run_summary: dict[str, Any],
    checkpoint_summary: dict[str, Any],
    cohort_manifest: dict[str, Any],
    split_labels: dict[str, Any],
) -> None:
    expected_total = cohort_manifest["target_size"]
    expected_splits = split_labels["counts"]
    run_split_counts = run_summary["split_counts"]
    manifest_split_counts = run_manifest["inputs"]["split_counts"]

    if expected_total != split_labels["counts"]["total"]:
        raise ValueError("cohort target size and split total diverge")
    if expected_splits != run_split_counts:
        raise ValueError("split labels and run summary diverge")
    if expected_splits != manifest_split_counts:
        raise ValueError("split labels and run manifest diverge")

    first_run = run_summary["first_run"]
    resumed_run = run_summary["resumed_run"]
    first_checkpoint = checkpoint_summary["first_checkpoint"]
    resumed_checkpoint = checkpoint_summary["resumed_checkpoint"]

    if first_run["processed_examples"] != first_checkpoint["processed_examples"]:
        raise ValueError("first-run processed counts diverge from checkpoint summary")
    if resumed_run["processed_examples"] != resumed_checkpoint["processed_examples"]:
        raise ValueError("resumed-run processed counts diverge from checkpoint summary")

    if first_run["processed_examples"] != run_manifest["execution"]["first_run_processed_examples"]:
        raise ValueError("first-run processed counts diverge from run manifest")
    if resumed_run["processed_examples"] != run_manifest["execution"][
        "resumed_run_processed_examples"
    ]:
        raise ValueError("resumed-run processed counts diverge from run manifest")


def build_metrics_summary(
    *,
    run_manifest_path: Path = DEFAULT_RUN_MANIFEST,
    run_summary_path: Path = DEFAULT_RUN_SUMMARY,
    checkpoint_summary_path: Path = DEFAULT_CHECKPOINT_SUMMARY,
    log_path: Path = DEFAULT_LOG_PATH,
    cohort_manifest_path: Path = DEFAULT_COHORT_MANIFEST,
    split_labels_path: Path = DEFAULT_SPLIT_LABELS,
) -> dict[str, Any]:
    for path, label in (
        (run_manifest_path, "run manifest"),
        (run_summary_path, "run summary"),
        (checkpoint_summary_path, "checkpoint summary"),
        (log_path, "log"),
        (cohort_manifest_path, "cohort manifest"),
        (split_labels_path, "split labels"),
    ):
        _require_exists(path, label)

    run_manifest = _read_json(run_manifest_path)
    run_summary = _read_json(run_summary_path)
    checkpoint_summary = _read_json(checkpoint_summary_path)
    cohort_manifest = _read_json(cohort_manifest_path)
    split_labels = _read_json(split_labels_path)
    log_lines = _load_lines(log_path)

    _validate_counts(
        run_manifest=run_manifest,
        run_summary=run_summary,
        checkpoint_summary=checkpoint_summary,
        cohort_manifest=cohort_manifest,
        split_labels=split_labels,
    )

    first_run = run_summary["first_run"]
    resumed_run = run_summary["resumed_run"]
    first_checkpoint = checkpoint_summary["first_checkpoint"]
    resumed_checkpoint = checkpoint_summary["resumed_checkpoint"]
    run_execution = run_manifest["execution"]

    checkpoint_continuity = {
        "declared": run_execution["resume_continuity"],
        "same_checkpoint_path": (
            first_checkpoint["checkpoint_path"] == resumed_checkpoint["checkpoint_path"]
        ),
        "same_checkpoint_ref": (
            first_checkpoint["checkpoint_ref"] == resumed_checkpoint["checkpoint_ref"]
        ),
        "same_processed_example_ids": (
            first_checkpoint["completed_example_ids"]
            == resumed_checkpoint["completed_example_ids"][
                : len(first_checkpoint["completed_example_ids"])
            ]
        ),
        "processed_example_delta": (
            resumed_run["processed_examples"] - first_run["processed_examples"]
        ),
    }

    metrics_summary = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "task_id": "P6-T019",
        "status": run_manifest["status"],
        "benchmark_task": run_summary["benchmark_task"],
        "results_dir": str(DEFAULT_RESULTS_DIR).replace("\\", "/"),
        "truth_boundary": {
            "runtime_surface": run_manifest["runtime_surface"],
            "prototype_runtime": True,
            "allowed_status": "completed_on_prototype_runtime",
            "forbidden_overclaims": [
                "production-equivalent runtime",
                "full corpus success without output artifacts",
                "silent cohort widening",
                "silent leakage across splits",
            ],
        },
        "source_files": {
            "run_manifest": str(run_manifest_path).replace("\\", "/"),
            "run_summary": str(run_summary_path).replace("\\", "/"),
            "checkpoint_summary": str(checkpoint_summary_path).replace("\\", "/"),
            "log": str(log_path).replace("\\", "/"),
            "cohort_manifest": str(cohort_manifest_path).replace("\\", "/"),
            "split_labels": str(split_labels_path).replace("\\", "/"),
        },
        "cohort": {
            "manifest_id": cohort_manifest["manifest_id"],
            "target_size": cohort_manifest["target_size"],
            "resolved_count": cohort_manifest["resolved_count"],
            "unresolved_count": cohort_manifest["unresolved_count"],
            "split_policy": cohort_manifest["split_policy"],
            "split_counts": split_labels["counts"],
            "cohort_shape": cohort_manifest["cohort_shape"],
            "accession_level_only": split_labels["leakage_ready"]["accession_level_only"],
            "cross_split_duplicates": split_labels["leakage_ready"]["cross_split_duplicates"],
        },
        "run": {
            "manifest_id": run_manifest["manifest_id"],
            "command": run_manifest["command"],
            "prepare_command": run_manifest["prepare_command"],
            "execution_mode": run_manifest["execution"]["mode"],
            "attempted": run_manifest["execution"]["attempted"],
            "final_status": run_manifest["execution"]["final_status"],
            "cohort_status": run_summary["cohort_status"],
            "selected_accession_count": run_summary["selected_accession_count"],
            "split_counts": run_summary["split_counts"],
            "requested_modalities": run_manifest["execution"]["requested_modalities"],
            "runtime_surface": run_summary["runtime_surface"],
            "remaining_gaps": run_summary["remaining_gaps"],
            "limitations": run_manifest["limitations"],
        },
        "runtime": {
            "first_run_processed_examples": first_run["processed_examples"],
            "resumed_run_processed_examples": resumed_run["processed_examples"],
            "checkpoint_writes": run_manifest["execution"]["checkpoint_writes"],
            "checkpoint_resumes": run_manifest["execution"]["checkpoint_resumes"],
            "resume_continuity": checkpoint_continuity,
            "first_run_available_modalities": first_run["available_modalities"],
            "resumed_run_available_modalities": resumed_run["available_modalities"],
            "summary_library_record_count": run_summary["summary_library"]["record_count"],
        },
        "loss_summary": {
            "first_run": _loss_summary(first_checkpoint["loss_history"]),
            "resumed_run": _loss_summary(resumed_checkpoint["loss_history"]),
        },
        "checkpoint_summary": {
            "first_run": _compact_checkpoint(first_checkpoint),
            "resumed_run": _compact_checkpoint(resumed_checkpoint),
        },
        "log_summary": {
            "line_count": len(log_lines),
            "contains_first_pass_marker": any(
                "first_pass=6 examples" in line for line in log_lines
            ),
            "contains_resume_completed_marker": any(
                "resume=completed" in line for line in log_lines
            ),
            "contains_runtime_surface_marker": any(
                "runtime_surface=local prototype runtime" in line for line in log_lines
            ),
        },
        "blocker_categories": run_manifest["blocker_categories"],
    }

    return metrics_summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Emit a machine-readable benchmark metrics summary pack.",
    )
    parser.add_argument("--run-manifest", type=Path, default=DEFAULT_RUN_MANIFEST)
    parser.add_argument("--run-summary", type=Path, default=DEFAULT_RUN_SUMMARY)
    parser.add_argument(
        "--checkpoint-summary",
        type=Path,
        default=DEFAULT_CHECKPOINT_SUMMARY,
    )
    parser.add_argument("--log-path", type=Path, default=DEFAULT_LOG_PATH)
    parser.add_argument("--cohort-manifest", type=Path, default=DEFAULT_COHORT_MANIFEST)
    parser.add_argument("--split-labels", type=Path, default=DEFAULT_SPLIT_LABELS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    summary = build_metrics_summary(
        run_manifest_path=args.run_manifest,
        run_summary_path=args.run_summary,
        checkpoint_summary_path=args.checkpoint_summary,
        log_path=args.log_path,
        cohort_manifest_path=args.cohort_manifest,
        split_labels_path=args.split_labels,
    )
    _write_json(args.output, summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
