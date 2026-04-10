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

from scripts.tasklib import load_json, save_json  # noqa: E402

DEFAULT_PROCUREMENT_STATUS_BOARD_PATH = (
    REPO_ROOT / "artifacts" / "status" / "procurement_status_board.json"
)
DEFAULT_REMAINING_TRANSFER_STATUS_PATH = (
    REPO_ROOT / "artifacts" / "status" / "broad_mirror_remaining_transfer_status.json"
)
DEFAULT_PROCUREMENT_PROCESS_DIAGNOSTICS_PATH = (
    REPO_ROOT / "artifacts" / "status" / "procurement_process_diagnostics_preview.json"
)
DEFAULT_PROCUREMENT_SUPERVISOR_STATE_PATH = (
    REPO_ROOT / "artifacts" / "runtime" / "procurement_supervisor_state.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "procurement_tail_signal_reconciliation_preview.json"
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _load_json_or_default(path: Path, default: Any) -> Any:
    return load_json(path, default) if path.exists() else default


def _normalize_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _coerce_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _tail_ids(rows: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    for row in rows:
        source_id = str(row.get("task_id") or row.get("source_id") or "").strip()
        filename = str(row.get("filename") or row.get("description") or "").strip()
        token = source_id or filename
        if token:
            ids.append(token)
    return sorted(set(ids))


def build_procurement_tail_signal_reconciliation_preview(
    board: dict[str, Any],
    remaining_transfer_status: dict[str, Any],
    process_diagnostics: dict[str, Any],
    supervisor_state: dict[str, Any],
    *,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    observed_at = observed_at or _utc_now()
    board = board if isinstance(board, dict) else {}
    remaining_transfer_status = (
        remaining_transfer_status if isinstance(remaining_transfer_status, dict) else {}
    )
    process_diagnostics = (
        process_diagnostics if isinstance(process_diagnostics, dict) else {}
    )
    supervisor_state = supervisor_state if isinstance(supervisor_state, dict) else {}

    board_supervisor = (
        board.get("procurement_supervisor")
        if isinstance(board.get("procurement_supervisor"), dict)
        else {}
    )
    board_summary = board.get("summary") if isinstance(board.get("summary"), dict) else {}
    remaining_summary = (
        remaining_transfer_status.get("summary")
        if isinstance(remaining_transfer_status.get("summary"), dict)
        else {}
    )
    diagnostics_summary = (
        process_diagnostics.get("summary")
        if isinstance(process_diagnostics.get("summary"), dict)
        else {}
    )

    board_active_count = _coerce_int(
        board_supervisor.get("active_observed_download_count")
        or board_summary.get("active_observed_download_count")
    )
    remaining_active_count = _coerce_int(remaining_summary.get("active_file_count"))
    diagnostics_authoritative_count = _coerce_int(
        diagnostics_summary.get("authoritative_tail_file_count")
    )
    raw_process_count = _coerce_int(diagnostics_summary.get("raw_process_table_active_count"))
    raw_duplicate_count = _coerce_int(
        diagnostics_summary.get("raw_process_table_duplicate_count")
    )
    stale_supervisor_pending_count = len(supervisor_state.get("pending") or [])
    stale_supervisor_status = str(supervisor_state.get("status") or "missing")

    board_rows = _normalize_rows(board_supervisor.get("active_observed_downloads"))
    diagnostics_rows = _normalize_rows(process_diagnostics.get("authoritative_tail_files"))
    active_tail_ids = _tail_ids(diagnostics_rows or board_rows)

    authoritative_counts = {
        "board": board_active_count,
        "remaining_transfer": remaining_active_count,
        "process_diagnostics": diagnostics_authoritative_count,
    }
    authoritative_count_values = {count for count in authoritative_counts.values() if count > 0}
    authoritative_counts_aligned = len(authoritative_count_values) <= 1 and len(
        authoritative_count_values
    ) > 0

    if authoritative_counts_aligned and stale_supervisor_status == "stale":
        reconciliation_state = "authoritative_tail_aligned_with_legacy_stale_signal"
        next_action = (
            "Trust the aligned board, remaining-transfer, and process-diagnostics counts "
            "for the live tail, and treat the stale supervisor-state file as legacy context."
        )
    elif authoritative_counts_aligned:
        reconciliation_state = "authoritative_tail_aligned"
        next_action = "Keep the aligned tail counts as the current procurement truth."
    else:
        reconciliation_state = "tail_signal_drift_requires_review"
        next_action = (
            "Inspect the procurement board, remaining-transfer, and diagnostics exports "
            "before relying on the tail count."
        )

    rows = [
        {
            "signal_source": "procurement_status_board",
            "active_count": board_active_count,
            "status": str(board.get("status") or ""),
            "observed_active_source": str(board_supervisor.get("observed_active_source") or ""),
            "tail_ids": _tail_ids(board_rows),
            "note": "Authoritative board count for live remaining downloads.",
        },
        {
            "signal_source": "remaining_transfer_status",
            "active_count": remaining_active_count,
            "status": str(remaining_transfer_status.get("status") or ""),
            "remaining_source_count": _coerce_int(remaining_summary.get("remaining_source_count")),
            "note": "Authoritative gap-file transfer summary for the broad mirror tail.",
        },
        {
            "signal_source": "procurement_process_diagnostics_preview",
            "active_count": diagnostics_authoritative_count,
            "raw_process_table_active_count": raw_process_count,
            "raw_process_table_duplicate_count": raw_duplicate_count,
            "tail_ids": _tail_ids(diagnostics_rows),
            "note": "Cross-check between authoritative tail files and raw process-table noise.",
        },
        {
            "signal_source": "procurement_supervisor_state",
            "status": stale_supervisor_status,
            "pending_count": stale_supervisor_pending_count,
            "observed_active_count": len(_normalize_rows(supervisor_state.get("observed_active"))),
            "note": "Legacy persisted supervisor-state signal kept only for reconciliation.",
        },
    ]

    return {
        "artifact_id": "procurement_tail_signal_reconciliation_preview",
        "schema_id": "proteosphere-procurement-tail-signal-reconciliation-preview-2026-04-03",
        "status": "report_only",
        "generated_at": observed_at.isoformat(),
        "summary": {
            "reconciliation_state": reconciliation_state,
            "authoritative_tail_file_count": max(authoritative_count_values or {0}),
            "board_active_observed_download_count": board_active_count,
            "remaining_transfer_active_file_count": remaining_active_count,
            "diagnostics_authoritative_tail_file_count": diagnostics_authoritative_count,
            "raw_process_table_active_count": raw_process_count,
            "raw_process_table_duplicate_count": raw_duplicate_count,
            "stale_supervisor_status": stale_supervisor_status,
            "stale_supervisor_pending_count": stale_supervisor_pending_count,
            "authoritative_counts_aligned": authoritative_counts_aligned,
            "active_tail_ids": active_tail_ids,
            "row_count": len(rows),
            "non_mutating": True,
            "report_only": True,
        },
        "rows": rows,
        "next_suggested_action": next_action,
        "source_artifacts": {
            "procurement_status_board": str(DEFAULT_PROCUREMENT_STATUS_BOARD_PATH).replace(
                "\\", "/"
            ),
            "remaining_transfer_status": str(DEFAULT_REMAINING_TRANSFER_STATUS_PATH).replace(
                "\\", "/"
            ),
            "procurement_process_diagnostics_preview": str(
                DEFAULT_PROCUREMENT_PROCESS_DIAGNOSTICS_PATH
            ).replace("\\", "/"),
            "procurement_supervisor_state": str(
                DEFAULT_PROCUREMENT_SUPERVISOR_STATE_PATH
            ).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only reconciliation surface for procurement-tail signals. "
                "It compares board truth, remaining-transfer truth, process diagnostics, "
                "and legacy supervisor-state noise without mutating procurement state."
            ),
            "report_only": True,
            "non_mutating": True,
            "authoritative_primary_truth": "board_and_remaining_transfer_status",
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a report-only procurement tail signal reconciliation preview."
    )
    parser.add_argument(
        "--procurement-status-board-path",
        type=Path,
        default=DEFAULT_PROCUREMENT_STATUS_BOARD_PATH,
    )
    parser.add_argument(
        "--remaining-transfer-status-path",
        type=Path,
        default=DEFAULT_REMAINING_TRANSFER_STATUS_PATH,
    )
    parser.add_argument(
        "--procurement-process-diagnostics-path",
        type=Path,
        default=DEFAULT_PROCUREMENT_PROCESS_DIAGNOSTICS_PATH,
    )
    parser.add_argument(
        "--procurement-supervisor-state-path",
        type=Path,
        default=DEFAULT_PROCUREMENT_SUPERVISOR_STATE_PATH,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_procurement_tail_signal_reconciliation_preview(
        _load_json_or_default(args.procurement_status_board_path, {}),
        _load_json_or_default(args.remaining_transfer_status_path, {}),
        _load_json_or_default(args.procurement_process_diagnostics_path, {}),
        _load_json_or_default(args.procurement_supervisor_state_path, {}),
    )
    save_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
