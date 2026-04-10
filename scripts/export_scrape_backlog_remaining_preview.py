from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRAPE_GAP_MATRIX = REPO_ROOT / "artifacts" / "status" / "scrape_gap_matrix_preview.json"
DEFAULT_OVERNIGHT_QUEUE_BACKLOG = (
    REPO_ROOT / "artifacts" / "status" / "overnight_queue_backlog_preview.json"
)
DEFAULT_SCRAPE_EXECUTION_WAVE = (
    REPO_ROOT / "artifacts" / "status" / "scrape_execution_wave_preview.json"
)
DEFAULT_TARGETED_PAGE_SCRAPE_EXECUTION = (
    REPO_ROOT / "artifacts" / "status" / "targeted_page_scrape_execution_preview.json"
)
DEFAULT_PROCUREMENT_TAIL_FREEZE_GATE = (
    REPO_ROOT / "artifacts" / "status" / "procurement_tail_freeze_gate_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "scrape_backlog_remaining_preview.json"
)

STRUCTURED_FIRST_POLICY = "structured_first_then_page_then_tail_blocked"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_list(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, (str, bytes)):
        values = [values]
    seen: dict[str, str] = {}
    for value in values:
        text = _normalize_text(value)
        if text:
            seen.setdefault(text.casefold(), text)
    return list(seen.values())


def _row_map(rows: Any, *, key: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        identifier = _normalize_text(row.get(key))
        if identifier:
            indexed[identifier] = dict(row)
    return indexed


def _summary_int(*values: Any) -> int:
    for value in values:
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
    return 0


def _count_lane_states(scrape_gap_matrix: dict[str, Any]) -> tuple[int, int, int]:
    summary = scrape_gap_matrix.get("summary") or {}
    rows = scrape_gap_matrix.get("rows") or []
    row_states = Counter()
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_states[_normalize_text(row.get("lane_state"))] += 1
    implemented = _summary_int(summary.get("implemented_lane_count"), row_states.get("implemented"))
    partial = _summary_int(summary.get("partial_lane_count"), row_states.get("partial"))
    missing = _summary_int(summary.get("missing_lane_count"), row_states.get("missing"))
    return implemented, partial, missing


def _compact_job(row: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "job_id": _normalize_text(row.get("job_id")),
        "lane_id": _normalize_text(row.get("lane_id")),
        "job_category": _normalize_text(row.get("job_category")),
        "recommended_action": _normalize_text(row.get("recommended_action")),
        "blocked_by_tail": bool(row.get("blocked_by_tail")),
        "rank": row.get("rank"),
    }
    for key in (
        "lane_label",
        "lane_state",
        "default_ingest_status",
        "accession",
        "target_family",
        "why_now",
        "page_scraping_started",
        "blocked_by_files",
    ):
        value = row.get(key)
        if value not in (None, "", [], {}):
            payload[key] = value
    return payload


def _next_priority_jobs(scrape_execution_wave: dict[str, Any]) -> list[dict[str, Any]]:
    wave_rows = scrape_execution_wave.get("wave_order") or []
    compact_rows: list[dict[str, Any]] = []
    for row in wave_rows:
        if isinstance(row, dict):
            compact_rows.append(_compact_job(row))
    if compact_rows:
        return compact_rows[:8]
    if not compact_rows:
        for section in ("structured_jobs", "page_jobs", "tail_blocked_jobs"):
            for row in scrape_execution_wave.get(section) or []:
                if isinstance(row, dict):
                    compact_rows.append(_compact_job(row))
    compact_rows.sort(
        key=lambda row: (
            int(row.get("rank") or 999),
            _normalize_text(row.get("job_id")).casefold(),
            _normalize_text(row.get("lane_id")).casefold(),
        )
    )
    return compact_rows[:8]


def _tail_blocked_family_count(scrape_execution_wave: dict[str, Any]) -> int:
    family_ids = {
        _normalize_text(row.get("lane_id"))
        for row in scrape_execution_wave.get("tail_blocked_jobs") or []
        if isinstance(row, dict) and _normalize_text(row.get("lane_id"))
    }
    return len(family_ids)


def build_scrape_backlog_remaining_preview(
    scrape_gap_matrix: dict[str, Any],
    overnight_queue_backlog: dict[str, Any],
    scrape_execution_wave: dict[str, Any],
    targeted_page_scrape_execution: dict[str, Any],
    procurement_tail_freeze_gate: dict[str, Any],
) -> dict[str, Any]:
    implemented_count, partial_count, missing_count = _count_lane_states(scrape_gap_matrix)
    wave_summary = scrape_execution_wave.get("summary") or {}
    page_jobs = scrape_execution_wave.get("page_jobs") or []
    next_priority_jobs = _next_priority_jobs(scrape_execution_wave)

    page_scrape_ready_count = _summary_int(
        wave_summary.get("page_job_count"),
        len([row for row in page_jobs if isinstance(row, dict)]),
        len(targeted_page_scrape_execution.get("rows") or []),
    )

    queue_summary = overnight_queue_backlog.get("summary") or {}
    tail_summary = procurement_tail_freeze_gate.get("freeze_conditions") or {}

    return {
        "artifact_id": "scrape_backlog_remaining_preview",
        "schema_id": "proteosphere-scrape-backlog-remaining-preview-2026-04-03",
        "status": "report_only",
        "generated_at": (
            scrape_execution_wave.get("generated_at")
            or targeted_page_scrape_execution.get("generated_at")
            or procurement_tail_freeze_gate.get("generated_at")
            or datetime.now(UTC).isoformat()
        ),
        "summary": {
            "implemented_and_harvestable_now_count": implemented_count,
            "preview_or_report_only_count": partial_count + missing_count,
            "still_missing_count": missing_count,
            "tail_blocked_family_count": _tail_blocked_family_count(scrape_execution_wave),
            "page_scrape_ready_count": page_scrape_ready_count,
            "structured_first_policy": STRUCTURED_FIRST_POLICY,
            "active_download_count": _summary_int(
                procurement_tail_freeze_gate.get("active_file_count"),
                overnight_queue_backlog.get("active_job_count"),
            ),
            "remaining_gap_file_count": _summary_int(
                procurement_tail_freeze_gate.get("remaining_gap_file_count")
            ),
            "queue_active_now_count": _summary_int(
                queue_summary.get("active_now"),
                overnight_queue_backlog.get("summary", {}).get("lane_counts", {}).get("active_now"),
            ),
            "queue_supervisor_pending_count": _summary_int(
                queue_summary.get("supervisor_pending"),
                overnight_queue_backlog.get("summary", {})
                .get("lane_counts", {})
                .get("supervisor_pending"),
            ),
            "tail_gate_status": _normalize_text(
                procurement_tail_freeze_gate.get("gate_status")
            ),
            "tail_gate_blocked": not bool(tail_summary.get("remaining_gap_files_zero"))
            or not bool(tail_summary.get("not_yet_started_file_count_zero"))
            or not bool(tail_summary.get("string_complete"))
            or not bool(tail_summary.get("uniprot_complete")),
            "next_priority_job_count": len(next_priority_jobs),
        },
        "next_priority_jobs": next_priority_jobs,
        "source_artifacts": {
            "scrape_gap_matrix": str(DEFAULT_SCRAPE_GAP_MATRIX).replace("\\", "/"),
            "overnight_queue_backlog": str(DEFAULT_OVERNIGHT_QUEUE_BACKLOG).replace("\\", "/"),
            "scrape_execution_wave": str(DEFAULT_SCRAPE_EXECUTION_WAVE).replace("\\", "/"),
            "targeted_page_scrape_execution": str(
                DEFAULT_TARGETED_PAGE_SCRAPE_EXECUTION
            ).replace("\\", "/"),
            "procurement_tail_freeze_gate": str(
                DEFAULT_PROCUREMENT_TAIL_FREEZE_GATE
            ).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This backlog preview is report-only and fail-closed. It summarizes "
                "the remaining scrape work from existing artifacts without starting "
                "new scraping or mutating curated truth."
            ),
            "report_only": True,
            "non_mutating": True,
            "scraping_started": False,
            "tail_blocked": _tail_blocked_family_count(scrape_execution_wave) > 0,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a report-only scrape backlog remaining preview."
    )
    parser.add_argument("--scrape-gap-matrix", type=Path, default=DEFAULT_SCRAPE_GAP_MATRIX)
    parser.add_argument(
        "--overnight-queue-backlog", type=Path, default=DEFAULT_OVERNIGHT_QUEUE_BACKLOG
    )
    parser.add_argument(
        "--scrape-execution-wave", type=Path, default=DEFAULT_SCRAPE_EXECUTION_WAVE
    )
    parser.add_argument(
        "--targeted-page-scrape-execution",
        type=Path,
        default=DEFAULT_TARGETED_PAGE_SCRAPE_EXECUTION,
    )
    parser.add_argument(
        "--procurement-tail-freeze-gate",
        type=Path,
        default=DEFAULT_PROCUREMENT_TAIL_FREEZE_GATE,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_scrape_backlog_remaining_preview(
        _read_json(args.scrape_gap_matrix),
        _read_json(args.overnight_queue_backlog),
        _read_json(args.scrape_execution_wave),
        _read_json(args.targeted_page_scrape_execution),
        _read_json(args.procurement_tail_freeze_gate),
    )
    _write_json(args.output_json, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
