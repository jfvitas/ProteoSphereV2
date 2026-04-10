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
DEFAULT_RECOVERY_CANDIDATES_PREVIEW_PATH = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_space_recovery_candidates_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_space_recovery_execution_batch_preview.json"
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


def _build_batch(
    rows: list[dict[str, Any]],
    *,
    batch_id: str,
    target_bytes: int,
) -> dict[str, Any]:
    selected_rows: list[dict[str, Any]] = []
    cumulative_bytes = 0

    if target_bytes > 0:
        for row in rows:
            reclaim_bytes = _coerce_int(row.get("reclaim_bytes_if_removed"))
            if reclaim_bytes <= 0:
                continue
            selected_rows.append(
                {
                    "path": row.get("path"),
                    "filename": row.get("filename"),
                    "reason": row.get("reason"),
                    "safety_tier": row.get("safety_tier"),
                    "size_gib": row.get("size_gib"),
                    "reclaim_gib_if_removed": row.get("reclaim_gib_if_removed"),
                }
            )
            cumulative_bytes += reclaim_bytes
            if cumulative_bytes >= target_bytes:
                break

    shortfall_bytes = max(target_bytes - cumulative_bytes, 0)
    return {
        "batch_id": batch_id,
        "target_bytes": target_bytes,
        "target_gib": round(target_bytes / GIB, 3),
        "selected_candidate_count": len(selected_rows),
        "cumulative_reclaim_bytes": cumulative_bytes,
        "cumulative_reclaim_gib": round(cumulative_bytes / GIB, 3),
        "meets_target": cumulative_bytes >= target_bytes,
        "shortfall_bytes": shortfall_bytes,
        "shortfall_gib": round(shortfall_bytes / GIB, 3),
        "rows": selected_rows,
    }


def build_procurement_space_recovery_execution_batch_preview(
    recovery_target_preview: dict[str, Any],
    recovery_candidates_preview: dict[str, Any],
    *,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    observed_at = observed_at or _utc_now()
    target_summary = (
        recovery_target_preview.get("summary")
        if isinstance(recovery_target_preview.get("summary"), dict)
        else {}
    )
    candidate_summary = (
        recovery_candidates_preview.get("summary")
        if isinstance(recovery_candidates_preview.get("summary"), dict)
        else {}
    )
    candidate_rows = recovery_candidates_preview.get("rows")
    if not isinstance(candidate_rows, list):
        candidate_rows = []

    zero_gap_batch = _build_batch(
        candidate_rows,
        batch_id="zero_gap_batch",
        target_bytes=_coerce_int(target_summary.get("reclaim_to_zero_bytes")),
    )
    buffer_10_batch = _build_batch(
        candidate_rows,
        batch_id="buffer_10_gib_batch",
        target_bytes=_coerce_int(target_summary.get("reclaim_to_10_gib_buffer_bytes")),
    )
    buffer_20_batch = _build_batch(
        candidate_rows,
        batch_id="buffer_20_gib_batch",
        target_bytes=_coerce_int(target_summary.get("reclaim_to_20_gib_buffer_bytes")),
    )

    if not candidate_rows:
        execution_state = "no_execution_batches_available"
        next_action = (
            "No ranked recovery candidates are available to form a report-only "
            "reclaim batch."
        )
    elif buffer_20_batch["meets_target"]:
        execution_state = "buffered_recovery_batches_available"
        next_action = (
            "A single ranked non-mutating batch can cover the current tail plus the 20 GiB "
            "buffer target."
        )
    elif buffer_10_batch["meets_target"]:
        execution_state = "ten_gib_buffer_batch_available"
        next_action = (
            "The ranked duplicate-first lane can cover the current tail plus a 10 GiB safety "
            "buffer, but not the 20 GiB buffer target."
        )
    elif zero_gap_batch["meets_target"]:
        execution_state = "zero_gap_batch_available_only"
        next_action = (
            "The ranked duplicate-first lane can close the exact tail deficit, but it still "
            "falls short of the buffered safety targets."
        )
    else:
        execution_state = "insufficient_ranked_capacity"
        next_action = (
            "The currently ranked recovery candidates do not fully close the exact tail "
            "deficit; widen the candidate review lane before acting."
        )

    return {
        "artifact_id": "procurement_space_recovery_execution_batch_preview",
        "schema_id": "proteosphere-procurement-space-recovery-execution-batch-preview-2026-04-03",
        "status": "report_only",
        "generated_at": observed_at.isoformat(),
        "summary": {
            "execution_state": execution_state,
            "ranked_candidate_count": _coerce_int(
                candidate_summary.get("ranked_candidate_count")
            ),
            "zero_gap_batch_meets_target": zero_gap_batch["meets_target"],
            "buffer_10_gib_batch_meets_target": buffer_10_batch["meets_target"],
            "buffer_20_gib_batch_meets_target": buffer_20_batch["meets_target"],
            "zero_gap_batch_reclaim_gib": zero_gap_batch["cumulative_reclaim_gib"],
            "buffer_10_gib_batch_reclaim_gib": buffer_10_batch["cumulative_reclaim_gib"],
            "buffer_20_gib_batch_reclaim_gib": buffer_20_batch["cumulative_reclaim_gib"],
            "non_mutating": True,
            "report_only": True,
        },
        "batches": {
            "zero_gap_batch": zero_gap_batch,
            "buffer_10_gib_batch": buffer_10_batch,
            "buffer_20_gib_batch": buffer_20_batch,
        },
        "next_suggested_action": next_action,
        "source_artifacts": {
            "procurement_space_recovery_target_preview": str(
                DEFAULT_RECOVERY_TARGET_PREVIEW_PATH
            ).replace("\\", "/"),
            "procurement_space_recovery_candidates_preview": str(
                DEFAULT_RECOVERY_CANDIDATES_PREVIEW_PATH
            ).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only execution-batch planner derived from the ranked "
                "recovery candidates and exact reclaim targets. It does not move, delete, "
                "or mutate files."
            ),
            "report_only": True,
            "non_mutating": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a report-only procurement space recovery execution-batch preview."
    )
    parser.add_argument(
        "--recovery-target-preview-path",
        type=Path,
        default=DEFAULT_RECOVERY_TARGET_PREVIEW_PATH,
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
    payload = build_procurement_space_recovery_execution_batch_preview(
        _load_json_or_default(args.recovery_target_preview_path, {}),
        _load_json_or_default(args.recovery_candidates_preview_path, {}),
    )
    save_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
