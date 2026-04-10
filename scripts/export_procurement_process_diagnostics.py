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
DEFAULT_PROCUREMENT_STATUS_BOARD_PATH = (
    REPO_ROOT / "artifacts" / "status" / "procurement_status_board.json"
)
DEFAULT_DOWNLOAD_LOCATION_AUDIT_PATH = (
    REPO_ROOT / "artifacts" / "status" / "download_location_audit_preview.json"
)
DEFAULT_PROCUREMENT_SOURCE_COMPLETION_PATH = (
    REPO_ROOT / "artifacts" / "status" / "procurement_source_completion_preview.json"
)
DEFAULT_REMAINING_TRANSFER_STATUS_PATH = (
    REPO_ROOT / "artifacts" / "status" / "broad_mirror_remaining_transfer_status.json"
)
DEFAULT_OUTPUT_PATH = (
    REPO_ROOT / "artifacts" / "status" / "procurement_process_diagnostics_preview.json"
)
DEFAULT_MARKDOWN_OUTPUT_PATH = (
    REPO_ROOT / "docs" / "reports" / "procurement_process_diagnostics_preview.md"
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
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _normalize_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _is_download_command(command_line: str) -> bool:
    normalized = _normalize_text(command_line).casefold()
    return any(script.casefold() in normalized for script in OBSERVED_DOWNLOAD_SCRIPTS)


def _command_signature(command_line: str) -> str:
    normalized = _normalize_text(command_line)
    if not normalized:
        return ""
    for script in OBSERVED_DOWNLOAD_SCRIPTS:
        marker = script.casefold()
        index = normalized.casefold().find(marker)
        if index >= 0:
            normalized = normalized[index:]
            break
    return " ".join(normalized.split())


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
        command_line = _normalize_text(item.get("CommandLine"))
        if not command_line or not _is_download_command(command_line):
            continue
        observations.append(
            {
                "pid": int(item.get("ProcessId") or 0),
                "name": _normalize_text(item.get("Name")),
                "command_line": command_line,
                "creation_date": _normalize_text(item.get("CreationDate")),
            }
        )
    return observations, "available"


def _authoritative_tail_files(
    download_location_audit: dict[str, Any] | None,
    source_completion: dict[str, Any] | None,
    board: dict[str, Any] | None,
    remaining_transfer_status: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    download_location_audit = (
        download_location_audit if isinstance(download_location_audit, dict) else {}
    )
    source_completion = source_completion if isinstance(source_completion, dict) else {}
    board = board if isinstance(board, dict) else {}
    remaining_transfer_status = (
        remaining_transfer_status if isinstance(remaining_transfer_status, dict) else {}
    )
    audit_rows = _normalize_rows(download_location_audit.get("rows"))
    if audit_rows:
        authoritative_from_audit: list[dict[str, Any]] = []
        source_index = (
            source_completion.get("source_completion_index")
            if isinstance(source_completion.get("source_completion_index"), dict)
            else {}
        )
        for row in audit_rows:
            state = _normalize_text(row.get("state"))
            if state not in {"in_process", "downloaded_and_in_process"}:
                continue
            source_id = _normalize_text(row.get("source_id"))
            source_row = (
                source_index.get(source_id.casefold(), {})
                if source_id
                else {}
            )
            authoritative_from_audit.append(
                {
                    "source": "download_location_audit_preview",
                    "source_id": row.get("source_id"),
                    "source_name": row.get("source_name"),
                    "filename": row.get("filename"),
                    "category": row.get("category"),
                    "gap_kind": "in_process",
                    "status": "running",
                    "pid": None,
                    "primary_live_path": row.get("primary_location"),
                    "completion_status": source_row.get("completion_status") or state,
                }
            )
        if authoritative_from_audit:
            return authoritative_from_audit

    board_supervisor = (
        board.get("procurement_supervisor")
        if isinstance(board.get("procurement_supervisor"), dict)
        else {}
    )

    authoritative_rows = _normalize_rows(board_supervisor.get("active_observed_downloads"))
    if authoritative_rows and any(
        _normalize_text(row.get("task_id"))
        or _normalize_text(row.get("source_id"))
        or _normalize_text(row.get("filename"))
        or _normalize_text(row.get("description"))
        or _normalize_text(row.get("source_name"))
        for row in authoritative_rows
    ):
        return [
            {
                "source": "procurement_status_board",
                "source_id": row.get("task_id") or row.get("source_id"),
                "source_name": row.get("source_name"),
                "filename": row.get("filename") or row.get("description"),
                "category": row.get("category"),
                "gap_kind": row.get("gap_kind") or "partial",
                "status": row.get("status") or "running",
                "pid": row.get("pid"),
            }
            for row in authoritative_rows
        ]

    remaining_sources = _normalize_rows(remaining_transfer_status.get("remaining_sources"))
    if remaining_sources:
        return [
            {
                "source": "remaining_transfer_status",
                "source_id": row.get("source_id"),
                "source_name": row.get("source_name"),
                "filename": row.get("representative_partial_files", [None])[0]
                or row.get("representative_missing_files", [None])[0],
                "category": row.get("category"),
                "gap_kind": row.get("status") or "partial",
                "status": row.get("status") or "partial",
                "pid": None,
            }
            for row in remaining_sources
        ]

    gap_files = _normalize_rows(remaining_transfer_status.get("gap_files"))
    return [
        {
            "source": "remaining_transfer_status",
            "source_id": row.get("source_id"),
            "source_name": row.get("source_name"),
            "filename": row.get("filename"),
            "category": row.get("category"),
            "gap_kind": row.get("gap_kind"),
            "status": "running",
            "pid": None,
        }
        for row in gap_files
    ]


def _group_raw_processes(processes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for process in processes:
        signature = _command_signature(process.get("command_line")) or _normalize_text(
            process.get("name")
        )
        grouped.setdefault(signature, []).append(process)

    rows: list[dict[str, Any]] = []
    for signature, items in grouped.items():
        pids = sorted(
            {
                int(item.get("pid") or 0)
                for item in items
                if int(item.get("pid") or 0) > 0
            }
        )
        rows.append(
            {
                "signature": signature,
                "process_count": len(items),
                "duplicate_process_count": max(len(items) - 1, 0),
                "pids": pids,
                "command_line": items[0].get("command_line"),
                "names": sorted(
                    {
                        _normalize_text(item.get("name"))
                        for item in items
                        if _normalize_text(item.get("name"))
                    }
                ),
            }
        )

    rows.sort(
        key=lambda row: (
            -int(row.get("process_count") or 0),
            _normalize_text(row.get("signature")).casefold(),
        )
    )
    return rows


def build_procurement_process_diagnostics(
    download_location_audit: dict[str, Any],
    source_completion: dict[str, Any],
    board: dict[str, Any],
    remaining_transfer_status: dict[str, Any],
    *,
    process_probe: Callable[[], tuple[list[dict[str, Any]], str]] | None = None,
) -> dict[str, Any]:
    board = board if isinstance(board, dict) else {}
    remaining_transfer_status = (
        remaining_transfer_status if isinstance(remaining_transfer_status, dict) else {}
    )
    board_supervisor = (
        board.get("procurement_supervisor")
        if isinstance(board.get("procurement_supervisor"), dict)
        else {}
    )
    remaining_summary = (
        remaining_transfer_status.get("summary")
        if isinstance(remaining_transfer_status.get("summary"), dict)
        else {}
    )
    remaining_sources = _normalize_rows(remaining_transfer_status.get("remaining_sources"))
    gap_files = _normalize_rows(remaining_transfer_status.get("gap_files"))

    authoritative_tail_files = _authoritative_tail_files(
        download_location_audit,
        source_completion,
        board,
        remaining_transfer_status,
    )
    raw_processes, observation_status = (
        process_probe or _probe_live_download_processes
    )()
    raw_processes = [
        {
            "pid": int(row.get("pid") or 0),
            "name": _normalize_text(row.get("name")),
            "command_line": _normalize_text(row.get("command_line")),
            "creation_date": _normalize_text(row.get("creation_date")),
        }
        for row in raw_processes
        if isinstance(row, dict)
        and _normalize_text(row.get("command_line"))
        and _is_download_command(_normalize_text(row.get("command_line")))
    ]
    grouped_processes = _group_raw_processes(raw_processes)

    raw_process_count = len(raw_processes)
    unique_signature_count = len(grouped_processes)
    duplicate_process_count = sum(
        int(row.get("duplicate_process_count") or 0) for row in grouped_processes
    )

    authoritative_sources = Counter(
        _normalize_text(row.get("source_id")) or "unknown" for row in authoritative_tail_files
    )

    return {
        "artifact_id": "procurement_process_diagnostics_preview",
        "schema_id": "proteosphere-procurement-process-diagnostics-preview-2026-04-03",
        "status": board.get("status") or remaining_transfer_status.get("status") or "attention",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "board_status": board.get("status"),
            "board_observed_active_source": board_supervisor.get("observed_active_source"),
            "remaining_transfer_status": remaining_transfer_status.get("status"),
            "remaining_transfer_active_file_count": int(
                remaining_summary.get("active_file_count") or 0
            ),
            "remaining_transfer_total_gap_files": int(
                remaining_summary.get("total_gap_files")
                or remaining_summary.get("active_file_count")
                or len(remaining_sources)
                or len(gap_files)
            ),
            "authoritative_tail_file_count": len(authoritative_tail_files),
            "authoritative_source_counts": dict(sorted(authoritative_sources.items())),
            "raw_process_table_active_count": raw_process_count,
            "raw_process_table_unique_signature_count": unique_signature_count,
            "raw_process_table_duplicate_count": duplicate_process_count,
            "raw_process_table_observation_status": observation_status,
            "authoritative_board_count": len(
                _normalize_rows(board_supervisor.get("active_observed_downloads"))
            ),
        },
        "authoritative_tail_files": authoritative_tail_files,
        "raw_process_table_observations": raw_processes,
        "raw_process_table_duplicate_groups": grouped_processes,
        "comparison": {
            "authoritative_files_preferred": True,
            "raw_process_excess": max(raw_process_count - len(authoritative_tail_files), 0),
            "raw_duplicate_processes": duplicate_process_count,
            "raw_duplicate_signature_groups": [
                row for row in grouped_processes if int(row.get("duplicate_process_count") or 0) > 0
            ],
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only procurement diagnostics view. The "
                "authoritative tail files come from the overflow-aware download "
                "location audit; raw process-table observations are "
                "diagnostic only."
            ),
            "report_only": True,
            "non_mutating": True,
            "authoritative_primary_truth": "download_location_audit_preview",
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# Procurement Process Diagnostics Preview",
        "",
        f"- Board status: `{summary.get('board_status')}`",
        f"- Remaining transfer status: `{summary.get('remaining_transfer_status')}`",
        f"- Authoritative tail files: `{summary.get('authoritative_tail_file_count')}`",
        f"- Raw process-table count: `{summary.get('raw_process_table_active_count')}`",
        f"- Raw duplicate processes: `{summary.get('raw_process_table_duplicate_count')}`",
        "",
        "## Authoritative Tail Files",
        "",
    ]
    for row in payload.get("authoritative_tail_files") or []:
        lines.append(
            f"- `{row.get('source_id')}`: `{row.get('filename')}` "
            f"from `{row.get('source')}`"
        )
    if not payload.get("authoritative_tail_files"):
        lines.append("- None detected")

    lines.extend(["", "## Raw Duplicate Processes", ""])
    for row in payload.get("raw_process_table_duplicate_groups") or []:
        lines.append(
            f"- `{row.get('process_count')}` x `{row.get('signature')}` "
            f"(duplicates: `{row.get('duplicate_process_count')}`)"
        )
    if not payload.get("raw_process_table_duplicate_groups"):
        lines.append("- None detected")

    lines.extend(["", "## Comparison", ""])
    comparison = payload.get("comparison") or {}
    lines.append(
        f"- Authoritative files preferred: `{comparison.get('authoritative_files_preferred')}`"
    )
    lines.append(f"- Raw duplicate processes: `{comparison.get('raw_duplicate_processes')}`")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export procurement process diagnostics preview."
    )
    parser.add_argument(
        "--download-location-audit",
        type=Path,
        default=DEFAULT_DOWNLOAD_LOCATION_AUDIT_PATH,
    )
    parser.add_argument(
        "--procurement-source-completion",
        type=Path,
        default=DEFAULT_PROCUREMENT_SOURCE_COMPLETION_PATH,
    )
    parser.add_argument(
        "--procurement-status-board",
        type=Path,
        default=DEFAULT_PROCUREMENT_STATUS_BOARD_PATH,
    )
    parser.add_argument(
        "--remaining-transfer-status",
        type=Path,
        default=DEFAULT_REMAINING_TRANSFER_STATUS_PATH,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MARKDOWN_OUTPUT_PATH)
    parser.add_argument("--no-markdown", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_procurement_process_diagnostics(
        _read_json(args.download_location_audit),
        _read_json(args.procurement_source_completion),
        _read_json(args.procurement_status_board),
        _read_json(args.remaining_transfer_status),
    )
    _write_json(args.output_json, payload)
    if not args.no_markdown:
        _write_text(args.output_md, render_markdown(payload))
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
