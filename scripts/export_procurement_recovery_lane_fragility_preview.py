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
DEFAULT_RECOVERY_COVERAGE_PREVIEW_PATH = (
    REPO_ROOT / "artifacts" / "status" / "procurement_space_recovery_coverage_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_recovery_lane_fragility_preview.json"
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


def _fraction(part: float, whole: float) -> float:
    if whole <= 0:
        return 0.0
    return round(part / whole, 3)


def build_procurement_recovery_lane_fragility_preview(
    recovery_candidates_preview: dict[str, Any],
    recovery_coverage_preview: dict[str, Any],
    *,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    observed_at = observed_at or _utc_now()
    candidate_summary = (
        recovery_candidates_preview.get("summary")
        if isinstance(recovery_candidates_preview.get("summary"), dict)
        else {}
    )
    coverage_summary = (
        recovery_coverage_preview.get("summary")
        if isinstance(recovery_coverage_preview.get("summary"), dict)
        else {}
    )
    rows = (
        recovery_candidates_preview.get("rows")
        if isinstance(recovery_candidates_preview.get("rows"), list)
        else []
    )
    sorted_rows = sorted(
        [row for row in rows if isinstance(row, dict)],
        key=lambda row: _coerce_float(row.get("reclaim_gib_if_removed")),
        reverse=True,
    )
    total_ranked_reclaim_gib = _coerce_float(candidate_summary.get("total_ranked_reclaim_gib"))
    zero_gap_shortfall_gib = _coerce_float(coverage_summary.get("zero_gap_shortfall_gib"))
    lead_gib = _coerce_float(sorted_rows[0].get("reclaim_gib_if_removed")) if sorted_rows else 0.0
    residual_without_lead_gib = round(max(total_ranked_reclaim_gib - lead_gib, 0.0), 3)
    residual_vs_shortfall_fraction = _fraction(residual_without_lead_gib, zero_gap_shortfall_gib)

    if total_ranked_reclaim_gib <= 0:
        fragility_state = "no_ranked_lane"
        next_action = "No ranked lane exists, so fragility analysis is not applicable."
    elif lead_gib <= 0:
        fragility_state = "distributed_without_lead_risk"
        next_action = "No lead candidate dominates the current lane."
    elif lead_gib >= zero_gap_shortfall_gib:
        fragility_state = "lead_candidate_covers_shortfall"
        next_action = (
            "The lead candidate alone exceeds the current shortfall, which makes "
            "the lane highly dependent on that single row."
        )
    elif residual_without_lead_gib < zero_gap_shortfall_gib:
        fragility_state = "lane_breaks_without_lead"
        next_action = (
            "If the lead candidate is excluded, the residual ranked lane still "
            "fails to bridge the shortfall."
        )
    else:
        fragility_state = "lane_survives_without_lead"
        next_action = (
            "The lane remains incomplete overall, but it does not collapse solely "
            "because of the lead candidate."
        )

    return {
        "artifact_id": "procurement_recovery_lane_fragility_preview",
        "schema_id": "proteosphere-procurement-recovery-lane-fragility-preview-2026-04-03",
        "status": "report_only",
        "generated_at": observed_at.isoformat(),
        "summary": {
            "fragility_state": fragility_state,
            "lead_candidate_filename": sorted_rows[0].get("filename") if sorted_rows else None,
            "lead_candidate_reclaim_gib": lead_gib,
            "residual_ranked_reclaim_without_lead_gib": residual_without_lead_gib,
            "zero_gap_shortfall_gib": zero_gap_shortfall_gib,
            "residual_vs_shortfall_fraction": residual_vs_shortfall_fraction,
            "non_mutating": True,
            "report_only": True,
        },
        "next_suggested_action": next_action,
        "source_artifacts": {
            "procurement_space_recovery_candidates_preview": str(
                DEFAULT_RECOVERY_CANDIDATES_PREVIEW_PATH
            ).replace("\\", "/"),
            "procurement_space_recovery_coverage_preview": str(
                DEFAULT_RECOVERY_COVERAGE_PREVIEW_PATH
            ).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only fragility view of the ranked recovery lane "
                "under lead-candidate exclusion."
            ),
            "report_only": True,
            "non_mutating": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a report-only procurement recovery lane fragility preview."
    )
    parser.add_argument(
        "--recovery-candidates-preview-path",
        type=Path,
        default=DEFAULT_RECOVERY_CANDIDATES_PREVIEW_PATH,
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
    payload = build_procurement_recovery_lane_fragility_preview(
        _load_json_or_default(args.recovery_candidates_preview_path, {}),
        _load_json_or_default(args.recovery_coverage_preview_path, {}),
    )
    save_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
