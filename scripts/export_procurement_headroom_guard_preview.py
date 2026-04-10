from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.tasklib import load_json, save_json  # noqa: E402

DEFAULT_TAIL_GROWTH_PREVIEW_PATH = (
    REPO_ROOT / "artifacts" / "status" / "procurement_tail_growth_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "procurement_headroom_guard_preview.json"
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


def build_procurement_headroom_guard_preview(
    tail_growth_preview: dict[str, Any],
    *,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    observed_at = observed_at or _utc_now()
    tail_growth_preview = (
        tail_growth_preview if isinstance(tail_growth_preview, dict) else {}
    )
    summary = tail_growth_preview.get("summary") if isinstance(
        tail_growth_preview.get("summary"), dict
    ) else {}
    rows = (
        tail_growth_preview.get("rows")
        if isinstance(tail_growth_preview.get("rows"), list)
        else []
    )

    disk = shutil.disk_usage(REPO_ROOT.anchor)
    free_bytes = int(disk.free)
    used_bytes = int(disk.used)
    active_tail_bytes = _coerce_int(summary.get("total_after_bytes"))
    recent_growth_bytes_per_second = float(summary.get("aggregate_bytes_per_second") or 0.0)
    estimated_hours_to_zero = (
        round(free_bytes / recent_growth_bytes_per_second / 3600, 3)
        if recent_growth_bytes_per_second > 0
        else None
    )
    free_to_active_tail_ratio = (
        round(free_bytes / active_tail_bytes, 3) if active_tail_bytes > 0 else None
    )

    if free_bytes < 30 * GIB or (
        estimated_hours_to_zero is not None and estimated_hours_to_zero < 2
    ):
        guard_state = "critical_headroom"
        next_action = (
            "Free additional space or intervene before assuming the tail can "
            "continue safely."
        )
    elif free_bytes < 75 * GIB or (
        estimated_hours_to_zero is not None and estimated_hours_to_zero < 8
    ):
        guard_state = "caution_headroom"
        next_action = "Keep the tail moving, but continue to watch free-space margin closely."
    else:
        guard_state = "healthy_headroom"
        next_action = (
            "Current free-space margin is still healthy enough for continued "
            "tail monitoring."
        )

    compact_rows = [
        {
            "source_id": row.get("source_id"),
            "filename": row.get("filename"),
            "after_bytes": row.get("after_bytes"),
            "delta_bytes": row.get("delta_bytes"),
            "bytes_per_second": row.get("bytes_per_second"),
            "growth_state": row.get("growth_state"),
        }
        for row in rows
    ]

    return {
        "artifact_id": "procurement_headroom_guard_preview",
        "schema_id": "proteosphere-procurement-headroom-guard-preview-2026-04-03",
        "status": "report_only",
        "generated_at": observed_at.isoformat(),
        "summary": {
            "guard_state": guard_state,
            "free_bytes": free_bytes,
            "free_gib": round(free_bytes / GIB, 3),
            "used_bytes": used_bytes,
            "active_tail_file_count": _coerce_int(summary.get("sampled_tail_file_count")),
            "active_tail_bytes": active_tail_bytes,
            "recent_growth_bytes_per_second": recent_growth_bytes_per_second,
            "estimated_hours_to_zero_free_at_recent_rate": estimated_hours_to_zero,
            "free_to_active_tail_ratio": free_to_active_tail_ratio,
            "non_mutating": True,
            "report_only": True,
        },
        "rows": compact_rows,
        "next_suggested_action": next_action,
        "source_artifacts": {
            "procurement_tail_growth_preview": str(DEFAULT_TAIL_GROWTH_PREVIEW_PATH).replace(
                "\\", "/"
            ),
            "disk_anchor": REPO_ROOT.anchor.replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only headroom guard derived from current free space and "
                "recent short-window tail growth. It does not predict final completion size "
                "and does not mutate downloads or storage."
            ),
            "report_only": True,
            "non_mutating": True,
            "short_window_growth_assumption": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a report-only procurement headroom guard preview."
    )
    parser.add_argument(
        "--tail-growth-preview-path",
        type=Path,
        default=DEFAULT_TAIL_GROWTH_PREVIEW_PATH,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_procurement_headroom_guard_preview(
        _load_json_or_default(args.tail_growth_preview_path, {})
    )
    save_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
