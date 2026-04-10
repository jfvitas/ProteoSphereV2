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

DEFAULT_RECOVERY_COVERAGE_PREVIEW_PATH = (
    REPO_ROOT / "artifacts" / "status" / "procurement_space_recovery_coverage_preview.json"
)
DEFAULT_RECOVERY_ESCALATION_LANE_PREVIEW_PATH = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_recovery_escalation_lane_preview.json"
)
DEFAULT_RECOVERY_SAFETY_REGISTER_PREVIEW_PATH = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_space_recovery_safety_register_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_recovery_shortfall_bridge_preview.json"
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _load_json_or_default(path: Path, default: Any) -> Any:
    return load_json(path, default) if path.exists() else default


def _coerce_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _coerce_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def build_procurement_recovery_shortfall_bridge_preview(
    recovery_coverage_preview: dict[str, Any],
    recovery_escalation_lane_preview: dict[str, Any],
    recovery_safety_register_preview: dict[str, Any],
    *,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    observed_at = observed_at or _utc_now()
    coverage_summary = (
        recovery_coverage_preview.get("summary")
        if isinstance(recovery_coverage_preview.get("summary"), dict)
        else {}
    )
    escalation_summary = (
        recovery_escalation_lane_preview.get("summary")
        if isinstance(recovery_escalation_lane_preview.get("summary"), dict)
        else {}
    )
    safety_summary = (
        recovery_safety_register_preview.get("summary")
        if isinstance(recovery_safety_register_preview.get("summary"), dict)
        else {}
    )

    zero_gap_shortfall_gib = _coerce_float(coverage_summary.get("zero_gap_shortfall_gib"))
    additional_ranked_reclaim_gib = _coerce_float(
        escalation_summary.get("additional_ranked_reclaim_gib")
    )
    review_required_count = _coerce_int(safety_summary.get("review_required_category_count"))
    escalation_state = escalation_summary.get("escalation_state")

    if zero_gap_shortfall_gib <= 0:
        bridge_state = "no_bridge_required"
        next_action = "The ranked lane already covers the zero-gap target."
    elif additional_ranked_reclaim_gib > 0:
        bridge_state = "ranked_bridge_available"
        next_action = (
            "An additional ranked reclaim bridge still exists inside the current "
            "candidate universe."
        )
    elif review_required_count > 0:
        bridge_state = "manual_review_bridge_possible"
        next_action = (
            "No ranked bridge remains, but a bounded manual-review bridge may "
            "still exist in the review-required lane."
        )
    else:
        bridge_state = "no_bridge_inside_current_universe"
        next_action = (
            "No ranked or review-required bridge remains inside the current "
            "candidate universe; any next step requires a broader search."
        )

    return {
        "artifact_id": "procurement_recovery_shortfall_bridge_preview",
        "schema_id": "proteosphere-procurement-recovery-shortfall-bridge-preview-2026-04-03",
        "status": "report_only",
        "generated_at": observed_at.isoformat(),
        "summary": {
            "bridge_state": bridge_state,
            "escalation_state": escalation_state,
            "zero_gap_shortfall_gib": zero_gap_shortfall_gib,
            "additional_ranked_reclaim_gib": additional_ranked_reclaim_gib,
            "review_required_category_count": review_required_count,
            "non_mutating": True,
            "report_only": True,
        },
        "next_suggested_action": next_action,
        "source_artifacts": {
            "procurement_space_recovery_coverage_preview": str(
                DEFAULT_RECOVERY_COVERAGE_PREVIEW_PATH
            ).replace("\\", "/"),
            "procurement_recovery_escalation_lane_preview": str(
                DEFAULT_RECOVERY_ESCALATION_LANE_PREVIEW_PATH
            ).replace("\\", "/"),
            "procurement_space_recovery_safety_register_preview": str(
                DEFAULT_RECOVERY_SAFETY_REGISTER_PREVIEW_PATH
            ).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only bridge view that explains whether any "
                "remaining shortfall bridge exists inside the current recovery universe."
            ),
            "report_only": True,
            "non_mutating": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a report-only procurement recovery shortfall bridge preview."
    )
    parser.add_argument(
        "--recovery-coverage-preview-path",
        type=Path,
        default=DEFAULT_RECOVERY_COVERAGE_PREVIEW_PATH,
    )
    parser.add_argument(
        "--recovery-escalation-lane-preview-path",
        type=Path,
        default=DEFAULT_RECOVERY_ESCALATION_LANE_PREVIEW_PATH,
    )
    parser.add_argument(
        "--recovery-safety-register-preview-path",
        type=Path,
        default=DEFAULT_RECOVERY_SAFETY_REGISTER_PREVIEW_PATH,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_procurement_recovery_shortfall_bridge_preview(
        _load_json_or_default(args.recovery_coverage_preview_path, {}),
        _load_json_or_default(args.recovery_escalation_lane_preview_path, {}),
        _load_json_or_default(args.recovery_safety_register_preview_path, {}),
    )
    save_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
