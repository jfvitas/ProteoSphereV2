from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "duplicate_storage_inventory.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "duplicate_storage_inventory.md"
DEFAULT_SCAN_ROOTS = (
    REPO_ROOT / "data" / "raw" / "protein_data_scope_seed",
    REPO_ROOT / "data" / "raw" / "local_copies",
    REPO_ROOT / "data" / "raw" / "local_registry",
    REPO_ROOT / "data" / "raw" / "bootstrap_runs",
    REPO_ROOT / "data" / "packages",
)
PROTECTED_PATHS = (
    REPO_ROOT / "data" / "canonical" / "LATEST.json",
    REPO_ROOT / "data" / "packages" / "LATEST.json",
    REPO_ROOT / "data" / "raw" / "bootstrap_runs" / "LATEST.json",
    REPO_ROOT / "data" / "raw" / "local_registry_runs" / "LATEST.json",
)
PARTIAL_SUFFIXES = (".part", ".partial", ".tmp")
ARCHIVE_SUFFIXES = (
    ".zip",
    ".tar",
    ".gz",
    ".tgz",
    ".bz2",
    ".xz",
    ".7z",
    ".rar",
)


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        parts = path.parts
        for anchor in ("data", "artifacts", "docs", "scripts", "tests"):
            if anchor in parts:
                return str(Path(*parts[parts.index(anchor) :]))
        return str(path)


def _iter_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    if root.is_file():
        return [root]
    return [path for path in root.rglob("*") if path.is_file()]


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _root_role(path: Path) -> str:
    rendered = _display_path(path).replace("\\", "/").casefold()
    if "data/raw/protein_data_scope_seed/" in f"{rendered}/" or rendered.endswith(
        "data/raw/protein_data_scope_seed"
    ):
        return "source_of_record"
    if "data/raw/local_copies/" in f"{rendered}/" or rendered.endswith("data/raw/local_copies"):
        return "mirror_copy"
    if "data/raw/local_registry/" in f"{rendered}/" or rendered.endswith("data/raw/local_registry"):
        return "registry_snapshot"
    if "data/raw/bootstrap_runs/" in f"{rendered}/" or rendered.endswith("data/raw/bootstrap_runs"):
        return "run_manifest"
    if "data/packages/" in f"{rendered}/" or rendered.endswith("data/packages"):
        return "derived_output"
    return "other"


def _is_partial(path: Path) -> bool:
    lower = path.name.casefold()
    return any(lower.endswith(suffix) for suffix in PARTIAL_SUFFIXES)


def _is_protected(path: Path) -> bool:
    rendered = _display_path(path).replace("\\", "/")
    protected = {
        "data/canonical/LATEST.json",
        "data/packages/LATEST.json",
        "data/raw/bootstrap_runs/LATEST.json",
        "data/raw/local_registry_runs/LATEST.json",
    }
    return rendered in protected


def _archive_like(path: Path) -> bool:
    lower = path.name.casefold()
    return any(lower.endswith(suffix) for suffix in ARCHIVE_SUFFIXES)


def _cheap_signature(path: Path, chunk_size: int = 65536) -> str:
    hasher = hashlib.sha256()
    size = path.stat().st_size
    hasher.update(str(size).encode("utf-8"))
    with path.open("rb") as handle:
        head = handle.read(chunk_size)
        hasher.update(head)
        if size > chunk_size:
            offset = max(size - chunk_size, 0)
            handle.seek(offset)
            tail = handle.read(chunk_size)
            hasher.update(tail)
    return hasher.hexdigest()


def _full_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(chunk_size)
            if not block:
                break
            hasher.update(block)
    return hasher.hexdigest()


@dataclass(frozen=True, slots=True)
class InventoryEntry:
    path: Path
    root_role: str
    size_bytes: int
    relative_path: str
    file_name: str
    extension: str
    is_partial: bool
    is_protected: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": _display_path(self.path),
            "root_role": self.root_role,
            "size_bytes": self.size_bytes,
            "relative_path": self.relative_path,
            "file_name": self.file_name,
            "extension": self.extension,
            "is_partial": self.is_partial,
            "is_protected": self.is_protected,
        }


def _classify_duplicate_group(entries: list[InventoryEntry]) -> tuple[str, bool, str]:
    roles = {entry.root_role for entry in entries}
    if any(entry.is_protected for entry in entries):
        return ("exact_duplicate_cross_location", False, "protected_surface_present")
    if any(entry.root_role == "derived_output" for entry in entries):
        return ("derived_duplicate", False, "derived_outputs_require_separate_retention")
    if any(entry.is_partial for entry in entries):
        return ("unsafe_near_duplicate", False, "partial_transfer_present")
    if _archive_like(entries[0].path):
        return ("equivalent_archive_copy", True, "archive_payload_is_byte_identical")
    if len(roles) > 1:
        return ("exact_duplicate_cross_location", True, "same_content_across_multiple_roots")
    return ("exact_duplicate_same_release", True, "same_content_within_same_root_role")


def build_duplicate_storage_inventory(
    *,
    scan_roots: tuple[Path, ...] = DEFAULT_SCAN_ROOTS,
) -> dict[str, Any]:
    entries: list[InventoryEntry] = []
    for root in scan_roots:
        for path in _iter_files(root):
            stat = path.stat()
            entries.append(
                InventoryEntry(
                    path=path,
                    root_role=_root_role(path),
                    size_bytes=stat.st_size,
                    relative_path=_display_path(path),
                    file_name=path.name,
                    extension=path.suffix.casefold(),
                    is_partial=_is_partial(path),
                    is_protected=_is_protected(path),
                )
            )

    size_buckets: dict[int, list[InventoryEntry]] = defaultdict(list)
    for entry in entries:
        size_buckets[entry.size_bytes].append(entry)

    candidate_entries = [
        bucket
        for bucket in size_buckets.values()
        if len(bucket) > 1 and not all(entry.is_partial for entry in bucket)
    ]

    cheap_buckets: dict[tuple[int, str], list[InventoryEntry]] = defaultdict(list)
    for bucket in candidate_entries:
        for entry in bucket:
            if entry.is_partial:
                continue
            signature = _cheap_signature(entry.path)
            cheap_buckets[(entry.size_bytes, signature)].append(entry)

    full_hash_buckets: dict[str, list[InventoryEntry]] = defaultdict(list)
    for bucket in cheap_buckets.values():
        if len(bucket) < 2:
            continue
        for entry in bucket:
            full_hash_buckets[_full_sha256(entry.path)].append(entry)

    duplicate_groups: list[dict[str, Any]] = []
    reclaimable_bytes = 0
    reclaimable_file_count = 0
    duplicate_file_count = 0
    for digest, bucket in sorted(full_hash_buckets.items(), key=lambda item: item[0]):
        if len(bucket) < 2:
            continue
        duplicate_file_count += len(bucket)
        duplicate_class, reclaimable, rationale = _classify_duplicate_group(bucket)
        bucket = sorted(bucket, key=lambda entry: entry.relative_path.casefold())
        reclaimable_group_bytes = bucket[0].size_bytes * (len(bucket) - 1) if reclaimable else 0
        reclaimable_bytes += reclaimable_group_bytes
        reclaimable_file_count += len(bucket) - 1 if reclaimable else 0
        duplicate_groups.append(
            {
                "sha256": digest,
                "duplicate_class": duplicate_class,
                "group_file_count": len(bucket),
                "size_bytes": bucket[0].size_bytes,
                "reclaimable": reclaimable,
                "reclaimable_bytes": reclaimable_group_bytes,
                "rationale": rationale,
                "root_roles": sorted({entry.root_role for entry in bucket}),
                "files": [entry.to_dict() for entry in bucket],
            }
        )

    partial_files = [entry.to_dict() for entry in entries if entry.is_partial]
    protected_files = [entry.to_dict() for entry in entries if entry.is_protected]

    summary = {
        "scanned_root_count": len(scan_roots),
        "scanned_file_count": len(entries),
        "candidate_size_bucket_count": len(candidate_entries),
        "duplicate_group_count": len(duplicate_groups),
        "duplicate_file_count": duplicate_file_count,
        "reclaimable_file_count": reclaimable_file_count,
        "reclaimable_bytes": reclaimable_bytes,
        "partial_file_count": len(partial_files),
        "protected_file_count": len(protected_files),
    }

    top_groups = sorted(
        duplicate_groups,
        key=lambda group: (
            int(group["reclaimable_bytes"]),
            int(group["group_file_count"]),
            str(group["sha256"]),
        ),
        reverse=True,
    )[:25]

    return {
        "schema_id": "proteosphere-duplicate-storage-inventory-2026-04-01",
        "generated_at": _utc_now().isoformat(),
        "scan_roots": [_display_path(path) for path in scan_roots],
        "summary": summary,
        "top_duplicate_groups": top_groups,
        "duplicate_groups": duplicate_groups,
        "partial_files": partial_files[:200],
        "protected_files": protected_files,
        "notes": [
            "This artifact is read-only and does not delete, relink, or rewrite files.",
            "Duplicate groups require full SHA-256 identity, not just path or size similarity.",
            "Protected latest surfaces and partial transfer files are never marked reclaimable.",
            "Reclaimable bytes are estimates only until manifests and downstream references are validated.",
        ],
    }


def render_duplicate_storage_inventory_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    top_groups = payload.get("top_duplicate_groups") or []
    lines = [
        "# Duplicate Storage Inventory",
        "",
        f"- Generated at: `{_normalize_text(payload.get('generated_at'))}`",
        f"- Machine note: [`artifacts/status/duplicate_storage_inventory.json`](/D:/documents/ProteoSphereV2/artifacts/status/duplicate_storage_inventory.json)",
        "",
        "## Summary",
        "",
        f"- Scanned files: `{summary.get('scanned_file_count', 0)}`",
        f"- Duplicate groups: `{summary.get('duplicate_group_count', 0)}`",
        f"- Duplicate files: `{summary.get('duplicate_file_count', 0)}`",
        f"- Reclaimable files (estimate): `{summary.get('reclaimable_file_count', 0)}`",
        f"- Reclaimable bytes (estimate): `{summary.get('reclaimable_bytes', 0)}`",
        f"- Partial files excluded from reclamation: `{summary.get('partial_file_count', 0)}`",
        f"- Protected latest files excluded from reclamation: `{summary.get('protected_file_count', 0)}`",
        "",
        "## Top Reclaimable Groups",
        "",
    ]
    if not top_groups:
        lines.append("- No exact duplicate groups were identified under the configured roots.")
    else:
        for group in top_groups[:10]:
            files = group.get("files") or []
            lead = files[0]["path"] if files else "unknown"
            lines.append(
                f"- `{group.get('duplicate_class')}`: `{group.get('group_file_count')}` files, "
                f"`{group.get('reclaimable_bytes')}` reclaimable bytes, lead file `{lead}`"
            )
    lines.extend(
        [
            "",
            "## Safety Notes",
            "",
            "- This report is inventory-only and performs no cleanup.",
            "- Exact duplicates are defined by full SHA-256 identity only.",
            "- Partial transfer files and protected latest pointers are excluded from reclamation.",
            "- Any future cleanup must validate manifests, canonical rebuilds, and packet planning after changes.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a read-only duplicate-file inventory across ProteoSphere storage roots."
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument(
        "--scan-root",
        action="append",
        dest="scan_roots",
        type=Path,
        default=None,
        help="Additional or replacement scan roots. Repeat for multiple roots.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    scan_roots = tuple(args.scan_roots) if args.scan_roots else DEFAULT_SCAN_ROOTS
    payload = build_duplicate_storage_inventory(scan_roots=scan_roots)
    markdown = render_duplicate_storage_inventory_markdown(payload)
    _write_json(args.output_json, payload)
    _write_text(args.output_md, markdown)
    print(
        "Duplicate storage inventory exported: "
        f"groups={payload['summary']['duplicate_group_count']} "
        f"reclaimable_bytes={payload['summary']['reclaimable_bytes']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
