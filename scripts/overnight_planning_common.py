from __future__ import annotations

import json
import re
import shlex
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.task_catalog import build_initial_queue

REPO_ROOT = Path(__file__).resolve().parents[1]
STATUS_DIR = REPO_ROOT / "artifacts" / "status"
RUNTIME_DIR = REPO_ROOT / "artifacts" / "runtime"
RUNTIME_CHECKPOINT_DIR = REPO_ROOT / "artifacts" / "runtime_checkpoints"


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise TypeError(f"expected JSON object at {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def normalize_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def source_row_map(source_coverage_matrix: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = source_coverage_matrix.get("matrix") or []
    return {
        str(row.get("normalized_name") or "").casefold(): row
        for row in rows
        if isinstance(row, dict) and str(row.get("normalized_name") or "").strip()
    }


def status_rank(status: str) -> int:
    order = {"implemented": 0, "partial": 1, "missing": 2}
    return order.get(str(status).casefold(), 3)


def parse_command_tokens(command_line: str) -> list[str]:
    try:
        return shlex.split(command_line, posix=False)
    except ValueError:
        return command_line.split()


def extract_flag_values(command_line: str, flag: str) -> list[str]:
    tokens = parse_command_tokens(command_line)
    if flag not in tokens:
        return []
    start = tokens.index(flag) + 1
    values: list[str] = []
    for token in tokens[start:]:
        if token.startswith("--"):
            break
        values.extend(part for part in token.split(",") if part)
    return [value.strip() for value in values if value.strip()]


def command_signature(command_line: str) -> str:
    normalized = str(command_line or "").strip()
    match = re.search(r"(download_all_sources\.py|download_raw_data\.py)", normalized, re.I)
    if not match:
        return normalized
    return normalized[match.start() :].strip()


def group_observed_active_jobs(
    observed_active: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for item in observed_active:
        if not isinstance(item, dict):
            continue
        raw_command = str(item.get("command_line") or "").strip()
        if not raw_command:
            continue
        sources = extract_flag_values(raw_command, "--sources")
        tiers = extract_flag_values(raw_command, "--tiers")
        files = extract_flag_values(raw_command, "--files")
        key = ",".join(sources or tiers or [command_signature(raw_command)])
        group = groups.setdefault(
            key,
            {
                "job_id": key,
                "source_kind": "observed_active",
                "job_state": "running",
                "rank_source": "observed_active",
                "source_keys": sources or tiers,
                "files": files,
                "pids": [],
                "pid_count": 0,
                "source_name": str(item.get("source_name") or "").strip(),
                "category": str(item.get("category") or "").strip(),
                "sample_command_signature": command_signature(raw_command),
                "priority": None,
                "phase": None,
                "type": "download",
                "title": (
                    f"Observed active {', '.join(sources or tiers or ['download'])}"
                ),
                "why_now": (
                    "Already active in the current supervisor snapshot; "
                    "keep it running without duplicate launches."
                ),
                "health_checkpoint": (
                    "Reconcile against artifacts/runtime/procurement_supervisor_state.json "
                    "before scheduling any duplicate download command."
                ),
            },
        )
        pid = item.get("pid")
        if pid is not None:
            group["pids"].append(int(pid))
        if not group["source_keys"]:
            group["source_keys"] = sources or tiers
        if not group["files"] and files:
            group["files"] = files
        if not group["source_name"] and str(item.get("source_name") or "").strip():
            group["source_name"] = str(item.get("source_name") or "").strip()
        if not group["category"] and str(item.get("category") or "").strip():
            group["category"] = str(item.get("category") or "").strip()
    rows = []
    for row in groups.values():
        row["pids"] = sorted(set(row["pids"]))
        row["pid_count"] = len(row["pids"])
        rows.append(row)
    rank_order = {"uniprot": 0, "string": 1}
    rows.sort(
        key=lambda row: (
            rank_order.get(str(row["job_id"]).casefold(), 99),
            row["job_id"].casefold(),
            -int(row["pid_count"] or 0),
            row["sample_command_signature"].casefold(),
        )
    )
    return rows


def task_to_dict(task: Any) -> dict[str, Any]:
    if isinstance(task, dict):
        return dict(task)
    if hasattr(task, "__dict__"):
        return dict(task.__dict__)
    return {}


def build_catalog_jobs(
    *,
    limit: int,
    excluded_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    excluded_ids = excluded_ids or set()
    tasks = build_initial_queue()
    rows: list[dict[str, Any]] = []
    for task in tasks:
        task_id = str(task.get("id") or "").strip()
        if not task_id or task_id in excluded_ids:
            continue
        files = [str(item) for item in task.get("files") or [] if str(item).strip()]
        text = " ".join(
            [
                task_id,
                str(task.get("title") or ""),
                str(task.get("type") or ""),
                " ".join(files),
                " ".join(str(item) for item in task.get("success_criteria") or []),
            ]
        ).casefold()
        if not any(
            token in text
            for token in (
                "scrape",
                "acquire",
                "export",
                "download",
                "probe",
                "validate",
                "materialize",
            )
        ) and not any(
            file_name.casefold().startswith(("scripts/export_", "execution/acquire/"))
            or file_name.casefold().startswith("scripts/validate_")
            or file_name.casefold().startswith("scripts/watch_")
            for file_name in files
        ):
            continue
        rows.append(
            {
                "job_id": task_id,
                "source_kind": "catalog",
                "job_state": str(task.get("status") or "pending").strip() or "pending",
                "rank_source": "catalog",
                "title": str(task.get("title") or "").strip(),
                "type": str(task.get("type") or "").strip(),
                "phase": int(task.get("phase") or 0),
                "priority": str(task.get("priority") or "").strip(),
                "files": files,
                "dependencies": normalize_list(task.get("dependencies")),
                "success_criteria": normalize_list(task.get("success_criteria")),
                "why_now": (
                    "High-priority backlog job with concrete file targets already "
                    "named in the task catalog."
                ),
                "health_checkpoint": (
                    "Do not schedule if the queue snapshot has already consumed or "
                    "completed this task id."
                ),
            }
        )
    priority_weight = {"high": 3, "medium": 2, "low": 1}
    rows.sort(
        key=lambda row: (
            -priority_weight.get(str(row.get("priority") or "").casefold(), 0),
            int(row.get("phase") or 0),
            str(row.get("job_id") or "").casefold(),
        )
    )
    return rows[:limit]


def load_runtime_state() -> dict[str, Any]:
    path = RUNTIME_DIR / "procurement_supervisor_state.json"
    return read_json(path)


def load_source_coverage_matrix() -> dict[str, Any]:
    return read_json(STATUS_DIR / "source_coverage_matrix.json")


def load_scrape_readiness_registry() -> dict[str, Any]:
    return read_json(STATUS_DIR / "scrape_readiness_registry_preview.json")


def load_procurement_status_board() -> dict[str, Any]:
    return read_json(STATUS_DIR / "procurement_status_board.json")


def load_live_bundle_validation() -> dict[str, Any]:
    return read_json(STATUS_DIR / "live_bundle_manifest_validation.json")


def count_statuses(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts = Counter(
        str(row.get(key) or "").casefold()
        for row in rows
        if isinstance(row, dict) and str(row.get(key) or "").strip()
    )
    return dict(sorted(counts.items()))
