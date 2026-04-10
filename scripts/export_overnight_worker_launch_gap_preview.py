from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.tasklib import load_json, save_json  # noqa: E402

DEFAULT_QUEUE_PATH = REPO_ROOT / "tasks" / "task_queue.json"
DEFAULT_MONITOR_PATH = REPO_ROOT / "artifacts" / "runtime" / "monitor_snapshot.json"
DEFAULT_ORCHESTRATOR_STATE_PATH = (
    REPO_ROOT / "artifacts" / "status" / "orchestrator_state.json"
)
DEFAULT_IDLE_STATUS_PATH = (
    REPO_ROOT / "artifacts" / "status" / "overnight_idle_status_preview.json"
)
DEFAULT_HEARTBEAT_PATH = REPO_ROOT / "artifacts" / "runtime" / "supervisor.heartbeat.json"
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "overnight_worker_launch_gap_preview.json"
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _load_json_or_default(path: Path, default: Any) -> Any:
    return load_json(path, default) if path.exists() else default


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


def _queue_counts(queue: list[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(str(task.get("status") or "").strip().lower() for task in queue))


def build_overnight_worker_launch_gap_preview(
    queue: list[dict[str, Any]],
    monitor_snapshot: dict[str, Any],
    orchestrator_state: dict[str, Any],
    idle_status_preview: dict[str, Any],
    heartbeat: dict[str, Any] | None,
    *,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    observed_at = observed_at or _utc_now()
    queue_counts = _queue_counts(queue)

    queue_ready_count = _coerce_int(queue_counts.get("ready"))
    queue_pending_count = _coerce_int(queue_counts.get("pending"))
    queue_dispatched_count = _coerce_int(queue_counts.get("dispatched"))
    queue_running_count = _coerce_int(queue_counts.get("running"))
    queue_blocked_count = _coerce_int(queue_counts.get("blocked"))

    monitor_ready_count = _coerce_int(monitor_snapshot.get("ready_count"))
    monitor_pending_count = _coerce_int(monitor_snapshot.get("dependency_ready_pending_count"))
    monitor_dispatch_queue_count = _coerce_int(monitor_snapshot.get("dispatch_queue_count"))
    monitor_review_queue_count = _coerce_int(monitor_snapshot.get("review_queue_count"))
    monitor_active_worker_count = _coerce_int(monitor_snapshot.get("active_worker_count"))
    monitor_blocked_count = _coerce_int(monitor_snapshot.get("blocked_count"))

    idle_queue_summary = idle_status_preview.get("queue_summary") or {}
    idle_in_flight_count = _coerce_int(idle_queue_summary.get("in_flight_count"))

    orchestrator_active_worker_count = len(orchestrator_state.get("active_workers") or [])
    launchable_backlog_count = (
        max(queue_ready_count, monitor_ready_count)
        + max(queue_dispatched_count, monitor_dispatch_queue_count)
        + monitor_review_queue_count
    )
    effective_active_worker_count = max(
        queue_running_count,
        monitor_active_worker_count,
        orchestrator_active_worker_count,
    )
    launch_gap_detected = launchable_backlog_count > 0 and effective_active_worker_count == 0

    heartbeat_last = _parse_timestamp((heartbeat or {}).get("last_heartbeat_at"))
    supervisor_heartbeat_fresh = bool(
        heartbeat_last and (observed_at - heartbeat_last).total_seconds() < 10 * 60
    )

    stale_runtime_signal_present = bool(
        idle_in_flight_count
        and idle_in_flight_count
        != (
            max(queue_ready_count, monitor_ready_count)
            + max(queue_pending_count, monitor_pending_count)
            + effective_active_worker_count
            + max(queue_dispatched_count, monitor_dispatch_queue_count)
            + monitor_review_queue_count
        )
    )

    if launch_gap_detected and not supervisor_heartbeat_fresh:
        launch_gap_state = "launch_gap_attention"
        next_launch_action = (
            "Refresh supervisor state first, then decide whether ready work "
            "needs relaunch."
        )
    elif launch_gap_detected:
        launch_gap_state = "launch_gap_present"
        next_launch_action = (
            "Inspect why ready or dispatched work exists without active workers "
            "before reseeding."
        )
    elif queue_pending_count > 0 or monitor_pending_count > 0:
        launch_gap_state = "non_launchable_pending_only"
        next_launch_action = (
            "Treat remaining pending work as dependency-bound or stale until it "
            "becomes ready."
        )
    elif max(queue_blocked_count, monitor_blocked_count) > 0:
        launch_gap_state = "blocked_or_idle_no_launch_gap"
        next_launch_action = (
            "No worker relaunch is needed; only the blocked task and procurement "
            "tail remain."
        )
    elif effective_active_worker_count > 0:
        launch_gap_state = "workers_active"
        next_launch_action = "Let the active workers continue."
    else:
        launch_gap_state = "idle_no_launch_gap"
        next_launch_action = "The queue is idle with no launch gap to close."

    rows = [
        {
            "lane": "ready_and_dispatch",
            "queue_ready_count": queue_ready_count,
            "monitor_ready_count": monitor_ready_count,
            "queue_dispatched_count": queue_dispatched_count,
            "monitor_dispatch_queue_count": monitor_dispatch_queue_count,
            "note": "Launchable work should appear here before worker pickup.",
        },
        {
            "lane": "workers",
            "queue_running_count": queue_running_count,
            "monitor_active_worker_count": monitor_active_worker_count,
            "orchestrator_active_worker_count": orchestrator_active_worker_count,
            "note": "Active worker views across queue, monitor, and orchestrator.",
        },
        {
            "lane": "dependency_pending",
            "queue_pending_count": queue_pending_count,
            "monitor_pending_count": monitor_pending_count,
            "blocked_count": max(queue_blocked_count, monitor_blocked_count),
            "note": "Pending-only work is not treated as a launch gap unless it becomes ready.",
        },
        {
            "lane": "idle_preview",
            "idle_in_flight_count": idle_in_flight_count,
            "idle_state": idle_status_preview.get("idle_state"),
            "note": "Older report-only in-flight count, useful for spotting stale drift.",
        },
        {
            "lane": "supervisor",
            "heartbeat_last_heartbeat_at": str((heartbeat or {}).get("last_heartbeat_at") or ""),
            "heartbeat_phase": str((heartbeat or {}).get("phase") or ""),
            "supervisor_heartbeat_fresh": supervisor_heartbeat_fresh,
            "note": (
                "Supervisor freshness helps separate launch gaps from stale "
                "control-plane reporting."
            ),
        },
    ]

    return {
        "artifact_id": "overnight_worker_launch_gap_preview",
        "schema_id": "proteosphere-overnight-worker-launch-gap-preview-2026-04-03",
        "status": "report_only",
        "generated_at": observed_at.isoformat(),
        "summary": {
            "launch_gap_state": launch_gap_state,
            "launchable_backlog_count": launchable_backlog_count,
            "launch_gap_detected": launch_gap_detected,
            "launch_gap_count": launchable_backlog_count if launch_gap_detected else 0,
            "queue_file_pending_count": queue_pending_count,
            "monitor_pending_count": monitor_pending_count,
            "queue_file_blocked_count": queue_blocked_count,
            "monitor_blocked_count": monitor_blocked_count,
            "active_worker_count": effective_active_worker_count,
            "supervisor_heartbeat_fresh": supervisor_heartbeat_fresh,
            "stale_runtime_signal_present": stale_runtime_signal_present,
            "row_count": len(rows),
            "non_mutating": True,
            "report_only": True,
        },
        "rows": rows,
        "next_suggested_action": next_launch_action,
        "source_artifacts": {
            "task_queue": str(DEFAULT_QUEUE_PATH).replace("\\", "/"),
            "monitor_snapshot": str(DEFAULT_MONITOR_PATH).replace("\\", "/"),
            "orchestrator_state": str(DEFAULT_ORCHESTRATOR_STATE_PATH).replace("\\", "/"),
            "overnight_idle_status_preview": str(DEFAULT_IDLE_STATUS_PATH).replace("\\", "/"),
            "supervisor_heartbeat": str(DEFAULT_HEARTBEAT_PATH).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only launch-gap surface for overnight execution. "
                "It explains whether launchable work exists without workers, but "
                "it does not dispatch or repair the queue."
            ),
            "report_only": True,
            "non_mutating": True,
            "no_worker_launch": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a report-only overnight worker launch-gap preview."
    )
    parser.add_argument("--queue-path", type=Path, default=DEFAULT_QUEUE_PATH)
    parser.add_argument("--monitor-path", type=Path, default=DEFAULT_MONITOR_PATH)
    parser.add_argument(
        "--orchestrator-state-path",
        type=Path,
        default=DEFAULT_ORCHESTRATOR_STATE_PATH,
    )
    parser.add_argument("--idle-status-path", type=Path, default=DEFAULT_IDLE_STATUS_PATH)
    parser.add_argument("--heartbeat-path", type=Path, default=DEFAULT_HEARTBEAT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    heartbeat = _load_json_or_default(args.heartbeat_path, {})
    if not isinstance(heartbeat, dict) or not heartbeat:
        heartbeat = None
    payload = build_overnight_worker_launch_gap_preview(
        _load_json_or_default(args.queue_path, []),
        _load_json_or_default(args.monitor_path, {}),
        _load_json_or_default(args.orchestrator_state_path, {}),
        _load_json_or_default(args.idle_status_path, {}),
        heartbeat,
    )
    save_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
