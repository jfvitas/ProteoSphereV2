from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INVENTORY_PATH = ROOT / "artifacts" / "status" / "duplicate_storage_inventory.json"
DEFAULT_STATUS_PATH = ROOT / "artifacts" / "status" / "duplicate_cleanup_status.json"
DEFAULT_OUTPUT_JSON = ROOT / "artifacts" / "status" / "duplicate_cleanup_dry_run_plan.json"
DEFAULT_OUTPUT_MD = ROOT / "docs" / "reports" / "duplicate_cleanup_dry_run_plan.md"

SAFE_FIRST_COHORTS = {
    "local_archive_equivalents",
    "seed_vs_local_copy_duplicates",
    "same_release_local_copy_duplicates",
}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise TypeError(f"{path} must contain a JSON object")
    return dict(payload)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _family_tags(paths: list[str]) -> set[str]:
    tags: set[str] = set()
    for path in paths:
        if "data\\raw\\local_copies" in path:
            tags.add("local_copies")
        if "data\\raw\\protein_data_scope_seed" in path:
            tags.add("protein_data_scope_seed")
    return tags


def _cohort_name(group: Mapping[str, Any], paths: list[str]) -> str | None:
    duplicate_class = str(group.get("duplicate_class") or "")
    tags = _family_tags(paths)
    if duplicate_class == "equivalent_archive_copy" and "local_copies" in tags:
        return "local_archive_equivalents"
    if (
        duplicate_class == "exact_duplicate_cross_location"
        and {"local_copies", "protein_data_scope_seed"}.issubset(tags)
    ):
        return "seed_vs_local_copy_duplicates"
    if duplicate_class == "exact_duplicate_same_release" and tags == {"local_copies"}:
        return "same_release_local_copy_duplicates"
    return None


def build_duplicate_cleanup_dry_run_plan(
    inventory: Mapping[str, Any],
    status_payload: Mapping[str, Any],
    *,
    max_actions: int = 100,
) -> dict[str, Any]:
    allowed_cohorts = {
        entry["cohort_name"]
        for entry in (status_payload.get("safe_first_cleanup_cohorts") or ())
        if entry.get("cohort_name") in SAFE_FIRST_COHORTS
    }
    actions: list[dict[str, Any]] = []
    total_reclaimable_bytes = 0

    for group in inventory.get("duplicate_groups") or ():
        if len(actions) >= max_actions:
            break
        if not isinstance(group, Mapping) or not group.get("reclaimable"):
            continue
        files = [
            str(item.get("relative_path") or item.get("path") or "")
            for item in (group.get("files") or ())
            if isinstance(item, Mapping)
        ]
        if not files:
            continue
        cohort_name = _cohort_name(group, files)
        if cohort_name not in allowed_cohorts:
            continue
        keeper = min(files, key=len)
        removals = [path for path in files if path != keeper]
        if not removals:
            continue
        reclaimable_bytes = int(group.get("reclaimable_bytes") or 0)
        total_reclaimable_bytes += reclaimable_bytes
        actions.append(
            {
                "cohort_name": cohort_name,
                "duplicate_class": group.get("duplicate_class"),
                "sha256": group.get("sha256"),
                "keeper_path": keeper,
                "removal_paths": removals,
                "reclaimable_bytes": reclaimable_bytes,
                "validation_gates": [
                    "exact_sha256_match",
                    "no_protected_paths",
                    "no_partial_paths",
                    "no_latest_surface_rewrites",
                ],
            }
        )

    return {
        "plan_id": "duplicate-cleanup-dry-run-plan",
        "generated_at": inventory.get("generated_at"),
        "source_inventory": "artifacts\\status\\duplicate_storage_inventory.json",
        "source_status": "artifacts\\status\\duplicate_cleanup_status.json",
        "allowed_cohorts": sorted(allowed_cohorts),
        "action_count": len(actions),
        "planned_reclaimable_bytes": total_reclaimable_bytes,
        "actions": actions,
    }


def render_duplicate_cleanup_dry_run_plan_markdown(payload: Mapping[str, Any]) -> str:
    lines = [
        "# Duplicate Cleanup Dry-Run Plan",
        "",
        f"- Generated at: `{payload.get('generated_at')}`",
        f"- Allowed cohorts: `{', '.join(payload.get('allowed_cohorts') or [])}`",
        f"- Action count: `{payload.get('action_count')}`",
        f"- Planned reclaimable bytes: `{payload.get('planned_reclaimable_bytes')}`",
        "",
        "## Planned Actions",
    ]
    for entry in payload.get("actions") or ():
        removals = ", ".join(f"`{path}`" for path in entry.get("removal_paths") or ())
        lines.append(
            f"- `{entry['cohort_name']}` / `{entry['duplicate_class']}`: keep "
            f"`{entry['keeper_path']}`, remove {removals}, reclaim "
            f"`{entry['reclaimable_bytes']}` bytes"
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory-json", type=Path, default=DEFAULT_INVENTORY_PATH)
    parser.add_argument("--status-json", type=Path, default=DEFAULT_STATUS_PATH)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--max-actions", type=int, default=100)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    inventory = _load_json(args.inventory_json)
    status_payload = _load_json(args.status_json)
    payload = build_duplicate_cleanup_dry_run_plan(
        inventory,
        status_payload,
        max_actions=max(1, int(args.max_actions)),
    )
    _write_json(args.output_json, payload)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(
        render_duplicate_cleanup_dry_run_plan_markdown(payload),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
