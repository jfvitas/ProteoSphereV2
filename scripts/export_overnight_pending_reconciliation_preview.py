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
DEFAULT_WAVE_ADVANCE_PATH = (
    REPO_ROOT / "artifacts" / "status" / "overnight_wave_advance_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "overnight_pending_reconciliation_preview.json"
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


def build_overnight_pending_reconciliation_preview(
    queue: list[dict[str, Any]],
    monitor_snapshot: dict[str, Any],
    orchestrator_state: dict[str, Any],
    idle_status_preview: dict[str, Any],
    wave_advance_preview: dict[str, Any],
    *,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    observed_at = observed_at or _utc_now()
    queue_counts = _queue_counts(queue)
    queue_pending_count = _coerce_int(queue_counts.get("pending"))
    queue_blocked_count = _coerce_int(queue_counts.get("blocked"))
    queue_done_count = _coerce_int(queue_counts.get("done"))

    monitor_pending_count = _coerce_int(monitor_snapshot.get("dependency_ready_pending_count"))
    monitor_ready_count = _coerce_int(monitor_snapshot.get("ready_count"))
    monitor_blocked_count = _coerce_int(monitor_snapshot.get("blocked_count"))
    monitor_done_count = _coerce_int(monitor_snapshot.get("done_count"))
    monitor_active_worker_count = _coerce_int(monitor_snapshot.get("active_worker_count"))

    idle_queue_summary = idle_status_preview.get("queue_summary") or {}
    idle_pending_count = _coerce_int(idle_queue_summary.get("pending_count"))
    idle_blocked_count = _coerce_int(idle_queue_summary.get("blocked_count"))
    idle_generated_at = _parse_timestamp(idle_status_preview.get("generated_at"))
    monitor_observed_at = _parse_timestamp(monitor_snapshot.get("observed_at"))
    idle_preview_generated_before_monitor = bool(
        idle_generated_at and monitor_observed_at and idle_generated_at < monitor_observed_at
    )

    orchestrator_active_worker_count = len(orchestrator_state.get("active_workers") or [])
    orchestrator_completed_count = len(orchestrator_state.get("completed_tasks") or [])
    wave_post_done_count = _coerce_int(
        (wave_advance_preview.get("post_queue_counts") or {}).get("done")
    )
    wave_post_blocked_count = _coerce_int(
        (wave_advance_preview.get("post_queue_counts") or {}).get("blocked")
    )

    stale_preview_detected = idle_preview_generated_before_monitor and (
        idle_pending_count != monitor_pending_count or idle_blocked_count != monitor_blocked_count
    )
    queue_monitor_pending_drift = queue_pending_count != monitor_pending_count

    if stale_preview_detected and queue_pending_count == monitor_pending_count:
        reconciliation_state = "stale_idle_preview_drift_resolved"
        next_action = (
            "Refresh the idle preview and keep using monitor/orchestrator state "
            "as the current truth."
        )
    elif queue_monitor_pending_drift:
        reconciliation_state = "queue_monitor_pending_drift_requires_review"
        next_action = (
            "Inspect queue serialization versus monitor snapshot before reseeding "
            "or dispatching more work."
        )
    elif queue_pending_count == 0 and monitor_pending_count == 0:
        reconciliation_state = "reconciled_no_pending"
        next_action = (
            "Treat the overnight queue as reconciled and idle aside from the "
            "blocked task and procurement tail."
        )
    else:
        reconciliation_state = "aligned_pending_work_present"
        next_action = (
            "Keep the queued pending work visible and avoid duplicate launches "
            "until it becomes ready."
        )

    rows = [
        {
            "signal_source": "task_queue",
            "observed_at": observed_at.isoformat(),
            "pending_count": queue_pending_count,
            "blocked_count": queue_blocked_count,
            "done_count": queue_done_count,
            "active_worker_count": _coerce_int(queue_counts.get("running"))
            + _coerce_int(queue_counts.get("dispatched")),
            "note": "Serialized queue file status counts.",
        },
        {
            "signal_source": "monitor_snapshot",
            "observed_at": str(monitor_snapshot.get("observed_at") or ""),
            "pending_count": monitor_pending_count,
            "blocked_count": monitor_blocked_count,
            "done_count": monitor_done_count,
            "active_worker_count": monitor_active_worker_count,
            "note": "Latest runtime monitor counts.",
        },
        {
            "signal_source": "orchestrator_state",
            "observed_at": str(orchestrator_state.get("last_tick_completed_at") or ""),
            "pending_count": 0,
            "blocked_count": len(orchestrator_state.get("blocked_tasks") or []),
            "done_count": orchestrator_completed_count,
            "active_worker_count": orchestrator_active_worker_count,
            "note": "Active worker and completed-task view from orchestrator state.",
        },
        {
            "signal_source": "overnight_idle_status_preview",
            "observed_at": str(idle_status_preview.get("generated_at") or ""),
            "pending_count": idle_pending_count,
            "blocked_count": idle_blocked_count,
            "done_count": None,
            "active_worker_count": _coerce_int(idle_queue_summary.get("active_worker_count")),
            "note": "Current report-only idle preview snapshot.",
        },
        {
            "signal_source": "overnight_wave_advance_preview",
            "observed_at": str(
                ((wave_advance_preview.get("monitor_summary") or {}).get("snapshot") or {}).get(
                    "observed_at"
                )
                or ""
            ),
            "pending_count": _coerce_int(
                ((wave_advance_preview.get("monitor_summary") or {}).get("snapshot") or {}).get(
                    "dependency_ready_pending_count"
                )
            ),
            "blocked_count": wave_post_blocked_count,
            "done_count": wave_post_done_count,
            "active_worker_count": _coerce_int(wave_advance_preview.get("active_worker_count")),
            "note": "Post-wave queue snapshot captured by the safe sequential advance helper.",
        },
    ]

    return {
        "artifact_id": "overnight_pending_reconciliation_preview",
        "schema_id": "proteosphere-overnight-pending-reconciliation-preview-2026-04-03",
        "status": "report_only",
        "generated_at": observed_at.isoformat(),
        "summary": {
            "reconciliation_state": reconciliation_state,
            "queue_file_pending_count": queue_pending_count,
            "monitor_pending_count": monitor_pending_count,
            "idle_preview_pending_count": idle_pending_count,
            "queue_file_blocked_count": queue_blocked_count,
            "monitor_blocked_count": monitor_blocked_count,
            "monitor_ready_count": monitor_ready_count,
            "monitor_active_worker_count": monitor_active_worker_count,
            "orchestrator_active_worker_count": orchestrator_active_worker_count,
            "idle_preview_generated_before_monitor": idle_preview_generated_before_monitor,
            "stale_preview_detected": stale_preview_detected,
            "queue_monitor_pending_drift": queue_monitor_pending_drift,
            "row_count": len(rows),
            "non_mutating": True,
            "report_only": True,
        },
        "rows": rows,
        "next_suggested_action": next_action,
        "source_artifacts": {
            "task_queue": str(DEFAULT_QUEUE_PATH).replace("\\", "/"),
            "monitor_snapshot": str(DEFAULT_MONITOR_PATH).replace("\\", "/"),
            "orchestrator_state": str(DEFAULT_ORCHESTRATOR_STATE_PATH).replace("\\", "/"),
            "overnight_idle_status_preview": str(DEFAULT_IDLE_STATUS_PATH).replace("\\", "/"),
            "overnight_wave_advance_preview": str(DEFAULT_WAVE_ADVANCE_PATH).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only reconciliation surface for overnight queue signals. "
                "It explains drift across serialized queue, monitor, orchestrator, "
                "and idle-preview artifacts "
                "without dispatching work or changing queue state."
            ),
            "report_only": True,
            "non_mutating": True,
            "no_dispatch_or_repair": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a report-only overnight pending reconciliation preview."
    )
    parser.add_argument("--queue-path", type=Path, default=DEFAULT_QUEUE_PATH)
    parser.add_argument("--monitor-path", type=Path, default=DEFAULT_MONITOR_PATH)
    parser.add_argument(
        "--orchestrator-state-path",
        type=Path,
        default=DEFAULT_ORCHESTRATOR_STATE_PATH,
    )
    parser.add_argument("--idle-status-path", type=Path, default=DEFAULT_IDLE_STATUS_PATH)
    parser.add_argument("--wave-advance-path", type=Path, default=DEFAULT_WAVE_ADVANCE_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_overnight_pending_reconciliation_preview(
        _load_json_or_default(args.queue_path, []),
        _load_json_or_default(args.monitor_path, {}),
        _load_json_or_default(args.orchestrator_state_path, {}),
        _load_json_or_default(args.idle_status_path, {}),
        _load_json_or_default(args.wave_advance_path, {}),
    )
    save_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
