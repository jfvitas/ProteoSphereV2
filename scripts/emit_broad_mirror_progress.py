from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "protein_data_scope" / "sources_manifest.json"
DEFAULT_SEED_ROOT = REPO_ROOT / "data" / "raw" / "protein_data_scope_seed"
DEFAULT_DOWNLOAD_LOCATION_AUDIT = (
    REPO_ROOT / "artifacts" / "status" / "download_location_audit_preview.json"
)
DEFAULT_JSON_OUTPUT = REPO_ROOT / "artifacts" / "status" / "broad_mirror_progress.json"
DEFAULT_MARKDOWN_OUTPUT = REPO_ROOT / "docs" / "reports" / "broad_mirror_progress.md"

HIGH_VALUE_CATEGORIES = {
    "interaction_network",
    "interaction_networks",
    "sequence_reference_backbone",
    "predicted_structures",
    "structure",
    "structure_sequence_crosswalks",
    "pathways_reactions_complexes",
    "nucleic_acid_reference",
    "bioactivity_chemistry",
    "protein_ligand_affinity",
    "motif",
    "enzyme_kinetics",
}
MEDIUM_VALUE_CATEGORIES = {
    "chemical_ontology",
    "ligands_modified_residues",
    "complexes",
    "domains_families_sites",
    "structural_classification",
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _expected_filenames(source: dict[str, Any]) -> list[str]:
    filenames: list[str] = []
    for item in source.get("top_level_files") or ():
        if not isinstance(item, dict):
            continue
        filename = str(item.get("filename") or "").strip()
        if filename:
            filenames.append(filename)
    return filenames


def _normalized_notes(source: dict[str, Any]) -> list[str]:
    notes = source.get("notes")
    if notes is None:
        return []
    if isinstance(notes, str):
        return [notes]
    if isinstance(notes, (list, tuple)):
        normalized: list[str] = []
        for note in notes:
            if note is None:
                continue
            text = str(note).strip()
            if text:
                normalized.append(text)
        return normalized
    text = str(notes).strip()
    return [text] if text else []


def _source_root(seed_root: Path, source_id: str) -> Path:
    return seed_root / source_id


def _source_file_maps(source_root: Path) -> tuple[dict[str, str], dict[str, list[str]]]:
    if not source_root.exists():
        return {}, {}
    exact_paths: dict[str, str] = {}
    basename_index: defaultdict[str, list[str]] = defaultdict(list)
    for child in sorted(
        source_root.rglob("*"),
        key=lambda item: item.relative_to(source_root).as_posix().casefold(),
    ):
        if not child.is_file() or child.name == "_source_metadata.json":
            continue
        relative_path = child.relative_to(source_root).as_posix()
        exact_paths[relative_path.casefold()] = relative_path
        basename_index[child.name.casefold()].append(relative_path)
    return exact_paths, dict(basename_index)


def _resolve_expected_path(
    expected_path: str,
    exact_paths: dict[str, str],
    basename_index: dict[str, list[str]],
) -> str | None:
    normalized = expected_path.replace("\\", "/").strip().casefold()
    if not normalized:
        return None
    if normalized in exact_paths:
        return exact_paths[normalized]
    basename = PurePosixPath(normalized).name
    candidates = basename_index.get(basename, [])
    if len(candidates) == 1:
        return candidates[0]
    return None


def _active_part_artifacts(source_root: Path) -> list[dict[str, Any]]:
    if not source_root.exists():
        return []
    artifacts: list[dict[str, Any]] = []
    for child in sorted(
        source_root.rglob("*"),
        key=lambda item: item.relative_to(source_root).as_posix().casefold(),
    ):
        if not child.is_file():
            continue
        lowered = child.name.casefold()
        if lowered.endswith(".part") or lowered.endswith(".partial"):
            artifacts.append(
                {
                    "filename": child.relative_to(source_root).as_posix(),
                    "size_bytes": child.stat().st_size,
                }
            )
    return artifacts


def _classify_expected_files(
    expected_files: list[str],
    exact_paths: dict[str, str],
    basename_index: dict[str, list[str]],
) -> tuple[list[str], list[str], list[str]]:
    present: list[str] = []
    partial: list[str] = []
    missing: list[str] = []
    for filename in expected_files:
        if _resolve_expected_path(filename, exact_paths, basename_index) is not None:
            present.append(filename)
            continue
        part_match = _resolve_expected_path(
            f"{filename}.part",
            exact_paths,
            basename_index,
        )
        partial_match = _resolve_expected_path(
            f"{filename}.partial",
            exact_paths,
            basename_index,
        )
        if part_match is not None or partial_match is not None:
            partial.append(filename)
            continue
        missing.append(filename)
    return present, partial, missing


def _value_tier(category: str) -> str:
    normalized = category.casefold()
    if normalized in HIGH_VALUE_CATEGORIES:
        return "high"
    if normalized in MEDIUM_VALUE_CATEGORIES:
        return "medium"
    return "support"


def _priority_rank(value_tier: str, coverage_percent: float) -> int:
    if coverage_percent >= 100.0:
        return 4
    if value_tier == "high":
        return 1
    if value_tier == "medium":
        return 2
    return 3


def _priority_label(priority_rank: int, value_tier: str) -> str:
    return {
        1: "P1 high-value gap",
        2: "P2 medium-value gap",
        3: "P3 support gap",
        4: "P4 complete",
    }.get(priority_rank, f"P{priority_rank} {value_tier}")


def _source_status(present_count: int, partial_count: int, expected_count: int) -> str:
    if expected_count == 0:
        return "empty"
    if present_count == expected_count:
        return "complete"
    if present_count > 0 or partial_count > 0:
        return "partial"
    return "missing"


def _location_audit_index(
    download_location_audit: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    if not isinstance(download_location_audit, dict):
        return {}
    source_summaries = {
        str(row.get("source_id") or "").strip(): row
        for row in download_location_audit.get("source_summaries") or []
        if isinstance(row, dict) and str(row.get("source_id") or "").strip()
    }
    indexed: dict[str, dict[str, Any]] = {}
    for row in download_location_audit.get("rows") or []:
        if not isinstance(row, dict):
            continue
        source_id = str(row.get("source_id") or "").strip()
        if not source_id:
            continue
        entry = indexed.setdefault(
            source_id,
            {
                "source_summary": source_summaries.get(source_id, {}),
                "rows": [],
            },
        )
        entry["rows"].append(row)
    return indexed


def _audit_active_part_artifacts(source_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for row in source_rows:
        for location in row.get("in_process_locations") or []:
            if not isinstance(location, dict):
                continue
            path = str(location.get("path") or "").strip()
            if not path:
                continue
            artifacts.append(
                {
                    "filename": path.replace("\\", "/"),
                    "size_bytes": location.get("size_bytes"),
                }
            )
    return artifacts


def _build_row_from_download_location_audit(
    *,
    source: dict[str, Any],
    expected_files: list[str],
    source_root: Path,
    audit_entry: dict[str, Any],
) -> dict[str, Any]:
    source_id = str(source.get("id") or "").strip()
    source_name = str(source.get("name") or source_id).strip()
    category = str(source.get("category") or "unknown").strip()
    value_tier = _value_tier(category)
    source_rows = [row for row in audit_entry.get("rows") or [] if isinstance(row, dict)]
    rows_by_filename = {
        str(row.get("filename") or "").strip(): row
        for row in source_rows
        if str(row.get("filename") or "").strip()
    }

    present_files: list[str] = []
    partial_files: list[str] = []
    missing_files: list[str] = []
    for filename in expected_files:
        row = rows_by_filename.get(filename, {})
        state = str(row.get("state") or "").strip()
        if state in {"downloaded", "downloaded_and_in_process"}:
            present_files.append(filename)
        if state in {"in_process", "downloaded_and_in_process"}:
            partial_files.append(filename)
        if state == "missing" or not state:
            missing_files.append(filename)

    expected_count = len(expected_files)
    present_count = len(present_files)
    partial_count = len(partial_files)
    missing_count = len(missing_files)
    coverage_percent = (
        round((present_count / expected_count * 100.0), 1) if expected_count else 100.0
    )
    priority_rank = _priority_rank(value_tier, coverage_percent)
    active_part_artifacts = _audit_active_part_artifacts(source_rows)
    active_part_bytes = sum(int(item.get("size_bytes") or 0) for item in active_part_artifacts)
    notes = _normalized_notes(source)
    source_summary = audit_entry.get("source_summary") or {}
    primary_root = str(source_summary.get("primary_root") or "").replace("\\", "/")
    overflow_completed = any(
        not str(location.get("path") or "").replace("\\", "/").startswith(primary_root)
        for row in source_rows
        for location in (row.get("final_locations") or [])
        if isinstance(location, dict)
    )
    if overflow_completed:
        notes.append("Cross-drive download authority is satisfied through the overflow root.")

    return {
        "source_id": source_id,
        "source_name": source_name,
        "category": category,
        "manual_review_required": bool(source.get("manual_review_required") is True),
        "notes": notes,
        "source_root": str(
            source_summary.get("primary_root") or _repo_relative(source_root)
        ).replace("\\", "/"),
        "expected_file_count": expected_count,
        "present_file_count": present_count,
        "partial_file_count": partial_count,
        "missing_file_count": missing_count,
        "active_part_file_count": len(active_part_artifacts),
        "active_part_bytes": active_part_bytes,
        "coverage_percent": coverage_percent,
        "priority_rank": priority_rank,
        "priority_label": _priority_label(priority_rank, value_tier),
        "estimated_value": value_tier if priority_rank < 4 else "complete",
        "status": _source_status(present_count, partial_count, expected_count),
        "present_files": present_files,
        "partial_files": partial_files,
        "missing_files": missing_files,
        "representative_missing_files": missing_files[:5],
        "representative_partial_files": partial_files[:5],
        "active_part_artifacts": active_part_artifacts,
        "authority": "download_location_audit_preview",
    }


def build_broad_mirror_progress(
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    seed_root: Path = DEFAULT_SEED_ROOT,
    download_location_audit_path: Path | None = DEFAULT_DOWNLOAD_LOCATION_AUDIT,
) -> dict[str, Any]:
    manifest = _read_json(manifest_path)
    sources = [item for item in manifest.get("sources") or () if isinstance(item, dict)]
    download_location_audit = (
        _read_json(download_location_audit_path)
        if download_location_audit_path is not None and download_location_audit_path.exists()
        else None
    )
    audit_index = _location_audit_index(download_location_audit)

    source_rows: list[dict[str, Any]] = []
    top_missing_files: list[dict[str, Any]] = []
    total_expected_files = 0
    total_present_files = 0
    total_partial_files = 0
    total_missing_files = 0
    total_active_part_files = 0
    total_active_part_bytes = 0

    for source in sources:
        source_id = str(source.get("id") or "").strip()
        if not source_id:
            continue
        source_name = str(source.get("name") or source_id).strip()
        category = str(source.get("category") or "unknown").strip()
        expected_files = _expected_filenames(source)
        source_root = _source_root(seed_root, source_id)
        audit_entry = audit_index.get(source_id)
        if audit_entry is not None:
            row = _build_row_from_download_location_audit(
                source=source,
                expected_files=expected_files,
                source_root=source_root,
                audit_entry=audit_entry,
            )
            active_part_artifacts = row["active_part_artifacts"]
            present_files = row["present_files"]
            partial_files = row["partial_files"]
            missing_files = row["missing_files"]
            expected_count = row["expected_file_count"]
            present_count = row["present_file_count"]
            partial_count = row["partial_file_count"]
            missing_count = row["missing_file_count"]
            coverage_percent = row["coverage_percent"]
            value_tier = _value_tier(category)
            priority_rank = row["priority_rank"]
            active_part_bytes = row["active_part_bytes"]
            source_rows.append(row)
        else:
            exact_paths, basename_index = _source_file_maps(source_root)
            active_part_artifacts = _active_part_artifacts(source_root)
            present_files, partial_files, missing_files = _classify_expected_files(
                expected_files,
                exact_paths,
                basename_index,
            )
            expected_count = len(expected_files)
            present_count = len(present_files)
            partial_count = len(partial_files)
            missing_count = len(missing_files)
            coverage_percent = (
                round((present_count / expected_count * 100.0), 1) if expected_count else 100.0
            )
            value_tier = _value_tier(category)
            priority_rank = _priority_rank(value_tier, coverage_percent)
            status = _source_status(present_count, partial_count, expected_count)
            active_part_bytes = sum(int(item["size_bytes"]) for item in active_part_artifacts)
            source_rows.append(
                {
                    "source_id": source_id,
                    "source_name": source_name,
                    "category": category,
                    "manual_review_required": bool(source.get("manual_review_required") is True),
                    "notes": _normalized_notes(source),
                    "source_root": _repo_relative(source_root),
                    "expected_file_count": expected_count,
                    "present_file_count": present_count,
                    "partial_file_count": partial_count,
                    "missing_file_count": missing_count,
                    "active_part_file_count": len(active_part_artifacts),
                    "active_part_bytes": active_part_bytes,
                    "coverage_percent": coverage_percent,
                    "priority_rank": priority_rank,
                    "priority_label": _priority_label(priority_rank, value_tier),
                    "estimated_value": value_tier if priority_rank < 4 else "complete",
                    "status": status,
                    "present_files": present_files,
                    "partial_files": partial_files,
                    "missing_files": missing_files,
                    "representative_missing_files": missing_files[:5],
                    "representative_partial_files": partial_files[:5],
                    "active_part_artifacts": active_part_artifacts,
                }
            )
        total_expected_files += expected_count
        total_present_files += present_count
        total_partial_files += partial_count
        total_missing_files += missing_count
        total_active_part_files += len(active_part_artifacts)
        total_active_part_bytes += active_part_bytes
        for filename in missing_files:
            top_missing_files.append(
                {
                    "source_id": source_id,
                    "source_name": source_name,
                    "category": category,
                    "priority_rank": priority_rank,
                    "estimated_value": value_tier,
                    "filename": filename,
                }
            )

    source_rows.sort(
        key=lambda row: (
            row["priority_rank"],
            -row["missing_file_count"],
            row["coverage_percent"],
            row["source_id"].casefold(),
        )
    )
    top_missing_files.sort(
        key=lambda row: (
            row["priority_rank"],
            row["estimated_value"],
            row["source_id"].casefold(),
            row["filename"].casefold(),
        )
    )
    top_priority_missing_files = top_missing_files[:20]

    source_status_counts = Counter(row["status"] for row in source_rows)
    priority_counts = Counter(str(row["priority_rank"]) for row in source_rows)
    value_tier_counts = Counter(row["estimated_value"] for row in source_rows)
    incomplete_sources = [row for row in source_rows if row["status"] != "complete"]
    complete_sources = [row for row in source_rows if row["status"] == "complete"]

    return {
        "schema_id": "proteosphere-broad-mirror-progress-2026-03-30",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "complete",
        "inputs": {
            "manifest_path": _repo_relative(manifest_path),
            "seed_root": _repo_relative(seed_root),
            "download_location_audit_path": (
                _repo_relative(download_location_audit_path)
                if (
                    download_location_audit_path is not None
                    and download_location_audit_path.exists()
                )
                else None
            ),
        },
        "summary": {
            "source_count": len(source_rows),
            "source_status_counts": dict(sorted(source_status_counts.items())),
            "priority_counts": dict(sorted(priority_counts.items(), key=lambda item: int(item[0]))),
            "value_tier_counts": dict(sorted(value_tier_counts.items())),
            "total_expected_files": total_expected_files,
            "total_present_files": total_present_files,
            "total_partial_files": total_partial_files,
            "total_missing_files": total_missing_files,
            "total_active_part_files": total_active_part_files,
            "total_active_part_bytes": total_active_part_bytes,
            "file_coverage_percent": round(
                (total_present_files / total_expected_files * 100.0), 1
            )
            if total_expected_files
            else 100.0,
            "incomplete_source_count": len(incomplete_sources),
            "complete_source_count": len(complete_sources),
            "top_gap_sources": [
                row["source_id"] for row in sorted(
                    incomplete_sources,
                    key=lambda row: (
                        row["priority_rank"],
                        -row["missing_file_count"],
                        row["coverage_percent"],
                        row["source_id"].casefold(),
                    ),
                )[:10]
            ],
        },
        "sources": source_rows,
        "top_missing_files": top_missing_files,
        "top_priority_missing_files": top_priority_missing_files,
    }


def _format_truncated(values: list[str], *, limit: int = 5) -> str:
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
        "# Broad Mirror Progress",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Manifest: `{payload['inputs']['manifest_path']}`",
        f"- Seed root: `{payload['inputs']['seed_root']}`",
        f"- Sources tracked: `{summary['source_count']}`",
        f"- File coverage: `{summary['total_present_files']}/{summary['total_expected_files']}`",
        f"- Coverage percent: `{summary['file_coverage_percent']}%`",
        f"- Complete sources: `{summary['complete_source_count']}`",
        f"- Incomplete sources: `{summary['incomplete_source_count']}`",
        f"- Missing files: `{summary['total_missing_files']}`",
        f"- Partial stubs: `{summary['total_partial_files']}`",
        f"- Active `.part` files: `{summary['total_active_part_files']}`",
        f"- Active `.part` bytes: `{summary['total_active_part_bytes']}`",
        "",
        "## Priority Overview",
        "",
    ]
    noted_sources = [row for row in payload["sources"] if row.get("notes")]
    for priority_rank in (1, 2, 3, 4):
        group = [row for row in payload["sources"] if row["priority_rank"] == priority_rank]
        if not group:
            continue
        group_title = group[0]["priority_label"]
        lines.append(f"### {group_title}")
        lines.append("")
        lines.append(
            "| Source | Status | Value | Coverage | Missing | Partial | "
            "Representative missing files |"
        )
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for row in group:
            lines.append(
                "| "
                + f"`{row['source_id']}` | "
                + f"{row['status']} | "
                + f"{row['estimated_value']} | "
                + f"{row['coverage_percent']}% | "
                + f"{row['missing_file_count']} | "
                + f"{row['partial_file_count']} | "
                + f"{_format_truncated(row['representative_missing_files'])} |"
            )
        lines.append("")
    if noted_sources:
        lines.append("## Source Notes")
        lines.append("")
        for row in noted_sources:
            lines.append(f"- `{row['source_id']}`: {_format_truncated(row['notes'], limit=10)}")
        lines.append("")
    if payload["top_priority_missing_files"]:
        lines.append("## Missing File Index")
        lines.append("")
        grouped: dict[str, list[str]] = defaultdict(list)
        for item in payload["top_priority_missing_files"]:
            grouped[item["source_id"]].append(item["filename"])
        for row in payload["sources"]:
            if row["source_id"] not in grouped:
                continue
            lines.append(
                f"- `{row['source_id']}`: {_format_truncated(grouped[row['source_id']], limit=20)}"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit broad mirror progress for the seed mirror.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--seed-root", type=Path, default=DEFAULT_SEED_ROOT)
    parser.add_argument(
        "--download-location-audit",
        type=Path,
        default=DEFAULT_DOWNLOAD_LOCATION_AUDIT,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-markdown", action="store_true")
    args = parser.parse_args(argv)

    payload = build_broad_mirror_progress(
        manifest_path=args.manifest,
        seed_root=args.seed_root,
        download_location_audit_path=args.download_location_audit,
    )
    _write_json(args.output, payload)
    if not args.no_markdown:
        _write_text(args.markdown_output, render_markdown(payload))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "Broad mirror progress exported: "
            f"sources={payload['summary']['source_count']} "
            f"coverage={payload['summary']['file_coverage_percent']}% "
            f"missing_files={payload['summary']['total_missing_files']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
