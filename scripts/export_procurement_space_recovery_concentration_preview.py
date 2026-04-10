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
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_space_recovery_concentration_preview.json"
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


def build_procurement_space_recovery_concentration_preview(
    recovery_candidates_preview: dict[str, Any],
    *,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    observed_at = observed_at or _utc_now()
    summary = (
        recovery_candidates_preview.get("summary")
        if isinstance(recovery_candidates_preview.get("summary"), dict)
        else {}
    )
    rows = (
        recovery_candidates_preview.get("rows")
        if isinstance(recovery_candidates_preview.get("rows"), list)
        else []
    )
    total_ranked_reclaim_gib = _coerce_float(summary.get("total_ranked_reclaim_gib"))
    sorted_rows = sorted(
        [row for row in rows if isinstance(row, dict)],
        key=lambda row: _coerce_float(row.get("reclaim_gib_if_removed")),
        reverse=True,
    )
    top1_gib = sum(_coerce_float(row.get("reclaim_gib_if_removed")) for row in sorted_rows[:1])
    top3_gib = sum(_coerce_float(row.get("reclaim_gib_if_removed")) for row in sorted_rows[:3])
    top5_gib = sum(_coerce_float(row.get("reclaim_gib_if_removed")) for row in sorted_rows[:5])

    top1_fraction = _fraction(top1_gib, total_ranked_reclaim_gib)
    top3_fraction = _fraction(top3_gib, total_ranked_reclaim_gib)
    top5_fraction = _fraction(top5_gib, total_ranked_reclaim_gib)

    if total_ranked_reclaim_gib <= 0:
        concentration_state = "no_ranked_reclaim"
        next_action = "No ranked reclaim lane is currently available to analyze."
    elif top1_fraction >= 0.5:
        concentration_state = "top1_dominant"
        next_action = (
            "The ranked reclaim lane is dominated by the single largest candidate; "
            "that row drives most of the current lane's capacity."
        )
    elif top3_fraction >= 0.75:
        concentration_state = "top3_concentrated"
        next_action = (
            "The ranked reclaim lane is concentrated in the top three candidates; "
            "those rows dominate the practical reclaim picture."
        )
    else:
        concentration_state = "distributed_lane"
        next_action = (
            "The ranked reclaim lane is distributed across multiple candidates; "
            "no single row dominates the current lane."
        )

    lead_row = sorted_rows[0] if sorted_rows else {}

    return {
        "artifact_id": "procurement_space_recovery_concentration_preview",
        "schema_id": "proteosphere-procurement-space-recovery-concentration-preview-2026-04-03",
        "status": "report_only",
        "generated_at": observed_at.isoformat(),
        "summary": {
            "concentration_state": concentration_state,
            "ranked_candidate_count": len(sorted_rows),
            "total_ranked_reclaim_gib": total_ranked_reclaim_gib,
            "top1_reclaim_fraction": top1_fraction,
            "top3_reclaim_fraction": top3_fraction,
            "top5_reclaim_fraction": top5_fraction,
            "lead_candidate_filename": lead_row.get("filename"),
            "lead_candidate_reclaim_gib": _coerce_float(lead_row.get("reclaim_gib_if_removed")),
            "non_mutating": True,
            "report_only": True,
        },
        "next_suggested_action": next_action,
        "source_artifacts": {
            "procurement_space_recovery_candidates_preview": str(
                DEFAULT_RECOVERY_CANDIDATES_PREVIEW_PATH
            ).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only concentration view of the current ranked "
                "space-recovery candidate lane."
            ),
            "report_only": True,
            "non_mutating": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a report-only procurement space recovery concentration preview."
    )
    parser.add_argument(
        "--recovery-candidates-preview-path",
        type=Path,
        default=DEFAULT_RECOVERY_CANDIDATES_PREVIEW_PATH,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_procurement_space_recovery_concentration_preview(
        _load_json_or_default(args.recovery_candidates_preview_path, {})
    )
    save_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
