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

DEFAULT_TAIL_GROWTH_PREVIEW_PATH = (
    REPO_ROOT / "artifacts" / "status" / "procurement_tail_growth_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_tail_source_pressure_preview.json"
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


def build_procurement_tail_source_pressure_preview(
    tail_growth_preview: dict[str, Any],
    *,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    observed_at = observed_at or _utc_now()
    tail_growth_preview = (
        tail_growth_preview if isinstance(tail_growth_preview, dict) else {}
    )
    rows = tail_growth_preview.get("rows")
    growth_rows = rows if isinstance(rows, list) else []

    total_after_bytes = 0
    total_delta_bytes = 0
    grouped: dict[str, dict[str, Any]] = {}
    for row in growth_rows:
        if not isinstance(row, dict):
            continue
        source_id = str(row.get("source_id") or "").strip() or "unknown"
        group = grouped.setdefault(
            source_id,
            {
                "source_id": source_id,
                "source_name": row.get("source_name"),
                "filename_count": 0,
                "after_bytes": 0,
                "delta_bytes": 0,
            },
        )
        group["filename_count"] += 1
        group["after_bytes"] += _coerce_int(row.get("after_bytes"))
        group["delta_bytes"] += _coerce_int(row.get("delta_bytes"))
        total_after_bytes += _coerce_int(row.get("after_bytes"))
        total_delta_bytes += _coerce_int(row.get("delta_bytes"))

    compact_rows: list[dict[str, Any]] = []
    for group in grouped.values():
        after_bytes = _coerce_int(group.get("after_bytes"))
        delta_bytes = _coerce_int(group.get("delta_bytes"))
        byte_share = round(after_bytes / total_after_bytes, 3) if total_after_bytes > 0 else None
        growth_share = round(delta_bytes / total_delta_bytes, 3) if total_delta_bytes > 0 else None
        compact_rows.append(
            {
                "source_id": group.get("source_id"),
                "source_name": group.get("source_name"),
                "filename_count": group.get("filename_count"),
                "after_bytes": after_bytes,
                "delta_bytes": delta_bytes,
                "byte_share": byte_share,
                "growth_share": growth_share,
            }
        )

    compact_rows.sort(key=lambda row: (row.get("after_bytes") or 0), reverse=True)
    dominant = compact_rows[0] if compact_rows else {}
    dominant_share = _coerce_float(dominant.get("byte_share"))
    if not compact_rows:
        pressure_state = "no_tail_sources"
        next_action = "No authoritative tail sources were available for pressure ranking."
    elif dominant_share >= 0.6:
        pressure_state = "source_dominant"
        next_action = (
            "One remaining source dominates the current tail bytes; prioritize "
            "that source if space pressure rises again."
        )
    else:
        pressure_state = "split_pressure"
        next_action = "Current tail pressure is split across the remaining authoritative sources."

    return {
        "artifact_id": "procurement_tail_source_pressure_preview",
        "schema_id": "proteosphere-procurement-tail-source-pressure-preview-2026-04-03",
        "status": "report_only",
        "generated_at": observed_at.isoformat(),
        "summary": {
            "pressure_state": pressure_state,
            "source_count": len(compact_rows),
            "total_after_bytes": total_after_bytes,
            "total_delta_bytes": total_delta_bytes,
            "dominant_source_id": dominant.get("source_id"),
            "dominant_source_name": dominant.get("source_name"),
            "dominant_source_byte_share": dominant.get("byte_share"),
            "dominant_source_growth_share": dominant.get("growth_share"),
            "non_mutating": True,
            "report_only": True,
        },
        "rows": compact_rows,
        "next_suggested_action": next_action,
        "source_artifacts": {
            "procurement_tail_growth_preview": str(DEFAULT_TAIL_GROWTH_PREVIEW_PATH).replace(
                "\\", "/"
            )
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only ranking of authoritative remaining tail "
                "sources by current partial bytes and recent growth."
            ),
            "report_only": True,
            "non_mutating": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a report-only procurement tail source pressure preview."
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
    payload = build_procurement_tail_source_pressure_preview(
        _load_json_or_default(args.tail_growth_preview_path, {})
    )
    save_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
