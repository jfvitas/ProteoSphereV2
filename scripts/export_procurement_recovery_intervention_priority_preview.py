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

DEFAULT_FILL_RISK_PREVIEW_PATH = (
    REPO_ROOT / "artifacts" / "status" / "procurement_tail_fill_risk_preview.json"
)
DEFAULT_RECOVERY_TRIGGER_PREVIEW_PATH = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_space_recovery_trigger_preview.json"
)
DEFAULT_RECOVERY_SAFETY_REGISTER_PREVIEW_PATH = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_space_recovery_safety_register_preview.json"
)
DEFAULT_RECOVERY_GAP_DRIFT_PREVIEW_PATH = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_space_recovery_gap_drift_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_recovery_intervention_priority_preview.json"
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


def build_procurement_recovery_intervention_priority_preview(
    fill_risk_preview: dict[str, Any],
    recovery_trigger_preview: dict[str, Any],
    recovery_safety_register_preview: dict[str, Any],
    recovery_gap_drift_preview: dict[str, Any],
    *,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    observed_at = observed_at or _utc_now()
    fill_summary = (
        fill_risk_preview.get("summary")
        if isinstance(fill_risk_preview.get("summary"), dict)
        else {}
    )
    trigger_summary = (
        recovery_trigger_preview.get("summary")
        if isinstance(recovery_trigger_preview.get("summary"), dict)
        else {}
    )
    safety_summary = (
        recovery_safety_register_preview.get("summary")
        if isinstance(recovery_safety_register_preview.get("summary"), dict)
        else {}
    )
    gap_summary = (
        recovery_gap_drift_preview.get("summary")
        if isinstance(recovery_gap_drift_preview.get("summary"), dict)
        else {}
    )

    risk_state = fill_summary.get("risk_state")
    trigger_state = trigger_summary.get("trigger_state")
    safety_state = safety_summary.get("safety_state")
    drift_state = gap_summary.get("drift_state")
    cushion_hours = _coerce_float(fill_summary.get("cushion_hours"))
    shortfall_gib = _coerce_float(gap_summary.get("current_zero_gap_shortfall_gib"))

    if (
        risk_state == "zero_before_completion"
        and trigger_state == "ranked_batch_insufficient_escalate"
        and safety_state == "duplicate_first_safety_lane_available"
    ):
        priority_state = "urgent_expand_duplicate_first_review"
        next_action = (
            "The tail is projected to exhaust free space before completion, and the current "
            "duplicate-first lane is still short of the exact target. Expand the duplicate-safe "
            "review set immediately."
        )
    elif (
        risk_state == "zero_before_completion"
        and trigger_state == "recovery_trigger_immediate"
    ):
        priority_state = "urgent_duplicate_first_recovery_lane_ready"
        next_action = (
            "The tail is projected to exhaust free space before completion, and the current "
            "duplicate-first lane already closes the exact deficit."
        )
    elif risk_state == "completion_before_zero":
        priority_state = "monitor_only"
        next_action = (
            "The current short-window fill-risk still favors completion before disk exhaustion; "
            "keep the recovery lane visible but non-urgent."
        )
    else:
        priority_state = "active_review_required"
        next_action = (
            "Recovery review should stay active because the current risk and trigger signals do "
            "not support treating the lane as safely deferred."
        )

    return {
        "artifact_id": "procurement_recovery_intervention_priority_preview",
        "schema_id": "proteosphere-procurement-recovery-intervention-priority-preview-2026-04-03",
        "status": "report_only",
        "generated_at": observed_at.isoformat(),
        "summary": {
            "priority_state": priority_state,
            "risk_state": risk_state,
            "trigger_state": trigger_state,
            "safety_state": safety_state,
            "drift_state": drift_state,
            "cushion_hours": cushion_hours,
            "current_zero_gap_shortfall_gib": shortfall_gib,
            "non_mutating": True,
            "report_only": True,
        },
        "next_suggested_action": next_action,
        "source_artifacts": {
            "procurement_tail_fill_risk_preview": str(
                DEFAULT_FILL_RISK_PREVIEW_PATH
            ).replace("\\", "/"),
            "procurement_space_recovery_trigger_preview": str(
                DEFAULT_RECOVERY_TRIGGER_PREVIEW_PATH
            ).replace("\\", "/"),
            "procurement_space_recovery_safety_register_preview": str(
                DEFAULT_RECOVERY_SAFETY_REGISTER_PREVIEW_PATH
            ).replace("\\", "/"),
            "procurement_space_recovery_gap_drift_preview": str(
                DEFAULT_RECOVERY_GAP_DRIFT_PREVIEW_PATH
            ).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only intervention-priority surface derived from current "
                "fill-risk, gap, trigger, and safety signals."
            ),
            "report_only": True,
            "non_mutating": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a report-only procurement recovery intervention-priority preview."
    )
    parser.add_argument(
        "--fill-risk-preview-path",
        type=Path,
        default=DEFAULT_FILL_RISK_PREVIEW_PATH,
    )
    parser.add_argument(
        "--recovery-trigger-preview-path",
        type=Path,
        default=DEFAULT_RECOVERY_TRIGGER_PREVIEW_PATH,
    )
    parser.add_argument(
        "--recovery-safety-register-preview-path",
        type=Path,
        default=DEFAULT_RECOVERY_SAFETY_REGISTER_PREVIEW_PATH,
    )
    parser.add_argument(
        "--recovery-gap-drift-preview-path",
        type=Path,
        default=DEFAULT_RECOVERY_GAP_DRIFT_PREVIEW_PATH,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_procurement_recovery_intervention_priority_preview(
        _load_json_or_default(args.fill_risk_preview_path, {}),
        _load_json_or_default(args.recovery_trigger_preview_path, {}),
        _load_json_or_default(args.recovery_safety_register_preview_path, {}),
        _load_json_or_default(args.recovery_gap_drift_preview_path, {}),
    )
    save_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
