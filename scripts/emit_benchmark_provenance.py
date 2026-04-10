from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

COHORT_MANIFEST = REPO_ROOT / "runs" / "real_data_benchmark" / "cohort" / "cohort_manifest.json"
SPLIT_LABELS = REPO_ROOT / "runs" / "real_data_benchmark" / "cohort" / "split_labels.json"
RUN_MANIFEST = REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "run_manifest.json"
RUN_SUMMARY = REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "run_summary.json"
SUMMARY = REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "summary.json"
CHECKPOINT_SUMMARY = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "checkpoint_summary.json"
)
LIVE_INPUTS = REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "live_inputs.json"
FULL_RESULTS_README = REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "README.md"
OUTPUT = REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "provenance_table.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _path(value: Path) -> str:
    return value.as_posix()


def _select_fields(payload: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: payload[field] for field in fields if field in payload}


def _checkpoint_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    provenance = payload.get("provenance", {})
    return {
        "run_id": payload.get("run_id"),
        "checkpoint_tag": payload.get("checkpoint_tag"),
        "checkpoint_ref": payload.get("checkpoint_ref"),
        "checkpoint_path": payload.get("checkpoint_path"),
        "processed_examples": payload.get("processed_examples"),
        "processable_example_ids": list(payload.get("processable_example_ids", [])),
        "completed_example_ids": list(payload.get("completed_example_ids", [])),
        "resumed_from": payload.get("resumed_from"),
        "dataset_signature": payload.get("dataset_signature"),
        "plan_signature": payload.get("plan_signature"),
        "deterministic_seed": payload.get("deterministic_seed"),
        "provenance": _select_fields(
            provenance,
            (
                "backend",
                "objective",
                "learning_rate",
                "requested_modalities",
                "fusion_modalities",
                "processable_example_ids",
                "completed_example_ids",
                "processed_example_ids",
            ),
        ),
    }


def _normalise_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "accession": row["accession"],
        "split": row["split"],
        "bucket": row["bucket"],
        "status": row["status"],
        "evidence_mode": row["evidence_mode"],
        "source_lanes": list(row.get("source_lanes", [])),
        "evidence_refs": list(row.get("evidence_refs", [])),
        "leakage_key": row["leakage_key"],
    }


def _compare_lists(name: str, left: list[Any], right: list[Any]) -> None:
    if left != right:
        raise SystemExit(f"{name} mismatch: {left!r} != {right!r}")


def _validate_inputs(
    cohort_manifest: dict[str, Any],
    split_labels: dict[str, Any],
    live_inputs: dict[str, Any],
    run_manifest: dict[str, Any],
    run_summary: dict[str, Any],
    summary: dict[str, Any],
    checkpoint_summary: dict[str, Any],
) -> dict[str, Any]:
    cohort_rows = cohort_manifest["cohort"]
    live_rows = live_inputs["cohort"]
    labels = split_labels["labels"]

    _compare_lists("cohort/live_inputs row count", [len(cohort_rows)], [len(live_rows)])
    _compare_lists("cohort/split_labels row count", [len(cohort_rows)], [len(labels)])
    _compare_lists(
        "cohort/live_inputs rows",
        [_normalise_row(row) for row in cohort_rows],
        [_normalise_row(row) for row in live_rows],
    )
    _compare_lists(
        "cohort/split_labels accessions",
        [row["accession"] for row in cohort_rows],
        [row["accession"] for row in labels],
    )
    _compare_lists(
        "cohort/split_labels splits",
        [row["split"] for row in cohort_rows],
        [row["split"] for row in labels],
    )
    _compare_lists(
        "first checkpoint cohort prefix",
        [
            row["accession"]
            for row in cohort_rows[
                : len(checkpoint_summary["first_checkpoint"]["completed_example_ids"])
            ]
        ],
        list(checkpoint_summary["first_checkpoint"]["completed_example_ids"]),
    )
    if not cohort_manifest["split_leakage_metadata"]["accession_level_only"]:
        raise SystemExit("cohort is expected to be accession-level only")
    if cohort_manifest["split_leakage_metadata"]["duplicate_accessions"] != []:
        raise SystemExit("cohort manifest unexpectedly contains duplicate accessions")
    if cohort_manifest["split_leakage_metadata"]["cross_split_duplicates"] != []:
        raise SystemExit("cohort manifest unexpectedly contains cross-split duplicates")

    first_checkpoint = checkpoint_summary["first_checkpoint"]
    resumed_checkpoint = checkpoint_summary["resumed_checkpoint"]
    if first_checkpoint["processed_examples"] != 6:
        raise SystemExit(
            "first checkpoint expected 6 processed examples, "
            f"got {first_checkpoint['processed_examples']}"
        )
    if resumed_checkpoint["processed_examples"] != 12:
        raise SystemExit(
            "resumed checkpoint expected 12 processed examples, "
            f"got {resumed_checkpoint['processed_examples']}"
        )
    _compare_lists(
        "checkpoint resume continuity",
        first_checkpoint["processable_example_ids"],
        resumed_checkpoint["processable_example_ids"],
    )
    if resumed_checkpoint["resumed_from"] != first_checkpoint["checkpoint_ref"]:
        raise SystemExit(
            "resumed checkpoint does not point back to the first checkpoint ref"
        )
    if run_manifest["status"] != "completed_on_prototype_runtime":
        raise SystemExit(f"unexpected run manifest status: {run_manifest['status']!r}")
    if run_summary["selected_accession_count"] != 12:
        raise SystemExit(
            f"expected 12 selected accessions, got {run_summary['selected_accession_count']}"
        )
    if run_summary["cohort_status"] != "frozen_12_accession_run_complete_on_prototype_runtime":
        raise SystemExit(f"unexpected run summary cohort status: {run_summary['cohort_status']!r}")
    if summary["status"] not in {"blocked_on_release_grade_bar", "completed"}:
        raise SystemExit(f"unexpected summary status: {summary['status']!r}")

    return {
        "selected_accession_count": run_summary["selected_accession_count"],
        "split_counts": run_summary["split_counts"],
        "requested_modalities": list(run_manifest["execution"]["requested_modalities"]),
        "runtime_surface": run_summary["runtime_surface"],
        "run_id": resumed_checkpoint["run_id"],
        "checkpoint_ref": resumed_checkpoint["checkpoint_ref"],
        "checkpoint_path": resumed_checkpoint["checkpoint_path"],
        "checkpoint_tag": resumed_checkpoint["checkpoint_tag"],
        "first_run_processed_examples": run_summary["first_run"]["processed_examples"],
        "resumed_run_processed_examples": run_summary["resumed_run"]["processed_examples"],
        "checkpoint_writes": run_manifest["execution"]["checkpoint_writes"],
        "checkpoint_resumes": run_manifest["execution"]["checkpoint_resumes"],
        "final_status": run_manifest["execution"]["final_status"],
        "resume_continuity": run_manifest["execution"]["resume_continuity"],
        "plan_backend_ready": run_summary["first_run"]["plan_backend_ready"],
        "plan_blocker": run_summary["first_run"]["plan_blocker"],
    }


def _build_rows(
    cohort_rows: list[dict[str, Any]],
    first_checkpoint_ids: list[str],
    resumed_checkpoint: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    first_checkpoint_set = set(first_checkpoint_ids)

    for index, row in enumerate(cohort_rows, start=1):
        accession = row["accession"]
        first_pass_visible = accession in first_checkpoint_set
        row_payload = {
            "row_index": index,
            "accession": accession,
            "canonical_id": f"protein:{accession}",
            "split": row["split"],
            "bucket": row["bucket"],
            "status": row["status"],
            "leakage_key": row["leakage_key"],
            "evidence_mode": row["evidence_mode"],
            "source_lanes": list(row.get("source_lanes", [])),
            "evidence_refs": list(row.get("evidence_refs", [])),
            "planning_index_ref": f"planning/{accession}",
            "checkpoint_coverage": {
                "first_pass_visible": first_pass_visible,
                "resumed_visible": True,
                "first_checkpoint_index": (
                    first_checkpoint_ids.index(accession) + 1 if first_pass_visible else None
                ),
                "final_checkpoint_index": (
                    resumed_checkpoint["completed_example_ids"].index(accession) + 1
                ),
            },
            "provenance_notes": _provenance_note(row["evidence_mode"]),
        }
        rows.append(row_payload)
    return rows


def _provenance_note(evidence_mode: str) -> str:
    notes = {
        "direct_live_smoke": "Backed by direct live-smoke evidence in the cited reports.",
        "live_summary_library_probe": (
            "Backed by the in-tree live probe and the summary-library evidence trail."
        ),
        "in_tree_live_snapshot": (
            "Backed by the in-tree live-derived snapshot artifact; "
            "not independently re-queried here."
        ),
        "live_verified_accession": (
            "Backed by the live-verified accession snapshot in the in-tree probe."
        ),
    }
    return notes.get(evidence_mode, "Evidence trail preserved from the frozen cohort manifest.")


def build_provenance_table() -> dict[str, Any]:
    cohort_manifest = _read_json(COHORT_MANIFEST)
    split_labels = _read_json(SPLIT_LABELS)
    run_manifest = _read_json(RUN_MANIFEST)
    run_summary = _read_json(RUN_SUMMARY)
    summary = _read_json(SUMMARY)
    checkpoint_summary = _read_json(CHECKPOINT_SUMMARY)
    live_inputs = _read_json(LIVE_INPUTS)

    run_context = _validate_inputs(
        cohort_manifest,
        split_labels,
        live_inputs,
        run_manifest,
        run_summary,
        summary,
        checkpoint_summary,
    )
    first_checkpoint = checkpoint_summary["first_checkpoint"]
    resumed_checkpoint = checkpoint_summary["resumed_checkpoint"]
    rows = _build_rows(
        cohort_manifest["cohort"],
        list(first_checkpoint["completed_example_ids"]),
        resumed_checkpoint,
    )

    evidence_modes = Counter(row["evidence_mode"] for row in cohort_manifest["cohort"])
    split_counts = Counter(row["split"] for row in cohort_manifest["cohort"])

    return {
        "schema_id": "benchmark-provenance-table-2026-03-22",
        "task_id": "P6-T016",
        "status": "prototype_provenance_table",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "scope": {
            "cohort_status": cohort_manifest["status"],
            "cohort_size": cohort_manifest["target_size"],
            "runtime_surface": run_summary["runtime_surface"],
            "honesty_boundary": (
                "prototype provenance only; no release-grade or corpus-scale overclaim"
            ),
            "limitations": list(run_manifest["limitations"]),
        },
        "source_artifacts": {
            "cohort_manifest": _path(COHORT_MANIFEST),
            "split_labels": _path(SPLIT_LABELS),
            "run_manifest": _path(RUN_MANIFEST),
            "run_summary": _path(RUN_SUMMARY),
            "summary": _path(SUMMARY),
            "checkpoint_summary": _path(CHECKPOINT_SUMMARY),
            "live_inputs": _path(LIVE_INPUTS),
            "full_results_readme": _path(FULL_RESULTS_README),
        },
        "consistency_checks": {
            "cohort_matches_live_inputs": True,
            "cohort_matches_split_labels": True,
            "checkpoint_identity_safe_resume": True,
            "checkpoint_first_pass_count": first_checkpoint["processed_examples"],
            "checkpoint_final_count": resumed_checkpoint["processed_examples"],
        },
        "run_context": {
            "manifest_id": cohort_manifest["manifest_id"],
            "run_manifest_id": run_manifest["manifest_id"],
            "run_id": run_context["run_id"],
            "checkpoint_ref": run_context["checkpoint_ref"],
            "checkpoint_path": run_context["checkpoint_path"],
            "checkpoint_tag": run_context["checkpoint_tag"],
            "resume_continuity": run_context["resume_continuity"],
            "requested_modalities": run_context["requested_modalities"],
            "split_counts": run_context["split_counts"],
            "selected_accession_count": run_context["selected_accession_count"],
            "first_run_processed_examples": run_context["first_run_processed_examples"],
            "resumed_run_processed_examples": run_context["resumed_run_processed_examples"],
            "checkpoint_writes": run_context["checkpoint_writes"],
            "checkpoint_resumes": run_context["checkpoint_resumes"],
            "final_status": run_context["final_status"],
            "blocker_categories": summary["blocker_categories"],
            "ready_for_next_wave": summary["ready_for_next_wave"],
            "execution_status": summary["status"],
            "execution_scope": summary["execution_scope"],
            "runtime": summary["runtime"],
            "artifacts": summary["artifacts"],
        },
        "checkpoint_snapshots": {
            "first_pass": _checkpoint_snapshot(first_checkpoint),
            "resumed_completion": _checkpoint_snapshot(resumed_checkpoint),
        },
        "cohort_summary": {
            "split_counts": dict(split_counts),
            "evidence_mode_counts": dict(evidence_modes),
            "rows": rows,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit the frozen benchmark provenance table.")
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT,
        help="Where to write the provenance table JSON.",
    )
    args = parser.parse_args()

    payload = build_provenance_table()
    _write_json(args.output, payload)
    print(f"wrote {args.output.as_posix()} ({len(payload['cohort_summary']['rows'])} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
