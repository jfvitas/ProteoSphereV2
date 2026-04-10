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

DEFAULT_PROCUREMENT_STATUS_BOARD_PATH = (
    REPO_ROOT / "artifacts" / "status" / "procurement_status_board.json"
)
DEFAULT_PROCUREMENT_SUPERVISOR_STATE_PATH = (
    REPO_ROOT / "artifacts" / "runtime" / "procurement_supervisor_state.json"
)
DEFAULT_HEARTBEAT_PATH = REPO_ROOT / "artifacts" / "runtime" / "supervisor.heartbeat.json"
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "procurement_supervisor_freshness_preview.json"
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


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _age_seconds(observed_at: datetime, value: datetime | None) -> int | None:
    if value is None:
        return None
    return max(int((observed_at - value).total_seconds()), 0)


def build_procurement_supervisor_freshness_preview(
    board: dict[str, Any],
    supervisor_state: dict[str, Any],
    heartbeat: dict[str, Any],
    *,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    observed_at = observed_at or _utc_now()
    board = board if isinstance(board, dict) else {}
    supervisor_state = supervisor_state if isinstance(supervisor_state, dict) else {}
    heartbeat = heartbeat if isinstance(heartbeat, dict) else {}

    board_supervisor = (
        board.get("procurement_supervisor")
        if isinstance(board.get("procurement_supervisor"), dict)
        else {}
    )
    board_generated_at = _parse_timestamp(
        board_supervisor.get("generated_at") or board.get("generated_at")
    )
    supervisor_generated_at = _parse_timestamp(supervisor_state.get("generated_at"))
    heartbeat_last = _parse_timestamp(heartbeat.get("last_heartbeat_at"))

    board_age_seconds = _age_seconds(observed_at, board_generated_at)
    supervisor_state_age_seconds = _age_seconds(observed_at, supervisor_generated_at)
    heartbeat_age_seconds = _age_seconds(observed_at, heartbeat_last)

    board_active_count = _coerce_int(board_supervisor.get("active_observed_download_count"))
    board_observed_active_source = str(board_supervisor.get("observed_active_source") or "")
    supervisor_state_status = str(supervisor_state.get("status") or "missing")
    supervisor_state_pending_count = len(supervisor_state.get("pending") or [])
    supervisor_state_observed_active_count = len(
        _normalize_rows(supervisor_state.get("observed_active"))
    )
    supervisor_state_completed_count = len(_normalize_rows(supervisor_state.get("completed")))
    supervisor_state_failed_count = len(_normalize_rows(supervisor_state.get("failed")))

    board_recent = board_age_seconds is not None and board_age_seconds <= 12 * 60 * 60
    supervisor_state_legacy_stale = (
        supervisor_state_status == "stale"
        and supervisor_state_age_seconds is not None
        and supervisor_state_age_seconds > 12 * 60 * 60
    )
    supervisor_heartbeat_fresh = (
        heartbeat_age_seconds is not None and heartbeat_age_seconds <= 10 * 60
    )
    stale_state_superseded_by_board = bool(
        supervisor_state_legacy_stale and supervisor_heartbeat_fresh and board_recent
    )

    if stale_state_superseded_by_board and board_active_count > 0:
        freshness_state = "legacy_stale_state_superseded"
        next_action = (
            "Treat the procurement board and fresh supervisor heartbeat as authoritative "
            "for the live tail, and do not interpret the legacy supervisor-state file as "
            "an active blocker."
        )
    elif supervisor_state_status in {"running", "planning"} and not supervisor_state_legacy_stale:
        freshness_state = "fresh_supervisor_state_available"
        next_action = (
            "Use the live procurement supervisor state together with the board while "
            "continuing to watch the tail downloads."
        )
    elif supervisor_state_status == "stale":
        freshness_state = "stale_supervisor_state_attention"
        next_action = (
            "Refresh procurement supervision before trusting the stale state file as "
            "a current operational signal."
        )
    else:
        freshness_state = "supervisor_state_unavailable"
        next_action = (
            "Use the procurement board and heartbeat as the current control-plane truth "
            "until a new supervisor-state artifact is available."
        )

    rows = [
        {
            "signal_source": "procurement_status_board",
            "status": str(board.get("status") or ""),
            "generated_at": str(board.get("generated_at") or ""),
            "age_seconds": board_age_seconds,
            "procurement_supervisor_status": str(board_supervisor.get("status") or ""),
            "active_observed_download_count": board_active_count,
            "observed_active_source": board_observed_active_source,
            "note": "Authoritative procurement board view used by the operator surfaces.",
        },
        {
            "signal_source": "procurement_supervisor_state",
            "status": supervisor_state_status,
            "generated_at": str(supervisor_state.get("generated_at") or ""),
            "age_seconds": supervisor_state_age_seconds,
            "pending_count": supervisor_state_pending_count,
            "observed_active_count": supervisor_state_observed_active_count,
            "completed_count": supervisor_state_completed_count,
            "failed_count": supervisor_state_failed_count,
            "note": "Legacy persisted procurement state that may lag behind the board.",
        },
        {
            "signal_source": "supervisor_heartbeat",
            "status": "fresh" if supervisor_heartbeat_fresh else "stale_or_missing",
            "generated_at": str(heartbeat.get("last_heartbeat_at") or ""),
            "age_seconds": heartbeat_age_seconds,
            "phase": str(heartbeat.get("phase") or ""),
            "supervisor_pid": heartbeat.get("supervisor_pid"),
            "note": "Fresh heartbeat indicates the main supervisor loop is still active.",
        },
    ]

    return {
        "artifact_id": "procurement_supervisor_freshness_preview",
        "schema_id": "proteosphere-procurement-supervisor-freshness-preview-2026-04-03",
        "status": "report_only",
        "generated_at": observed_at.isoformat(),
        "summary": {
            "freshness_state": freshness_state,
            "board_active_observed_download_count": board_active_count,
            "board_observed_active_source": board_observed_active_source,
            "board_recent": board_recent,
            "board_age_seconds": board_age_seconds,
            "supervisor_state_status": supervisor_state_status,
            "supervisor_state_age_seconds": supervisor_state_age_seconds,
            "supervisor_state_pending_count": supervisor_state_pending_count,
            "supervisor_state_observed_active_count": supervisor_state_observed_active_count,
            "supervisor_state_completed_count": supervisor_state_completed_count,
            "supervisor_heartbeat_fresh": supervisor_heartbeat_fresh,
            "heartbeat_age_seconds": heartbeat_age_seconds,
            "stale_state_superseded_by_board": stale_state_superseded_by_board,
            "row_count": len(rows),
            "non_mutating": True,
            "report_only": True,
        },
        "rows": rows,
        "next_suggested_action": next_action,
        "source_artifacts": {
            "procurement_status_board": str(DEFAULT_PROCUREMENT_STATUS_BOARD_PATH).replace(
                "\\", "/"
            ),
            "procurement_supervisor_state": str(
                DEFAULT_PROCUREMENT_SUPERVISOR_STATE_PATH
            ).replace("\\", "/"),
            "supervisor_heartbeat": str(DEFAULT_HEARTBEAT_PATH).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only freshness surface for procurement control-plane "
                "signals. It explains whether the persisted procurement supervisor state "
                "is fresh, stale, or safely superseded by the live board and heartbeat."
            ),
            "report_only": True,
            "non_mutating": True,
            "no_procurement_restart": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a report-only procurement supervisor freshness preview."
    )
    parser.add_argument(
        "--procurement-status-board-path",
        type=Path,
        default=DEFAULT_PROCUREMENT_STATUS_BOARD_PATH,
    )
    parser.add_argument(
        "--procurement-supervisor-state-path",
        type=Path,
        default=DEFAULT_PROCUREMENT_SUPERVISOR_STATE_PATH,
    )
    parser.add_argument("--heartbeat-path", type=Path, default=DEFAULT_HEARTBEAT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_procurement_supervisor_freshness_preview(
        _load_json_or_default(args.procurement_status_board_path, {}),
        _load_json_or_default(args.procurement_supervisor_state_path, {}),
        _load_json_or_default(args.heartbeat_path, {}),
    )
    save_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
