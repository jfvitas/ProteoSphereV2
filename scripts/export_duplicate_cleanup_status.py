from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = ROOT / "artifacts" / "status" / "duplicate_storage_inventory.json"
DEFAULT_OUTPUT_JSON = ROOT / "artifacts" / "status" / "duplicate_cleanup_status.json"
DEFAULT_OUTPUT_MD = ROOT / "docs" / "reports" / "duplicate_cleanup_status.md"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise TypeError("inventory payload must be a mapping")
    return dict(payload)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _root_prefix(relative_path: str, depth: int = 4) -> str:
    parts = [part for part in str(relative_path).split("\\") if part]
    if not parts:
        return ""
    return "\\".join(parts[:depth])


def _family_tags(paths: Iterable[str]) -> set[str]:
    tags: set[str] = set()
    for path in paths:
        text = str(path)
        if "data\\raw\\local_copies" in text:
            tags.add("local_copies")
        if "data\\raw\\protein_data_scope_seed" in text:
            tags.add("protein_data_scope_seed")
        if "data\\raw\\local_registry" in text:
            tags.add("local_registry")
        if "data\\raw\\bootstrap_runs" in text:
            tags.add("bootstrap_runs")
        if "data\\packages" in text:
            tags.add("packages")
    return tags


def _safe_first_label(group: Mapping[str, Any], paths: tuple[str, ...]) -> str | None:
    duplicate_class = str(group.get("duplicate_class") or "")
    families = _family_tags(paths)
    if duplicate_class == "equivalent_archive_copy" and "local_copies" in families:
        return "local_archive_equivalents"
    if (
        duplicate_class == "exact_duplicate_cross_location"
        and {"local_copies", "protein_data_scope_seed"}.issubset(families)
    ):
        return "seed_vs_local_copy_duplicates"
    if duplicate_class == "exact_duplicate_same_release" and families == {"local_copies"}:
        return "same_release_local_copy_duplicates"
    return None


def build_duplicate_cleanup_status(
    inventory: Mapping[str, Any],
    *,
    top_n: int = 8,
) -> dict[str, Any]:
    summary = inventory.get("summary") or {}
    duplicate_groups = inventory.get("duplicate_groups") or ()

    class_bytes: Counter[str] = Counter()
    class_groups: Counter[str] = Counter()
    root_bytes: Counter[str] = Counter()
    root_groups: Counter[str] = Counter()
    cohort_bytes: Counter[str] = Counter()
    cohort_groups: Counter[str] = Counter()
    cohort_examples: defaultdict[str, list[str]] = defaultdict(list)

    for group in duplicate_groups:
        if not isinstance(group, Mapping) or not group.get("reclaimable"):
            continue
        reclaimable_bytes = int(group.get("reclaimable_bytes") or 0)
        duplicate_class = str(group.get("duplicate_class") or "unknown")
        files = tuple(
            str(item.get("relative_path") or item.get("path") or "")
            for item in (group.get("files") or ())
            if isinstance(item, Mapping)
        )
        if not files:
            continue

        class_bytes[duplicate_class] += reclaimable_bytes
        class_groups[duplicate_class] += 1

        seen_roots: set[str] = set()
        for relative_path in files:
            root = _root_prefix(relative_path)
            if root and root not in seen_roots:
                root_bytes[root] += reclaimable_bytes
                root_groups[root] += 1
                seen_roots.add(root)

        cohort = _safe_first_label(group, files)
        if cohort:
            cohort_bytes[cohort] += reclaimable_bytes
            cohort_groups[cohort] += 1
            if len(cohort_examples[cohort]) < 3:
                cohort_examples[cohort].append(files[0])

    top_duplicate_classes = [
        {
            "duplicate_class": duplicate_class,
            "group_count": class_groups[duplicate_class],
            "reclaimable_bytes": class_bytes[duplicate_class],
        }
        for duplicate_class, _ in class_bytes.most_common(top_n)
    ]
    top_root_prefixes = [
        {
            "root_prefix": root_prefix,
            "group_count": root_groups[root_prefix],
            "reclaimable_bytes": root_bytes[root_prefix],
        }
        for root_prefix, _ in root_bytes.most_common(top_n)
    ]
    safe_first_cleanup_cohorts = [
        {
            "cohort_name": cohort_name,
            "group_count": cohort_groups[cohort_name],
            "reclaimable_bytes": cohort_bytes[cohort_name],
            "example_paths": cohort_examples[cohort_name],
        }
        for cohort_name, _ in cohort_bytes.most_common()
    ]

    return {
        "status_id": "duplicate-cleanup-status",
        "generated_at": inventory.get("generated_at"),
        "source_inventory": str(DEFAULT_INPUT_PATH.relative_to(ROOT)).replace("/", "\\"),
        "inventory_summary": {
            "scanned_root_count": summary.get("scanned_root_count"),
            "scanned_file_count": summary.get("scanned_file_count"),
            "duplicate_group_count": summary.get("duplicate_group_count"),
            "duplicate_file_count": summary.get("duplicate_file_count"),
            "reclaimable_file_count": summary.get("reclaimable_file_count"),
            "reclaimable_bytes": summary.get("reclaimable_bytes"),
            "partial_file_count": summary.get("partial_file_count"),
            "protected_file_count": summary.get("protected_file_count"),
        },
        "top_duplicate_classes": top_duplicate_classes,
        "top_root_prefixes": top_root_prefixes,
        "safe_first_cleanup_cohorts": safe_first_cleanup_cohorts,
    }


def render_duplicate_cleanup_status_markdown(payload: Mapping[str, Any]) -> str:
    summary = payload.get("inventory_summary") or {}
    lines = [
        "# Duplicate Cleanup Status",
        "",
        f"- Generated at: `{payload.get('generated_at') or 'unknown'}`",
        f"- Scanned files: `{summary.get('scanned_file_count')}`",
        f"- Duplicate groups: `{summary.get('duplicate_group_count')}`",
        f"- Reclaimable files: `{summary.get('reclaimable_file_count')}`",
        f"- Reclaimable bytes: `{summary.get('reclaimable_bytes')}`",
        f"- Protected files: `{summary.get('protected_file_count')}`",
        f"- Partial files excluded: `{summary.get('partial_file_count')}`",
        "",
        "## Top Duplicate Classes",
    ]
    for entry in payload.get("top_duplicate_classes") or ():
        lines.append(
            f"- `{entry['duplicate_class']}`: `{entry['group_count']}` groups, "
            f"`{entry['reclaimable_bytes']}` reclaimable bytes"
        )
    lines.extend(["", "## Top Root Prefixes"])
    for entry in payload.get("top_root_prefixes") or ():
        lines.append(
            f"- `{entry['root_prefix']}`: `{entry['group_count']}` groups, "
            f"`{entry['reclaimable_bytes']}` reclaimable bytes"
        )
    lines.extend(["", "## Safe-First Cleanup Cohorts"])
    for entry in payload.get("safe_first_cleanup_cohorts") or ():
        examples = ", ".join(f"`{item}`" for item in entry.get("example_paths") or ())
        lines.append(
            f"- `{entry['cohort_name']}`: `{entry['group_count']}` groups, "
            f"`{entry['reclaimable_bytes']}` reclaimable bytes"
            + (f"; examples: {examples}" if examples else "")
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--top-n", type=int, default=8)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    inventory = _load_json(args.input_json)
    payload = build_duplicate_cleanup_status(inventory, top_n=max(1, int(args.top_n)))
    _write_json(args.output_json, payload)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(
        render_duplicate_cleanup_status_markdown(payload),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
