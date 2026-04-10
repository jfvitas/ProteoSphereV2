from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BROAD_MIRROR_PROGRESS_PATH = (
    REPO_ROOT / "artifacts" / "status" / "broad_mirror_progress.json"
)
DEFAULT_SUPERVISOR_STATE_PATH = (
    REPO_ROOT / "artifacts" / "runtime" / "procurement_supervisor_state.json"
)
DEFAULT_LOCAL_REGISTRY_SUMMARY_PATH = (
    REPO_ROOT / "artifacts" / "status" / "source_coverage_matrix.json"
)
DEFAULT_REMAINING_TRANSFER_STATUS_PATH = (
    REPO_ROOT / "artifacts" / "status" / "broad_mirror_remaining_transfer_status.json"
)
DEFAULT_DOWNLOAD_LOCATION_AUDIT_PATH = (
    REPO_ROOT / "artifacts" / "status" / "download_location_audit_preview.json"
)
DEFAULT_STALE_PART_AUDIT_PATH = (
    REPO_ROOT / "artifacts" / "status" / "procurement_stale_part_audit_preview.json"
)
DEFAULT_OUTPUT_PATH = REPO_ROOT / "artifacts" / "status" / "procurement_status_board.json"
DEFAULT_MARKDOWN_OUTPUT_PATH = (
    REPO_ROOT / "docs" / "reports" / "procurement_status_board.md"
)
OBSERVED_DOWNLOAD_SCRIPTS = (
    "download_all_sources.py",
    "download_raw_data.py",
    "download_resolver_safe_urls.py",
)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise TypeError(f"expected JSON object at {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _casefold(value: Any) -> str:
    return str(value or "").strip().casefold()


def _normalize_sequence(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _normalize_task_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _download_location_active_rows(
    location_audit: dict[str, Any],
    stale_part_audit: dict[str, Any],
) -> list[dict[str, Any]]:
    stale_paths = {
        _casefold(row.get("part_path"))
        for row in _normalize_task_list(stale_part_audit.get("rows"))
        if _casefold(row.get("classification")) == "stale_residue_after_final"
    }
    active_rows: list[dict[str, Any]] = []
    for row in _normalize_task_list(location_audit.get("rows")):
        live_locations = [
            location
            for location in _normalize_task_list(row.get("in_process_locations"))
            if _casefold(location.get("path")) not in stale_paths
        ]
        if not live_locations:
            continue
        active_rows.append(
            {
                "task_id": row.get("source_id"),
                "description": row.get("filename"),
                "category": row.get("category"),
                "priority": None,
                "pid": None,
                "status": "running",
                "started_at": "",
                "filename": row.get("filename"),
                "source_name": row.get("source_name"),
                "path": live_locations[0].get("path"),
            }
        )
    return active_rows


def _is_download_command(command_line: str) -> bool:
    normalized = str(command_line or "").casefold()
    return any(script.casefold() in normalized for script in OBSERVED_DOWNLOAD_SCRIPTS)


def _matches_task_command(command_line: str, task: dict[str, Any]) -> bool:
    normalized = str(command_line or "").casefold()
    command = task.get("command")
    if not isinstance(command, list) or len(command) < 2:
        return False
    script_name = Path(str(command[1])).name.casefold()
    if script_name not in normalized:
        return False
    for token in command[2:]:
        text = str(token or "").strip()
        if text and text.casefold() not in normalized:
            return False
    return True


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


def _compact_broad_mirror(progress: dict[str, Any]) -> dict[str, Any]:
    summary = progress.get("summary") if isinstance(progress.get("summary"), dict) else {}
    sources = [row for row in progress.get("sources") or [] if isinstance(row, dict)]
    source_status_counts = Counter(_casefold(row.get("status")) or "unknown" for row in sources)

    gap_sources: list[dict[str, Any]] = []
    for row in sources:
        if _casefold(row.get("status")) == "complete":
            continue
        gap_sources.append(
            {
                "scope": "broad_mirror",
                "source_id": row.get("source_id"),
                "source_name": row.get("source_name"),
                "category": row.get("category"),
                "status": row.get("status"),
                "priority_rank": row.get("priority_rank"),
                "coverage_percent": row.get("coverage_percent"),
                "missing_file_count": row.get("missing_file_count"),
                "partial_file_count": row.get("partial_file_count"),
                "representative_missing_files": _normalize_sequence(
                    row.get("representative_missing_files")
                ),
                "representative_partial_files": _normalize_sequence(
                    row.get("representative_partial_files")
                ),
                "rationale": (
                    f"{row.get('status')} mirror family; "
                    f"{row.get('missing_file_count')} missing files"
                ),
            }
        )

    gap_sources.sort(
        key=lambda row: (
            int(row.get("priority_rank") or 99),
            -int(row.get("missing_file_count") or 0),
            float(row.get("coverage_percent") or 0.0),
            _casefold(row.get("source_id")),
        )
    )

    top_missing_files_source = (
        progress.get("top_priority_missing_files")
        or progress.get("top_missing_files")
        or []
    )
    top_missing_files = [
        item
        for item in top_missing_files_source
        if isinstance(item, dict)
    ][:10]

    return {
        "source_count": summary.get("source_count"),
        "file_coverage_percent": summary.get("file_coverage_percent"),
        "total_expected_files": summary.get("total_expected_files"),
        "total_present_files": summary.get("total_present_files"),
        "total_missing_files": summary.get("total_missing_files"),
        "total_partial_files": summary.get("total_partial_files"),
        "source_status_counts": dict(sorted(source_status_counts.items())),
        "complete_source_count": summary.get("complete_source_count"),
        "incomplete_source_count": summary.get("incomplete_source_count"),
        "top_gap_sources": gap_sources[:10],
        "top_missing_files": top_missing_files,
    }


def _compact_supervisor_state(
    state: dict[str, Any],
    *,
    remaining_transfer_status: dict[str, Any] | None = None,
    download_location_audit: dict[str, Any] | None = None,
    stale_part_audit: dict[str, Any] | None = None,
    process_probe: Callable[[], tuple[list[dict[str, Any]], str]] | None = None,
) -> dict[str, Any]:
    remaining_transfer_status = (
        remaining_transfer_status if isinstance(remaining_transfer_status, dict) else {}
    )
    download_location_audit = (
        download_location_audit if isinstance(download_location_audit, dict) else {}
    )
    stale_part_audit = stale_part_audit if isinstance(stale_part_audit, dict) else {}
    authoritative_active_files = _normalize_task_list(
        remaining_transfer_status.get("actively_transferring_now")
    )
    authoritative_pending_files = _normalize_task_list(
        remaining_transfer_status.get("not_yet_started")
    )
    remaining_summary = (
        remaining_transfer_status.get("summary")
        if isinstance(remaining_transfer_status.get("summary"), dict)
        else {}
    )
    audit_summary = (
        download_location_audit.get("summary")
        if isinstance(download_location_audit.get("summary"), dict)
        else {}
    )
    remaining_active_count = int(remaining_summary.get("active_file_count") or 0)
    remaining_pending_count = int(
        remaining_summary.get("not_yet_started_file_count") or 0
    )
    audit_in_process_count = int(audit_summary.get("in_process_count") or 0)
    audit_missing_count = int(audit_summary.get("missing_count") or 0)
    location_active_rows = _download_location_active_rows(
        download_location_audit,
        stale_part_audit,
    )
    if location_active_rows:
        source_counts = Counter(
            _casefold(row.get("task_id")) or _casefold(row.get("source_name")) or "unknown"
            for row in location_active_rows
        )
        return {
            "status": state.get("status"),
            "generated_at": state.get("generated_at"),
            "active_observed_download_count": len(location_active_rows),
            "observed_active_source": "download_location_audit",
            "active_observed_downloads": location_active_rows,
            "completed_download_count": len(_normalize_task_list(state.get("completed"))),
            "not_yet_started_file_count": remaining_pending_count,
            "raw_process_table_active_count": None,
            "active_source_counts": dict(sorted(source_counts.items())),
        }
    if (
        audit_in_process_count == 0
        and audit_missing_count == 0
        and remaining_active_count == 0
        and remaining_pending_count == 0
    ):
        return {
            "status": remaining_transfer_status.get("status") or state.get("status"),
            "generated_at": remaining_transfer_status.get("generated_at")
            or state.get("generated_at"),
            "active_observed_download_count": 0,
            "observed_active_source": "authoritative_complete",
            "active_observed_downloads": [],
            "completed_download_count": len(_normalize_task_list(state.get("completed"))),
            "not_yet_started_file_count": 0,
            "raw_process_table_active_count": 0,
            "active_source_counts": {},
        }
    if (
        authoritative_active_files
        or authoritative_pending_files
        or remaining_active_count > 0
        or remaining_pending_count > 0
    ):
        visible_active_tasks = [
            {
                "task_id": row.get("source_id"),
                "description": row.get("filename"),
                "category": row.get("category"),
                "priority": row.get("priority_rank"),
                "pid": None,
                "status": "running",
                "started_at": "",
                "filename": row.get("filename"),
                "source_name": row.get("source_name"),
                "gap_kind": row.get("gap_kind"),
            }
            for row in authoritative_active_files
        ]
        if not visible_active_tasks:
            gap_rows = _normalize_task_list(remaining_transfer_status.get("gap_files"))
            visible_active_tasks = [
                {
                    "task_id": row.get("source_id"),
                    "description": row.get("filename"),
                    "category": row.get("category"),
                    "priority": row.get("priority_rank"),
                    "pid": None,
                    "status": "running",
                    "started_at": "",
                    "filename": row.get("filename"),
                    "source_name": row.get("source_name"),
                    "gap_kind": row.get("gap_kind"),
                }
                for row in gap_rows
            ]
        return {
            "status": remaining_transfer_status.get("status"),
            "generated_at": remaining_transfer_status.get("generated_at"),
            "active_observed_download_count": remaining_active_count,
            "observed_active_source": "remaining_transfer_status",
            "active_observed_downloads": visible_active_tasks,
            "completed_download_count": len(_normalize_task_list(state.get("completed"))),
            "not_yet_started_file_count": remaining_pending_count,
            "raw_process_table_active_count": None,
            "active_source_counts": remaining_summary.get("active_source_counts", {}),
        }

    observed_active_tasks = _normalize_task_list(
        state.get("observed_active")
        or (state.get("state", {}) or {}).get("observed_active")
    )
    active_tasks = _normalize_task_list(state.get("active"))
    completed_tasks = _normalize_task_list(state.get("completed"))

    visible_active_tasks: list[dict[str, Any]] = []
    observed_active_source = "none"
    live_processes, observation_status = (process_probe or _probe_live_download_processes)()
    if observation_status == "available":
        observed_from_process_table: list[dict[str, Any]] = []
        for process in live_processes:
            command_line = str(process.get("command_line") or "").strip()
            if not command_line or not _is_download_command(command_line):
                continue
            matched_task = next(
                (
                    task
                    for task in _normalize_task_list(state.get("active"))
                    if _matches_task_command(command_line, task)
                ),
                None,
            )
            observed_from_process_table.append(
                {
                    "task_id": matched_task.get("task_id") if matched_task else "",
                    "description": matched_task.get("description") if matched_task else "",
                    "category": matched_task.get("category") if matched_task else "bulk",
                    "priority": matched_task.get("priority") if matched_task else None,
                    "pid": process.get("pid"),
                    "status": "running",
                    "started_at": process.get("creation_date") or "",
                    "command_line": command_line,
                    "ownership": "observed_only",
                }
            )
        visible_active_tasks = observed_from_process_table
        observed_active_source = "process_table"
    elif observed_active_tasks:
        visible_active_tasks = list(observed_active_tasks)
        observed_active_source = "observed_active"
    elif active_tasks:
        visible_active_tasks = active_tasks
        observed_active_source = "active"
    else:
        live_processes = []
        observation_status = "unavailable"
    if not visible_active_tasks and active_tasks and observation_status != "available":
        visible_active_tasks = active_tasks
        observed_active_source = "active"

    return {
        "status": state.get("status"),
        "generated_at": state.get("generated_at"),
        "active_observed_download_count": len(visible_active_tasks),
        "observed_active_source": observed_active_source,
        "active_observed_downloads": [
            {
                "task_id": task.get("task_id"),
                "description": task.get("description"),
                "category": task.get("category"),
                "priority": task.get("priority"),
                "pid": task.get("pid"),
                "status": task.get("status"),
                "started_at": task.get("started_at"),
            }
            for task in visible_active_tasks
        ],
        "completed_download_count": len(completed_tasks),
        "not_yet_started_file_count": 0,
        "raw_process_table_active_count": (
            len(live_processes) if observation_status == "available" else None
        ),
        "active_source_counts": {},
    }


def _compact_local_registry_summary(summary: dict[str, Any]) -> dict[str, Any]:
    matrix = [row for row in summary.get("matrix") or [] if isinstance(row, dict)]
    effective_status_counts = Counter(
        _casefold(row.get("effective_status")) or _casefold(row.get("status")) or "unknown"
        for row in matrix
    )

    gap_families = [
        row
        for row in matrix
        if _casefold(row.get("effective_status")) in {"missing", "partial", "degraded"}
    ]
    gap_families.sort(
        key=lambda row: (
            float(row.get("coverage_score") or 0.0),
            _casefold(row.get("source_name")),
        )
    )

    top_gap_families: list[dict[str, Any]] = []
    for row in gap_families[:10]:
        planning_signals = (
            row.get("planning_signals") if isinstance(row.get("planning_signals"), dict) else {}
        )
        top_gap_families.append(
            {
                "scope": "local_registry",
                "source_name": row.get("source_name"),
                "category": row.get("category"),
                "status": row.get("effective_status") or row.get("status"),
                "coverage_score": row.get("coverage_score"),
                "facet_counts": row.get("facet_counts"),
                "available_via": _normalize_sequence(row.get("available_via")),
                "rationale": (
                    f"registry {row.get('effective_status')} lane; "
                    f"procurement_gap={planning_signals.get('procurement_gap')}"
                ),
            }
        )

    return {
        "source_count": len(matrix),
        "effective_status_counts": dict(sorted(effective_status_counts.items())),
        "gap_family_count": len(gap_families),
        "top_gap_families": top_gap_families,
    }


def _compact_remaining_transfer_status(status: dict[str, Any]) -> dict[str, Any]:
    summary = status.get("summary") if isinstance(status.get("summary"), dict) else {}
    sources = [row for row in status.get("sources") or [] if isinstance(row, dict)]
    gap_files = [row for row in status.get("gap_files") or [] if isinstance(row, dict)]

    remaining_sources: list[dict[str, Any]] = []
    for row in sources[:10]:
        remaining_sources.append(
            {
                "source_id": row.get("source_id"),
                "source_name": row.get("source_name"),
                "status": row.get("status"),
                "coverage_percent": row.get("coverage_percent"),
                "active_file_count": row.get("active_file_count"),
                "not_yet_started_file_count": row.get("not_yet_started_file_count"),
                "priority_rank": row.get("priority_rank"),
                "representative_missing_files": _normalize_sequence(
                    row.get("representative_missing_files")
                ),
                "representative_partial_files": _normalize_sequence(
                    row.get("representative_partial_files")
                ),
            }
        )

    top_gap_files = [
        {
            "source_id": row.get("source_id"),
            "source_name": row.get("source_name"),
            "filename": row.get("filename"),
            "gap_kind": row.get("gap_kind"),
            "category": row.get("category"),
            "priority_rank": row.get("priority_rank"),
            "coverage_percent": row.get("coverage_percent"),
        }
        for row in gap_files[:10]
    ]
    active_file_count = summary.get("active_file_count")
    not_yet_started_file_count = summary.get("not_yet_started_file_count")
    total_gap_files = summary.get("total_gap_files")
    if total_gap_files is None:
        total_gap_files = int(active_file_count or 0) + int(not_yet_started_file_count or 0)

    return {
        "status": status.get("status"),
        "generated_at": status.get("generated_at"),
        "broad_mirror_coverage_percent": summary.get("broad_mirror_coverage_percent"),
        "remaining_source_count": summary.get("remaining_source_count"),
        "active_file_count": active_file_count,
        "not_yet_started_file_count": not_yet_started_file_count,
        "active_source_counts": summary.get("active_source_counts", {}),
        "total_gap_files": total_gap_files,
        "top_gap_files": top_gap_files,
        "remaining_sources": remaining_sources,
    }


def _merge_gap_lists(
    broad_mirror_gaps: list[dict[str, Any]],
    registry_gaps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()

    for row in broad_mirror_gaps:
        source_key = _casefold(row.get("source_id"))
        if not source_key:
            continue
        seen_keys.add(("broad_mirror", source_key))
        merged.append(row)

    for row in registry_gaps:
        source_key = _casefold(row.get("source_name"))
        if not source_key or ("broad_mirror", source_key) in seen_keys:
            continue
        merged.append(row)

    def sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
        scope_rank = 0 if row.get("scope") == "broad_mirror" else 1
        priority_rank = row.get("priority_rank")
        if priority_rank is None:
            status = _casefold(row.get("status"))
            if status == "missing":
                priority_rank = 1
            elif status == "partial":
                priority_rank = 2
            elif status == "degraded":
                priority_rank = 3
            else:
                priority_rank = 4
        status = _casefold(row.get("status"))
        status_rank = 0 if status in {"missing", "partial", "degraded"} else 1
        coverage = row.get("coverage_percent")
        if coverage is None:
            coverage = row.get("coverage_score")
        return (
            scope_rank,
            int(priority_rank or 99),
            status_rank,
            float(coverage or 0.0),
            _casefold(row.get("source_id") or row.get("source_name")),
        )

    merged.sort(key=sort_key)
    return merged[:10]


def build_procurement_status_board(
    *,
    broad_mirror_progress_path: Path = DEFAULT_BROAD_MIRROR_PROGRESS_PATH,
    remaining_transfer_status_path: Path = DEFAULT_REMAINING_TRANSFER_STATUS_PATH,
    supervisor_state_path: Path = DEFAULT_SUPERVISOR_STATE_PATH,
    local_registry_summary_path: Path = DEFAULT_LOCAL_REGISTRY_SUMMARY_PATH,
    download_location_audit_path: Path | None = None,
    stale_part_audit_path: Path | None = None,
    process_probe: Callable[[], tuple[list[dict[str, Any]], str]] | None = None,
) -> dict[str, Any]:
    for path, label in (
        (broad_mirror_progress_path, "broad mirror progress"),
        (remaining_transfer_status_path, "remaining transfer status"),
        (supervisor_state_path, "procurement supervisor state"),
        (local_registry_summary_path, "local registry summary"),
    ):
        if not path.exists():
            raise FileNotFoundError(f"missing {label}: {path}")

    broad_mirror_progress = _read_json(broad_mirror_progress_path)
    remaining_transfer_status = _read_json(remaining_transfer_status_path)
    supervisor_state = _read_json(supervisor_state_path)
    local_registry_summary = _read_json(local_registry_summary_path)
    download_location_audit = (
        _read_json(download_location_audit_path)
        if download_location_audit_path is not None and download_location_audit_path.exists()
        else {}
    )
    stale_part_audit = (
        _read_json(stale_part_audit_path)
        if stale_part_audit_path is not None and stale_part_audit_path.exists()
        else {}
    )

    broad_mirror = _compact_broad_mirror(broad_mirror_progress)
    remaining_transfer = _compact_remaining_transfer_status(remaining_transfer_status)
    supervisor = _compact_supervisor_state(
        supervisor_state,
        remaining_transfer_status=remaining_transfer_status,
        download_location_audit=download_location_audit,
        stale_part_audit=stale_part_audit,
        process_probe=process_probe,
    )
    local_registry = _compact_local_registry_summary(local_registry_summary)
    top_remaining_gaps = list(broad_mirror["top_gap_sources"])

    board_status = "attention"
    if (
        remaining_transfer["total_gap_files"] == 0
        and
        supervisor["active_observed_download_count"] == 0
        and broad_mirror["file_coverage_percent"] == 100.0
        and not broad_mirror["incomplete_source_count"]
        and remaining_transfer["not_yet_started_file_count"] == 0
    ):
        board_status = "green"

    return {
        "schema_id": "proteosphere-procurement-status-board-2026-03-30",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": board_status,
        "inputs": {
            "broad_mirror_progress_path": str(broad_mirror_progress_path).replace("\\", "/"),
            "supervisor_state_path": str(supervisor_state_path).replace("\\", "/"),
            "local_registry_summary_path": str(local_registry_summary_path).replace("\\", "/"),
            "download_location_audit_path": (
                str(download_location_audit_path).replace("\\", "/")
                if download_location_audit_path is not None
                else None
            ),
            "stale_part_audit_path": (
                str(stale_part_audit_path).replace("\\", "/")
                if stale_part_audit_path is not None
                else None
            ),
        },
        "summary": {
            "broad_mirror_coverage_percent": broad_mirror["file_coverage_percent"],
            "broad_mirror_source_count": broad_mirror["source_count"],
            "source_family_status_counts": broad_mirror["source_status_counts"],
            "broad_mirror_total_missing_files": broad_mirror["total_missing_files"],
            "broad_mirror_incomplete_source_count": broad_mirror["incomplete_source_count"],
            "remaining_transfer_source_count": remaining_transfer["remaining_source_count"],
            "remaining_transfer_active_file_count": remaining_transfer["active_file_count"],
            "remaining_transfer_not_yet_started_file_count": remaining_transfer[
                "not_yet_started_file_count"
            ],
            "remaining_transfer_total_gap_files": remaining_transfer["total_gap_files"],
            "active_observed_download_count": supervisor["active_observed_download_count"],
            "observed_active_source": supervisor["observed_active_source"],
            "download_location_missing_count": int(
                (download_location_audit.get("summary") or {}).get("missing_count") or 0
            ),
            "download_location_in_process_count": int(
                (download_location_audit.get("summary") or {}).get("in_process_count") or 0
            ),
            "stale_part_residue_count": int(
                (stale_part_audit.get("summary") or {}).get("stale_residue_count") or 0
            ),
            "local_registry_source_count": local_registry["source_count"],
            "local_registry_effective_status_counts": local_registry[
                "effective_status_counts"
            ],
            "local_registry_gap_family_count": local_registry["gap_family_count"],
            "top_remaining_gap_count": len(top_remaining_gaps),
        },
        "broad_mirror": broad_mirror,
        "remaining_transfer": remaining_transfer,
        "procurement_supervisor": supervisor,
        "download_location_audit": {
            "status": download_location_audit.get("status"),
            "generated_at": download_location_audit.get("generated_at"),
            "summary": download_location_audit.get("summary", {}),
        }
        if download_location_audit
        else None,
        "stale_part_audit": {
            "status": stale_part_audit.get("status"),
            "generated_at": stale_part_audit.get("generated_at"),
            "summary": stale_part_audit.get("summary", {}),
            "rows": stale_part_audit.get("rows", []),
        }
        if stale_part_audit
        else None,
        "local_registry_summary": local_registry,
        "top_remaining_gaps": top_remaining_gaps,
        "truth_boundary": {
            "summary": (
                "This board is a report-only consolidation of broad mirror progress, "
                "location-aware transfer truth, procurement supervisor state, and local "
                "registry coverage. It does not launch downloads or promote registry state."
            ),
            "report_only": True,
            "non_mutating": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Procurement Status Board",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Board status: `{payload['status']}`",
        f"- Broad mirror coverage: `{summary['broad_mirror_coverage_percent']}%`",
        f"- Broad mirror source count: `{summary['broad_mirror_source_count']}`",
        f"- Source-family status counts: `{summary['source_family_status_counts']}`",
        f"- Remaining transfer sources: `{summary['remaining_transfer_source_count']}`",
        f"- Remaining transfer active files: `{summary['remaining_transfer_active_file_count']}`",
        "- Remaining transfer not-yet-started files: "
        f"`{summary['remaining_transfer_not_yet_started_file_count']}`",
        f"- Active observed downloads: `{summary['active_observed_download_count']}`",
        f"- Active source field: `{summary['observed_active_source']}`",
        f"- Local registry source count: `{summary['local_registry_source_count']}`",
        f"- Local registry status counts: `{summary['local_registry_effective_status_counts']}`",
        "",
        "## Top Remaining Gaps",
        "",
        "| Scope | Family | Status | Coverage | Missing / score | Rationale |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for row in payload["top_remaining_gaps"]:
        coverage = row.get("coverage_percent")
        if coverage is None:
            coverage = row.get("coverage_score")
        missing_or_score = row.get("missing_file_count")
        if missing_or_score is None:
            missing_or_score = row.get("coverage_score")
        family = row.get("source_id") or row.get("source_name")
        lines.append(
            "| "
            + f"{row.get('scope')} | "
            + f"`{family}` | "
            + f"{row.get('status')} | "
            + f"{coverage} | "
            + f"{missing_or_score} | "
            + f"{row.get('rationale')} |"
        )

    if payload["broad_mirror"]["top_missing_files"]:
        lines.extend(["", "## Top Missing Files", ""])
        for row in payload["broad_mirror"]["top_missing_files"]:
            lines.append(
                f"- `{row['source_id']}`: `{row['filename']}` "
                f"(priority {row['priority_rank']}, value {row['estimated_value']})"
            )

    if payload.get("remaining_transfer"):
        lines.extend(["", "## Remaining Transfers", ""])
        remaining_transfer = payload["remaining_transfer"]
        lines.append(
            f"- Remaining sources: `{remaining_transfer['remaining_source_count']}`"
        )
        lines.append(
            f"- Active files: `{remaining_transfer['active_file_count']}`"
        )
        lines.append(
            f"- Not-yet-started files: `{remaining_transfer['not_yet_started_file_count']}`"
        )
        lines.append(
            f"- Total gap files: `{remaining_transfer['total_gap_files']}`"
        )
        if remaining_transfer["remaining_sources"]:
            lines.append("")
            lines.append("| Source | Status | Active | Not started | Coverage |")
            lines.append("| --- | --- | --- | --- | --- |")
            for row in remaining_transfer["remaining_sources"]:
                lines.append(
                    "| "
                    + f"`{row.get('source_name') or row.get('source_id')}` | "
                    + f"{row.get('status')} | "
                    + f"{row.get('active_file_count')} | "
                    + f"{row.get('not_yet_started_file_count')} | "
                    + f"{row.get('coverage_percent')} |"
                )
        if remaining_transfer["top_gap_files"]:
            lines.extend(["", "Top remaining filenames:"])
            for row in remaining_transfer["top_gap_files"]:
                lines.append(
                    f"- `{row['source_id']}`: `{row['filename']}` "
                    f"({row['gap_kind']}, priority {row['priority_rank']})"
                )

    if payload["procurement_supervisor"]["active_observed_downloads"]:
        lines.extend(["", "## Active Downloads", ""])
        for row in payload["procurement_supervisor"]["active_observed_downloads"]:
            lines.append(
                f"- `{row.get('task_id')}` pid=`{row.get('pid')}` "
                f"status=`{row.get('status')}` description={row.get('description')}"
            )

    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export the procurement status board.")
    parser.add_argument(
        "--broad-mirror-progress",
        type=Path,
        default=DEFAULT_BROAD_MIRROR_PROGRESS_PATH,
    )
    parser.add_argument(
        "--remaining-transfer-status",
        type=Path,
        default=DEFAULT_REMAINING_TRANSFER_STATUS_PATH,
    )
    parser.add_argument(
        "--supervisor-state",
        type=Path,
        default=DEFAULT_SUPERVISOR_STATE_PATH,
    )
    parser.add_argument(
        "--local-registry-summary",
        type=Path,
        default=DEFAULT_LOCAL_REGISTRY_SUMMARY_PATH,
    )
    parser.add_argument(
        "--download-location-audit",
        type=Path,
        default=DEFAULT_DOWNLOAD_LOCATION_AUDIT_PATH,
    )
    parser.add_argument(
        "--stale-part-audit",
        type=Path,
        default=DEFAULT_STALE_PART_AUDIT_PATH,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT_PATH)
    parser.add_argument("--no-markdown", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    argv_tokens = list(argv or [])
    explicit_download_location_audit = argv is None or "--download-location-audit" in argv_tokens
    explicit_stale_part_audit = argv is None or "--stale-part-audit" in argv_tokens

    payload = build_procurement_status_board(
        broad_mirror_progress_path=args.broad_mirror_progress,
        remaining_transfer_status_path=args.remaining_transfer_status,
        supervisor_state_path=args.supervisor_state,
        local_registry_summary_path=args.local_registry_summary,
        download_location_audit_path=(
            args.download_location_audit if explicit_download_location_audit else None
        ),
        stale_part_audit_path=(args.stale_part_audit if explicit_stale_part_audit else None),
    )
    _write_json(args.output, payload)
    if not args.no_markdown:
        _write_text(args.markdown_output, render_markdown(payload))

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "Procurement status board exported: "
            f"status={payload['status']} "
            f"coverage={payload['summary']['broad_mirror_coverage_percent']}% "
            f"active={payload['summary']['active_observed_download_count']} "
            f"gaps={payload['summary']['top_remaining_gap_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
