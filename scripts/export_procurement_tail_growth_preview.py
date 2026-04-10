from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.tasklib import load_json, save_json  # noqa: E402

DEFAULT_PROCUREMENT_STATUS_BOARD_PATH = (
    REPO_ROOT / "artifacts" / "status" / "procurement_status_board.json"
)
DEFAULT_BROAD_MIRROR_PROGRESS_PATH = (
    REPO_ROOT / "artifacts" / "status" / "broad_mirror_progress.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "procurement_tail_growth_preview.json"
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _load_json_or_default(path: Path, default: Any) -> Any:
    return load_json(path, default) if path.exists() else default


def _normalize_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _coerce_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _part_path(source_root: str, filename: str) -> Path | None:
    if not source_root or not filename:
        return None
    root = REPO_ROOT / Path(source_root)
    candidates = (
        root / f"{filename}.part",
        root / f"{filename}.partial",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _size_reader(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0


def build_procurement_tail_growth_preview(
    board: dict[str, Any],
    broad_progress: dict[str, Any],
    *,
    sample_window_seconds: int = 5,
    observed_at: datetime | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
    size_reader: Callable[[Path], int] = _size_reader,
) -> dict[str, Any]:
    observed_at = observed_at or _utc_now()
    board = board if isinstance(board, dict) else {}
    broad_progress = broad_progress if isinstance(broad_progress, dict) else {}

    board_supervisor = (
        board.get("procurement_supervisor")
        if isinstance(board.get("procurement_supervisor"), dict)
        else {}
    )
    active_rows = _normalize_rows(board_supervisor.get("active_observed_downloads"))
    progress_sources = {
        str(row.get("source_id") or ""): row
        for row in _normalize_rows(broad_progress.get("sources"))
    }

    tracked: list[dict[str, Any]] = []
    for row in active_rows:
        source_id = str(row.get("task_id") or row.get("source_id") or "").strip()
        filename = str(row.get("filename") or row.get("description") or "").strip()
        source_progress = progress_sources.get(source_id) or {}
        source_root = str(source_progress.get("source_root") or "").strip()
        part_path = _part_path(source_root, filename)
        tracked.append(
            {
                "source_id": source_id,
                "source_name": row.get("source_name"),
                "filename": filename,
                "category": row.get("category"),
                "path": str(part_path).replace("\\", "/") if part_path is not None else None,
                "part_path": part_path,
            }
        )

    before_sizes = {
        row["filename"]: size_reader(row["part_path"])
        for row in tracked
        if row["part_path"] is not None
    }
    if before_sizes and sample_window_seconds > 0:
        sleep_fn(sample_window_seconds)
    after_sizes = {
        row["filename"]: size_reader(row["part_path"])
        for row in tracked
        if row["part_path"] is not None
    }

    rows: list[dict[str, Any]] = []
    total_before = 0
    total_after = 0
    total_delta = 0
    positive_growth_file_count = 0
    sampled_tail_file_count = 0
    for row in tracked:
        filename = row["filename"]
        if row["part_path"] is None:
            rows.append(
                {
                    "source_id": row["source_id"],
                    "source_name": row.get("source_name"),
                    "filename": filename,
                    "category": row.get("category"),
                    "path": None,
                    "before_bytes": None,
                    "after_bytes": None,
                    "delta_bytes": None,
                    "bytes_per_second": None,
                    "growth_state": "missing_partial_artifact",
                }
            )
            continue

        before = _coerce_int(before_sizes.get(filename))
        after = _coerce_int(after_sizes.get(filename))
        delta = after - before
        bytes_per_second = (
            round(delta / sample_window_seconds, 3) if sample_window_seconds > 0 else None
        )
        growth_state = "growing" if delta > 0 else "flat_or_stalled"
        sampled_tail_file_count += 1
        total_before += before
        total_after += after
        total_delta += delta
        if delta > 0:
            positive_growth_file_count += 1

        rows.append(
            {
                "source_id": row["source_id"],
                "source_name": row.get("source_name"),
                "filename": filename,
                "category": row.get("category"),
                "path": row.get("path"),
                "before_bytes": before,
                "after_bytes": after,
                "delta_bytes": delta,
                "bytes_per_second": bytes_per_second,
                "growth_state": growth_state,
            }
        )

    stalled_file_count = max(sampled_tail_file_count - positive_growth_file_count, 0)
    if sampled_tail_file_count == 0:
        growth_state = "no_tail_files_sampled"
    elif positive_growth_file_count == sampled_tail_file_count:
        growth_state = "active_growth"
    elif positive_growth_file_count > 0:
        growth_state = "mixed_growth"
    else:
        growth_state = "flat_or_stalled"

    aggregate_bytes_per_second = (
        round(total_delta / sample_window_seconds, 3)
        if sample_window_seconds > 0 and sampled_tail_file_count > 0
        else None
    )
    if growth_state == "active_growth":
        next_action = (
            "Keep the procurement tail running; both authoritative remaining "
            "files are still growing."
        )
    elif growth_state == "mixed_growth":
        next_action = "Watch the slower tail file and keep the active-growth lane visible."
    elif growth_state == "flat_or_stalled":
        next_action = (
            "Inspect the tail downloads before assuming the procurement lane "
            "is still healthy."
        )
    else:
        next_action = "No authoritative tail partials were sampled."

    return {
        "artifact_id": "procurement_tail_growth_preview",
        "schema_id": "proteosphere-procurement-tail-growth-preview-2026-04-03",
        "status": "report_only",
        "generated_at": observed_at.isoformat(),
        "summary": {
            "growth_state": growth_state,
            "active_tail_file_count": len(active_rows),
            "sampled_tail_file_count": sampled_tail_file_count,
            "positive_growth_file_count": positive_growth_file_count,
            "stalled_file_count": stalled_file_count,
            "sample_window_seconds": sample_window_seconds,
            "total_before_bytes": total_before,
            "total_after_bytes": total_after,
            "total_delta_bytes": total_delta,
            "aggregate_bytes_per_second": aggregate_bytes_per_second,
            "non_mutating": True,
            "report_only": True,
        },
        "rows": rows,
        "next_suggested_action": next_action,
        "source_artifacts": {
            "procurement_status_board": str(DEFAULT_PROCUREMENT_STATUS_BOARD_PATH).replace(
                "\\", "/"
            ),
            "broad_mirror_progress": str(DEFAULT_BROAD_MIRROR_PROGRESS_PATH).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only short-window growth sample for the authoritative "
                "procurement tail files. It measures current partial-file growth without "
                "starting, stopping, or resuming downloads."
            ),
            "report_only": True,
            "non_mutating": True,
            "short_window_sample_only": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a report-only procurement tail growth preview."
    )
    parser.add_argument(
        "--procurement-status-board-path",
        type=Path,
        default=DEFAULT_PROCUREMENT_STATUS_BOARD_PATH,
    )
    parser.add_argument(
        "--broad-mirror-progress-path",
        type=Path,
        default=DEFAULT_BROAD_MIRROR_PROGRESS_PATH,
    )
    parser.add_argument("--sample-window-seconds", type=int, default=5)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_procurement_tail_growth_preview(
        _load_json_or_default(args.procurement_status_board_path, {}),
        _load_json_or_default(args.broad_mirror_progress_path, {}),
        sample_window_seconds=args.sample_window_seconds,
    )
    save_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
