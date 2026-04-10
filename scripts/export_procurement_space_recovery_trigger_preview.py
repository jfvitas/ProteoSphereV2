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
DEFAULT_RECOVERY_EXECUTION_BATCH_PREVIEW_PATH = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_space_recovery_execution_batch_preview.json"
)
DEFAULT_RECOVERY_TARGET_PREVIEW_PATH = (
    REPO_ROOT / "artifacts" / "status" / "procurement_space_recovery_target_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_space_recovery_trigger_preview.json"
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _load_json_or_default(path: Path, default: Any) -> Any:
    return load_json(path, default) if path.exists() else default


def _coerce_bool(value: Any) -> bool:
    return bool(value)


def build_procurement_space_recovery_trigger_preview(
    fill_risk_preview: dict[str, Any],
    recovery_execution_batch_preview: dict[str, Any],
    recovery_target_preview: dict[str, Any],
    *,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    observed_at = observed_at or _utc_now()
    fill_summary = (
        fill_risk_preview.get("summary")
        if isinstance(fill_risk_preview.get("summary"), dict)
        else {}
    )
    execution_summary = (
        recovery_execution_batch_preview.get("summary")
        if isinstance(recovery_execution_batch_preview.get("summary"), dict)
        else {}
    )
    target_summary = (
        recovery_target_preview.get("summary")
        if isinstance(recovery_target_preview.get("summary"), dict)
        else {}
    )

    risk_state = fill_summary.get("risk_state")
    execution_state = execution_summary.get("execution_state")
    zero_gap_available = _coerce_bool(execution_summary.get("zero_gap_batch_meets_target"))
    reclaim_to_zero_gib = target_summary.get("reclaim_to_zero_gib")

    if risk_state in {"completion_before_zero", "insufficient_rate_data"}:
        trigger_state = "prepare_recovery_review"
        next_action = (
            "Keep the recovery lane visible and reviewed, but the current short-window "
            "timing does not yet imply immediate space exhaustion before completion."
        )
    elif zero_gap_available:
        trigger_state = "recovery_trigger_immediate"
        next_action = (
            "The ranked duplicate-first recovery batch can close the exact deficit and "
            "should be treated as the immediate report-only recovery lane."
        )
    elif execution_state == "insufficient_ranked_capacity":
        trigger_state = "ranked_batch_insufficient_escalate"
        next_action = (
            "The current ranked recovery lane does not fully close the exact deficit; "
            "widen candidate review before trusting the tail to finish."
        )
    else:
        trigger_state = "prepare_recovery_review"
        next_action = (
            "Recovery review is warranted, but the current trigger does not yet land in "
            "a fully executable ranked lane."
        )

    return {
        "artifact_id": "procurement_space_recovery_trigger_preview",
        "schema_id": "proteosphere-procurement-space-recovery-trigger-preview-2026-04-03",
        "status": "report_only",
        "generated_at": observed_at.isoformat(),
        "summary": {
            "trigger_state": trigger_state,
            "risk_state": risk_state,
            "execution_state": execution_state,
            "zero_gap_batch_meets_target": zero_gap_available,
            "reclaim_to_zero_gib": reclaim_to_zero_gib,
            "non_mutating": True,
            "report_only": True,
        },
        "next_suggested_action": next_action,
        "source_artifacts": {
            "procurement_tail_fill_risk_preview": str(
                DEFAULT_FILL_RISK_PREVIEW_PATH
            ).replace("\\", "/"),
            "procurement_space_recovery_execution_batch_preview": str(
                DEFAULT_RECOVERY_EXECUTION_BATCH_PREVIEW_PATH
            ).replace("\\", "/"),
            "procurement_space_recovery_target_preview": str(
                DEFAULT_RECOVERY_TARGET_PREVIEW_PATH
            ).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only trigger surface that combines current fill risk "
                "with the ranked recovery batch planner. It does not move or delete files."
            ),
            "report_only": True,
            "non_mutating": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a report-only procurement space recovery trigger preview."
    )
    parser.add_argument(
        "--fill-risk-preview-path",
        type=Path,
        default=DEFAULT_FILL_RISK_PREVIEW_PATH,
    )
    parser.add_argument(
        "--recovery-execution-batch-preview-path",
        type=Path,
        default=DEFAULT_RECOVERY_EXECUTION_BATCH_PREVIEW_PATH,
    )
    parser.add_argument(
        "--recovery-target-preview-path",
        type=Path,
        default=DEFAULT_RECOVERY_TARGET_PREVIEW_PATH,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_procurement_space_recovery_trigger_preview(
        _load_json_or_default(args.fill_risk_preview_path, {}),
        _load_json_or_default(args.recovery_execution_batch_preview_path, {}),
        _load_json_or_default(args.recovery_target_preview_path, {}),
    )
    save_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
