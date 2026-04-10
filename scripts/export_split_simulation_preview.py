from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from training_set_builder_preview_support import (  # noqa: E402
    DEFAULT_SPLIT_DRY_RUN_VALIDATION,
    DEFAULT_SPLIT_FOLD_EXPORT_GATE,
    DEFAULT_SPLIT_POST_STAGING_GATE_CHECK,
    read_json,
    write_json,
    write_text,
)

DEFAULT_SPLIT_LABELS = REPO_ROOT / "runs" / "real_data_benchmark" / "cohort" / "split_labels.json"
DEFAULT_PACKAGE_READINESS = REPO_ROOT / "artifacts" / "status" / "package_readiness_preview.json"
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "split_simulation_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "split_simulation_preview.md"


def _count_by(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts = Counter()
    for item in items:
        value = str(item.get(key) or "").strip() or "unknown"
        counts[value] += 1
    return dict(sorted(counts.items()))


def _listify(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, (str, bytes)):
        values = [values]
    seen: dict[str, str] = {}
    for value in values:
        text = str(value or "").strip()
        if text:
            seen.setdefault(text.casefold(), text)
    return list(seen.values())


def build_split_simulation_preview(
    split_labels: dict[str, Any],
    dry_run_validation: dict[str, Any],
    fold_export_gate_preview: dict[str, Any],
    post_staging_gate_check_preview: dict[str, Any],
    package_readiness_preview: dict[str, Any],
) -> dict[str, Any]:
    labels = [
        row for row in split_labels.get("labels") or [] if isinstance(row, dict)
    ]
    counts = split_labels.get("counts") if isinstance(split_labels.get("counts"), dict) else {}
    dry_run_value = dry_run_validation.get("validation")
    dry_run = dry_run_value if isinstance(dry_run_value, dict) else {}
    gate_value = fold_export_gate_preview.get("gate")
    gate = gate_value if isinstance(gate_value, dict) else {}
    validation_snapshot_value = fold_export_gate_preview.get("validation_snapshot")
    validation_snapshot = (
        validation_snapshot_value if isinstance(validation_snapshot_value, dict) else {}
    )
    unlock_value = fold_export_gate_preview.get("unlock_readiness")
    gate_unlock = unlock_value if isinstance(unlock_value, dict) else {}
    post_stage_value = post_staging_gate_check_preview.get("gate_check")
    post_stage = post_stage_value if isinstance(post_stage_value, dict) else {}
    blocked_report_value = post_staging_gate_check_preview.get("blocked_report")
    blocked_report = blocked_report_value if isinstance(blocked_report_value, dict) else {}
    package_summary_value = package_readiness_preview.get("summary")
    package_summary = package_summary_value if isinstance(package_summary_value, dict) else {}

    blocked_reasons = _listify(package_summary.get("blocked_reasons"))
    if not bool(package_summary.get("ready_for_package")) and not blocked_reasons:
        blocked_reasons = [
            "package_ready=false",
        ]

    rows = [
        {
            "accession": row.get("accession"),
            "split": row.get("split"),
            "bucket": row.get("bucket"),
            "status": row.get("status"),
            "leakage_key": row.get("leakage_key"),
        }
        for row in labels
    ]

    split_counts = _count_by(labels, "split")
    bucket_counts = _count_by(labels, "bucket")

    return {
        "artifact_id": "split_simulation_preview",
        "schema_id": "proteosphere-split-simulation-preview-2026-04-03",
        "status": "report_only",
        "generated_at": split_labels.get("date") or package_readiness_preview.get("generated_at"),
        "split_labels": {
            "manifest_id": split_labels.get("manifest_id"),
            "split_policy": split_labels.get("split_policy"),
            "counts": counts,
            "leakage_ready": split_labels.get("leakage_ready") or {},
        },
        "summary": {
            "label_count": len(labels),
            "split_counts": split_counts,
            "label_totals": dict(counts),
            "bucket_counts": bucket_counts,
            "dry_run_validation_status": dry_run_validation.get("status"),
            "dry_run_issue_count": len(dry_run.get("issues") or []),
            "dry_run_match_count": len(dry_run.get("matches") or []),
            "candidate_row_count": dry_run.get("candidate_row_count")
            or validation_snapshot.get("candidate_row_count"),
            "assignment_count": dry_run.get("assignment_count")
            or validation_snapshot.get("assignment_count"),
            "fold_export_gate_status": fold_export_gate_preview.get("status"),
            "fold_export_ready": bool(gate.get("fold_export_ready")),
            "cv_fold_export_unlocked": bool(gate_unlock.get("cv_fold_export_unlocked")),
            "post_staging_gate_status": post_staging_gate_check_preview.get("status"),
            "post_staging_gate_check_status": post_stage.get("gate_status"),
            "package_ready": bool(package_summary.get("ready_for_package")),
            "package_blocking_factors": blocked_reasons,
        },
        "rows": rows,
        "gates": {
            "dry_run_validation": {
                "status": dry_run_validation.get("status"),
                "issues": dry_run.get("issues") or [],
                "matches": dry_run.get("matches") or [],
            },
            "fold_export_gate": {
                "status": fold_export_gate_preview.get("status"),
                "gate_status": gate.get("gate_status") or fold_export_gate_preview.get("status"),
                "blocked_today_reason": gate.get("blocked_today_reason"),
                "required_condition_count": gate.get("required_condition_count"),
            },
            "post_staging_gate_check": {
                "status": post_staging_gate_check_preview.get("status"),
                "gate_status": post_stage.get("gate_status"),
                "blocked_reasons": _listify(blocked_report.get("blocked_reasons")),
            },
            "package_readiness": {
                "status": package_readiness_preview.get("status"),
                "ready_for_package": bool(package_summary.get("ready_for_package")),
                "blocked_reasons": blocked_reasons,
            },
        },
        "truth_boundary": {
            "summary": (
                "This split simulation preview is report-only. It mirrors the current split labels "
                "and gate states for operator review, but it does not commit folds or authorize "
                "package materialization."
            ),
            "report_only": True,
            "non_governing": True,
            "final_split_committed": bool(
                split_labels.get("leakage_ready", {}).get("accession_level_only")
                and not split_labels.get("leakage_ready", {}).get("cross_split_duplicates")
            ),
            "package_ready": bool(package_summary.get("ready_for_package")),
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Split Simulation Preview",
        "",
        f"- Labels: `{summary['label_count']}`",
        f"- Dry-run status: `{summary['dry_run_validation_status']}`",
        f"- Fold export gate: `{summary['fold_export_gate_status']}`",
        f"- Post-staging gate: `{summary['post_staging_gate_status']}`",
        f"- Package ready: `{summary['package_ready']}`",
        "",
        "## Split Counts",
        "",
    ]
    for split_name, count in summary["split_counts"].items():
        lines.append(f"- `{split_name}`: `{count}`")
    lines.extend(["", "## Package Blockers", ""])
    if summary["package_blocking_factors"]:
        for blocker in summary["package_blocking_factors"]:
            lines.append(f"- {blocker}")
    else:
        lines.append("- none")
    lines.extend(["", "## Truth Boundary", ""])
    lines.append(f"- {payload['truth_boundary']['summary']}")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export split simulation preview.")
    parser.add_argument("--split-labels", type=Path, default=DEFAULT_SPLIT_LABELS)
    parser.add_argument(
        "--split-engine-dry-run-validation",
        type=Path,
        default=DEFAULT_SPLIT_DRY_RUN_VALIDATION,
    )
    parser.add_argument(
        "--split-fold-export-gate",
        type=Path,
        default=DEFAULT_SPLIT_FOLD_EXPORT_GATE,
    )
    parser.add_argument(
        "--split-post-staging-gate-check",
        type=Path,
        default=DEFAULT_SPLIT_POST_STAGING_GATE_CHECK,
    )
    parser.add_argument(
        "--package-readiness",
        type=Path,
        default=DEFAULT_PACKAGE_READINESS,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_split_simulation_preview(
        read_json(args.split_labels),
        read_json(args.split_engine_dry_run_validation),
        read_json(args.split_fold_export_gate),
        read_json(args.split_post_staging_gate_check),
        read_json(args.package_readiness),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
