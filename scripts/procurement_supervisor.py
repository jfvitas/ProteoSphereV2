# ruff: noqa: I001
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from collections.abc import Callable
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = REPO_ROOT / "artifacts" / "runtime"
STATE_PATH = RUNTIME_DIR / "procurement_supervisor_state.json"
PID_PATH = RUNTIME_DIR / "procurement_supervisor.pid"
OBSERVED_DOWNLOAD_SCRIPTS = (
    "download_all_sources.py",
    "download_raw_data.py",
    "download_resolver_safe_urls.py",
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class ProcurementTask:
    task_id: str
    priority: int
    description: str
    command: list[str]
    stdout_log: str
    stderr_log: str
    category: str
    notes: list[str] = field(default_factory=list)


def _coerce_text(value: Any) -> str:
    return str(value or "").strip()


def _matches_task_command(command_line: str, task: ProcurementTask) -> bool:
    normalized = command_line.casefold()
    command_tokens = task.command[1:]
    if not command_tokens:
        return False
    script_name = Path(command_tokens[0]).name.casefold()
    if script_name not in normalized:
        return False
    return all(_coerce_text(token).casefold() in normalized for token in command_tokens[1:])


def _is_download_command(command_line: str) -> bool:
    normalized = command_line.casefold()
    return any(script_name.casefold() in normalized for script_name in OBSERVED_DOWNLOAD_SCRIPTS)


def _run_process_table_probe(
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
        command_line = _coerce_text(item.get("CommandLine"))
        if not command_line or not _is_download_command(command_line):
            continue
        observations.append(
            {
                "pid": int(item.get("ProcessId") or 0),
                "name": _coerce_text(item.get("Name")),
                "command_line": command_line,
                "creation_date": _coerce_text(item.get("CreationDate")),
            }
        )
    return observations, "available"


def build_task_queue() -> list[ProcurementTask]:
    return [
        ProcurementTask(
            task_id="guarded_sources",
            priority=100,
            description="Download guarded-tier bulk sources (STRING and BioGRID).",
            command=[
                sys.executable,
                "protein_data_scope/download_all_sources.py",
                "--tiers",
                "guarded",
                "--dest",
                str(REPO_ROOT / "data" / "raw" / "protein_data_scope_seed"),
                "--timeout",
                "1800",
                "--retries",
                "4",
            ],
            stdout_log="guarded_procurement_stdout.log",
            stderr_log="guarded_procurement_stderr.log",
            category="bulk",
            notes=["highest-priority safe bulk tranche after direct tier"],
        ),
        ProcurementTask(
            task_id="packet_gap_accession_refresh",
            priority=95,
            description=(
                "Refresh the five deficit accessions across live "
                "accession-oriented sources."
            ),
            command=[
                sys.executable,
                "scripts/download_raw_data.py",
                "--accessions",
                "P00387,P09105,Q2TAC2,Q9NZD4,Q9UCM0",
                "--sources",
                "uniprot,alphafold,bindingdb,intact,rcsb_pdbe",
                "--allow-insecure-ssl",
                "--download-alphafold-assets",
                "--download-mmcif",
            ],
            stdout_log="packet_gap_refresh_stdout.log",
            stderr_log="packet_gap_refresh_stderr.log",
            category="targeted",
            notes=["targets the remaining packet-deficit accessions directly"],
        ),
        ProcurementTask(
            task_id="resolver_safe_bulk",
            priority=90,
            description=(
                "Download resolver-tier sources with direct bulk URLs "
                "that are already known and actionable."
            ),
            command=[
                sys.executable,
                "protein_data_scope/download_all_sources.py",
                "--sources",
                "alphafold_db",
                "intact",
                "bindingdb",
                "--allow-manual",
                "--dest",
                str(REPO_ROOT / "data" / "raw" / "protein_data_scope_seed"),
                "--timeout",
                "1800",
                "--retries",
                "4",
            ],
            stdout_log="resolver_safe_bulk_stdout.log",
            stderr_log="resolver_safe_bulk_stderr.log",
            category="bulk",
            notes=[
                "manual-review sources with explicit bulk URLs",
                "keeps resolver landing-page-only sources out of the auto queue",
            ],
        ),
        ProcurementTask(
            task_id="chembl_rnacentral_bulk",
            priority=88,
            description="Download newly pinned ChEMBL and RNAcentral bulk files.",
            command=[
                sys.executable,
                "protein_data_scope/download_all_sources.py",
                "--sources",
                "chembl",
                "rnacentral",
                "--allow-manual",
                "--extract",
                "--dest",
                str(REPO_ROOT / "data" / "raw" / "protein_data_scope_seed"),
                "--timeout",
                "1800",
                "--retries",
                "4",
            ],
            stdout_log="chembl_rnacentral_bulk_stdout.log",
            stderr_log="chembl_rnacentral_bulk_stderr.log",
            category="bulk",
            notes=[
                "uses pinned latest/current_release URLs only",
                "does not attempt RNAcentral BED or database-mapping fan-out",
            ],
        ),
        ProcurementTask(
            task_id="interpro_complexportal_resolver_small",
            priority=86,
            description="Download the safe small-file InterPro and Complex Portal resolver subset.",
            command=[
                sys.executable,
                "scripts/download_resolver_safe_urls.py",
                "--resolver-json",
                "artifacts/status/p28_interpro_complexportal_resolver.json",
                "--sources",
                "interpro",
                "complex_portal",
                "--dest",
                str(REPO_ROOT / "data" / "raw" / "protein_data_scope_seed"),
                "--timeout",
                "1800",
                "--retries",
                "4",
            ],
            stdout_log="interpro_complexportal_resolver_stdout.log",
            stderr_log="interpro_complexportal_resolver_stderr.log",
            category="resolver",
            notes=[
                "downloads only resolver-pinned safe URLs",
                "defers giant XML/tar payloads and oversized predicted archives",
            ],
        ),
        ProcurementTask(
            task_id="q9ucm0_refresh",
            priority=85,
            description="Refresh Q9UCM0 explicitly after the bulk/deficit waves.",
            command=[
                sys.executable,
                "scripts/download_raw_data.py",
                "--accessions",
                "Q9UCM0",
                "--sources",
                "uniprot,alphafold,bindingdb,intact,rcsb_pdbe",
                "--allow-insecure-ssl",
                "--download-alphafold-assets",
                "--download-mmcif",
            ],
            stdout_log="q9ucm0_refresh_stdout.log",
            stderr_log="q9ucm0_refresh_stderr.log",
            category="targeted",
            notes=["kept as a narrower explicit refresh in case broader deficit run exits first"],
        ),
    ]


def load_state() -> dict[str, Any]:
    task_ids = [task.task_id for task in build_task_queue()]
    if not STATE_PATH.exists():
        return {
            "generated_at": utc_now(),
            "status": "idle",
            "active": [],
            "observed_active": [],
            "stale_active": [],
            "completed": [],
            "failed": [],
            "pending": task_ids,
            "history": [],
            "observation_status": "unavailable",
            "handoff_required": False,
        }
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    loaded_active = list(state.get("active", []))
    if loaded_active:
        stale_active = list(state.get("stale_active", []))
        stale_active.extend(loaded_active)
        state["stale_active"] = stale_active
    state["active"] = []
    state["observed_active"] = list(state.get("observed_active", []))
    state["stale_active"] = list(state.get("stale_active", []))
    state["handoff_required"] = bool(state.get("handoff_required") or state["stale_active"])
    state.setdefault("observation_status", "unavailable")
    known_done = {
        str(item.get("task_id", ""))
        for item in state.get("completed", []) + state.get("failed", []) + state.get("active", [])
        if str(item.get("task_id", "")).strip()
    }
    pending = list(state.get("pending", []))
    for task_id in task_ids:
        if task_id not in pending and task_id not in known_done:
            pending.append(task_id)
    state["pending"] = pending
    return state


def save_state(state: dict[str, Any]) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def get_task_map() -> dict[str, ProcurementTask]:
    return {task.task_id: task for task in build_task_queue()}


def _find_active_index(active: list[dict[str, Any]], task_id: str) -> int | None:
    for index, item in enumerate(active):
        if str(item.get("task_id")) == task_id:
            return index
    return None


def start_task(task: ProcurementTask) -> dict[str, Any]:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    stdout_path = RUNTIME_DIR / task.stdout_log
    stderr_path = RUNTIME_DIR / task.stderr_log
    stdout_handle = stdout_path.open("a", encoding="utf-8")
    stderr_handle = stderr_path.open("a", encoding="utf-8")
    process = subprocess.Popen(
        task.command,
        cwd=REPO_ROOT,
        stdout=stdout_handle,
        stderr=stderr_handle,
        text=True,
    )
    return {
        "task_id": task.task_id,
        "description": task.description,
        "priority": task.priority,
        "category": task.category,
        "pid": process.pid,
        "started_at": utc_now(),
        "stdout_log": str(stdout_path.relative_to(REPO_ROOT)),
        "stderr_log": str(stderr_path.relative_to(REPO_ROOT)),
        "command": task.command,
        "_process": process,
        "_stdout_handle": stdout_handle,
        "_stderr_handle": stderr_handle,
    }


def finalize_task(entry: dict[str, Any], *, returncode: int) -> dict[str, Any]:
    result = {k: v for k, v in entry.items() if not k.startswith("_")}
    result["finished_at"] = utc_now()
    result["returncode"] = returncode
    result["status"] = "completed" if returncode == 0 else "failed"
    return result


def observe_live_download_jobs(
    *,
    probe: Callable[[], tuple[list[dict[str, Any]], str]] | None = None,
    task_map: dict[str, ProcurementTask] | None = None,
) -> dict[str, Any]:
    live_processes, observation_status = (probe or _run_process_table_probe)()
    task_map = task_map or get_task_map()
    observed: list[dict[str, Any]] = []
    for process in live_processes:
        command_line = str(process.get("command_line") or "")
        if not command_line or not _is_download_command(command_line):
            continue
        observed_task_id = ""
        for task in task_map.values():
            if _matches_task_command(command_line, task):
                observed_task_id = task.task_id
                break
        observed.append(
            {
                "pid": process.get("pid"),
                "name": process.get("name", ""),
                "command_line": command_line,
                "task_id": observed_task_id,
                "ownership": "observed_only",
                "observed_at": utc_now(),
            }
        )
    return {
        "status": observation_status,
        "observed_active": observed,
        "observed_pids": [item.get("pid") for item in observed if item.get("pid")],
    }


def refresh_active(state: dict[str, Any], *, processes: dict[str, dict[str, Any]]) -> None:
    active = list(state.get("active", []))
    still_active: list[dict[str, Any]] = []
    for entry in active:
        task_id = str(entry.get("task_id"))
        process_entry = processes.get(task_id)
        process = process_entry.get("_process") if process_entry else None
        if process is None:
            still_active.append(entry)
            continue
        returncode = process.poll()
        if returncode is None:
            still_active.append(entry)
            continue
        process_entry["_stdout_handle"].close()
        process_entry["_stderr_handle"].close()
        result = finalize_task(process_entry, returncode=returncode)
        state.setdefault("history", []).append(result)
        if returncode == 0:
            state.setdefault("completed", []).append(result)
        else:
            state.setdefault("failed", []).append(result)
        processes.pop(task_id, None)
    state["active"] = still_active


def reconcile_observed_active(state: dict[str, Any], observation: dict[str, Any]) -> None:
    observed_active = list(observation.get("observed_active", []))
    observed_pids = {int(item.get("pid") or 0) for item in observed_active if item.get("pid")}
    state["observed_active"] = observed_active
    state["observation_status"] = str(observation.get("status") or "unavailable")
    state["handoff_required"] = bool(state.get("stale_active") or observed_active)

    stale_active = list(state.get("stale_active", []))
    retained_active: list[dict[str, Any]] = []
    for entry in list(state.get("active", [])):
        pid = entry.get("pid")
        if pid is not None and int(pid) in observed_pids:
            retained_active.append(entry)
            continue
        stale_active.append(
            {
                **{k: v for k, v in entry.items() if not k.startswith("_")},
                "status": "stale",
                "handoff_reason": "no_live_handle",
            }
        )
    state["active"] = retained_active
    state["stale_active"] = stale_active
    if stale_active:
        state["handoff_required"] = True


def fill_slots(
    state: dict[str, Any],
    *,
    processes: dict[str, dict[str, Any]],
    max_parallel: int,
) -> None:
    if state.get("observation_status") == "unavailable":
        return
    if state.get("stale_active"):
        return
    task_map = get_task_map()
    pending_ids = list(state.get("pending", []))
    observed_count = len(state.get("observed_active", []))
    active_count = observed_count if observed_count else len(state.get("active", []))
    if active_count >= max_parallel:
        return
    sorted_pending = sorted(
        (task_map[task_id] for task_id in pending_ids if task_id in task_map),
        key=lambda task: (-task.priority, task.task_id),
    )
    while active_count < max_parallel and sorted_pending:
        task = sorted_pending.pop(0)
        if _find_active_index(state.get("active", []), task.task_id) is not None:
            continue
        entry = start_task(task)
        processes[task.task_id] = entry
        state.setdefault("active", []).append(
            {k: v for k, v in entry.items() if not k.startswith("_")}
        )
        state["pending"] = [
            task_id for task_id in state.get("pending", []) if task_id != task.task_id
        ]
        active_count += 1


def summarize_state(state: dict[str, Any]) -> dict[str, Any]:
    active_count = len(state.get("active", []))
    observed_count = len(state.get("observed_active", []))
    stale_count = len(state.get("stale_active", []))
    handoff_required = bool(state.get("handoff_required") or stale_count or observed_count)
    if state.get("observation_status") == "unavailable":
        if active_count or observed_count or stale_count or state.get("pending"):
            status = "stale"
        else:
            status = "idle"
    elif stale_count and (active_count > 0 or observed_count > 0):
        status = "running"
    elif stale_count or (observed_count and active_count == 0):
        status = "stale"
    elif active_count or state.get("pending"):
        status = "running"
    else:
        status = "idle"
    return {
        "generated_at": utc_now(),
        "status": status,
        "active_count": active_count,
        "observed_active_count": observed_count,
        "stale_active_count": stale_count,
        "pending_count": len(state.get("pending", [])),
        "completed_count": len(state.get("completed", [])),
        "failed_count": len(state.get("failed", [])),
        "active": state.get("active", []),
        "observed_active": state.get("observed_active", []),
        "stale_active": state.get("stale_active", []),
        "pending": state.get("pending", []),
        "completed_ids": [item.get("task_id") for item in state.get("completed", [])],
        "failed_ids": [item.get("task_id") for item in state.get("failed", [])],
        "observation_status": state.get("observation_status", "unavailable"),
        "handoff_required": handoff_required,
    }


def run_once(max_parallel: int) -> dict[str, Any]:
    state = load_state()
    state["generated_at"] = utc_now()
    processes: dict[str, dict[str, Any]] = {}
    refresh_active(state, processes=processes)
    observation = observe_live_download_jobs(task_map=get_task_map())
    reconcile_observed_active(state, observation)
    fill_slots(state, processes=processes, max_parallel=max_parallel)
    state["status"] = summarize_state(state)["status"]
    save_state(state)
    return summarize_state(state)


def loop(max_parallel: int, poll_seconds: int) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    PID_PATH.write_text(str(os.getpid()), encoding="utf-8")
    state = load_state()
    processes: dict[str, dict[str, Any]] = {}
    try:
        while True:
            refresh_active(state, processes=processes)
            observation = observe_live_download_jobs(task_map=get_task_map())
            reconcile_observed_active(state, observation)
            fill_slots(state, processes=processes, max_parallel=max_parallel)
            state["generated_at"] = utc_now()
            state["status"] = summarize_state(state)["status"]
            save_state(state)
            time.sleep(poll_seconds)
    finally:
        if PID_PATH.exists():
            PID_PATH.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description="Procurement download supervisor.")
    parser.add_argument("--once", action="store_true", help="Run one supervisor tick.")
    parser.add_argument("--loop", action="store_true", help="Run continuously.")
    parser.add_argument("--poll-seconds", type=int, default=30)
    parser.add_argument("--max-parallel", type=int, default=2)
    parser.add_argument("--json", action="store_true", help="Emit JSON summary.")
    args = parser.parse_args()

    if args.loop:
        loop(max_parallel=args.max_parallel, poll_seconds=args.poll_seconds)
        return 0

    summary = run_once(max_parallel=args.max_parallel)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
