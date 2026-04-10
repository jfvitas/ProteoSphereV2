from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BROAD_MIRROR_PROGRESS = (
    REPO_ROOT / "artifacts" / "status" / "broad_mirror_progress.json"
)
DEFAULT_REMAINING_GAPS = (
    REPO_ROOT / "artifacts" / "status" / "broad_mirror_remaining_gaps.json"
)
DEFAULT_REMAINING_TRANSFER_STATUS = (
    REPO_ROOT / "artifacts" / "status" / "broad_mirror_remaining_transfer_status.json"
)
DEFAULT_SOURCE_COMPLETION = (
    REPO_ROOT / "artifacts" / "status" / "procurement_source_completion_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "procurement_tail_freeze_gate_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "procurement_tail_freeze_gate_preview.md"
)

TRACKED_SOURCES = ("string", "uniprot")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _source_status_lookup(progress: dict[str, Any]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for row in progress.get("sources") or []:
        if not isinstance(row, dict):
            continue
        source_id = str(row.get("source_id") or "").strip()
        if source_id:
            lookup[source_id] = str(row.get("status") or "").strip()
    return lookup


def _tracked_gap_files(remaining_gaps: dict[str, Any]) -> list[dict[str, Any]]:
    tracked: list[dict[str, Any]] = []
    for row in remaining_gaps.get("gap_files") or []:
        if not isinstance(row, dict):
            continue
        source_id = str(row.get("source_id") or "").strip()
        if source_id in TRACKED_SOURCES:
            tracked.append(dict(row))
    return tracked


def build_procurement_tail_freeze_gate_preview(
    broad_mirror_progress: dict[str, Any],
    remaining_gaps: dict[str, Any],
    remaining_transfer_status: dict[str, Any],
    source_completion: dict[str, Any],
) -> dict[str, Any]:
    progress_summary = broad_mirror_progress.get("summary") or {}
    gap_summary = remaining_gaps.get("summary") or {}
    transfer_summary = remaining_transfer_status.get("summary") or {}
    source_status_lookup = _source_status_lookup(broad_mirror_progress)
    tracked_gap_files = _tracked_gap_files(remaining_gaps)

    remaining_gap_files = int(gap_summary.get("total_gap_files") or len(tracked_gap_files))
    not_yet_started_file_count = int(
        transfer_summary.get("not_yet_started_file_count") or 0
    )
    string_complete = bool(source_completion.get("string_completion_ready"))
    uniprot_complete = bool(source_completion.get("uniprot_completion_ready"))

    freeze_ready = (
        remaining_gap_files == 0
        and not_yet_started_file_count == 0
        and string_complete
        and uniprot_complete
    )

    return {
        "artifact_id": "procurement_tail_freeze_gate_preview",
        "schema_id": "proteosphere-procurement-tail-freeze-gate-preview-2026-04-02",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "gate_status": (
            "ready_to_freeze_complete_mirror"
            if freeze_ready
            else "blocked_pending_zero_gap"
        ),
        "tracked_sources": list(TRACKED_SOURCES),
        "broad_mirror_coverage_percent": progress_summary.get("file_coverage_percent"),
        "remaining_gap_file_count": remaining_gap_files,
        "active_file_count": int(transfer_summary.get("active_file_count") or 0),
        "not_yet_started_file_count": not_yet_started_file_count,
        "tracked_gap_files": [
            {
                "source_id": row.get("source_id"),
                "filename": row.get("filename"),
                "gap_kind": row.get("gap_kind"),
            }
            for row in tracked_gap_files
        ],
        "source_statuses": {
            "string": source_completion.get("string_completion_status")
            or source_status_lookup.get("string"),
            "uniprot": source_completion.get("uniprot_completion_status")
            or source_status_lookup.get("uniprot"),
        },
        "freeze_conditions": {
            "remaining_gap_files_zero": remaining_gap_files == 0,
            "not_yet_started_file_count_zero": not_yet_started_file_count == 0,
            "string_complete": string_complete,
            "uniprot_complete": uniprot_complete,
        },
        "source_specific_gates": {
            "string_completion_gate": source_completion.get("string_completion_status"),
            "uniref_completion_gate": source_completion.get("uniprot_completion_status"),
            "string_completion_ready": string_complete,
            "uniref_completion_ready": uniprot_complete,
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only procurement freeze gate. It does not mutate "
                "the broad mirror surfaces and does not mark the mirror complete "
                "unless all tracked freeze conditions are true."
            ),
            "report_only": True,
            "complete_mirror_locked": False,
            "freeze_requires_zero_gap": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Procurement Tail Freeze Gate Preview",
        "",
        f"- Gate status: `{payload['gate_status']}`",
        f"- Coverage: `{payload['broad_mirror_coverage_percent']}%`",
        f"- Remaining gap files: `{payload['remaining_gap_file_count']}`",
        f"- Active files: `{payload['active_file_count']}`",
        f"- Not yet started: `{payload['not_yet_started_file_count']}`",
        "",
        "## Freeze Conditions",
        "",
    ]
    for key, value in payload["freeze_conditions"].items():
        lines.append(f"- `{key}`: `{value}`")
    if payload["tracked_gap_files"]:
        lines.extend(["", "## Tracked Gap Files", ""])
        for row in payload["tracked_gap_files"]:
            lines.append(
                f"- `{row['source_id']}`: `{row['filename']}` ({row['gap_kind']})"
            )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a procurement-tail freeze gate preview."
    )
    parser.add_argument(
        "--broad-mirror-progress",
        type=Path,
        default=DEFAULT_BROAD_MIRROR_PROGRESS,
    )
    parser.add_argument("--remaining-gaps", type=Path, default=DEFAULT_REMAINING_GAPS)
    parser.add_argument(
        "--remaining-transfer-status",
        type=Path,
        default=DEFAULT_REMAINING_TRANSFER_STATUS,
    )
    parser.add_argument(
        "--source-completion",
        type=Path,
        default=DEFAULT_SOURCE_COMPLETION,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_procurement_tail_freeze_gate_preview(
        _read_json(args.broad_mirror_progress),
        _read_json(args.remaining_gaps),
        _read_json(args.remaining_transfer_status),
        _read_json(args.source_completion),
    )
    _write_json(args.output_json, payload)
    _write_text(args.output_md, render_markdown(payload))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
