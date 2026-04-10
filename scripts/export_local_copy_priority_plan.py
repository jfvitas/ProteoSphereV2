from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRIORITY_JSON = REPO_ROOT / "artifacts" / "status" / "p32_local_copy_priority.json"
DEFAULT_BIO_AGENT_LAB_ROOT = Path(r"C:\Users\jfvit\Documents\bio-agent-lab")
DEFAULT_LOCAL_COPIES_ROOT = REPO_ROOT / "data" / "raw" / "local_copies"


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"expected JSON object at {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_slug(value: str) -> str:
    slug = "".join(ch if ch.isalnum() else "_" for ch in value)
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_").lower()


def _path_relative_to_root(path: Path, root: Path) -> Path:
    try:
        return path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"path {path} is not under root {root}") from exc


def _path_display_ref(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def _infer_destination_slug(source_path: Path, bio_agent_lab_root: Path) -> str:
    relative = _path_relative_to_root(source_path, bio_agent_lab_root)
    parts = relative.parts
    if not parts:
        raise ValueError(f"cannot infer destination slug for {source_path}")

    if parts[0].casefold() == "data" and len(parts) >= 3:
        branch = parts[1].casefold()
        if branch == "releases":
            return f"releases_{_normalize_slug(parts[2])}"
        if branch == "extracted":
            return f"extracted_{_normalize_slug(parts[2])}"
        if branch == "raw":
            if parts[2].casefold() == "skempi":
                return "skempi"
            return _normalize_slug(parts[2])

    if parts[0].casefold() == "data_sources" and len(parts) >= 2:
        family = parts[1].casefold()
        if family == "pdbbind":
            name = parts[-1].casefold()
            pdbbind_map = {
                "p-l.tar.gz": "pdbbind_pl",
                "p-na.tar.gz": "pdbbind_p_na",
                "na-l.tar.gz": "pdbbind_na_l",
                "p-p.tar.gz": "pdbbind_pp",
                "index": "pdbbind_index",
                "index.tar.gz": "pdbbind_index",
                "index (1).tar.gz": "pdbbind_index",
            }
            if name in pdbbind_map:
                return pdbbind_map[name]
            return f"pdbbind_{_normalize_slug(parts[-1])}"
        if family == "alphafold":
            return "alphafold_db"
        return _normalize_slug(parts[1])

    return _normalize_slug("_".join(parts))


def _source_kind(source_path: Path) -> str:
    if source_path.exists():
        return "directory" if source_path.is_dir() else "file"
    if source_path.name.casefold().endswith(".tar.gz") or source_path.suffix:
        return "file"
    return "directory"


def _destination_path(
    *,
    source_path: Path,
    bio_agent_lab_root: Path,
    local_copies_root: Path,
) -> tuple[Path, Path, str]:
    destination_slug = _infer_destination_slug(source_path, bio_agent_lab_root)
    destination_root = local_copies_root / destination_slug
    if _source_kind(source_path) == "file":
        return destination_root, destination_root / source_path.name, destination_slug
    return destination_root, destination_root, destination_slug


def _compact_entry(
    entry: dict[str, Any],
    *,
    bio_agent_lab_root: Path,
    local_copies_root: Path,
) -> dict[str, Any]:
    source_path = Path(_clean_text(entry.get("path")))
    destination_root, destination_path, destination_slug = _destination_path(
        source_path=source_path,
        bio_agent_lab_root=bio_agent_lab_root,
        local_copies_root=local_copies_root,
    )
    source_exists = source_path.exists()
    destination_exists = destination_path.exists()
    source_kind = _source_kind(source_path)
    copy_mode = "copy_file" if source_kind == "file" else "mirror_directory"
    copy_shape = "single_file" if source_kind == "file" else "directory_tree"

    return {
        "priority": entry.get("priority"),
        "source_path": str(source_path),
        "source_relative_path": _path_display_ref(source_path, bio_agent_lab_root),
        "source_kind": source_kind,
        "source_category": entry.get("kind"),
        "destination_root": str(destination_root),
        "destination_path": str(destination_path),
        "destination_relative_path": _path_display_ref(destination_path, REPO_ROOT),
        "destination_slug": destination_slug,
        "copy_mode": copy_mode,
        "copy_shape": copy_shape,
        "source_exists": source_exists,
        "destination_exists": destination_exists,
        "copy_metadata": {
            "present_file_count": entry.get("present_file_count"),
            "present_total_bytes": entry.get("present_total_bytes"),
            "value": entry.get("value"),
            "why_now": entry.get("why_now"),
            "kind": entry.get("kind"),
        },
    }


def build_local_copy_priority_plan(
    *,
    priority_json_path: Path = DEFAULT_PRIORITY_JSON,
    bio_agent_lab_root: Path = DEFAULT_BIO_AGENT_LAB_ROOT,
    local_copies_root: Path = DEFAULT_LOCAL_COPIES_ROOT,
) -> dict[str, Any]:
    payload = _read_json(priority_json_path)
    queue = payload.get("uncopied_priority")
    if not isinstance(queue, list):
        raise TypeError("priority JSON must contain an uncopied_priority list")

    ordered_entries = sorted(
        [entry for entry in queue if isinstance(entry, dict)],
        key=lambda item: (
            int(item.get("priority") or 0),
            _clean_text(item.get("path")).casefold(),
        ),
    )

    pending_items: list[dict[str, Any]] = []
    skipped_items: list[dict[str, Any]] = []
    blocked_items: list[dict[str, Any]] = []

    for entry in ordered_entries:
        plan_item = _compact_entry(
            entry,
            bio_agent_lab_root=bio_agent_lab_root,
            local_copies_root=local_copies_root,
        )
        if not plan_item["source_exists"]:
            plan_item = {**plan_item, "mirror_status": "blocked_source_missing"}
            blocked_items.append(plan_item)
            continue
        if plan_item["destination_exists"]:
            skipped_items.append(
                {
                    **plan_item,
                    "mirror_status": "already_mirrored",
                    "skip_reason": "destination already exists in local_copies",
                }
            )
            continue
        pending_items.append({**plan_item, "mirror_status": "pending_copy"})

    pending_bytes = sum(
        int(item.get("copy_metadata", {}).get("present_total_bytes") or 0)
        for item in pending_items
    )
    return {
        "schema_id": "proteosphere-p32-local-copy-execution-plan-2026-03-30",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "status": "planning_only",
        "priority_json_path": str(priority_json_path),
        "bio_agent_lab_root": str(bio_agent_lab_root),
        "local_copies_root": str(local_copies_root),
        "total_items": len(ordered_entries),
        "pending_count": len(pending_items),
        "skipped_count": len(skipped_items),
        "blocked_count": len(blocked_items),
        "pending_total_bytes": pending_bytes,
        "pending_items": pending_items,
        "skipped_items": skipped_items,
        "blocked_items": blocked_items,
        "notes": [
            "This planner is read-only and does not copy files.",
            "Items are filtered out of the pending queue when the inferred "
            "destination already exists.",
            "Destination inference preserves the current local_copies naming "
            "pattern where possible.",
        ],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a read-only execution plan from p32_local_copy_priority.json."
    )
    parser.add_argument("--priority-json", type=Path, default=DEFAULT_PRIORITY_JSON)
    parser.add_argument("--bio-agent-lab-root", type=Path, default=DEFAULT_BIO_AGENT_LAB_ROOT)
    parser.add_argument("--local-copies-root", type=Path, default=DEFAULT_LOCAL_COPIES_ROOT)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_local_copy_priority_plan(
        priority_json_path=args.priority_json,
        bio_agent_lab_root=args.bio_agent_lab_root,
        local_copies_root=args.local_copies_root,
    )
    if args.output is not None:
        _write_json(args.output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
