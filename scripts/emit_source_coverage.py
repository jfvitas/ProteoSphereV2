from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_COHORT_MANIFEST = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "cohort" / "cohort_manifest.json"
)
DEFAULT_LIVE_INPUTS = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "live_inputs.json"
)
DEFAULT_RUN_MANIFEST = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "run_manifest.json"
)
DEFAULT_RUN_SUMMARY = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "run_summary.json"
)
DEFAULT_CHECKPOINT_SUMMARY = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "checkpoint_summary.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "source_coverage.json"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _build_lane_index(cohort_rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    lane_index: dict[str, list[str]] = defaultdict(list)
    for row in cohort_rows:
        accession = str(row["accession"])
        for lane in row.get("source_lanes", []):
            lane_index[str(lane)].append(accession)
    return {lane: sorted(accessions) for lane, accessions in sorted(lane_index.items())}


def _classify_coverage(row: dict[str, Any]) -> dict[str, Any]:
    source_lanes = [str(lane) for lane in row.get("source_lanes", [])]
    lane_depth = len(source_lanes)
    evidence_mode = str(row.get("evidence_mode") or "unknown")
    status = str(row.get("status") or "unknown")
    bucket = str(row.get("bucket") or "unknown")
    split = str(row.get("split") or "unknown")
    thin_coverage = lane_depth <= 1

    if evidence_mode == "direct_live_smoke":
        validation_class = "direct_live_smoke"
        conservative_evidence_tier = (
            "direct_multilane" if lane_depth > 1 else "direct_single_lane"
        )
    elif evidence_mode == "live_summary_library_probe":
        validation_class = "probe_backed"
        conservative_evidence_tier = (
            "probe_supported_multilane" if lane_depth > 1 else "probe_supported_single_lane"
        )
    elif evidence_mode == "in_tree_live_snapshot":
        validation_class = "snapshot_backed"
        conservative_evidence_tier = (
            "snapshot_backed_multilane" if lane_depth > 1 else "snapshot_backed_single_lane"
        )
    elif evidence_mode == "live_verified_accession":
        validation_class = "verified_accession"
        conservative_evidence_tier = (
            "verified_accession_multilane"
            if lane_depth > 1
            else "verified_accession_single_lane"
        )
    else:
        validation_class = evidence_mode
        conservative_evidence_tier = "unknown"

    coverage_notes: list[str] = []
    if thin_coverage:
        coverage_notes.append("single-lane coverage")
    if evidence_mode == "live_summary_library_probe":
        coverage_notes.append("summary-library probe rather than direct assay")
    if evidence_mode == "in_tree_live_snapshot":
        coverage_notes.append("backed by in-tree live-derived snapshot")
    if evidence_mode == "live_verified_accession":
        coverage_notes.append("verified accession only")

    return {
        "accession": str(row["accession"]),
        "split": split,
        "bucket": bucket,
        "status": status,
        "evidence_mode": evidence_mode,
        "validation_class": validation_class,
        "lane_depth": lane_depth,
        "thin_coverage": thin_coverage,
        "mixed_evidence": evidence_mode == "live_summary_library_probe",
        "conservative_evidence_tier": conservative_evidence_tier,
        "source_lanes": source_lanes,
        "evidence_refs": [str(ref) for ref in row.get("evidence_refs", [])],
        "leakage_key": str(row.get("leakage_key") or row["accession"]),
        "coverage_notes": coverage_notes,
    }


def build_source_coverage(
    cohort_manifest_path: Path,
    live_inputs_path: Path,
    run_manifest_path: Path,
    run_summary_path: Path,
    checkpoint_summary_path: Path,
) -> dict[str, Any]:
    cohort_manifest = _read_json(cohort_manifest_path)
    live_inputs = _read_json(live_inputs_path)
    run_manifest = _read_json(run_manifest_path)
    run_summary = _read_json(run_summary_path)
    checkpoint_summary = _read_json(checkpoint_summary_path)

    cohort_rows = list(cohort_manifest.get("cohort", []))
    matrix = [_classify_coverage(row) for row in cohort_rows]
    lane_index = _build_lane_index(cohort_rows)
    lane_depth_counts = Counter(str(entry["lane_depth"]) for entry in matrix)
    evidence_mode_counts = Counter(str(entry["evidence_mode"]) for entry in matrix)
    validation_class_counts = Counter(str(entry["validation_class"]) for entry in matrix)
    thin_accessions = [entry["accession"] for entry in matrix if entry["thin_coverage"]]
    mixed_evidence_accessions = [
        entry["accession"] for entry in matrix if entry["mixed_evidence"]
    ]
    direct_live_smoke_accessions = [
        entry["accession"] for entry in matrix if entry["validation_class"] == "direct_live_smoke"
    ]
    probe_backed_accessions = [
        entry["accession"] for entry in matrix if entry["validation_class"] == "probe_backed"
    ]
    snapshot_backed_accessions = [
        entry["accession"] for entry in matrix if entry["validation_class"] == "snapshot_backed"
    ]
    verified_accession_accessions = [
        entry["accession"] for entry in matrix if entry["validation_class"] == "verified_accession"
    ]

    return {
        "schema_id": "real-data-benchmark-source-coverage-2026-03-22",
        "task_id": "P6-T017",
        "date": "2026-03-22",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "status": "complete",
        "semantics": {
            "artifact_kind": "conservative_source_coverage_inventory",
            "coverage_not_validation": True,
            "release_grade_corpus_validation": False,
            "mixed_evidence_rows_are_conservative": True,
            "row_class_definitions": {
                "direct_live_smoke": "direct live evidence for the accession lanes present",
                "probe_backed": "includes probe-backed support; do not treat as direct assay depth",
                "snapshot_backed": (
                    "backed by in-tree live-derived snapshot; not corpus-scale validation"
                ),
                "verified_accession": "accession verified only; lane depth remains thin",
            },
        },
        "frozen_cohort": {
            "manifest_id": cohort_manifest.get("manifest_id"),
            "target_size": cohort_manifest.get("target_size"),
            "resolved_count": cohort_manifest.get("resolved_count"),
            "unresolved_count": cohort_manifest.get("unresolved_count"),
            "split_counts": cohort_manifest.get("split_counts", {}),
            "split_leakage_metadata": cohort_manifest.get("split_leakage_metadata", {}),
        },
        "inputs": {
            "cohort_manifest": str(cohort_manifest_path).replace("\\", "/"),
            "live_inputs": str(live_inputs_path).replace("\\", "/"),
            "run_manifest": str(run_manifest_path).replace("\\", "/"),
            "run_summary": str(run_summary_path).replace("\\", "/"),
            "checkpoint_summary": str(checkpoint_summary_path).replace("\\", "/"),
            "benchmark_manifest": str(
                REPO_ROOT / "runs" / "real_data_benchmark" / "manifest.json"
            ).replace("\\", "/"),
            "benchmark_runbook": str(
                REPO_ROOT / "runs" / "real_data_benchmark" / "README.md"
            ).replace("\\", "/"),
            "live_smoke_reports": [
                str(REPO_ROOT / "docs" / "reports" / "live_source_smoke_2026_03_22.md").replace(
                    "\\", "/"
                ),
                str(REPO_ROOT / "docs" / "reports" / "ppi_live_smoke_2026_03_22.md").replace(
                    "\\", "/"
                ),
                str(
                    REPO_ROOT / "docs" / "reports" / "annotation_pathway_live_smoke_2026_03_22.md"
                ).replace("\\", "/"),
                str(REPO_ROOT / "docs" / "reports" / "bindingdb_live_smoke_2026_03_22.md").replace(
                    "\\", "/"
                ),
                str(
                    REPO_ROOT / "docs" / "reports" / "evolutionary_live_smoke_2026_03_22.md"
                ).replace("\\", "/"),
            ],
        },
        "run_context": {
            "run_status": run_manifest.get("status"),
            "run_final_status": run_manifest.get("execution", {}).get("final_status"),
            "runtime_surface": run_summary.get("runtime_surface"),
            "checkpoint_ref": checkpoint_summary.get("resumed_checkpoint", {}).get(
                "checkpoint_ref"
            ),
            "checkpoint_processed_examples": checkpoint_summary.get("resumed_checkpoint", {}).get(
                "processed_examples"
            ),
        },
        "coverage_matrix": matrix,
        "lane_index": lane_index,
        "summary": {
            "total_accessions": len(matrix),
            "resolved_accessions": sum(1 for row in matrix if row["status"] == "resolved"),
            "unresolved_accessions": sum(1 for row in matrix if row["status"] != "resolved"),
            "lane_depth_counts": dict(
                sorted(lane_depth_counts.items(), key=lambda item: int(item[0]))
            ),
            "evidence_mode_counts": dict(sorted(evidence_mode_counts.items())),
            "validation_class_counts": dict(sorted(validation_class_counts.items())),
            "thin_coverage_accessions": thin_accessions,
            "mixed_evidence_accessions": mixed_evidence_accessions,
            "direct_live_smoke_accessions": direct_live_smoke_accessions,
            "probe_backed_accessions": probe_backed_accessions,
            "snapshot_backed_accessions": snapshot_backed_accessions,
            "verified_accession_accessions": verified_accession_accessions,
            "thin_coverage_threshold": 1,
        },
        "source_artifacts": {
            "selected_example_probe": cohort_manifest.get("evidence_basis", {}).get(
                "selected_example_probe"
            ),
            "live_inputs_snapshot": str(live_inputs_path).replace("\\", "/"),
            "live_inputs_task_id": live_inputs.get("task_id"),
            "live_inputs_requested_modalities": list(live_inputs.get("requested_modalities", [])),
            "benchmark_artifacts": {
                "run_manifest": str(run_manifest_path).replace("\\", "/"),
                "run_summary": str(run_summary_path).replace("\\", "/"),
                "checkpoint_summary": str(checkpoint_summary_path).replace("\\", "/"),
            },
        },
        "blockers": list(cohort_manifest.get("blockers", [])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit the real-data benchmark source coverage matrix."
    )
    parser.add_argument("--cohort-manifest", type=Path, default=DEFAULT_COHORT_MANIFEST)
    parser.add_argument("--live-inputs", type=Path, default=DEFAULT_LIVE_INPUTS)
    parser.add_argument("--run-manifest", type=Path, default=DEFAULT_RUN_MANIFEST)
    parser.add_argument("--run-summary", type=Path, default=DEFAULT_RUN_SUMMARY)
    parser.add_argument("--checkpoint-summary", type=Path, default=DEFAULT_CHECKPOINT_SUMMARY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    payload = build_source_coverage(
        args.cohort_manifest,
        args.live_inputs,
        args.run_manifest,
        args.run_summary,
        args.checkpoint_summary,
    )
    _write_json(args.output, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
