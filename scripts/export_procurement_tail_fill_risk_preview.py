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

DEFAULT_COMPLETION_MARGIN_PREVIEW_PATH = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_tail_completion_margin_preview.json"
)
DEFAULT_HEADROOM_GUARD_PREVIEW_PATH = (
    REPO_ROOT / "artifacts" / "status" / "procurement_headroom_guard_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "procurement_tail_fill_risk_preview.json"
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


def build_procurement_tail_fill_risk_preview(
    completion_margin_preview: dict[str, Any],
    headroom_guard_preview: dict[str, Any],
    *,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    observed_at = observed_at or _utc_now()
    completion_summary = (
        completion_margin_preview.get("summary")
        if isinstance(completion_margin_preview.get("summary"), dict)
        else {}
    )
    headroom_summary = (
        headroom_guard_preview.get("summary")
        if isinstance(headroom_guard_preview.get("summary"), dict)
        else {}
    )
    completion_rows = completion_margin_preview.get("rows")
    if not isinstance(completion_rows, list):
        completion_rows = []

    free_bytes = _coerce_int(completion_summary.get("free_bytes"))
    aggregate_bps = _coerce_float(headroom_summary.get("recent_growth_bytes_per_second"))
    hours_to_zero = _coerce_float(
        headroom_summary.get("estimated_hours_to_zero_free_at_recent_rate")
    )
    completion_hours = [
        _coerce_float(row.get("estimated_hours_to_completion_at_recent_rate"))
        for row in completion_rows
        if _coerce_float(row.get("estimated_hours_to_completion_at_recent_rate")) > 0
    ]
    slowest_completion_hours = max(completion_hours) if completion_hours else 0.0
    cushion_hours = (
        round(hours_to_zero - slowest_completion_hours, 3)
        if hours_to_zero > 0 and slowest_completion_hours > 0
        else None
    )

    if aggregate_bps <= 0 or not completion_hours:
        risk_state = "insufficient_rate_data"
        next_action = (
            "Tail growth or completion timing could not be estimated cleanly; keep "
            "sampling before making a recovery-trigger decision."
        )
    elif hours_to_zero <= 0:
        risk_state = "space_exhaustion_imminent"
        next_action = (
            "Free space is effectively exhausted at the current tail rate; treat "
            "recovery review as urgent."
        )
    elif hours_to_zero < slowest_completion_hours:
        risk_state = "zero_before_completion"
        next_action = (
            "At the current tail rate, D: is projected to fill before the slower "
            "remaining download completes."
        )
    else:
        risk_state = "completion_before_zero"
        next_action = (
            "At the current tail rate, both remaining downloads are projected to "
            "finish before D: reaches zero free space."
        )

    return {
        "artifact_id": "procurement_tail_fill_risk_preview",
        "schema_id": "proteosphere-procurement-tail-fill-risk-preview-2026-04-03",
        "status": "report_only",
        "generated_at": observed_at.isoformat(),
        "summary": {
            "risk_state": risk_state,
            "free_bytes": free_bytes,
            "aggregate_bytes_per_second": aggregate_bps,
            "estimated_hours_to_zero_free": round(hours_to_zero, 3)
            if hours_to_zero > 0
            else 0.0,
            "slowest_completion_hours": round(slowest_completion_hours, 3)
            if slowest_completion_hours > 0
            else 0.0,
            "cushion_hours": cushion_hours,
            "non_mutating": True,
            "report_only": True,
        },
        "rows": [
            {
                "comparison": "tail_fill_window",
                "estimated_hours_to_zero_free": round(hours_to_zero, 3)
                if hours_to_zero > 0
                else 0.0,
                "slowest_completion_hours": round(slowest_completion_hours, 3)
                if slowest_completion_hours > 0
                else 0.0,
                "cushion_hours": cushion_hours,
            }
        ],
        "next_suggested_action": next_action,
        "source_artifacts": {
            "procurement_tail_completion_margin_preview": str(
                DEFAULT_COMPLETION_MARGIN_PREVIEW_PATH
            ).replace("\\", "/"),
            "procurement_headroom_guard_preview": str(
                DEFAULT_HEADROOM_GUARD_PREVIEW_PATH
            ).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only tail fill-risk estimate that compares recent "
                "growth-based time-to-zero against current completion ETA estimates."
            ),
            "report_only": True,
            "non_mutating": True,
            "short_window_growth_assumption": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a report-only procurement tail fill-risk preview."
    )
    parser.add_argument(
        "--completion-margin-preview-path",
        type=Path,
        default=DEFAULT_COMPLETION_MARGIN_PREVIEW_PATH,
    )
    parser.add_argument(
        "--headroom-guard-preview-path",
        type=Path,
        default=DEFAULT_HEADROOM_GUARD_PREVIEW_PATH,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_procurement_tail_fill_risk_preview(
        _load_json_or_default(args.completion_margin_preview_path, {}),
        _load_json_or_default(args.headroom_guard_preview_path, {}),
    )
    save_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
