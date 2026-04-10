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

DEFAULT_RECOVERY_TARGET_PREVIEW_PATH = (
    REPO_ROOT / "artifacts" / "status" / "procurement_space_recovery_target_preview.json"
)
DEFAULT_RECOVERY_EXECUTION_BATCH_PREVIEW_PATH = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_space_recovery_execution_batch_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_space_recovery_gap_drift_preview.json"
)
GIB = 1024**3


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _load_json_or_default(path: Path, default: Any) -> Any:
    return load_json(path, default) if path.exists() else default


def _coerce_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def build_procurement_space_recovery_gap_drift_preview(
    recovery_target_preview: dict[str, Any],
    recovery_execution_batch_preview: dict[str, Any],
    previous_payload: dict[str, Any] | None = None,
    *,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    observed_at = observed_at or _utc_now()
    target_summary = (
        recovery_target_preview.get("summary")
        if isinstance(recovery_target_preview.get("summary"), dict)
        else {}
    )
    batches = (
        recovery_execution_batch_preview.get("batches")
        if isinstance(recovery_execution_batch_preview.get("batches"), dict)
        else {}
    )
    zero_gap_batch = batches.get("zero_gap_batch")
    if not isinstance(zero_gap_batch, dict):
        zero_gap_batch = {}

    current_gap_bytes = max(
        _coerce_int(target_summary.get("reclaim_to_zero_bytes"))
        - _coerce_int(zero_gap_batch.get("cumulative_reclaim_bytes")),
        0,
    )
    previous_summary = (
        previous_payload.get("summary")
        if isinstance(previous_payload, dict)
        and isinstance(previous_payload.get("summary"), dict)
        else {}
    )
    previous_gap_bytes = _coerce_int(previous_summary.get("current_zero_gap_shortfall_bytes"))
    gap_delta_bytes = current_gap_bytes - previous_gap_bytes

    if current_gap_bytes <= 0:
        drift_state = "no_zero_gap_shortfall"
        next_action = (
            "The current ranked recovery lane covers the exact zero-gap target; keep the "
            "lane visible while watching buffered targets."
        )
    elif previous_gap_bytes <= 0:
        drift_state = "first_shortfall_observation"
        next_action = (
            "A positive zero-gap shortfall is now present; treat the ranked duplicate-first "
            "lane as insufficient until widened."
        )
    elif gap_delta_bytes > 0:
        drift_state = "gap_widening"
        next_action = (
            "The exact zero-gap shortfall is widening relative to the previous observation; "
            "recovery review is becoming more urgent."
        )
    elif gap_delta_bytes < 0:
        drift_state = "gap_narrowing"
        next_action = (
            "The exact zero-gap shortfall is narrowing relative to the previous observation, "
            "but the ranked lane still does not fully close the deficit."
        )
    else:
        drift_state = "gap_flat"
        next_action = (
            "The exact zero-gap shortfall is stable relative to the previous observation; "
            "keep the recovery review lane active."
        )

    return {
        "artifact_id": "procurement_space_recovery_gap_drift_preview",
        "schema_id": "proteosphere-procurement-space-recovery-gap-drift-preview-2026-04-03",
        "status": "report_only",
        "generated_at": observed_at.isoformat(),
        "summary": {
            "drift_state": drift_state,
            "current_zero_gap_shortfall_bytes": current_gap_bytes,
            "current_zero_gap_shortfall_gib": round(current_gap_bytes / GIB, 3),
            "previous_zero_gap_shortfall_bytes": previous_gap_bytes,
            "previous_zero_gap_shortfall_gib": round(previous_gap_bytes / GIB, 3),
            "gap_delta_bytes": gap_delta_bytes,
            "gap_delta_gib": round(gap_delta_bytes / GIB, 3),
            "non_mutating": True,
            "report_only": True,
        },
        "next_suggested_action": next_action,
        "source_artifacts": {
            "procurement_space_recovery_target_preview": str(
                DEFAULT_RECOVERY_TARGET_PREVIEW_PATH
            ).replace("\\", "/"),
            "procurement_space_recovery_execution_batch_preview": str(
                DEFAULT_RECOVERY_EXECUTION_BATCH_PREVIEW_PATH
            ).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only drift view of the exact zero-gap reclaim shortfall "
                "relative to the ranked recovery batch lane."
            ),
            "report_only": True,
            "non_mutating": True,
            "previous_artifact_comparison_only": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a report-only procurement space recovery gap-drift preview."
    )
    parser.add_argument(
        "--recovery-target-preview-path",
        type=Path,
        default=DEFAULT_RECOVERY_TARGET_PREVIEW_PATH,
    )
    parser.add_argument(
        "--recovery-execution-batch-preview-path",
        type=Path,
        default=DEFAULT_RECOVERY_EXECUTION_BATCH_PREVIEW_PATH,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    previous_payload = (
        _load_json_or_default(args.output, {}) if args.output.exists() else {}
    )
    payload = build_procurement_space_recovery_gap_drift_preview(
        _load_json_or_default(args.recovery_target_preview_path, {}),
        _load_json_or_default(args.recovery_execution_batch_preview_path, {}),
        previous_payload,
    )
    save_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
