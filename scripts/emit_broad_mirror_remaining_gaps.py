from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BROAD_MIRROR_PROGRESS = REPO_ROOT / "artifacts" / "status" / "broad_mirror_progress.json"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "artifacts" / "status" / "broad_mirror_remaining_gaps.json"
DEFAULT_MARKDOWN_OUTPUT = REPO_ROOT / "docs" / "reports" / "broad_mirror_remaining_gaps.md"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _casefold(value: Any) -> str:
    return str(value or "").strip().casefold()


def _sort_source_rows(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        int(row.get("priority_rank") or 99),
        -int(row.get("missing_file_count") or 0),
        float(row.get("coverage_percent") or 0.0),
        _casefold(row.get("source_id")),
    )


def _gap_file_rows(source_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in source_rows:
        base = {
            "source_id": source.get("source_id"),
            "source_name": source.get("source_name"),
            "category": source.get("category"),
            "priority_rank": source.get("priority_rank"),
            "coverage_percent": source.get("coverage_percent"),
        }
        for filename in source.get("missing_files") or []:
            rows.append({**base, "gap_kind": "missing", "filename": filename})
        for filename in source.get("partial_files") or []:
            rows.append({**base, "gap_kind": "partial", "filename": filename})
    rows.sort(
        key=lambda row: (
            int(row.get("priority_rank") or 99),
            0 if row.get("gap_kind") == "missing" else 1,
            _casefold(row.get("source_id")),
            _casefold(row.get("filename")),
        )
    )
    return rows


def build_remaining_broad_mirror_gaps(
    *,
    broad_mirror_progress_path: Path = DEFAULT_BROAD_MIRROR_PROGRESS,
) -> dict[str, Any]:
    progress = _read_json(broad_mirror_progress_path)
    source_rows = [row for row in progress.get("sources") or [] if isinstance(row, dict)]
    remaining_sources = [row for row in source_rows if _casefold(row.get("status")) != "complete"]
    remaining_sources.sort(key=_sort_source_rows)
    gap_files = _gap_file_rows(remaining_sources)
    complete_sources = [row for row in source_rows if _casefold(row.get("status")) == "complete"]
    total_missing_files = sum(int(row.get("missing_file_count") or 0) for row in remaining_sources)
    total_partial_files = sum(int(row.get("partial_file_count") or 0) for row in remaining_sources)

    return {
        "schema_id": "proteosphere-broad-mirror-remaining-gaps-2026-03-31",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "planning",
        "basis": {
            "broad_mirror_progress_path": str(broad_mirror_progress_path).replace("\\", "/"),
        },
        "summary": {
            "broad_mirror_coverage_percent": progress.get("summary", {}).get(
                "file_coverage_percent"
            ),
            "source_count": len(source_rows),
            "remaining_source_count": len(remaining_sources),
            "excluded_complete_source_count": len(complete_sources),
            "total_missing_files": total_missing_files,
            "total_partial_files": total_partial_files,
            "total_gap_files": total_missing_files + total_partial_files,
            "top_gap_sources": [row.get("source_id") for row in remaining_sources],
        },
        "remaining_sources": [
            {
                "source_id": row.get("source_id"),
                "source_name": row.get("source_name"),
                "category": row.get("category"),
                "status": row.get("status"),
                "priority_rank": row.get("priority_rank"),
                "coverage_percent": row.get("coverage_percent"),
                "missing_file_count": row.get("missing_file_count"),
                "partial_file_count": row.get("partial_file_count"),
                "gap_file_count": int(row.get("missing_file_count") or 0)
                + int(row.get("partial_file_count") or 0),
                "representative_missing_files": list(row.get("representative_missing_files") or []),
                "representative_partial_files": list(row.get("representative_partial_files") or []),
                "missing_files": list(row.get("missing_files") or []),
                "partial_files": list(row.get("partial_files") or []),
            }
            for row in remaining_sources
        ],
        "gap_files": gap_files,
        "notes": [
            "Complete sources are omitted so the slice stays focused on the live online gaps.",
            "Recognition-fixed sources remain excluded unless they re-open as partial or missing.",
        ],
    }


def _format_file_list(values: list[str], *, limit: int = 5) -> str:
    if not values:
        return "none"
    shown = values[:limit]
    text = ", ".join(f"`{value}`" for value in shown)
    if len(values) > limit:
        text += f" (+{len(values) - limit} more)"
    return text


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Remaining Broad Mirror Gaps",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Basis: `{payload['basis']['broad_mirror_progress_path']}`",
        f"- Broad mirror coverage: `{summary['broad_mirror_coverage_percent']}%`",
        f"- Remaining sources: `{summary['remaining_source_count']}`",
        f"- Excluded complete sources: `{summary['excluded_complete_source_count']}`",
        f"- Missing files: `{summary['total_missing_files']}`",
        f"- Partial files: `{summary['total_partial_files']}`",
        f"- Ranked gap files: `{summary['total_gap_files']}`",
        "",
        "## Ranked Sources",
        "",
        "| Source | Status | Coverage | Missing | Partial | Gap files |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["remaining_sources"]:
        lines.append(
            "| "
            + f"`{row['source_id']}` ({row['source_name']}) | "
            + f"{row['status']} | "
            + f"{row['coverage_percent']}% | "
            + f"{row['missing_file_count']} | "
            + f"{row['partial_file_count']} | "
            + f"{row['gap_file_count']} |"
        )
    lines.extend(
        [
            "",
            "## Ranked Gap Files",
            "",
            "| Rank | Source | Kind | File |",
            "| --- | --- | --- | --- |",
        ]
    )
    for index, row in enumerate(payload["gap_files"], start=1):
        lines.append(
            "| "
            + f"{index} | "
            + f"`{row['source_id']}` | "
            + f"{row['gap_kind']} | "
            + f"`{row['filename']}` |"
        )
    lines.extend(["", "## Source File Lists", ""])
    for row in payload["remaining_sources"]:
        lines.append(
            f"- `{row['source_id']}` missing: {_format_file_list(row['missing_files'])}; "
            f"partial: {_format_file_list(row['partial_files'])}"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit the remaining broad mirror gap plan.")
    parser.add_argument("--broad-mirror-progress", type=Path, default=DEFAULT_BROAD_MIRROR_PROGRESS)
    parser.add_argument("--output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-markdown", action="store_true")
    args = parser.parse_args(argv)

    payload = build_remaining_broad_mirror_gaps(
        broad_mirror_progress_path=args.broad_mirror_progress,
    )
    _write_json(args.output, payload)
    if not args.no_markdown:
        _write_text(args.markdown_output, render_markdown(payload))

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "Remaining broad mirror gaps exported: "
            f"sources={payload['summary']['remaining_source_count']} "
            f"gap_files={payload['summary']['total_gap_files']} "
            f"coverage={payload['summary']['broad_mirror_coverage_percent']}%"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
