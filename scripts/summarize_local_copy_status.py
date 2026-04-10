from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_local_copy_priority_plan import (  # noqa: I001
    build_local_copy_priority_plan,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRIORITY_JSON = REPO_ROOT / "artifacts" / "status" / "p32_local_copy_priority.json"
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "p32_local_copy_status.json"
DEFAULT_MARKDOWN_OUTPUT = REPO_ROOT / "docs" / "reports" / "p32_local_copy_status.md"
DEFAULT_BIO_AGENT_LAB_ROOT = Path(r"C:\Users\jfvit\Documents\bio-agent-lab")
DEFAULT_LOCAL_COPIES_ROOT = REPO_ROOT / "data" / "raw" / "local_copies"
DEFAULT_ROBOCOPY_LOG_ROOTS = (
    REPO_ROOT / "artifacts" / "runtime",
    REPO_ROOT / "artifacts" / "status",
    DEFAULT_BIO_AGENT_LAB_ROOT / "logs",
    DEFAULT_BIO_AGENT_LAB_ROOT / "artifacts" / "runtime",
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _iter_files(root: Path) -> tuple[Path, ...]:
    if not root.exists():
        return ()
    if root.is_file():
        return (root,)
    return tuple(path for path in root.rglob("*") if path.is_file())


def _collect_path_stats(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "exists": False,
            "kind": "missing",
            "file_count": 0,
            "total_bytes": 0,
        }
    if path.is_file():
        stat = path.stat()
        return {
            "exists": True,
            "kind": "file",
            "file_count": 1,
            "total_bytes": stat.st_size,
        }

    file_count = 0
    total_bytes = 0
    for file_path in _iter_files(path):
        stat = file_path.stat()
        file_count += 1
        total_bytes += stat.st_size
    return {
        "exists": True,
        "kind": "directory",
        "file_count": file_count,
        "total_bytes": total_bytes,
    }


def _normalize_log_text(text: str) -> str:
    return text.casefold()


def _log_is_complete(text: str) -> bool:
    normalized = _normalize_log_text(text)
    return "ended :" in normalized or "ended:" in normalized


def _discover_logs(
    log_roots: tuple[Path, ...],
    explicit_logs: tuple[Path, ...],
) -> tuple[Path, ...]:
    discovered: dict[str, Path] = {}
    for path in explicit_logs:
        resolved = path.resolve()
        if resolved.exists():
            discovered.setdefault(str(resolved).casefold(), resolved)
    for root in log_roots:
        if not root.exists():
            continue
        if root.is_file():
            if "robocopy" in root.name.casefold() and root.suffix.casefold() == ".log":
                discovered.setdefault(str(root.resolve()).casefold(), root.resolve())
            continue
        for path in root.rglob("*robocopy*.log"):
            if path.is_file():
                resolved = path.resolve()
                discovered.setdefault(str(resolved).casefold(), resolved)
    return tuple(sorted(discovered.values(), key=lambda path: str(path).casefold()))


def _log_matches_item(text: str, item: dict[str, Any]) -> bool:
    normalized = _normalize_log_text(text)
    tokens = {
        _clean_text(item.get("source_path")),
        _clean_text(item.get("destination_path")),
        _clean_text(item.get("source_relative_path")),
        _clean_text(item.get("destination_relative_path")),
        _clean_text(item.get("destination_slug")),
        Path(_clean_text(item.get("source_path"))).name,
        Path(_clean_text(item.get("destination_path"))).name,
    }
    for token in tokens:
        token = token.strip()
        if token and token.casefold() in normalized:
            return True
    return False


def _flatten_priority_items(plan: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for section_name in ("pending_items", "skipped_items", "blocked_items"):
        for item in plan.get(section_name) or []:
            if isinstance(item, dict):
                items.append(item)
    return sorted(
        items,
        key=lambda item: (
            int(item.get("priority") or 0),
            _clean_text(item.get("destination_slug")).casefold(),
        ),
    )


def _classify_item(
    item: dict[str, Any],
    *,
    destination_stats: dict[str, Any],
    log_records: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    matched_logs: list[dict[str, Any]] = []
    active_log_paths: list[str] = []
    completed_log_paths: list[str] = []
    for log_record in log_records:
        text = _clean_text(log_record.get("text"))
        if not text or not _log_matches_item(text, item):
            continue
        matched_logs.append(log_record)
        if log_record.get("complete"):
            completed_log_paths.append(_clean_text(log_record.get("path")))
        else:
            active_log_paths.append(_clean_text(log_record.get("path")))

    source_exists = bool(item.get("source_exists"))
    destination_exists = bool(destination_stats.get("exists"))
    destination_has_content = int(destination_stats.get("file_count") or 0) > 0
    destination_total_bytes = int(destination_stats.get("total_bytes") or 0)

    if not source_exists:
        copy_status = "blocked"
        status_reason = "source missing in bio-agent-lab"
    elif active_log_paths:
        copy_status = "in_progress"
        status_reason = "matching active robocopy log found"
    elif destination_exists and destination_has_content:
        copy_status = "complete"
        status_reason = "destination exists in local_copies"
    elif completed_log_paths:
        copy_status = "complete"
        status_reason = "matching completed robocopy log found"
    else:
        copy_status = "pending"
        status_reason = "not mirrored yet"

    return {
        **item,
        "copy_status": copy_status,
        "status_reason": status_reason,
        "destination_stats": {
            **destination_stats,
            "total_bytes": destination_total_bytes,
        },
        "matched_log_paths": [str(path) for path in completed_log_paths + active_log_paths],
    }


def build_local_copy_status(
    *,
    priority_json_path: Path = DEFAULT_PRIORITY_JSON,
    bio_agent_lab_root: Path = DEFAULT_BIO_AGENT_LAB_ROOT,
    local_copies_root: Path = DEFAULT_LOCAL_COPIES_ROOT,
    robocopy_logs: tuple[Path, ...] = (),
    robocopy_log_roots: tuple[Path, ...] = DEFAULT_ROBOCOPY_LOG_ROOTS,
) -> dict[str, Any]:
    plan = build_local_copy_priority_plan(
        priority_json_path=priority_json_path,
        bio_agent_lab_root=bio_agent_lab_root,
        local_copies_root=local_copies_root,
    )
    all_items = _flatten_priority_items(plan)
    discovered_logs = _discover_logs(robocopy_log_roots, robocopy_logs)
    log_records: list[dict[str, Any]] = []
    for path in discovered_logs:
        text = path.read_text(encoding="utf-8", errors="replace")
        log_records.append(
            {
                "path": str(path),
                "text": text,
                "complete": _log_is_complete(text),
                "size_bytes": path.stat().st_size,
                "line_count": len(text.splitlines()),
            }
        )

    items: list[dict[str, Any]] = []
    for item in all_items:
        destination_path = Path(_clean_text(item.get("destination_path")))
        destination_stats = _collect_path_stats(destination_path)
        items.append(
            _classify_item(
                item,
                destination_stats=destination_stats,
                log_records=tuple(log_records),
            )
        )

    status_counts: dict[str, int] = {}
    for item in items:
        status_counts[item["copy_status"]] = status_counts.get(item["copy_status"], 0) + 1

    return {
        "schema_id": "proteosphere-p32-local-copy-status-2026-03-30",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "status": "planning_only",
        "priority_json_path": str(priority_json_path),
        "bio_agent_lab_root": str(bio_agent_lab_root),
        "local_copies_root": str(local_copies_root),
        "robocopy_log_paths": [str(path) for path in discovered_logs],
        "item_status_counts": dict(sorted(status_counts.items())),
        "items": items,
        "notes": [
            "This is a read-only monitoring snapshot.",
            "If no robocopy logs are discovered, item status falls back to local_copies presence.",
            "Active log matches take precedence over destination existence when "
            "a copy is still running.",
        ],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Local Copy Status",
        "",
        f"- Generated at: `{payload.get('generated_at')}`",
        f"- Status: `{payload.get('status')}`",
        f"- Log count: `{len(payload.get('robocopy_log_paths') or [])}`",
        "",
        "## Items",
        "",
    ]
    for item in payload.get("items") or []:
        if not isinstance(item, dict):
            continue
        stats = item.get("destination_stats") or {}
        lines.extend(
            [
                f"- `{item.get('destination_slug')}` -> `{item.get('copy_status')}`",
                f"  - destination: `{item.get('destination_path')}`",
                f"  - planned bytes: `{item.get('copy_metadata', {}).get('present_total_bytes')}`",
                f"  - current bytes: `{stats.get('total_bytes')}`",
                f"  - current files: `{stats.get('file_count')}`",
                f"  - reason: `{item.get('status_reason')}`",
            ]
        )
        matched_logs = item.get("matched_log_paths") or []
        if matched_logs:
            lines.append(f"  - logs: `{matched_logs}`")
    lines.extend(
        [
            "",
            "## Notes",
            "",
            *(f"- {note}" for note in payload.get("notes") or []),
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize the status of planned local copy items."
    )
    parser.add_argument("--priority-json", type=Path, default=DEFAULT_PRIORITY_JSON)
    parser.add_argument("--bio-agent-lab-root", type=Path, default=DEFAULT_BIO_AGENT_LAB_ROOT)
    parser.add_argument("--local-copies-root", type=Path, default=DEFAULT_LOCAL_COPIES_ROOT)
    parser.add_argument(
        "--robocopy-log",
        action="append",
        type=Path,
        default=[],
        help="Explicit robocopy log path. May be passed multiple times.",
    )
    parser.add_argument(
        "--robocopy-log-root",
        action="append",
        type=Path,
        default=[],
        help="Directory to scan for robocopy*.log files. May be passed multiple times.",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_local_copy_status(
        priority_json_path=args.priority_json,
        bio_agent_lab_root=args.bio_agent_lab_root,
        local_copies_root=args.local_copies_root,
        robocopy_logs=tuple(args.robocopy_log),
        robocopy_log_roots=tuple(args.robocopy_log_root) or DEFAULT_ROBOCOPY_LOG_ROOTS,
    )
    _write_json(args.output, payload)
    _write_text(args.markdown, render_markdown(payload))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "Local copy status exported: "
            f"items={len(payload['items'])} logs={len(payload['robocopy_log_paths'])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
