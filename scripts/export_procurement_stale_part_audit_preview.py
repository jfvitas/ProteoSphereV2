from __future__ import annotations

import argparse
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from scripts.web_enrichment_preview_support import read_json, write_json, write_text
except ModuleNotFoundError:  # pragma: no cover
    from web_enrichment_preview_support import read_json, write_json, write_text

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOWNLOAD_LOCATION_AUDIT = (
    REPO_ROOT / "artifacts" / "status" / "download_location_audit_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "procurement_stale_part_audit_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "procurement_stale_part_audit_preview.md"
)


def _path_size(path_text: str) -> int | None:
    path = Path(path_text)
    if not path.exists() or not path.is_file():
        return None
    return path.stat().st_size


def build_procurement_stale_part_audit_preview(
    download_location_audit_preview: dict[str, Any],
    *,
    sample_seconds: float = 2.0,
) -> dict[str, Any]:
    rows = [
        row
        for row in (download_location_audit_preview.get("rows") or [])
        if isinstance(row, dict) and (row.get("in_process_locations") or [])
    ]
    initial_sizes: dict[str, int | None] = {}
    for row in rows:
        for location in row.get("in_process_locations") or []:
            path_text = str(location.get("path") or "").replace("/", "\\")
            initial_sizes[path_text] = _path_size(path_text)

    if rows and sample_seconds > 0:
        time.sleep(sample_seconds)

    result_rows: list[dict[str, Any]] = []
    for row in rows:
        final_locations = row.get("final_locations") or []
        for location in row.get("in_process_locations") or []:
            path_text = str(location.get("path") or "").replace("/", "\\")
            first_size = initial_sizes.get(path_text)
            second_size = _path_size(path_text)
            delta = None if first_size is None or second_size is None else second_size - first_size
            classification = "live_transfer"
            if final_locations and (delta == 0 or delta is None):
                classification = "stale_residue_after_final"
            elif delta == 0 or delta is None:
                classification = "idle_in_process_needs_review"
            result_rows.append(
                {
                    "source_id": row.get("source_id"),
                    "filename": row.get("filename"),
                    "part_path": str(location.get("path") or ""),
                    "has_final_location": bool(final_locations),
                    "sample_seconds": sample_seconds,
                    "initial_size_bytes": first_size,
                    "final_size_bytes": second_size,
                    "delta_bytes": delta,
                    "classification": classification,
                }
            )

    return {
        "artifact_id": "procurement_stale_part_audit_preview",
        "schema_id": "proteosphere-procurement-stale-part-audit-preview-2026-04-04",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "in_process_row_count": len(result_rows),
            "live_transfer_count": sum(
                1 for row in result_rows if row["classification"] == "live_transfer"
            ),
            "stale_residue_count": sum(
                1
                for row in result_rows
                if row["classification"] == "stale_residue_after_final"
            ),
            "review_count": sum(
                1
                for row in result_rows
                if row["classification"] == "idle_in_process_needs_review"
            ),
        },
        "rows": result_rows,
        "truth_boundary": {
            "summary": (
                "This audit samples .part files over a short interval so stale residue can be "
                "distinguished from live transfer without mutating download state."
            ),
            "report_only": True,
            "non_mutating": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Procurement Stale Part Audit Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        "",
    ]
    for row in payload.get("rows") or []:
        lines.append(
            f"- `{row['filename']}` / `{row['classification']}` / delta `{row['delta_bytes']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit .part files for live growth vs stale residue."
    )
    parser.add_argument(
        "--download-location-audit",
        type=Path,
        default=DEFAULT_DOWNLOAD_LOCATION_AUDIT,
    )
    parser.add_argument("--sample-seconds", type=float, default=2.0)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_procurement_stale_part_audit_preview(
        read_json(args.download_location_audit),
        sample_seconds=args.sample_seconds,
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
