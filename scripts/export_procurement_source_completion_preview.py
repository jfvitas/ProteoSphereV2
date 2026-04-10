from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.web_enrichment_preview_support import read_json, write_json, write_text
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from web_enrichment_preview_support import read_json, write_json, write_text

DEFAULT_DOWNLOAD_LOCATION_AUDIT = (
    REPO_ROOT / "artifacts" / "status" / "download_location_audit_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "procurement_source_completion_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "procurement_source_completion_preview.md"
)


def _normalize_rows(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    return [item for item in values if isinstance(item, dict)]


def _casefold(value: Any) -> str:
    return str(value or "").strip().casefold()


def _normalize_path_entries(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        for location in _normalize_rows(row.get(key)):
            path_text = str(location.get("path") or "").strip()
            if not path_text:
                continue
            normalized = path_text.replace("\\", "/")
            if normalized in seen:
                continue
            seen.add(normalized)
            entries.append(
                {
                    "path": normalized,
                    "size_bytes": location.get("size_bytes"),
                    "last_write_time": location.get("last_write_time"),
                }
            )
    return entries


def _source_completion_entry(
    source_id: str,
    source_summary: dict[str, Any],
    source_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    downloaded_count = sum(1 for row in source_rows if row.get("state") == "downloaded")
    in_process_count = sum(
        1
        for row in source_rows
        if row.get("state") in {"in_process", "downloaded_and_in_process"}
    )
    missing_count = sum(1 for row in source_rows if row.get("state") == "missing")
    completion_status = (
        "complete"
        if missing_count == 0 and in_process_count == 0
        else "active"
        if missing_count == 0 and in_process_count > 0
        else "missing"
    )

    final_locations = _normalize_path_entries(source_rows, "final_locations")
    in_process_locations = _normalize_path_entries(source_rows, "in_process_locations")
    failed_snapshot_locations = _normalize_path_entries(
        source_rows, "failed_snapshot_locations"
    )
    primary_root = str(source_summary.get("primary_root") or "").replace("\\", "/")
    non_primary_final_locations = [
        location
        for location in final_locations
        if not str(location.get("path") or "").startswith(primary_root)
    ]

    primary_live_location = None
    if in_process_locations:
        primary_live_location = in_process_locations[0]["path"]
    elif non_primary_final_locations:
        primary_live_location = non_primary_final_locations[0]["path"]
    elif final_locations:
        primary_live_location = final_locations[0]["path"]
    completed_off_primary_root = (
        completion_status == "complete"
        and bool(non_primary_final_locations)
    )
    authority_note = (
        "completed_off_primary_root_intentionally_authoritative"
        if completed_off_primary_root
        else "primary_or_in_process_location_authoritative"
    )

    return {
        "source_id": source_id,
        "source_name": source_summary.get("source_name"),
        "category": source_summary.get("category"),
        "expected_file_count": source_summary.get("expected_file_count"),
        "downloaded_count": downloaded_count,
        "in_process_count": in_process_count,
        "missing_count": missing_count,
        "completion_status": completion_status,
        "ready_to_materialize": completion_status == "complete",
        "source_state": source_summary.get("source_state"),
        "primary_root": source_summary.get("primary_root"),
        "overflow_root": source_summary.get("overflow_root"),
        "primary_live_path": primary_live_location,
        "final_locations": final_locations,
        "in_process_locations": in_process_locations,
        "failed_snapshot_locations": failed_snapshot_locations,
        "has_failed_snapshot": bool(failed_snapshot_locations),
        "completed_off_primary_root": completed_off_primary_root,
        "authority_note": authority_note,
        "authority": "download_location_audit_preview",
        "rows": [
            {
                "filename": row.get("filename"),
                "state": row.get("state"),
                "primary_location": row.get("primary_location"),
                "accounted_for": row.get("accounted_for"),
            }
            for row in source_rows
        ],
    }


def build_procurement_source_completion_preview(
    download_location_audit_preview: dict[str, Any],
) -> dict[str, Any]:
    source_summaries = [
        row
        for row in _normalize_rows(download_location_audit_preview.get("source_summaries"))
        if _casefold(row.get("source_id"))
    ]
    rows = _normalize_rows(download_location_audit_preview.get("rows"))

    rows_by_source: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        source_id = _casefold(row.get("source_id"))
        if not source_id:
            continue
        rows_by_source.setdefault(source_id, []).append(row)

    source_completion: list[dict[str, Any]] = []
    for source_summary in source_summaries:
        source_id = _casefold(source_summary.get("source_id"))
        source_rows = rows_by_source.get(source_id, [])
        source_completion.append(
            _source_completion_entry(source_id, source_summary, source_rows)
        )

    source_completion.sort(key=lambda row: row["source_id"])
    indexed = {row["source_id"]: row for row in source_completion}
    string_entry = indexed.get("string", {})
    uniprot_entry = indexed.get("uniprot", {})

    return {
        "artifact_id": "procurement_source_completion_preview",
        "schema_id": "proteosphere-procurement-source-completion-preview-2026-04-05",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "authority": "download_location_audit_preview",
        "tracked_sources": ["string", "uniprot"],
        "string_completion_status": string_entry.get("completion_status"),
        "string_completion_ready": string_entry.get("ready_to_materialize", False),
        "uniprot_completion_status": uniprot_entry.get("completion_status"),
        "uniprot_completion_ready": uniprot_entry.get("ready_to_materialize", False),
        "source_completion": source_completion,
        "source_completion_index": indexed,
        "truth_boundary": {
            "summary": (
                "This is a report-only per-source completion view derived from "
                "download_location_audit_preview. It distinguishes STRING and UniRef "
                "completion independently and does not mutate procurement state."
            ),
            "report_only": True,
            "non_mutating": True,
            "authority": "download_location_audit_preview",
        },
        "next_suggested_action": (
            "Treat STRING and UniRef as complete when their final files are present in the "
            "authority locations exposed here, including intentional overflow authority on C:."
        ),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Procurement Source Completion Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- STRING: `{payload.get('string_completion_status')}`",
        f"- UniRef: `{payload.get('uniprot_completion_status')}`",
        "",
        "## Source Completion",
        "",
    ]
    for row in payload.get("source_completion") or []:
        lines.append(
            f"- `{row['source_id']}` / `{row['completion_status']}` / "
            f"`{row.get('primary_live_path')}`"
        )
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a report-only per-source procurement completion preview."
    )
    parser.add_argument(
        "--download-location-audit",
        type=Path,
        default=DEFAULT_DOWNLOAD_LOCATION_AUDIT,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_procurement_source_completion_preview(
        read_json(args.download_location_audit),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
