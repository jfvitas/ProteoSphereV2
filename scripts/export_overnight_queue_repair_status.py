from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.overnight_planning_common import write_json, write_text  # noqa: E402
from scripts.tasklib import load_json, task_counts  # noqa: E402

DEFAULT_QUEUE_PATH = REPO_ROOT / "tasks" / "task_queue.json"
DEFAULT_STATE_PATH = REPO_ROOT / "artifacts" / "status" / "orchestrator_state.json"
DEFAULT_REPAIR_REPORT_PATH = (
    REPO_ROOT / "artifacts" / "status" / "overnight_queue_repair_report.json"
)
DEFAULT_DISPATCH_DIR = REPO_ROOT / "artifacts" / "dispatch"
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "overnight_queue_repair_status.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "overnight_queue_repair_status.md"
DEFAULT_STALE_AFTER_HOURS = 6


def _load_queue(path: Path) -> list[dict[str, Any]]:
    payload = load_json(path, [])
    return payload if isinstance(payload, list) else []


def _load_report(path: Path) -> dict[str, Any]:
    payload = load_json(path, {})
    return payload if isinstance(payload, dict) else {}


def _manifest_path(dispatch_dir: Path, task_id: str) -> Path:
    return dispatch_dir / f"{task_id}.json"


def _current_dispatch_ids(queue: list[dict[str, Any]]) -> list[str]:
    return sorted(
        {
            str(task.get("id") or "").strip()
            for task in queue
            if str(task.get("id") or "").strip()
            and task.get("status") in {"dispatched", "running"}
        }
    )


def _stale_dispatch_ids(
    queue: list[dict[str, Any]],
    dispatch_dir: Path,
    stale_after: timedelta,
    now: datetime,
) -> list[str]:
    queue_lookup = {task["id"]: task for task in queue if str(task.get("id") or "").strip()}
    stale_ids: list[str] = []
    for task_id in _current_dispatch_ids(queue):
        task = queue_lookup.get(task_id)
        if not task:
            continue
        manifest = _manifest_path(dispatch_dir, task_id)
        if not manifest.exists():
            stale_ids.append(task_id)
            continue
        age = now - datetime.fromtimestamp(manifest.stat().st_mtime, tz=UTC)
        if age >= stale_after:
            stale_ids.append(task_id)
    return stale_ids


def _recovery_state(
    repaired_ids: list[str],
    redispatched_ids: list[str],
    current_stale_ids: list[str],
    report_present: bool,
) -> str:
    if not report_present:
        return "report_missing"
    if current_stale_ids:
        return "needs_rerun"
    if repaired_ids and redispatched_ids:
        return "repaired_and_redispatched"
    if repaired_ids:
        return "repaired_and_idle"
    return "report_only"


def build_overnight_queue_repair_status(
    queue: list[dict[str, Any]],
    state: dict[str, Any],
    repair_report: dict[str, Any],
    dispatch_dir: Path,
    *,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    observed_at = observed_at or datetime.now(UTC)
    queue_by_id = {
        str(task.get("id") or "").strip(): task
        for task in queue
        if str(task.get("id") or "").strip()
    }
    queue_counts = task_counts(queue)
    active_dispatch_ids = _current_dispatch_ids(queue)
    stale_after_hours = int(repair_report.get("stale_after_hours") or DEFAULT_STALE_AFTER_HOURS)
    current_stale_ids = _stale_dispatch_ids(
        queue,
        dispatch_dir,
        timedelta(hours=stale_after_hours),
        observed_at,
    )
    missing_manifest_ids = [
        task_id
        for task_id in active_dispatch_ids
        if not _manifest_path(dispatch_dir, task_id).exists()
    ]

    repaired_stale_ids = [
        str(task_id).strip()
        for task_id in repair_report.get("demoted_stale_dispatches") or []
        if str(task_id).strip()
    ]
    deleted_dispatch_manifests = [
        str(task_id).strip()
        for task_id in repair_report.get("deleted_dispatch_manifests") or []
        if str(task_id).strip()
    ]
    redispatched_repaired_ids = [
        task_id
        for task_id in repaired_stale_ids
        if queue_by_id.get(task_id, {}).get("status") in {"dispatched", "running"}
    ]
    idle_repaired_ids = [
        task_id
        for task_id in repaired_stale_ids
        if queue_by_id.get(task_id, {}).get("status") not in {"dispatched", "running"}
    ]

    report_present = bool(repair_report)
    recovery_state = _recovery_state(
        repaired_stale_ids,
        redispatched_repaired_ids,
        current_stale_ids,
        report_present,
    )

    return {
        "artifact_id": "overnight_queue_repair_status",
        "schema_id": "proteosphere-overnight-queue-repair-status-2026-04-03",
        "status": "report_only",
        "generated_at": observed_at.isoformat(),
        "queue_counts": queue_counts,
        "state_summary": {
            "active_worker_count": len(state.get("active_workers", [])),
            "dispatch_queue_count": len(state.get("dispatch_queue", [])),
            "blocked_task_count": len(state.get("blocked_tasks", [])),
            "completed_task_count": len(state.get("completed_tasks", [])),
        },
        "dispatch_counts": {
            "active_dispatch_count": len(active_dispatch_ids),
            "current_stale_dispatch_count": len(current_stale_ids),
            "missing_manifest_count": len(missing_manifest_ids),
        },
        "repair_report_present": report_present,
        "repair_report_repaired_at": repair_report.get("repaired_at"),
        "repair_report_stale_after_hours": stale_after_hours,
        "repaired_stale_dispatch_ids": repaired_stale_ids,
        "deleted_dispatch_manifests": deleted_dispatch_manifests,
        "recovered_and_redispatched_ids": redispatched_repaired_ids,
        "recovered_and_idle_ids": idle_repaired_ids,
        "current_stale_dispatch_ids": current_stale_ids,
        "missing_dispatch_manifest_ids": missing_manifest_ids,
        "recovery_state": recovery_state,
        "summary": {
            "repaired_stale_dispatch_count": len(repaired_stale_ids),
            "recovered_and_redispatched_count": len(redispatched_repaired_ids),
            "recovered_and_idle_count": len(idle_repaired_ids),
            "current_stale_dispatch_count": len(current_stale_ids),
            "missing_dispatch_manifest_count": len(missing_manifest_ids),
            "operator_message": (
                "Stale-dispatch recovery is visible from the repair report; "
                "current queue state remains report-only."
            ),
        },
        "truth_boundary": {
            "summary": (
                "This status artifact only surfaces stale-dispatch recovery. It "
                "does not change queue semantics, dispatch ordering, or manifest "
                "state."
            ),
            "report_only": True,
            "no_queue_semantics_changed": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Overnight Queue Repair Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Recovery state: `{payload['recovery_state']}`",
        f"- Repair report present: `{payload['repair_report_present']}`",
        f"- Repaired stale dispatches: `{payload['summary']['repaired_stale_dispatch_count']}`",
        f"- Recovered and redispatched: `{payload['summary']['recovered_and_redispatched_count']}`",
        f"- Recovered and idle: `{payload['summary']['recovered_and_idle_count']}`",
        (
            "- Current stale dispatch candidates: "
            f"`{payload['summary']['current_stale_dispatch_count']}`"
        ),
        "",
        "## Repaired Stale Dispatches",
        "",
    ]
    if payload["repaired_stale_dispatch_ids"]:
        lines.extend(f"- `{task_id}`" for task_id in payload["repaired_stale_dispatch_ids"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Current Stale Candidates",
            "",
        ]
    )
    if payload["current_stale_dispatch_ids"]:
        lines.extend(f"- `{task_id}`" for task_id in payload["current_stale_dispatch_ids"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Truth Boundary",
            "",
            f"- {payload['truth_boundary']['summary']}",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a report-only overnight queue repair status artifact."
    )
    parser.add_argument("--queue-path", type=Path, default=DEFAULT_QUEUE_PATH)
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--repair-report-path", type=Path, default=DEFAULT_REPAIR_REPORT_PATH)
    parser.add_argument("--dispatch-dir", type=Path, default=DEFAULT_DISPATCH_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument(
        "--observed-at",
        type=str,
        default=None,
        help="Optional ISO timestamp for deterministic reporting.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    queue = _load_queue(args.queue_path)
    state = _load_json_state(args.state_path)
    repair_report = _load_report(args.repair_report_path)
    observed_at = datetime.fromisoformat(args.observed_at) if args.observed_at else None
    payload = build_overnight_queue_repair_status(
        queue,
        state,
        repair_report,
        args.dispatch_dir,
        observed_at=observed_at,
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(json.dumps(payload, indent=2))


def _load_json_state(path: Path) -> dict[str, Any]:
    payload = load_json(
        path,
        {
            "active_workers": [],
            "completed_tasks": [],
            "failed_tasks": [],
            "blocked_tasks": [],
            "review_queue": [],
            "dispatch_queue": [],
            "last_task_generation_ts": None,
        },
    )
    return payload if isinstance(payload, dict) else {}


if __name__ == "__main__":
    main()
