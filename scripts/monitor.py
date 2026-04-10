from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from collections.abc import Callable
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.tasklib import dependencies_complete, load_json, save_json, task_counts
from scripts.build_operational_readiness_snapshot import build_operational_readiness_snapshot
from scripts.summarize_soak_ledger import summarize_entries

QUEUE_PATH = Path("tasks/task_queue.json")
STATE_PATH = Path("artifacts/status/orchestrator_state.json")
SNAPSHOT_PATH = Path("artifacts/runtime/monitor_snapshot.json")
SOAK_LEDGER_PATH = Path("artifacts/runtime/soak_ledger.jsonl")
HEARTBEAT_PATH = Path("artifacts/runtime/supervisor.heartbeat.json")
SUPERVISOR_STATE_PATH = Path("artifacts/runtime/procurement_supervisor_state.json")
PROCUREMENT_STATUS_BOARD_PATH = Path("artifacts/status/procurement_status_board.json")
BROAD_MIRROR_PROGRESS_PATH = Path("artifacts/status/broad_mirror_progress.json")
REMAINING_TRANSFER_STATUS_PATH = Path(
    "artifacts/status/broad_mirror_remaining_transfer_status.json"
)
PACKET_DEFICIT_PATH = Path("artifacts/status/packet_deficit_dashboard.json")
DEFAULT_STAGNATION_SECONDS = 900
DEFAULT_CYCLE_START_GRACE_SECONDS = 90
OBSERVED_DOWNLOAD_SCRIPTS = (
    "download_all_sources.py",
    "download_raw_data.py",
    "download_resolver_safe_urls.py",
)


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


def dependency_ready_pending_count(queue: list[dict[str, Any]]) -> int:
    return sum(
        1
        for task in queue
        if task.get("status") == "pending" and dependencies_complete(task, queue)
    )


def build_monitor_snapshot(
    queue: list[dict[str, Any]],
    state: dict[str, Any],
    *,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    counts = task_counts(queue)
    active_workers = list(state.get("active_workers", []))
    return {
        "observed_at": (observed_at or _utc_now()).isoformat(),
        "queue_counts": counts,
        "ready_count": counts.get("ready", 0),
        "dependency_ready_pending_count": dependency_ready_pending_count(queue),
        "active_worker_count": len(active_workers),
        "active_worker_ids": [
            str(worker.get("task_id", "")).strip()
            for worker in active_workers
            if str(worker.get("task_id", "")).strip()
        ],
        "dispatch_queue_count": len(state.get("dispatch_queue", [])),
        "review_queue_count": len(state.get("review_queue", [])),
        "blocked_count": counts.get("blocked", 0),
        "done_count": counts.get("done", 0) + counts.get("reviewed", 0),
        "last_tick_completed_at": state.get("last_tick_completed_at"),
    }


def evaluate_alerts(
    snapshot: dict[str, Any],
    previous_snapshot: dict[str, Any] | None,
    *,
    heartbeat: dict[str, Any] | None = None,
    now: datetime | None = None,
    stagnation_seconds: int = DEFAULT_STAGNATION_SECONDS,
) -> list[str]:
    alerts: list[str] = []
    queue_counts = dict(snapshot.get("queue_counts", {}))
    pending_count = int(queue_counts.get("pending", 0))
    dependency_ready_count = int(snapshot.get("dependency_ready_pending_count", 0))
    active_worker_count = int(snapshot.get("active_worker_count", 0))
    dispatch_queue_count = int(snapshot.get("dispatch_queue_count", 0))
    blocked_count = int(snapshot.get("blocked_count", 0))

    cycle_start_grace_active = False
    if heartbeat:
        heartbeat_phase = str(heartbeat.get("phase") or "").strip().lower()
        heartbeat_at = _parse_timestamp(heartbeat.get("last_heartbeat_at"))
        elapsed_since_heartbeat = None
        if heartbeat_at is not None:
            elapsed_since_heartbeat = ((now or _utc_now()) - heartbeat_at).total_seconds()
        if (
            heartbeat_phase == "cycle_start"
            and elapsed_since_heartbeat is not None
            and elapsed_since_heartbeat <= DEFAULT_CYCLE_START_GRACE_SECONDS
        ):
            cycle_start_grace_active = True

    if (
        dependency_ready_count > 0
        and active_worker_count == 0
        and dispatch_queue_count == 0
        and not cycle_start_grace_active
    ):
        alerts.append(
            "queue starvation: "
            f"{dependency_ready_count} dependency-ready pending task(s) but no active workers "
            "or queued dispatches"
        )

    if previous_snapshot:
        previous_blocked_count = int(previous_snapshot.get("blocked_count", 0))
        if blocked_count > previous_blocked_count:
            blocked_delta = blocked_count - previous_blocked_count
            alerts.append(
                "blocked backlog grew: "
                f"{previous_blocked_count} -> {blocked_count} (+{blocked_delta})"
            )

        elapsed_seconds: float | None = None
        previous_observed_at = _parse_timestamp(previous_snapshot.get("observed_at"))
        if previous_observed_at is not None:
            elapsed_seconds = ((now or _utc_now()) - previous_observed_at).total_seconds()
        same_tick = snapshot.get("last_tick_completed_at") == previous_snapshot.get(
            "last_tick_completed_at"
        )
        same_workers = snapshot.get("active_worker_ids") == previous_snapshot.get(
            "active_worker_ids"
        )
        same_dispatch_queue = int(snapshot.get("dispatch_queue_count", 0)) == int(
            previous_snapshot.get("dispatch_queue_count", 0)
        )
        done_count = int(snapshot.get("done_count", 0))
        previous_done_count = int(previous_snapshot.get("done_count", 0))
        if (
            pending_count > 0
            and active_worker_count > 0
            and same_tick
            and same_workers
            and same_dispatch_queue
            and done_count <= previous_done_count
            and elapsed_seconds is not None
            and elapsed_seconds >= stagnation_seconds
        ):
            alerts.append(
                "dispatch stagnation: "
                f"no tick or completion progress for {int(elapsed_seconds)}s while "
                f"{active_worker_count} worker(s) remain assigned"
            )

    return alerts


def read_soak_summary(path: Path = SOAK_LEDGER_PATH) -> dict[str, Any] | None:
    if not path.exists():
        return None
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parsed = json.loads(line)
        if isinstance(parsed, dict):
            entries.append(parsed)
    if not entries:
        return None
    return summarize_entries(entries)


def read_operational_readiness_snapshot() -> dict[str, Any] | None:
    queue_path = QUEUE_PATH
    state_path = STATE_PATH
    heartbeat_path = Path("artifacts/runtime/supervisor.heartbeat.json")
    benchmark_summary_path = Path("runs/real_data_benchmark/full_results/summary.json")
    if not queue_path.exists() or not state_path.exists() or not SOAK_LEDGER_PATH.exists():
        return None
    return build_operational_readiness_snapshot(
        queue_path=queue_path,
        state_path=state_path,
        heartbeat_path=heartbeat_path,
        procurement_supervisor_state_path=SUPERVISOR_STATE_PATH,
        ledger_path=SOAK_LEDGER_PATH,
        benchmark_summary_path=benchmark_summary_path,
        repo_root=Path.cwd(),
        observed_at=_utc_now(),
    )


def read_supervisor_heartbeat(path: Path = HEARTBEAT_PATH) -> dict[str, Any] | None:
    payload = load_json(path, {})
    return payload if isinstance(payload, dict) and payload else None


def read_procurement_supervisor_state(
    path: Path = SUPERVISOR_STATE_PATH,
) -> dict[str, Any] | None:
    payload = load_json(path, {})
    return payload if isinstance(payload, dict) and payload else None


def read_procurement_status_board(
    path: Path = PROCUREMENT_STATUS_BOARD_PATH,
) -> dict[str, Any] | None:
    payload = load_json(path, {})
    return payload if isinstance(payload, dict) and payload else None


def _is_download_command(command_line: str) -> bool:
    normalized = str(command_line or "").casefold()
    return any(script.casefold() in normalized for script in OBSERVED_DOWNLOAD_SCRIPTS)


def _probe_live_download_processes(
    *,
    runner: Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None,
) -> tuple[list[dict[str, Any]], str]:
    command = (
        "$items = Get-CimInstance Win32_Process | Where-Object { "
        "$_.CommandLine -and ($_.CommandLine -match "
        "'download_all_sources\\.py|download_raw_data\\.py|download_resolver_safe_urls\\.py') "
        "}; "
        "$items | Select-Object ProcessId,Name,CommandLine,CreationDate | ConvertTo-Json -Depth 4"
    )
    runner = runner or (
        lambda args: subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False,
        )
    )
    completed = runner(["powershell", "-NoProfile", "-Command", command])
    stdout = completed.stdout.strip() if completed.stdout else ""
    if completed.returncode != 0 or not stdout:
        return [], "unavailable"
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return [], "unavailable"
    if isinstance(payload, dict):
        payload = [payload]
    observations: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        command_line = str(item.get("CommandLine") or "").strip()
        if not command_line or not _is_download_command(command_line):
            continue
        observations.append(
            {
                "pid": int(item.get("ProcessId") or 0),
                "name": str(item.get("Name") or "").strip(),
                "command_line": command_line,
                "creation_date": str(item.get("CreationDate") or "").strip(),
            }
        )
    return observations, "available"


def _normalize_active_downloads(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for task in tasks:
        if not isinstance(task, dict):
            continue
        normalized.append(
            {
                "task_id": str(task.get("task_id") or "").strip(),
                "description": str(task.get("description") or "").strip(),
                "category": str(task.get("category") or "").strip(),
                "priority": task.get("priority"),
                "pid": task.get("pid"),
                "status": str(task.get("status") or "running").strip() or "running",
                "started_at": str(task.get("started_at") or "").strip(),
                "command_line": str(task.get("command_line") or "").strip(),
                "ownership": str(task.get("ownership") or "").strip() or "observed_only",
                "filename": str(task.get("filename") or "").strip(),
                "source_name": str(task.get("source_name") or "").strip(),
                "gap_kind": str(task.get("gap_kind") or "").strip(),
            }
        )
    return normalized


def _summarize_procurement_visibility(
    *,
    board: dict[str, Any] | None,
    supervisor_state: dict[str, Any] | None,
    broad_progress: dict[str, Any] | None = None,
    process_probe: Callable[[], tuple[list[dict[str, Any]], str]] | None = None,
) -> dict[str, Any] | None:
    broad_mirror = broad_progress if isinstance(broad_progress, dict) else None
    board_summary: dict[str, Any] = {}
    active_downloads: list[dict[str, Any]] = []
    observed_active_source = "none"
    observation_status = "unavailable"
    raw_process_table_downloads: list[dict[str, Any]] = []
    raw_process_table_active_count: int | None = None

    if process_probe is not None:
        live_processes, observation_status = process_probe()
        if observation_status == "available":
            raw_process_table_downloads = _normalize_active_downloads(
                [
                    {
                        "task_id": "",
                        "description": "",
                        "category": "bulk",
                        "priority": None,
                        "pid": process.get("pid"),
                        "status": "running",
                        "started_at": process.get("creation_date") or "",
                        "command_line": process.get("command_line") or "",
                        "ownership": "observed_only",
                    }
                    for process in live_processes
                    if _is_download_command(str(process.get("command_line") or ""))
                ]
            )
            raw_process_table_active_count = len(raw_process_table_downloads)

    if board:
        board_summary = board.get("summary") or {}
        supervisor = board.get("procurement_supervisor")
        if broad_mirror is None and isinstance(board.get("broad_mirror"), dict):
            broad_mirror = board.get("broad_mirror")
        if isinstance(supervisor, dict):
            authoritative_downloads = _normalize_active_downloads(
                supervisor.get("active_observed_downloads") or []
            )
            authoritative_source = (
                supervisor.get("observed_active_source")
                or (
                    "observed_active"
                    if supervisor.get("active_observed_downloads")
                    else "active"
                )
            )
            authoritative_count = int(
                supervisor.get("active_observed_download_count")
                or board_summary.get("active_observed_download_count")
                or 0
            )
            if authoritative_downloads or authoritative_count > 0:
                active_downloads = authoritative_downloads
                observed_active_source = authoritative_source
        if not active_downloads and raw_process_table_downloads:
            active_downloads = raw_process_table_downloads
            observed_active_source = "process_table"
        if not active_downloads and supervisor_state:
            active_downloads = _normalize_active_downloads(
                supervisor_state.get("observed_active") or supervisor_state.get("active") or []
            )
            observed_active_source = (
                supervisor_state.get("observed_active_source")
                or (
                    "observed_active"
                    if supervisor_state.get("observed_active")
                    else "active"
                )
            )
        return {
            "source": "procurement_status_board",
            "status": board.get("status"),
            "active_observed_download_count": len(active_downloads),
            "observed_active_source": observed_active_source,
            "active_observed_downloads": active_downloads,
            "raw_process_table_active_count": raw_process_table_active_count,
            "broad_mirror": broad_mirror,
            "board_summary": board_summary,
        }

    if supervisor_state:
        if raw_process_table_downloads:
            active_downloads = raw_process_table_downloads
            observed_active_source = "process_table"
        else:
            active_downloads = _normalize_active_downloads(
                supervisor_state.get("observed_active") or supervisor_state.get("active") or []
            )
            observed_active_source = (
                supervisor_state.get("observed_active_source")
                or ("observed_active" if supervisor_state.get("observed_active") else "active")
            )
        if broad_mirror is None and isinstance(broad_progress, dict):
            broad_mirror = broad_progress
        return {
            "source": "procurement_supervisor_state",
            "status": supervisor_state.get("status"),
            "active_observed_download_count": len(active_downloads),
            "observed_active_source": observed_active_source,
            "active_observed_downloads": active_downloads,
            "raw_process_table_active_count": raw_process_table_active_count,
            "broad_mirror": broad_mirror,
            "board_summary": board_summary,
        }

    if broad_mirror is not None:
        return {
            "source": "broad_mirror_progress",
            "status": broad_mirror.get("status"),
            "active_observed_download_count": len(active_downloads),
            "observed_active_source": observed_active_source,
            "active_observed_downloads": active_downloads,
            "raw_process_table_active_count": raw_process_table_active_count,
            "broad_mirror": broad_mirror,
            "board_summary": board_summary,
        }

    return None


def read_broad_mirror_progress(path: Path = BROAD_MIRROR_PROGRESS_PATH) -> dict[str, Any] | None:
    payload = load_json(path, {})
    if not isinstance(payload, dict) or not payload:
        return None
    summary = payload.get("summary")
    sources = payload.get("sources")
    if not isinstance(summary, dict) or not isinstance(sources, list):
        return None
    top_gap_sources = summary.get("top_gap_sources", [])
    top_priority_missing_files = payload.get("top_priority_missing_files", [])
    source_rows: list[dict[str, Any]] = []
    for row in sources[:8]:
        if not isinstance(row, dict):
            continue
        source_rows.append(
            {
                "source_id": row.get("source_id"),
                "source_name": row.get("source_name"),
                "status": row.get("status"),
                "coverage_percent": row.get("coverage_percent"),
                "missing_file_count": row.get("missing_file_count"),
                "partial_file_count": row.get("partial_file_count"),
                "priority_rank": row.get("priority_rank"),
            }
        )
    return {
        "status": payload.get("status"),
        "generated_at": payload.get("generated_at"),
        "source_count": summary.get("source_count"),
        "file_coverage_percent": summary.get("file_coverage_percent"),
        "total_expected_files": summary.get("total_expected_files"),
        "total_present_files": summary.get("total_present_files"),
        "total_missing_files": summary.get("total_missing_files"),
        "total_partial_files": summary.get("total_partial_files"),
        "top_gap_sources": list(top_gap_sources) if isinstance(top_gap_sources, list) else [],
        "top_priority_missing_files": [
            item
            for item in top_priority_missing_files
            if isinstance(item, dict)
        ][:10],
        "sources": source_rows,
    }


def read_remaining_transfer_status(
    path: Path = REMAINING_TRANSFER_STATUS_PATH,
) -> dict[str, Any] | None:
    payload = load_json(path, {})
    if not isinstance(payload, dict) or not payload:
        return None
    summary = payload.get("summary")
    sources = payload.get("sources")
    gap_files = payload.get("gap_files")
    if (
        not isinstance(summary, dict)
        or not isinstance(sources, list)
        or not isinstance(gap_files, list)
    ):
        return None

    source_rows: list[dict[str, Any]] = []
    for row in sources[:5]:
        if not isinstance(row, dict):
            continue
        source_rows.append(
            {
                "source_id": row.get("source_id"),
                "source_name": row.get("source_name"),
                "status": row.get("status"),
                "active_file_count": row.get("active_file_count"),
                "not_yet_started_file_count": row.get("not_yet_started_file_count"),
                "coverage_percent": row.get("coverage_percent"),
                "representative_missing_files": row.get("representative_missing_files"),
                "representative_partial_files": row.get("representative_partial_files"),
            }
        )

    return {
        "status": payload.get("status"),
        "generated_at": payload.get("generated_at"),
        "broad_mirror_coverage_percent": summary.get("broad_mirror_coverage_percent"),
        "remaining_source_count": summary.get("remaining_source_count"),
        "active_file_count": summary.get("active_file_count"),
        "not_yet_started_file_count": summary.get("not_yet_started_file_count"),
        "active_source_counts": summary.get("active_source_counts", {}),
        "total_gap_files": summary.get("total_gap_files"),
        "remaining_sources": source_rows,
        "top_gap_files": [
            item for item in gap_files if isinstance(item, dict)
        ][:10],
    }


def read_packet_deficit_summary(path: Path = PACKET_DEFICIT_PATH) -> dict[str, Any] | None:
    payload = load_json(path, {})
    if not isinstance(payload, dict) or not payload:
        return None
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        return None
    top_fixes = summary.get("highest_leverage_source_fixes", [])
    source_refs: list[str] = []
    if isinstance(top_fixes, list):
        for item in top_fixes[:7]:
            if not isinstance(item, dict):
                continue
            source_ref = str(item.get("source_ref", "")).strip()
            if source_ref:
                source_refs.append(source_ref)
    return {
        "packets": summary.get("packet_count"),
        "complete": summary.get("complete_packet_count"),
        "partial": summary.get("partial_packet_count"),
        "unresolved": summary.get("unresolved_packet_count"),
        "deficit_packets": summary.get("packet_deficit_count"),
        "missing_modalities": summary.get("total_missing_modality_count"),
        "modality_deficits": summary.get("modality_deficit_counts", {}),
        "top_source_refs": source_refs,
    }


def main() -> None:
    queue = load_json(QUEUE_PATH, [])
    state = load_json(STATE_PATH, {})
    previous_snapshot = load_json(SNAPSHOT_PATH, {})
    snapshot = build_monitor_snapshot(queue, state)
    heartbeat = read_supervisor_heartbeat()
    procurement_board = read_procurement_status_board()
    procurement_state = read_procurement_supervisor_state()
    broad_progress = read_broad_mirror_progress()
    remaining_transfer = read_remaining_transfer_status()
    procurement_visibility = _summarize_procurement_visibility(
        board=procurement_board,
        supervisor_state=procurement_state,
        broad_progress=broad_progress,
        process_probe=_probe_live_download_processes,
    )
    alerts = evaluate_alerts(snapshot, previous_snapshot or None, heartbeat=heartbeat)

    print("Queue:", snapshot["queue_counts"])
    print("Ready tasks:", snapshot["ready_count"])
    print("Dependency-ready pending tasks:", snapshot["dependency_ready_pending_count"])
    print("Active workers:", snapshot["active_worker_count"])
    print("Dispatch queue:", snapshot["dispatch_queue_count"])
    print("Review queue:", snapshot["review_queue_count"])
    if procurement_visibility:
        print(
            "Procurement supervisor:",
            {
                "source": procurement_visibility.get("source"),
                "status": procurement_visibility.get("status"),
                "observed_active_source": procurement_visibility.get(
                    "observed_active_source"
                ),
                "active_observed_download_count": procurement_visibility.get(
                    "active_observed_download_count"
                ),
                "raw_process_table_active_count": procurement_visibility.get(
                    "raw_process_table_active_count"
                ),
            },
        )
        observed_active = procurement_visibility.get("active_observed_downloads", [])
        if observed_active:
            print("Observed active procurement lanes:")
            for lane in observed_active[:10]:
                print(
                    "-",
                    {
                        "task_id": lane.get("task_id") or "",
                        "filename": lane.get("filename") or lane.get("description") or "",
                        "source_name": lane.get("source_name") or "",
                        "pid": lane.get("pid"),
                        "ownership": lane.get("ownership") or "",
                        "command_line": lane.get("command_line") or "",
                    },
                )
    if procurement_visibility and procurement_visibility.get("broad_mirror"):
        broad_mirror = procurement_visibility["broad_mirror"]
        print(
            "Broad mirror progress:",
            {
                "status": broad_mirror.get("status"),
                "source_count": broad_mirror.get("source_count"),
                "file_coverage_percent": broad_mirror.get("file_coverage_percent"),
                "total_present_files": broad_mirror.get("total_present_files"),
                "total_expected_files": broad_mirror.get("total_expected_files"),
                "total_missing_files": broad_mirror.get("total_missing_files"),
                "total_partial_files": broad_mirror.get("total_partial_files"),
                "top_gap_sources": broad_mirror.get("top_gap_sources", []),
            },
        )
        for row in broad_mirror.get("sources", [])[:5]:
            print(
                "-",
                {
                    "source_id": row.get("source_id"),
                    "status": row.get("status"),
                    "coverage_percent": row.get("coverage_percent"),
                    "missing_file_count": row.get("missing_file_count"),
                    "partial_file_count": row.get("partial_file_count"),
                },
            )
    elif broad_progress:
        print(
            "Broad mirror progress:",
            {
                "status": broad_progress.get("status"),
                "source_count": broad_progress.get("source_count"),
                "file_coverage_percent": broad_progress.get("file_coverage_percent"),
                "total_present_files": broad_progress.get("total_present_files"),
                "total_expected_files": broad_progress.get("total_expected_files"),
                "total_missing_files": broad_progress.get("total_missing_files"),
                "total_partial_files": broad_progress.get("total_partial_files"),
                "top_gap_sources": broad_progress.get("top_gap_sources", []),
            },
        )
        for row in broad_progress.get("sources", [])[:5]:
            print(
                "-",
                {
                    "source_id": row.get("source_id"),
                    "status": row.get("status"),
                    "coverage_percent": row.get("coverage_percent"),
                    "missing_file_count": row.get("missing_file_count"),
                    "partial_file_count": row.get("partial_file_count"),
                },
            )
    if remaining_transfer:
        print(
            "Remaining transfer status:",
            {
                "status": remaining_transfer.get("status"),
                "remaining_source_count": remaining_transfer.get("remaining_source_count"),
                "active_file_count": remaining_transfer.get("active_file_count"),
                "not_yet_started_file_count": remaining_transfer.get(
                    "not_yet_started_file_count"
                ),
                "active_source_counts": remaining_transfer.get("active_source_counts", {}),
                "total_gap_files": remaining_transfer.get("total_gap_files"),
            },
        )
        if remaining_transfer.get("remaining_sources"):
            print("Remaining transfer sources:")
            for row in remaining_transfer["remaining_sources"][:5]:
                print(
                    "-",
                    {
                        "source_id": row.get("source_id"),
                        "source_name": row.get("source_name"),
                        "status": row.get("status"),
                        "active_file_count": row.get("active_file_count"),
                        "not_yet_started_file_count": row.get(
                            "not_yet_started_file_count"
                        ),
                        "coverage_percent": row.get("coverage_percent"),
                    },
                )
        if remaining_transfer.get("top_gap_files"):
            print("Top remaining transfer files:")
            for row in remaining_transfer["top_gap_files"][:10]:
                print(
                    "-",
                    {
                        "source_id": row.get("source_id"),
                        "source_name": row.get("source_name"),
                        "filename": row.get("filename"),
                        "gap_kind": row.get("gap_kind"),
                        "category": row.get("category"),
                    },
                )
    if alerts:
        print("Alerts:")
        for alert in alerts:
            print("-", alert)
    else:
        print("Alerts: none")

    soak_summary = read_soak_summary()
    if soak_summary:
        print(
            "Soak summary:",
            {
                "entries": soak_summary["entry_count"],
                "window_hours": soak_summary["observed_window_hours"],
                "progress_ratio": soak_summary["observed_window_progress_ratio"],
                "remaining_hours": soak_summary["remaining_hours_to_weeklong"],
                "estimated_weeklong_at": soak_summary["estimated_weeklong_completion_at"],
                "incidents": soak_summary["incident_count"],
                "healthy_ratio": soak_summary["healthy_ratio"],
                "weeklong_claim_allowed": soak_summary["truth_boundary"][
                    "weeklong_soak_claim_allowed"
                ],
            },
        )

    readiness = read_operational_readiness_snapshot()
    if readiness:
        print(
            "Operational readiness:",
            {
                "supervisor": readiness["supervisor"]["status"],
                "ready": readiness["release_gate"]["operational_readiness_ready"],
                "truth_audit": readiness["truth_audit"]["status"],
                "queue_drift": readiness["queue_drift"]["status"],
                "capture_age_seconds": readiness["queue_drift"]["capture_age_seconds"],
                "weeklong_met": readiness["release_gate"]["weeklong_requirement_met"],
                "blocking_reasons": readiness["release_gate"]["blocking_reasons"],
            },
        )

    packet_deficits = read_packet_deficit_summary()
    if packet_deficits:
        print("Packet deficits:", packet_deficits)

    save_json(SNAPSHOT_PATH, snapshot)


if __name__ == "__main__":
    main()
