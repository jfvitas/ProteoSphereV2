from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.tasklib import load_json, save_json  # noqa: E402

DEFAULT_RECOVERY_CANDIDATES_PREVIEW_PATH = (
    REPO_ROOT / "artifacts" / "status" / "procurement_space_recovery_candidates_preview.json"
)
DEFAULT_RECOVERY_EXECUTION_BATCH_PREVIEW_PATH = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_space_recovery_execution_batch_preview.json"
)
DEFAULT_RECOVERY_SAFETY_REGISTER_PREVIEW_PATH = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_space_recovery_safety_register_preview.json"
)
DEFAULT_RECOVERY_COVERAGE_PREVIEW_PATH = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_space_recovery_coverage_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_recovery_escalation_lane_preview.json"
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _load_json_or_default(path: Path, default: Any) -> Any:
    return load_json(path, default) if path.exists() else default


def _coerce_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _coerce_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def build_procurement_recovery_escalation_lane_preview(
    recovery_candidates_preview: dict[str, Any],
    recovery_execution_batch_preview: dict[str, Any],
    recovery_safety_register_preview: dict[str, Any],
    recovery_coverage_preview: dict[str, Any],
    *,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    observed_at = observed_at or _utc_now()
    candidates_summary = (
        recovery_candidates_preview.get("summary")
        if isinstance(recovery_candidates_preview.get("summary"), dict)
        else {}
    )
    execution_summary = (
        recovery_execution_batch_preview.get("summary")
        if isinstance(recovery_execution_batch_preview.get("summary"), dict)
        else {}
    )
    safety_summary = (
        recovery_safety_register_preview.get("summary")
        if isinstance(recovery_safety_register_preview.get("summary"), dict)
        else {}
    )
    coverage_summary = (
        recovery_coverage_preview.get("summary")
        if isinstance(recovery_coverage_preview.get("summary"), dict)
        else {}
    )
    zero_gap_batch = (
        recovery_execution_batch_preview.get("batches", {}).get("zero_gap_batch", {})
        if isinstance(recovery_execution_batch_preview.get("batches"), dict)
        else {}
    )

    total_ranked_reclaim_gib = _coerce_float(candidates_summary.get("total_ranked_reclaim_gib"))
    zero_gap_reclaim_gib = _coerce_float(zero_gap_batch.get("cumulative_reclaim_gib"))
    additional_ranked_reclaim_gib = round(
        max(total_ranked_reclaim_gib - zero_gap_reclaim_gib, 0.0), 3
    )
    review_required_count = _coerce_int(safety_summary.get("review_required_category_count"))
    duplicate_first_count = _coerce_int(safety_summary.get("duplicate_first_category_count"))
    ranked_candidate_count = _coerce_int(candidates_summary.get("ranked_candidate_count"))
    zero_gap_shortfall_gib = _coerce_float(coverage_summary.get("zero_gap_shortfall_gib"))
    coverage_state = coverage_summary.get("coverage_state")
    execution_state = execution_summary.get("execution_state")

    if zero_gap_shortfall_gib <= 0:
        escalation_state = "no_escalation_required"
        next_action = "The current ranked recovery lane already covers the exact zero-gap target."
    elif additional_ranked_reclaim_gib > 0:
        escalation_state = "extend_ranked_lane_before_manual_review"
        next_action = (
            "Extend the ranked recovery lane before considering any "
            "manual-review expansion."
        )
    elif review_required_count > 0:
        escalation_state = "manual_review_lane_available"
        next_action = (
            "The duplicate-safe ranked lane is exhausted; the next escalation "
            "step is bounded manual review of review-required candidates."
        )
    elif ranked_candidate_count > 0 and duplicate_first_count == ranked_candidate_count:
        escalation_state = "ranked_duplicate_lane_exhausted"
        next_action = (
            "The ranked duplicate-safe lane is exhausted and still short of "
            "the exact target; no additional ranked lane remains inside the "
            "current candidate universe."
        )
    else:
        escalation_state = "no_recovery_lane_available"
        next_action = (
            "No ranked recovery lane is currently available; treat any next "
            "step as manual investigation only."
        )

    return {
        "artifact_id": "procurement_recovery_escalation_lane_preview",
        "schema_id": "proteosphere-procurement-recovery-escalation-lane-preview-2026-04-03",
        "status": "report_only",
        "generated_at": observed_at.isoformat(),
        "summary": {
            "escalation_state": escalation_state,
            "coverage_state": coverage_state,
            "execution_state": execution_state,
            "zero_gap_shortfall_gib": zero_gap_shortfall_gib,
            "additional_ranked_reclaim_gib": additional_ranked_reclaim_gib,
            "review_required_category_count": review_required_count,
            "duplicate_first_category_count": duplicate_first_count,
            "non_mutating": True,
            "report_only": True,
        },
        "next_suggested_action": next_action,
        "source_artifacts": {
            "procurement_space_recovery_candidates_preview": str(
                DEFAULT_RECOVERY_CANDIDATES_PREVIEW_PATH
            ).replace("\\", "/"),
            "procurement_space_recovery_execution_batch_preview": str(
                DEFAULT_RECOVERY_EXECUTION_BATCH_PREVIEW_PATH
            ).replace("\\", "/"),
            "procurement_space_recovery_safety_register_preview": str(
                DEFAULT_RECOVERY_SAFETY_REGISTER_PREVIEW_PATH
            ).replace("\\", "/"),
            "procurement_space_recovery_coverage_preview": str(
                DEFAULT_RECOVERY_COVERAGE_PREVIEW_PATH
            ).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only escalation-lane view that explains "
                "whether any additional ranked recovery lane remains."
            ),
            "report_only": True,
            "non_mutating": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a report-only procurement recovery escalation-lane preview."
    )
    parser.add_argument(
        "--recovery-candidates-preview-path",
        type=Path,
        default=DEFAULT_RECOVERY_CANDIDATES_PREVIEW_PATH,
    )
    parser.add_argument(
        "--recovery-execution-batch-preview-path",
        type=Path,
        default=DEFAULT_RECOVERY_EXECUTION_BATCH_PREVIEW_PATH,
    )
    parser.add_argument(
        "--recovery-safety-register-preview-path",
        type=Path,
        default=DEFAULT_RECOVERY_SAFETY_REGISTER_PREVIEW_PATH,
    )
    parser.add_argument(
        "--recovery-coverage-preview-path",
        type=Path,
        default=DEFAULT_RECOVERY_COVERAGE_PREVIEW_PATH,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_procurement_recovery_escalation_lane_preview(
        _load_json_or_default(args.recovery_candidates_preview_path, {}),
        _load_json_or_default(args.recovery_execution_batch_preview_path, {}),
        _load_json_or_default(args.recovery_safety_register_preview_path, {}),
        _load_json_or_default(args.recovery_coverage_preview_path, {}),
    )
    save_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
