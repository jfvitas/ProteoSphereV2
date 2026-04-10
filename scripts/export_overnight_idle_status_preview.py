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

DEFAULT_QUEUE_PATH = REPO_ROOT / "tasks" / "task_queue.json"
DEFAULT_MONITOR_PATH = REPO_ROOT / "artifacts" / "runtime" / "monitor_snapshot.json"
DEFAULT_PROCUREMENT_BOARD_PATH = (
    REPO_ROOT / "artifacts" / "status" / "procurement_status_board.json"
)
DEFAULT_SUPERVISOR_STATE_PATH = (
    REPO_ROOT / "artifacts" / "runtime" / "procurement_supervisor_state.json"
)
DEFAULT_HEARTBEAT_PATH = REPO_ROOT / "artifacts" / "runtime" / "supervisor.heartbeat.json"
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "overnight_idle_status_preview.json"


def _utc_now() -> datetime:
    return datetime.now(UTC)


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


def _coerce_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _queue_counts(queue: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for task in queue:
        status = str(task.get("status") or "").strip().lower() or "unknown"
        counts[status] = counts.get(status, 0) + 1
    return counts


def _pick_first_int(payload: dict[str, Any], paths: list[list[str]]) -> int:
    for path in paths:
        current: Any = payload
        found = True
        for key in path:
            if not isinstance(current, dict) or key not in current:
                found = False
                break
            current = current[key]
        if found:
            return _coerce_int(current)
    return 0


def _listify(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    rows = []
    for item in value:
        text = str(item or "").strip()
        if text:
            rows.append(text)
    return rows


def _summarize_tail_awareness(
    procurement_board: dict[str, Any], supervisor_state: dict[str, Any]
) -> dict[str, Any]:
    remaining_transfer = (
        procurement_board.get("remaining_transfer")
        if isinstance(procurement_board.get("remaining_transfer"), dict)
        else {}
    )
    observed_active = _listify(supervisor_state.get("observed_active"))
    pending = _listify(supervisor_state.get("pending"))
    authoritative_active_download_count = _pick_first_int(
        procurement_board,
        [
            ["summary", "active_download_count"],
            ["remaining_transfer", "active_file_count"],
        ],
    )
    active_download_count = authoritative_active_download_count or len(observed_active)
    remaining_source_count = max(
        _pick_first_int(
            procurement_board,
            [
                ["summary", "remaining_source_count"],
                ["remaining_transfer", "remaining_source_count"],
            ],
        ),
        0,
    )
    total_gap_files = max(
        _pick_first_int(
            procurement_board,
            [
                ["summary", "total_gap_files"],
                ["remaining_transfer", "total_gap_files"],
            ],
        ),
        len(_listify(remaining_transfer.get("top_gap_files"))),
    )
    tail_status = str(procurement_board.get("status") or "unknown").strip().lower() or "unknown"
    if active_download_count > 0:
        tail_state = "active"
    elif tail_status in {"blocked", "attention"}:
        tail_state = "blocked"
    elif remaining_source_count == 0 and total_gap_files == 0:
        tail_state = "drained"
    else:
        tail_state = "observed"
    return {
        "tail_state": tail_state,
        "status": tail_status,
        "active_download_count": active_download_count,
        "authoritative_active_download_count": authoritative_active_download_count,
        "raw_observed_active_count": len(observed_active),
        "remaining_source_count": remaining_source_count,
        "total_gap_files": total_gap_files,
        "observed_active_sources": observed_active,
        "observed_pending_sources": pending,
        "top_gap_files": _listify(remaining_transfer.get("top_gap_files")),
    }


def _extract_queue_state(
    queue: list[dict[str, Any]], monitor_snapshot: dict[str, Any]
) -> dict[str, int]:
    counts = _queue_counts(queue)
    snapshot_counts = monitor_snapshot.get("queue_counts")
    if isinstance(snapshot_counts, dict):
        for key, value in snapshot_counts.items():
            counts[str(key).strip().lower()] = _coerce_int(value)
    counts["ready"] = max(_coerce_int(monitor_snapshot.get("ready_count")), counts.get("ready", 0))
    counts["pending"] = max(
        _coerce_int(monitor_snapshot.get("dependency_ready_pending_count")),
        counts.get("pending", 0),
    )
    counts["blocked"] = max(
        _coerce_int(monitor_snapshot.get("blocked_count")),
        counts.get("blocked", 0),
    )
    counts["done"] = max(_coerce_int(monitor_snapshot.get("done_count")), counts.get("done", 0))
    counts["active_workers"] = max(
        _coerce_int(monitor_snapshot.get("active_worker_count")),
        counts.get("running", 0) + counts.get("dispatched", 0),
    )
    counts["dispatch_queue"] = max(
        _coerce_int(monitor_snapshot.get("dispatch_queue_count")),
        counts.get("dispatched", 0),
    )
    counts["review_queue"] = max(
        _coerce_int(monitor_snapshot.get("review_queue_count")),
        counts.get("reviewed", 0),
    )
    return counts


def _stale_heartbeat(
    heartbeat: dict[str, Any] | None,
    observed_at: datetime,
    *,
    threshold_minutes: int = 30,
) -> bool:
    if not heartbeat:
        return False
    last_heartbeat_at = _parse_timestamp(heartbeat.get("last_heartbeat_at"))
    if last_heartbeat_at is None:
        return False
    return (observed_at - last_heartbeat_at).total_seconds() >= threshold_minutes * 60


def build_overnight_idle_status_preview(
    queue: list[dict[str, Any]],
    monitor_snapshot: dict[str, Any],
    procurement_board: dict[str, Any],
    supervisor_state: dict[str, Any],
    heartbeat: dict[str, Any] | None = None,
    *,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    observed_at = observed_at or _utc_now()
    queue_counts = _extract_queue_state(queue, monitor_snapshot)
    tail_awareness = _summarize_tail_awareness(procurement_board, supervisor_state)

    ready_count = _coerce_int(queue_counts.get("ready"))
    pending_count = _coerce_int(queue_counts.get("pending"))
    blocked_count = _coerce_int(queue_counts.get("blocked"))
    active_workers = _coerce_int(queue_counts.get("active_workers"))
    dispatch_queue = _coerce_int(queue_counts.get("dispatch_queue"))
    review_queue = _coerce_int(queue_counts.get("review_queue"))
    in_flight = ready_count + pending_count + active_workers + dispatch_queue + review_queue

    reasons: list[str] = []
    next_action = "Keep monitoring the overnight supervisor and wait for the next signal."
    status = "healthy_queue_drained"

    if _stale_heartbeat(heartbeat, observed_at):
        status = "stalled_or_attention_needed"
        reasons.append("Supervisor heartbeat is stale relative to the observation time.")
        next_action = "Refresh the supervisor and verify the queue state before seeding more work."
    elif ready_count > 0 or active_workers > 0 or dispatch_queue > 0 or review_queue > 0:
        status = "healthy_active"
        if ready_count > 0:
            reasons.append(f"Queue still has {ready_count} ready task(s).")
        if active_workers > 0:
            reasons.append(f"{active_workers} active worker(s) are still in flight.")
        if dispatch_queue > 0:
            reasons.append(f"Dispatch queue still holds {dispatch_queue} task(s).")
        if review_queue > 0:
            reasons.append(f"Review queue still holds {review_queue} task(s).")
        next_action = "Let the active queue continue and avoid duplicate launches."
    elif blocked_count > 0:
        status = "blocked_waiting"
        reasons.append(f"Queue has {blocked_count} blocked task(s) and no active work is running.")
        next_action = "Resolve the blocker or procurement dependency before reseeding the queue."
    elif tail_awareness["active_download_count"] > 0:
        status = "healthy_queue_drained"
        reasons.append(
            "The task queue is drained, but the procurement tail still has active downloads."
        )
        reasons.append(
            f"{tail_awareness['active_download_count']} active download(s) remain "
            "under procurement watch."
        )
        next_action = "Keep the tail downloads running and wait for the next replenishment wave."
    else:
        status = "healthy_queue_drained"
        reasons.append("No ready, pending, active, or dispatched tasks remain in the queue.")
        if tail_awareness["tail_state"] == "drained":
            reasons.append("Procurement tail is also drained or fully reconciled.")
        else:
            reasons.append("Procurement tail is quiet enough to treat the overnight loop as idle.")
        next_action = "Queue a fresh wave only if you intend to continue development immediately."

    if not reasons:
        reasons.append(
            "Queue and procurement signals are consistent with an idle but healthy overnight state."
        )

    if status == "healthy_queue_drained" and tail_awareness["tail_state"] == "active":
        reasons.append(
            "Queue drainage is explicitly separate from the still-active procurement tail."
        )

    return {
        "artifact_id": "overnight_idle_status_preview",
        "schema_id": "proteosphere-overnight-idle-status-preview-2026-04-03",
        "status": "report_only",
        "generated_at": observed_at.isoformat(),
        "idle_state": status,
        "queue_summary": {
            "ready_count": ready_count,
            "pending_count": pending_count,
            "blocked_count": blocked_count,
            "active_worker_count": active_workers,
            "dispatch_queue_count": dispatch_queue,
            "review_queue_count": review_queue,
            "in_flight_count": in_flight,
            "queue_is_drained": in_flight == 0,
        },
        "procurement_tail_awareness": tail_awareness,
        "reason_summary": reasons,
        "next_suggested_action": next_action,
        "signals": {
            "monitor_status": str(monitor_snapshot.get("status") or "unknown").strip() or "unknown",
            "monitor_observed_at": str(monitor_snapshot.get("observed_at") or "").strip(),
            "heartbeat_last_heartbeat_at": str(
                (heartbeat or {}).get("last_heartbeat_at") or ""
            ).strip(),
            "heartbeat_phase": str((heartbeat or {}).get("phase") or "").strip(),
            "procurement_board_status": (
                str(procurement_board.get("status") or "unknown").strip() or "unknown"
            ),
            "supervisor_state_status": (
                str(supervisor_state.get("status") or "unknown").strip() or "unknown"
            ),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only overnight idle/drained preview. It interprets queue, "
                "monitor, and procurement-tail signals, but it does not launch work or "
                "override the remaining tail downloads."
            ),
            "report_only": True,
            "procurement_tail_awareness_explicit": True,
            "no_launch_or_dispatch": True,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a report-only overnight idle/drained status preview."
    )
    parser.add_argument("--queue-path", type=Path, default=DEFAULT_QUEUE_PATH)
    parser.add_argument("--monitor-path", type=Path, default=DEFAULT_MONITOR_PATH)
    parser.add_argument(
        "--procurement-board-path",
        type=Path,
        default=DEFAULT_PROCUREMENT_BOARD_PATH,
    )
    parser.add_argument("--supervisor-state-path", type=Path, default=DEFAULT_SUPERVISOR_STATE_PATH)
    parser.add_argument("--heartbeat-path", type=Path, default=DEFAULT_HEARTBEAT_PATH)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--observed-at", type=str, default="")
    return parser.parse_args(argv)


def _load_json_or_default(path: Path, default: Any) -> Any:
    return load_json(path, default) if path.exists() else default


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    queue = _load_json_or_default(args.queue_path, [])
    monitor_snapshot = _load_json_or_default(args.monitor_path, {})
    procurement_board = _load_json_or_default(args.procurement_board_path, {})
    supervisor_state = _load_json_or_default(args.supervisor_state_path, {})
    heartbeat = _load_json_or_default(args.heartbeat_path, {})
    if not isinstance(heartbeat, dict) or not heartbeat:
        heartbeat = None
    observed_at = _parse_timestamp(args.observed_at) or _utc_now()
    payload = build_overnight_idle_status_preview(
        queue if isinstance(queue, list) else [],
        monitor_snapshot if isinstance(monitor_snapshot, dict) else {},
        procurement_board if isinstance(procurement_board, dict) else {},
        supervisor_state if isinstance(supervisor_state, dict) else {},
        heartbeat,
        observed_at=observed_at,
    )
    save_json(args.output_json, payload)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
