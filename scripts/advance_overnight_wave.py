from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.auto_task_generator import replenish_queue
from scripts.monitor import build_monitor_snapshot, evaluate_alerts
from scripts.orchestrator import tick as orchestrator_tick
from scripts.task_catalog import build_initial_queue
from scripts.tasklib import load_json, task_counts

QUEUE_PATH = Path("tasks/task_queue.json")
STATE_PATH = Path("artifacts/status/orchestrator_state.json")
MONITOR_SNAPSHOT_PATH = Path("artifacts/runtime/monitor_snapshot.json")
DEFAULT_LIMITS = {
    "coding": 10,
    "analysis": 3,
    "integration": 3,
    "gpu": 1,
}


def _catalog_task_ids() -> set[str]:
    return {task["id"] for task in build_initial_queue()}


def _catalog_exhausted(queue: list[dict[str, Any]]) -> bool:
    queue_ids = {
        task_id
        for task in queue
        if (task_id := str(task.get("id") or "").strip())
    }
    catalog_ids = _catalog_task_ids()
    return catalog_ids.issubset(queue_ids)


def _load_queue() -> list[dict[str, Any]]:
    queue = load_json(QUEUE_PATH, [])
    return queue if isinstance(queue, list) else []


def _load_state() -> dict[str, Any]:
    state = load_json(STATE_PATH, {})
    return state if isinstance(state, dict) else {}


def advance_overnight_wave(
    *,
    threshold: int = 12,
    batch_size: int = 25,
    run_monitor: bool = False,
    limits: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Advance the overnight queue in a strictly sequential order."""

    effective_limits = dict(DEFAULT_LIMITS)
    if limits:
        effective_limits.update(limits)

    pre_queue = _load_queue()
    pre_state = _load_state()
    pre_queue_counts = task_counts(pre_queue)
    pre_active_worker_count = len(pre_state.get("active_workers", []))

    with contextlib.redirect_stdout(io.StringIO()):
        added_task_count = replenish_queue(threshold=threshold, batch_size=batch_size)
    with contextlib.redirect_stdout(io.StringIO()):
        orchestrator_tick(effective_limits)

    post_queue = _load_queue()
    post_state = _load_state()
    post_queue_counts = task_counts(post_queue)
    post_active_worker_count = len(post_state.get("active_workers", []))
    catalog_exhausted = _catalog_exhausted(post_queue)

    report: dict[str, Any] = {
        "status": "ok",
        "execution_order": ["auto_task_generator", "orchestrator"],
        "threshold": threshold,
        "batch_size": batch_size,
        "limits": effective_limits,
        "pre_queue_total": len(pre_queue),
        "post_queue_total": len(post_queue),
        "pre_queue_counts": pre_queue_counts,
        "post_queue_counts": post_queue_counts,
        "pre_active_worker_count": pre_active_worker_count,
        "post_active_worker_count": post_active_worker_count,
        "added_task_count": added_task_count,
        "dispatched_count": int(post_queue_counts.get("dispatched", 0)),
        "running_count": int(post_queue_counts.get("running", 0)),
        "active_worker_count": post_active_worker_count,
        "catalog_size": len(build_initial_queue()),
        "catalog_exhausted": catalog_exhausted,
    }

    if run_monitor:
        previous_snapshot = load_json(MONITOR_SNAPSHOT_PATH, {})
        if not isinstance(previous_snapshot, dict):
            previous_snapshot = {}
        observed_at = datetime.now(UTC)
        monitor_snapshot = build_monitor_snapshot(
            post_queue,
            post_state,
            observed_at=observed_at,
        )
        monitor_alerts = evaluate_alerts(
            monitor_snapshot,
            previous_snapshot or None,
            now=observed_at,
        )
        report["execution_order"].append("monitor")
        report["monitor_summary"] = {
            "snapshot": monitor_snapshot,
            "alerts": monitor_alerts,
        }
    else:
        report["monitor_summary"] = {
            "status": "skipped",
            "alerts": [],
        }

    return report


def _format_report(report: dict[str, Any]) -> str:
    lines = [
        "Sequential overnight wave advanced.",
        f"Pre queue counts: {report['pre_queue_counts']}",
        f"Post queue counts: {report['post_queue_counts']}",
        f"Added tasks: {report['added_task_count']}",
        f"Dispatched count: {report['dispatched_count']}",
        f"Active worker count: {report['active_worker_count']}",
        f"Catalog exhausted: {report['catalog_exhausted']}",
        f"Execution order: {', '.join(report['execution_order'])}",
    ]
    monitor_summary = report.get("monitor_summary") or {}
    if monitor_summary.get("status") == "skipped":
        lines.append("Monitor: skipped")
    else:
        alerts = monitor_summary.get("alerts", [])
        lines.append(f"Monitor alerts: {alerts}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Advance the overnight queue sequentially.")
    parser.add_argument("--threshold", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--run-monitor", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--coding-limit", type=int, default=DEFAULT_LIMITS["coding"])
    parser.add_argument("--analysis-limit", type=int, default=DEFAULT_LIMITS["analysis"])
    parser.add_argument("--integration-limit", type=int, default=DEFAULT_LIMITS["integration"])
    parser.add_argument("--gpu-limit", type=int, default=DEFAULT_LIMITS["gpu"])
    args = parser.parse_args(argv)

    limits = {
        "coding": args.coding_limit,
        "analysis": args.analysis_limit,
        "integration": args.integration_limit,
        "gpu": args.gpu_limit,
    }
    report = advance_overnight_wave(
        threshold=args.threshold,
        batch_size=args.batch_size,
        run_monitor=args.run_monitor,
        limits=limits,
    )
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(_format_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
