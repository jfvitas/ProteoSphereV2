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

from scripts.overnight_planning_common import (  # noqa: E402
    REPO_ROOT as COMMON_REPO_ROOT,
)
from scripts.overnight_planning_common import (  # noqa: E402
    build_catalog_jobs,
    group_observed_active_jobs,
    load_runtime_state,
    write_json,
    write_text,
)
from scripts.procurement_supervisor import build_task_queue  # noqa: E402

assert REPO_ROOT == COMMON_REPO_ROOT

DEFAULT_RUNTIME_STATE = REPO_ROOT / "artifacts" / "runtime" / "procurement_supervisor_state.json"
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "overnight_queue_backlog_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "overnight_queue_backlog_preview.md"


def _task_map() -> dict[str, dict[str, Any]]:
    return {
        str(task.task_id): dict(task.__dict__)
        for task in build_task_queue()
        if str(task.task_id).strip()
    }


def _pending_runtime_jobs(state: dict[str, Any]) -> list[dict[str, Any]]:
    task_map = _task_map()
    rows: list[dict[str, Any]] = []
    for task_id in state.get("pending") or []:
        task = task_map.get(str(task_id))
        if not task:
            continue
        rows.append(
            {
                "job_id": str(task.get("task_id") or "").strip(),
                "source_kind": "supervisor_pending",
                "job_state": "pending",
                "rank_source": "supervisor_pending",
                "title": str(task.get("description") or "").strip(),
                "category": str(task.get("category") or "").strip(),
                "priority": int(task.get("priority") or 0),
                "command": task.get("command") or [],
                "stdout_log": str(task.get("stdout_log") or "").strip(),
                "stderr_log": str(task.get("stderr_log") or "").strip(),
                "why_now": (
                    "Already queued by the supervisor and should be observed rather "
                    "than duplicated."
                ),
                "health_checkpoint": (
                    "Keep this job in the supervisor state until the active observed "
                    "downloads and the runtime snapshot reconcile."
                ),
            }
        )
    return rows


def build_overnight_queue_backlog_preview(
    runtime_state: dict[str, Any],
) -> dict[str, Any]:
    runtime_status = str(runtime_state.get("status") or "").strip().casefold()
    runtime_active = runtime_state.get("active") or []
    observed_active = runtime_state.get("observed_active") or []
    if runtime_status == "stale" and not runtime_active:
        observed_active = []
    active_rows = group_observed_active_jobs(observed_active)
    pending_rows = (
        []
        if runtime_status == "stale" and not runtime_active
        else _pending_runtime_jobs(runtime_state)
    )
    excluded_ids = {
        str(row.get("job_id") or "").strip()
        for row in active_rows + pending_rows
        if str(row.get("job_id") or "").strip()
    }
    catalog_rows = build_catalog_jobs(limit=22, excluded_ids=excluded_ids)
    rows: list[dict[str, Any]] = []
    for rank, row in enumerate(active_rows + pending_rows + catalog_rows, start=1):
        payload = dict(row)
        payload["rank"] = rank
        payload["task_id"] = payload.get("job_id")
        payload["queue_window"] = (
            "active_now"
            if row["source_kind"] == "observed_active"
            else "supervisor_pending"
            if row["source_kind"] == "supervisor_pending"
            else "overnight_catalog"
        )
        rows.append(payload)
    return {
        "artifact_id": "overnight_queue_backlog_preview",
        "schema_id": "proteosphere-overnight-queue-backlog-preview-2026-04-03",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "job_count": len(rows),
        "active_job_count": len(active_rows),
        "supervisor_pending_job_count": len(pending_rows),
        "catalog_job_count": len(catalog_rows),
        "rows": rows,
        "summary": {
            "pending_task_count": len(pending_rows) + len(catalog_rows),
            "selected_top_count": len(rows),
            "lane_counts": {
                "active_now": len(active_rows),
                "supervisor_pending": len(pending_rows),
                "overnight_catalog": len(catalog_rows),
            },
            "observed_active_source_keys": [row["job_id"] for row in active_rows],
            "supervisor_pending_ids": [row["job_id"] for row in pending_rows],
            "catalog_focus_ids": [row["job_id"] for row in catalog_rows[:8]],
            "queue_state_counts": {
                "active_now": len(active_rows),
                "supervisor_pending": len(pending_rows),
                "overnight_catalog": len(catalog_rows),
            },
        },
        "truth_boundary": {
            "summary": (
                "This backlog is report-only. It ranks the next 12-hour window from "
                "the observed supervisor state and the task catalog, but it does not "
                "launch or duplicate any job."
            ),
            "report_only": True,
            "launch_blocked_for_active_jobs": True,
            "duplicate_launches_forbidden": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Overnight Queue Backlog Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Job count: `{payload['job_count']}`",
        f"- Active jobs: `{payload['active_job_count']}`",
        f"- Supervisor pending jobs: `{payload['supervisor_pending_job_count']}`",
        f"- Catalog jobs: `{payload['catalog_job_count']}`",
        "",
        "## Jobs",
        "",
    ]
    for row in payload["rows"]:
        label = row.get("title") or row["job_id"]
        lines.append(f"- `{row['rank']}` `{row['queue_window']}` `{row['job_id']}` / `{label}`")
        details = []
        if row["source_kind"] == "observed_active":
            details.append(f"pid_count={row['pid_count']}")
        if row["source_kind"] == "catalog":
            details.append(f"priority={row.get('priority')}")
            details.append(f"phase={row.get('phase')}")
        if row["source_kind"] == "supervisor_pending":
            details.append(f"category={row.get('category')}")
        if details:
            lines.append(f"  detail: {', '.join(details)}")
    lines.extend(["", "## Truth Boundary", "", f"- {payload['truth_boundary']['summary']}", ""])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a report-only overnight queue backlog preview."
    )
    parser.add_argument("--runtime-state", type=Path, default=DEFAULT_RUNTIME_STATE)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    runtime_state = (
        load_runtime_state()
        if args.runtime_state == DEFAULT_RUNTIME_STATE
        else json.loads(args.runtime_state.read_text(encoding="utf-8"))
    )
    payload = build_overnight_queue_backlog_preview(runtime_state)
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
