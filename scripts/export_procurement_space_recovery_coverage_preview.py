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
    / "procurement_space_recovery_coverage_preview.json"
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


def _coverage_ratio(reclaim_bytes: int, target_bytes: int) -> float:
    if target_bytes <= 0:
        return 1.0
    return min(reclaim_bytes / target_bytes, 1.0)


def build_procurement_space_recovery_coverage_preview(
    recovery_target_preview: dict[str, Any],
    recovery_execution_batch_preview: dict[str, Any],
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

    zero_gap_batch = (
        batches.get("zero_gap_batch")
        if isinstance(batches.get("zero_gap_batch"), dict)
        else {}
    )
    buffer_10_batch = (
        batches.get("buffer_10_gib_batch")
        if isinstance(batches.get("buffer_10_gib_batch"), dict)
        else {}
    )
    buffer_20_batch = (
        batches.get("buffer_20_gib_batch")
        if isinstance(batches.get("buffer_20_gib_batch"), dict)
        else {}
    )

    reclaim_to_zero_bytes = _coerce_int(target_summary.get("reclaim_to_zero_bytes"))
    reclaim_to_10_bytes = _coerce_int(target_summary.get("reclaim_to_10_gib_buffer_bytes"))
    reclaim_to_20_bytes = _coerce_int(target_summary.get("reclaim_to_20_gib_buffer_bytes"))
    zero_gap_reclaim_bytes = _coerce_int(zero_gap_batch.get("cumulative_reclaim_bytes"))
    buffer_10_reclaim_bytes = _coerce_int(buffer_10_batch.get("cumulative_reclaim_bytes"))
    buffer_20_reclaim_bytes = _coerce_int(buffer_20_batch.get("cumulative_reclaim_bytes"))

    zero_gap_coverage_fraction = round(
        _coverage_ratio(zero_gap_reclaim_bytes, reclaim_to_zero_bytes), 3
    )
    buffer_10_coverage_fraction = round(
        _coverage_ratio(buffer_10_reclaim_bytes, reclaim_to_10_bytes), 3
    )
    buffer_20_coverage_fraction = round(
        _coverage_ratio(buffer_20_reclaim_bytes, reclaim_to_20_bytes), 3
    )

    if reclaim_to_zero_bytes <= 0:
        coverage_state = "no_recovery_required"
        next_action = (
            "No additional recovery target is currently required by the exact "
            "completion margin."
        )
    elif zero_gap_coverage_fraction >= 1.0:
        coverage_state = "zero_gap_covered"
        next_action = (
            "The ranked recovery lane covers the exact zero-gap target; keep "
            "buffered targets visible."
        )
    elif buffer_10_coverage_fraction >= 1.0:
        coverage_state = "ten_gib_buffer_covered_zero_gap_short"
        next_action = (
            "The ranked lane reaches the 10 GiB buffer target but remains "
            "short of the exact zero-gap target; keep the shortfall visible."
        )
    else:
        coverage_state = "ranked_lane_short_of_zero_gap"
        next_action = (
            "The ranked recovery lane remains short of the exact zero-gap and buffered targets; "
            "treat the current batch as incomplete."
        )

    return {
        "artifact_id": "procurement_space_recovery_coverage_preview",
        "schema_id": "proteosphere-procurement-space-recovery-coverage-preview-2026-04-03",
        "status": "report_only",
        "generated_at": observed_at.isoformat(),
        "summary": {
            "coverage_state": coverage_state,
            "zero_gap_coverage_fraction": zero_gap_coverage_fraction,
            "buffer_10_gib_coverage_fraction": buffer_10_coverage_fraction,
            "buffer_20_gib_coverage_fraction": buffer_20_coverage_fraction,
            "zero_gap_shortfall_gib": round(
                max(reclaim_to_zero_bytes - zero_gap_reclaim_bytes, 0) / GIB, 3
            ),
            "buffer_10_gib_shortfall_gib": round(
                max(reclaim_to_10_bytes - buffer_10_reclaim_bytes, 0) / GIB, 3
            ),
            "buffer_20_gib_shortfall_gib": round(
                max(reclaim_to_20_bytes - buffer_20_reclaim_bytes, 0) / GIB, 3
            ),
            "non_mutating": True,
            "report_only": True,
        },
        "targets": {
            "reclaim_to_zero_gib": round(reclaim_to_zero_bytes / GIB, 3),
            "reclaim_to_10_gib_buffer_gib": round(reclaim_to_10_bytes / GIB, 3),
            "reclaim_to_20_gib_buffer_gib": round(reclaim_to_20_bytes / GIB, 3),
            "ranked_reclaim_gib": round(zero_gap_reclaim_bytes / GIB, 3),
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
                "This is a report-only coverage view for the ranked recovery "
                "lane against exact and buffered reclaim targets."
            ),
            "report_only": True,
            "non_mutating": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a report-only procurement space recovery coverage preview."
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
    payload = build_procurement_space_recovery_coverage_preview(
        _load_json_or_default(args.recovery_target_preview_path, {}),
        _load_json_or_default(args.recovery_execution_batch_preview_path, {}),
    )
    save_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
