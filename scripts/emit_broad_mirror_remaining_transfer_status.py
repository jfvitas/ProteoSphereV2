from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REMAINING_GAPS_PATH = (
    REPO_ROOT / "artifacts" / "status" / "broad_mirror_remaining_gaps.json"
)
DEFAULT_RUNTIME_DIR = REPO_ROOT / "artifacts" / "runtime"
DEFAULT_SEED_ROOT = REPO_ROOT / "data" / "raw" / "protein_data_scope_seed"
DEFAULT_JSON_OUTPUT = (
    REPO_ROOT / "artifacts" / "status" / "broad_mirror_remaining_transfer_status.json"
)
DEFAULT_MARKDOWN_OUTPUT = (
    REPO_ROOT / "docs" / "reports" / "broad_mirror_remaining_transfer_status.md"
)


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


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _tail_lines(path: Path, *, limit: int = 120) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    return lines[-limit:]


def _log_candidates(runtime_dir: Path, source_id: str) -> list[Path]:
    source_key = source_id.casefold()
    candidates = [
        path
        for path in runtime_dir.glob("*stdout.log")
        if source_key in path.name.casefold()
    ]
    return sorted(candidates, key=lambda item: item.name.casefold())


def _partial_candidates(seed_root: Path, source_id: str, filename: str) -> list[Path]:
    source_root = seed_root / source_id
    return [
        source_root / f"{filename}.part",
        source_root / f"{filename}.partial",
    ]


def _file_evidence(
    *,
    source_id: str,
    filename: str,
    runtime_dir: Path,
    seed_root: Path,
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for log_path in _log_candidates(runtime_dir, source_id):
        tail = _tail_lines(log_path)
        if any(filename in line for line in tail):
            evidence.append(
                {
                    "kind": "stdout_log_tail",
                    "log": _repo_relative(log_path),
                }
            )
    for partial_path in _partial_candidates(seed_root, source_id, filename):
        if partial_path.exists():
            evidence.append(
                {
                    "kind": "on_disk_partial",
                    "path": _repo_relative(partial_path),
                    "size_bytes": partial_path.stat().st_size,
                    "last_write_time": datetime.fromtimestamp(
                        partial_path.stat().st_mtime, tz=UTC
                    ).isoformat(),
                }
            )
    return evidence


def _sort_remaining_source(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        int(row.get("priority_rank") or 99),
        -int(row.get("missing_file_count") or 0),
        float(row.get("coverage_percent") or 0.0),
        _casefold(row.get("source_id")),
    )


def build_remaining_transfer_status(
    *,
    remaining_gaps_path: Path = DEFAULT_REMAINING_GAPS_PATH,
    runtime_dir: Path = DEFAULT_RUNTIME_DIR,
    seed_root: Path = DEFAULT_SEED_ROOT,
) -> dict[str, Any]:
    gaps = _read_json(remaining_gaps_path)
    remaining_sources = [
        row for row in gaps.get("remaining_sources") or [] if isinstance(row, dict)
    ]
    remaining_sources.sort(key=_sort_remaining_source)

    source_rows: list[dict[str, Any]] = []
    active_files: list[dict[str, Any]] = []
    not_yet_started_files: list[dict[str, Any]] = []
    active_count_by_source: dict[str, int] = {}

    for source in remaining_sources:
        source_id = str(source.get("source_id") or "").strip()
        if not source_id:
            continue
        source_name = str(source.get("source_name") or source_id).strip()
        active_entries: list[dict[str, Any]] = []
        inactive_entries: list[dict[str, Any]] = []

        for gap_kind, filenames in (
            ("missing", source.get("missing_files") or []),
            ("partial", source.get("partial_files") or []),
        ):
            for filename in filenames:
                filename = str(filename).strip()
                if not filename:
                    continue
                evidence = _file_evidence(
                    source_id=source_id,
                    filename=filename,
                    runtime_dir=runtime_dir,
                    seed_root=seed_root,
                )
                row = {
                    "source_id": source_id,
                    "source_name": source_name,
                    "category": source.get("category"),
                    "gap_kind": gap_kind,
                    "filename": filename,
                    "evidence": evidence,
                }
                if evidence:
                    active_entries.append(row)
                    active_files.append(row)
                else:
                    inactive_entries.append(row)
                    not_yet_started_files.append(row)

        active_count_by_source[source_id] = len(active_entries)
        source_rows.append(
            {
                "source_id": source_id,
                "source_name": source_name,
                "category": source.get("category"),
                "status": source.get("status"),
                "coverage_percent": source.get("coverage_percent"),
                "active_file_count": len(active_entries),
                "not_yet_started_file_count": len(inactive_entries),
                "actively_transferring_now": active_entries,
                "not_yet_started": inactive_entries,
            }
        )

    return {
        "schema_id": "proteosphere-broad-mirror-remaining-transfer-status-2026-03-31",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "planning",
        "basis": {
            "remaining_gaps_path": str(remaining_gaps_path).replace("\\", "/"),
            "runtime_dir": str(runtime_dir).replace("\\", "/"),
            "seed_root": str(seed_root).replace("\\", "/"),
        },
        "summary": {
            "broad_mirror_coverage_percent": gaps.get("summary", {}).get(
                "broad_mirror_coverage_percent"
            ),
            "remaining_source_count": len(source_rows),
            "active_file_count": len(active_files),
            "not_yet_started_file_count": len(not_yet_started_files),
            "active_source_counts": dict(sorted(active_count_by_source.items())),
        },
        "sources": source_rows,
        "actively_transferring_now": active_files,
        "not_yet_started": not_yet_started_files,
        "notes": [
            "A file is considered active when it appears in the tail of a current runtime stdout log or has a live .part/.partial artifact on disk.",
            "Files with no current log-tail hit and no partial artifact are treated as not yet started.",
        ],
    }


def _format_evidence(evidence: list[dict[str, Any]]) -> str:
    if not evidence:
        return "none"
    parts = []
    for item in evidence:
        if item.get("kind") == "stdout_log_tail":
            parts.append(f"log:{Path(str(item['log'])).name}")
        elif item.get("kind") == "on_disk_partial":
            parts.append(f"partial:{Path(str(item['path'])).name}")
    return ", ".join(parts)


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Remaining Broad Mirror Transfer Status",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Basis: `{payload['basis']['remaining_gaps_path']}`",
        f"- Coverage: `{summary['broad_mirror_coverage_percent']}%`",
        f"- Remaining sources: `{summary['remaining_source_count']}`",
        f"- Actively transferring now: `{summary['active_file_count']}`",
        f"- Not yet started: `{summary['not_yet_started_file_count']}`",
        "",
        "## By Source",
        "",
        "| Source | Active now | Not yet started |",
        "| --- | --- | --- |",
    ]
    for row in payload["sources"]:
        lines.append(
            "| "
            + f"`{row['source_id']}` ({row['source_name']}) | "
            + f"{row['active_file_count']} | "
            + f"{row['not_yet_started_file_count']} |"
        )

    lines.extend(["", "## Actively Transferring Now", ""])
    for row in payload["actively_transferring_now"]:
        lines.append(
            f"- `{row['source_id']}`: `{row['filename']}` "
            f"({row['gap_kind']}; evidence: {_format_evidence(row['evidence'])})"
        )

    lines.extend(["", "## Not Yet Started", ""])
    for row in payload["not_yet_started"]:
        lines.append(f"- `{row['source_id']}`: `{row['filename']}` ({row['gap_kind']})")

    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Emit the remaining broad mirror transfer status."
    )
    parser.add_argument("--remaining-gaps", type=Path, default=DEFAULT_REMAINING_GAPS_PATH)
    parser.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME_DIR)
    parser.add_argument("--seed-root", type=Path, default=DEFAULT_SEED_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-markdown", action="store_true")
    args = parser.parse_args(argv)

    payload = build_remaining_transfer_status(
        remaining_gaps_path=args.remaining_gaps,
        runtime_dir=args.runtime_dir,
        seed_root=args.seed_root,
    )
    _write_json(args.output, payload)
    if not args.no_markdown:
        _write_text(args.markdown_output, render_markdown(payload))

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "Remaining broad mirror transfer status exported: "
            f"active={payload['summary']['active_file_count']} "
            f"pending={payload['summary']['not_yet_started_file_count']} "
            f"coverage={payload['summary']['broad_mirror_coverage_percent']}%"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
