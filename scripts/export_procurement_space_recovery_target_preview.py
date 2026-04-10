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
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_space_recovery_target_preview.json"
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


def build_procurement_space_recovery_target_preview(
    completion_margin_preview: dict[str, Any],
    *,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    observed_at = observed_at or _utc_now()
    completion_margin_preview = (
        completion_margin_preview
        if isinstance(completion_margin_preview, dict)
        else {}
    )
    summary = (
        completion_margin_preview.get("summary")
        if isinstance(completion_margin_preview.get("summary"), dict)
        else {}
    )

    free_bytes = _coerce_int(summary.get("free_bytes"))
    total_remaining_bytes = _coerce_int(summary.get("total_remaining_bytes"))
    projected_free_after_completion = _coerce_int(
        summary.get("projected_free_after_completion_bytes")
    )
    reclaim_to_zero_bytes = max(-projected_free_after_completion, 0)
    reclaim_to_10_gib_buffer_bytes = max(reclaim_to_zero_bytes + 10 * GIB, 0)
    reclaim_to_20_gib_buffer_bytes = max(reclaim_to_zero_bytes + 20 * GIB, 0)

    if reclaim_to_zero_bytes <= 0:
        target_state = "no_recovery_required"
        next_action = (
            "The current free-space margin already covers the remaining "
            "authoritative tail."
        )
    elif reclaim_to_20_gib_buffer_bytes <= 20 * GIB:
        target_state = "moderate_recovery_required"
        next_action = "Recover enough space to cover the exact tail plus a small safety buffer."
    else:
        target_state = "substantial_recovery_required"
        next_action = (
            "Recover a substantial amount of space before assuming the "
            "remaining tail can finish safely."
        )

    return {
        "artifact_id": "procurement_space_recovery_target_preview",
        "schema_id": "proteosphere-procurement-space-recovery-target-preview-2026-04-03",
        "status": "report_only",
        "generated_at": observed_at.isoformat(),
        "summary": {
            "target_state": target_state,
            "free_bytes": free_bytes,
            "free_gib": round(free_bytes / GIB, 3) if free_bytes > 0 else 0.0,
            "total_remaining_bytes": total_remaining_bytes,
            "total_remaining_gib": (
                round(total_remaining_bytes / GIB, 3) if total_remaining_bytes > 0 else 0.0
            ),
            "reclaim_to_zero_bytes": reclaim_to_zero_bytes,
            "reclaim_to_zero_gib": round(reclaim_to_zero_bytes / GIB, 3),
            "reclaim_to_10_gib_buffer_bytes": reclaim_to_10_gib_buffer_bytes,
            "reclaim_to_10_gib_buffer_gib": round(
                reclaim_to_10_gib_buffer_bytes / GIB, 3
            ),
            "reclaim_to_20_gib_buffer_bytes": reclaim_to_20_gib_buffer_bytes,
            "reclaim_to_20_gib_buffer_gib": round(
                reclaim_to_20_gib_buffer_bytes / GIB, 3
            ),
            "non_mutating": True,
            "report_only": True,
        },
        "next_suggested_action": next_action,
        "source_artifacts": {
            "procurement_tail_completion_margin_preview": str(
                DEFAULT_COMPLETION_MARGIN_PREVIEW_PATH
            ).replace("\\", "/")
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only recovery target derived from the exact "
                "tail completion margin. It does not move or delete files."
            ),
            "report_only": True,
            "non_mutating": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a report-only procurement space recovery target preview."
    )
    parser.add_argument(
        "--completion-margin-preview-path",
        type=Path,
        default=DEFAULT_COMPLETION_MARGIN_PREVIEW_PATH,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_procurement_space_recovery_target_preview(
        _load_json_or_default(args.completion_margin_preview_path, {})
    )
    save_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
