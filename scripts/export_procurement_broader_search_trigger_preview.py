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

DEFAULT_TAIL_FILL_RISK_PREVIEW_PATH = (
    REPO_ROOT / "artifacts" / "status" / "procurement_tail_fill_risk_preview.json"
)
DEFAULT_RECOVERY_SHORTFALL_BRIDGE_PREVIEW_PATH = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_recovery_shortfall_bridge_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_broader_search_trigger_preview.json"
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


def build_procurement_broader_search_trigger_preview(
    tail_fill_risk_preview: dict[str, Any],
    recovery_shortfall_bridge_preview: dict[str, Any],
    *,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    observed_at = observed_at or _utc_now()
    risk_summary = (
        tail_fill_risk_preview.get("summary")
        if isinstance(tail_fill_risk_preview.get("summary"), dict)
        else {}
    )
    bridge_summary = (
        recovery_shortfall_bridge_preview.get("summary")
        if isinstance(recovery_shortfall_bridge_preview.get("summary"), dict)
        else {}
    )
    risk_state = risk_summary.get("risk_state")
    cushion_hours = _coerce_float(risk_summary.get("cushion_hours"))
    bridge_state = bridge_summary.get("bridge_state")
    shortfall_gib = _coerce_float(bridge_summary.get("zero_gap_shortfall_gib"))

    if bridge_state == "no_bridge_required":
        trigger_state = "no_broader_search_required"
        next_action = (
            "No broader search is required because the current lane already "
            "covers the shortfall."
        )
    elif (
        risk_state == "zero_before_completion"
        and bridge_state == "no_bridge_inside_current_universe"
    ):
        trigger_state = "broader_search_immediate"
        next_action = (
            "The tail is projected to hit zero before completion and no bridge "
            "remains inside the current universe; broaden the search immediately."
        )
    elif bridge_state == "manual_review_bridge_possible":
        trigger_state = "manual_review_before_broader_search"
        next_action = (
            "A bounded manual-review bridge still exists, so review that lane "
            "before broadening the search universe."
        )
    else:
        trigger_state = "prepare_broader_search"
        next_action = (
            "The current bridge picture is weak enough that broader-search prep "
            "should begin, even if execution is not yet immediate."
        )

    return {
        "artifact_id": "procurement_broader_search_trigger_preview",
        "schema_id": "proteosphere-procurement-broader-search-trigger-preview-2026-04-03",
        "status": "report_only",
        "generated_at": observed_at.isoformat(),
        "summary": {
            "trigger_state": trigger_state,
            "risk_state": risk_state,
            "bridge_state": bridge_state,
            "cushion_hours": cushion_hours,
            "zero_gap_shortfall_gib": shortfall_gib,
            "non_mutating": True,
            "report_only": True,
        },
        "next_suggested_action": next_action,
        "source_artifacts": {
            "procurement_tail_fill_risk_preview": str(
                DEFAULT_TAIL_FILL_RISK_PREVIEW_PATH
            ).replace("\\", "/"),
            "procurement_recovery_shortfall_bridge_preview": str(
                DEFAULT_RECOVERY_SHORTFALL_BRIDGE_PREVIEW_PATH
            ).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only trigger view for when the recovery search "
                "must broaden beyond the current candidate universe."
            ),
            "report_only": True,
            "non_mutating": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a report-only procurement broader-search trigger preview."
    )
    parser.add_argument(
        "--tail-fill-risk-preview-path",
        type=Path,
        default=DEFAULT_TAIL_FILL_RISK_PREVIEW_PATH,
    )
    parser.add_argument(
        "--recovery-shortfall-bridge-preview-path",
        type=Path,
        default=DEFAULT_RECOVERY_SHORTFALL_BRIDGE_PREVIEW_PATH,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_procurement_broader_search_trigger_preview(
        _load_json_or_default(args.tail_fill_risk_preview_path, {}),
        _load_json_or_default(args.recovery_shortfall_bridge_preview_path, {}),
    )
    save_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
