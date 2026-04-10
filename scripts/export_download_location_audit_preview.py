from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.tasklib import load_json, save_json  # noqa: E402

DEFAULT_MANIFEST_PATH = REPO_ROOT / "protein_data_scope" / "sources_manifest.json"
DEFAULT_PRIMARY_SEED_ROOT = REPO_ROOT / "data" / "raw" / "protein_data_scope_seed"
DEFAULT_OVERFLOW_SEED_ROOT = (
    Path("C:/CSTEMP/ProteoSphereV2_overflow/protein_data_scope_seed")
)
DEFAULT_FAILED_SNAPSHOT_ROOT = (
    Path("C:/CSTEMP/ProteoSphereV2_overflow/failed_uniprot_snapshots")
)
DEFAULT_OUTPUT_PATH = (
    REPO_ROOT / "artifacts" / "status" / "download_location_audit_preview.json"
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _normalize_sources(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    sources = manifest.get("sources")
    if not isinstance(sources, list):
        return []
    return [item for item in sources if isinstance(item, dict)]


def _normalize_files(source: dict[str, Any]) -> list[dict[str, Any]]:
    files = source.get("top_level_files")
    if not isinstance(files, list):
        return []
    return [item for item in files if isinstance(item, dict)]


def _snapshot_matches(source_id: str, filename: str, path: Path) -> bool:
    if not path.is_file():
        return False
    name = path.name
    if not name.startswith(f"{filename}.failed_snapshot_"):
        return False
    return source_id == "uniprot" and filename == "uniref100.xml.gz"


def _find_failed_snapshots(
    source_id: str,
    filename: str,
    *,
    failed_snapshot_root: Path,
) -> list[Path]:
    if not failed_snapshot_root.exists():
        return []
    matches = [
        path
        for path in failed_snapshot_root.iterdir()
        if _snapshot_matches(source_id, filename, path)
    ]
    return sorted(matches)


def _path_payload(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path).replace("\\", "/"),
        "size_bytes": stat.st_size,
        "last_write_time": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
    }


def _collect_row(
    source_id: str,
    source_name: str,
    category: str | None,
    filename: str,
    url: str | None,
    *,
    primary_seed_root: Path,
    overflow_seed_root: Path,
    failed_snapshot_root: Path,
) -> dict[str, Any]:
    primary_final = primary_seed_root / source_id / filename
    primary_part = primary_seed_root / source_id / f"{filename}.part"
    overflow_final = overflow_seed_root / source_id / filename
    overflow_part = overflow_seed_root / source_id / f"{filename}.part"
    failed_snapshots = _find_failed_snapshots(
        source_id,
        filename,
        failed_snapshot_root=failed_snapshot_root,
    )

    final_locations = [
        _path_payload(path)
        for path in (primary_final, overflow_final)
        if path.exists() and path.is_file()
    ]
    in_process_locations = [
        _path_payload(path)
        for path in (primary_part, overflow_part)
        if path.exists() and path.is_file()
    ]
    failed_snapshot_locations = [_path_payload(path) for path in failed_snapshots]

    if in_process_locations and final_locations:
        state = "downloaded_and_in_process"
    elif in_process_locations:
        state = "in_process"
    elif final_locations:
        state = "downloaded"
    else:
        state = "missing"

    primary_location = None
    if in_process_locations:
        primary_location = in_process_locations[0]["path"]
    elif final_locations:
        primary_location = final_locations[0]["path"]

    return {
        "source_id": source_id,
        "source_name": source_name,
        "category": category,
        "filename": filename,
        "url": url,
        "state": state,
        "primary_location": primary_location,
        "final_locations": final_locations,
        "in_process_locations": in_process_locations,
        "failed_snapshot_locations": failed_snapshot_locations,
        "has_failed_snapshot": bool(failed_snapshot_locations),
        "accounted_for": state != "missing",
    }


def build_download_location_audit_preview(
    manifest: dict[str, Any],
    *,
    primary_seed_root: Path = DEFAULT_PRIMARY_SEED_ROOT,
    overflow_seed_root: Path = DEFAULT_OVERFLOW_SEED_ROOT,
    failed_snapshot_root: Path = DEFAULT_FAILED_SNAPSHOT_ROOT,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    observed_at = observed_at or _utc_now()
    rows: list[dict[str, Any]] = []
    source_summaries: list[dict[str, Any]] = []

    for source in _normalize_sources(manifest):
        source_id = str(source.get("id") or "").strip()
        source_name = str(source.get("name") or source_id).strip()
        category = source.get("category")
        source_rows = [
            _collect_row(
                source_id,
                source_name,
                category,
                str(file_row.get("filename") or "").strip(),
                str(file_row.get("url") or "").strip() or None,
                primary_seed_root=primary_seed_root,
                overflow_seed_root=overflow_seed_root,
                failed_snapshot_root=failed_snapshot_root,
            )
            for file_row in _normalize_files(source)
        ]
        rows.extend(source_rows)

        downloaded_count = sum(1 for row in source_rows if row["state"] == "downloaded")
        in_process_count = sum(
            1
            for row in source_rows
            if row["state"] in {"in_process", "downloaded_and_in_process"}
        )
        missing_count = sum(1 for row in source_rows if row["state"] == "missing")
        source_state = (
            "complete"
            if missing_count == 0 and in_process_count == 0
            else "active"
            if missing_count == 0 and in_process_count > 0
            else "missing"
        )
        source_summaries.append(
            {
                "source_id": source_id,
                "source_name": source_name,
                "category": category,
                "expected_file_count": len(source_rows),
                "downloaded_count": downloaded_count,
                "in_process_count": in_process_count,
                "missing_count": missing_count,
                "source_state": source_state,
                "primary_root": str(primary_seed_root / source_id).replace("\\", "/"),
                "overflow_root": str(overflow_seed_root / source_id).replace("\\", "/"),
            }
        )

    downloaded_count = sum(1 for row in rows if row["state"] == "downloaded")
    in_process_count = sum(
        1 for row in rows if row["state"] in {"in_process", "downloaded_and_in_process"}
    )
    missing_count = sum(1 for row in rows if row["state"] == "missing")

    return {
        "artifact_id": "download_location_audit_preview",
        "schema_id": "proteosphere-download-location-audit-preview-2026-04-04",
        "status": "report_only",
        "generated_at": observed_at.isoformat(),
        "summary": {
            "wanted_file_count": len(rows),
            "downloaded_count": downloaded_count,
            "in_process_count": in_process_count,
            "missing_count": missing_count,
            "accounted_for_count": downloaded_count + in_process_count,
            "all_wanted_files_accounted_for": missing_count == 0,
            "non_mutating": True,
            "report_only": True,
        },
        "roots": {
            "primary_seed_root": str(primary_seed_root).replace("\\", "/"),
            "overflow_seed_root": str(overflow_seed_root).replace("\\", "/"),
            "failed_snapshot_root": str(failed_snapshot_root).replace("\\", "/"),
        },
        "source_summaries": source_summaries,
        "rows": rows,
        "next_suggested_action": (
            "Treat files with final locations as downloaded and files with .part locations "
            "as actively in process, regardless of older stale procurement artifacts."
        ),
        "truth_boundary": {
            "summary": (
                "This is a report-only location audit built from the broad-mirror manifest "
                "and live filesystem checks across the primary and overflow download roots."
            ),
            "report_only": True,
            "non_mutating": True,
            "filesystem_observed": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a location-aware audit of wanted broad-mirror downloads."
    )
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--primary-seed-root", type=Path, default=DEFAULT_PRIMARY_SEED_ROOT)
    parser.add_argument(
        "--overflow-seed-root",
        type=Path,
        default=DEFAULT_OVERFLOW_SEED_ROOT,
    )
    parser.add_argument(
        "--failed-snapshot-root",
        type=Path,
        default=DEFAULT_FAILED_SNAPSHOT_ROOT,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_download_location_audit_preview(
        load_json(args.manifest_path, {}),
        primary_seed_root=args.primary_seed_root,
        overflow_seed_root=args.overflow_seed_root,
        failed_snapshot_root=args.failed_snapshot_root,
    )
    save_json(args.output, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
