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

DEFAULT_LOG_PROGRESS_REGISTRY_PATH = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_tail_log_progress_registry_preview.json"
)
DEFAULT_TAIL_GROWTH_PREVIEW_PATH = (
    REPO_ROOT / "artifacts" / "status" / "procurement_tail_growth_preview.json"
)
DEFAULT_HEADROOM_GUARD_PREVIEW_PATH = (
    REPO_ROOT / "artifacts" / "status" / "procurement_headroom_guard_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_tail_completion_margin_preview.json"
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


def _coerce_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def build_procurement_tail_completion_margin_preview(
    log_progress_registry: dict[str, Any],
    tail_growth_preview: dict[str, Any],
    headroom_guard_preview: dict[str, Any],
    *,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    observed_at = observed_at or _utc_now()
    log_progress_registry = (
        log_progress_registry if isinstance(log_progress_registry, dict) else {}
    )
    tail_growth_preview = (
        tail_growth_preview if isinstance(tail_growth_preview, dict) else {}
    )
    headroom_guard_preview = (
        headroom_guard_preview if isinstance(headroom_guard_preview, dict) else {}
    )

    growth_rows = {
        str(row.get("filename") or ""): row
        for row in (tail_growth_preview.get("rows") or [])
        if isinstance(row, dict)
    }
    free_bytes = _coerce_int((headroom_guard_preview.get("summary") or {}).get("free_bytes"))

    rows: list[dict[str, Any]] = []
    total_remaining_bytes = 0
    parsed_total_count = 0
    for row in (log_progress_registry.get("rows") or []):
        if not isinstance(row, dict):
            continue
        filename = str(row.get("filename") or "")
        total_bytes = _coerce_int(row.get("total_bytes_from_log"))
        current_bytes = _coerce_int(row.get("current_bytes_from_log"))
        if filename in growth_rows:
            growth_after = _coerce_int(growth_rows[filename].get("after_bytes"))
            if growth_after > 0:
                current_bytes = growth_after
        remaining_bytes = max(total_bytes - current_bytes, 0) if total_bytes > 0 else 0
        recent_rate = _coerce_float((growth_rows.get(filename) or {}).get("bytes_per_second"))
        hours_to_completion = (
            round(remaining_bytes / recent_rate / 3600, 3) if recent_rate > 0 else None
        )
        if total_bytes > 0:
            parsed_total_count += 1
            total_remaining_bytes += remaining_bytes
        rows.append(
            {
                "source_id": row.get("source_id"),
                "source_name": row.get("source_name"),
                "filename": filename,
                "current_bytes": current_bytes,
                "total_bytes": total_bytes,
                "remaining_bytes": remaining_bytes,
                "recent_growth_bytes_per_second": recent_rate if recent_rate > 0 else None,
                "estimated_hours_to_completion_at_recent_rate": hours_to_completion,
                "match_state": row.get("match_state"),
            }
        )

    projected_free_after_completion = free_bytes - total_remaining_bytes
    if parsed_total_count == 0:
        completion_state = "no_exact_total_available"
        next_action = (
            "No parsed total sizes are available yet; fall back to growth-only "
            "procurement monitoring."
        )
    elif projected_free_after_completion < 0:
        completion_state = "insufficient_margin_for_tail_completion"
        next_action = (
            "Current free space is below the exact remaining tail bytes; free "
            "space before assuming both downloads can finish."
        )
    elif projected_free_after_completion < 20 * GIB:
        completion_state = "tight_margin_for_tail_completion"
        next_action = (
            "The remaining tail should fit, but the projected post-completion "
            "margin is tight."
        )
    else:
        completion_state = "sufficient_margin_for_tail_completion"
        next_action = (
            "Current free space should cover the exact remaining authoritative "
            "tail with room to spare."
        )

    return {
        "artifact_id": "procurement_tail_completion_margin_preview",
        "schema_id": "proteosphere-procurement-tail-completion-margin-preview-2026-04-03",
        "status": "report_only",
        "generated_at": observed_at.isoformat(),
        "summary": {
            "completion_state": completion_state,
            "parsed_total_count": parsed_total_count,
            "free_bytes": free_bytes,
            "free_gib": round(free_bytes / GIB, 3) if free_bytes > 0 else 0.0,
            "total_remaining_bytes": total_remaining_bytes,
            "total_remaining_gib": round(total_remaining_bytes / GIB, 3)
            if total_remaining_bytes > 0
            else 0.0,
            "projected_free_after_completion_bytes": projected_free_after_completion,
            "projected_free_after_completion_gib": round(
                projected_free_after_completion / GIB, 3
            ),
            "non_mutating": True,
            "report_only": True,
            "exact_log_total_based": parsed_total_count > 0,
        },
        "rows": rows,
        "next_suggested_action": next_action,
        "source_artifacts": {
            "procurement_tail_log_progress_registry_preview": str(
                DEFAULT_LOG_PROGRESS_REGISTRY_PATH
            ).replace("\\", "/"),
            "procurement_tail_growth_preview": str(
                DEFAULT_TAIL_GROWTH_PREVIEW_PATH
            ).replace("\\", "/"),
            "procurement_headroom_guard_preview": str(
                DEFAULT_HEADROOM_GUARD_PREVIEW_PATH
            ).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only completion-margin estimate using totals "
                "parsed from the current tail-download stdout logs plus current "
                "free space and recent growth."
            ),
            "report_only": True,
            "non_mutating": True,
            "exact_when_log_totals_present": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a report-only procurement tail completion margin preview."
    )
    parser.add_argument(
        "--log-progress-registry-path",
        type=Path,
        default=DEFAULT_LOG_PROGRESS_REGISTRY_PATH,
    )
    parser.add_argument(
        "--tail-growth-preview-path",
        type=Path,
        default=DEFAULT_TAIL_GROWTH_PREVIEW_PATH,
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
    payload = build_procurement_tail_completion_margin_preview(
        _load_json_or_default(args.log_progress_registry_path, {}),
        _load_json_or_default(args.tail_growth_preview_path, {}),
        _load_json_or_default(args.headroom_guard_preview_path, {}),
    )
    save_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
